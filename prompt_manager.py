import gspread
import os
from dotenv import load_dotenv
import logging
import re
from google.oauth2 import service_account
import json
import base64

# 設置日誌
logger = logging.getLogger(__name__)

class GoogleSheetPromptManager:
    def _is_valid_base64(self, s):
        """檢查字串是否為有效的 base64 編碼"""
        try:
            if isinstance(s, str):
                # 檢查字串是否只包含 base64 字符
                import string
                valid_chars = string.ascii_letters + string.digits + '+/='
                if not all(c in valid_chars for c in s.strip()):
                    return False
                # 嘗試解碼
                base64.b64decode(s)
                return True
        except Exception:
            return False
        return False

    def _log_environment_info(self):
        """記錄環境資訊，協助 Railway 部署診斷"""
        try:
            logger.info("=== 環境診斷資訊 ===")
            logger.info(f"PROMPT_MANAGER: {'已設定' if os.getenv('PROMPT_MANAGER') else '未設定'}")
            logger.info(f"SERVICE_ACCOUNT_BASE64: {'已設定' if os.getenv('SERVICE_ACCOUNT_BASE64') else '未設定'}")
            
            # 檢查是否在 Railway 環境
            railway_env = os.getenv('RAILWAY_ENVIRONMENT')
            if railway_env:
                logger.info(f"Railway 環境: {railway_env}")
            
            # 記錄時區資訊
            import datetime
            logger.info(f"系統時間: {datetime.datetime.now()}")
            logger.info(f"UTC 時間: {datetime.datetime.utcnow()}")
            
        except Exception as e:
            logger.warning(f"環境診斷記錄失敗: {str(e)}")

    def __init__(self, spreadsheet_name: str = None, sheet_index: int = 0):
        load_dotenv(override=True)
        self.sheet_id = spreadsheet_name or os.getenv('PROMPT_MANAGER')
        
        if not self.sheet_id:
            raise ValueError("未設定 PROMPT_MANAGER 環境變數")
        
        # 更新權限範圍
        self.SCOPES = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive',
            'https://spreadsheets.google.com/feeds'
        ]
        self.SPREADSHEET_ID = os.getenv('GOOGLE_SHEETS_ID')
        
        # 延遲初始化 - 先不連接 Google API
        self.target_sheet = None
        self.credentials = None
        self.prompts = {}
        self._initialization_error = None
        
        logger.info(f"✅ Prompt Manager 已建立 (延遲連接模式)，Sheet ID: {self.sheet_id}")

    def _initialize_connection(self):
        """延遲初始化 Google API 連接"""
        if self.target_sheet is not None:
            return  # 已經初始化
        
        if self._initialization_error is not None:
            raise self._initialization_error  # 之前初始化失敗
        
        try:
            # 從環境變數讀取 base64 編碼的 service account
            base64_content = os.getenv('SERVICE_ACCOUNT_BASE64')
            if not base64_content:
                raise ValueError("未設定 SERVICE_ACCOUNT_BASE64 環境變數")
            
            # 驗證 base64 格式
            if not self._is_valid_base64(base64_content):
                raise ValueError("SERVICE_ACCOUNT_BASE64 不是有效的 base64 編碼")
            
            # 解碼 base64 內容
            try:
                decoded_content = base64.b64decode(base64_content).decode('utf-8')
                service_account_info = json.loads(decoded_content)
            except Exception as e:
                raise ValueError(f"SERVICE_ACCOUNT_BASE64 解碼失敗: {str(e)}")
            
            # 驗證服務帳戶資訊格式
            required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
            missing_fields = [field for field in required_fields if field not in service_account_info]
            if missing_fields:
                raise ValueError(f"服務帳戶資訊缺少必要欄位: {missing_fields}")
            
            if service_account_info.get('type') != 'service_account':
                raise ValueError("這不是有效的服務帳戶金鑰檔案")
            
            self.credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=self.SCOPES
            )
            
            client = gspread.authorize(self.credentials)
            
            # 直接開啟指定 ID 的試算表，避免使用 openall() 造成的認證問題
            try:
                self.target_sheet = client.open_by_key(self.sheet_id)
                logger.info(f"✅ 成功連接到試算表: {self.target_sheet.title}")
            except Exception as e:
                raise ValueError(f"無法開啟試算表 ID {self.sheet_id}: {str(e)}")
            
            # Railway 部署環境檢查
            self._log_environment_info()
            
            logger.info(f"✅ 成功初始化 Google API 連接")
            
        except Exception as e:
            logger.error(f"❌ Google API 連接失敗: {str(e)}")
            # 提供更詳細的錯誤訊息協助 Railway 部署診斷
            if "Invalid JWT Signature" in str(e) or "invalid_grant" in str(e):
                logger.error("💡 建議檢查項目:")
                logger.error("   1. SERVICE_ACCOUNT_BASE64 環境變數是否正確設定")
                logger.error("   2. Google 服務帳戶金鑰是否已過期 - 需要重新生成")
                logger.error("   3. 服務帳戶是否有 Google Sheets 和 Drive 權限")
                logger.error("   4. 時間同步問題 (Railway 伺服器時間)")
                logger.error("💡 請執行 diagnose_service_account.py 進行詳細診斷")
            
            # 將錯誤儲存，避免重複嘗試
            self._initialization_error = e
            raise

    def _load_prompts_if_needed(self):
        """如果 prompts 為空，則從 Google Sheets 載入"""
        if not self.prompts:
            try:
                # 確保 Google API 連接已初始化
                self._initialize_connection()
                
                # 使用第一個工作表
                sheet = self.target_sheet.worksheets()[0]
                records = sheet.get_all_records()
                
                # 清理提示詞中的換行符號
                self.prompts = {}
                for row in records:
                    prompt_id = row['prompt_id']
                    prompt_text = row['prompt_text']
                    # 清理換行符號和空格
                    prompt_text = prompt_text.replace('\r\n', ' ').replace('\n', ' ').strip()
                    self.prompts[prompt_id] = prompt_text
                
                logger.info(f"✅ 成功載入 {len(self.prompts)} 個提示詞")
            except Exception as e:
                logger.error(f"❌ 載入提示詞失敗: {str(e)}")
                raise

    def get_prompt(self, prompt_id: str) -> str:
        # 如果 prompts 為空，先載入
        self._load_prompts_if_needed()
        
        prompt = self.prompts.get(prompt_id)
        if prompt is None:
            logger.warning(f"❌ 找不到提示詞: {prompt_id}")
        return prompt

    def get_prompt_and_format(self, prompt_id: str, **kwargs) -> str:
        raw = self.get_prompt(prompt_id)
        if not raw:
            raise ValueError(f"Prompt '{prompt_id}' not found.")
        try:
            # 清理參數中的換行符號和空格
            cleaned_kwargs = {}
            for key, value in kwargs.items():
                if isinstance(value, (list, dict)):
                    cleaned_kwargs[key] = str(value)
                elif value is None:
                    cleaned_kwargs[key] = ""
                else:
                    cleaned_kwargs[key] = str(value).replace('\r\n', ' ').replace('\n', ' ').strip()

            # 逐一替換已知參數名稱，避免 JSON 大括號被 str.format() 誤解析
            result = raw
            for key, value in cleaned_kwargs.items():
                # 匹配 {key}、{ key }、{"key"}、{  "key"  } 等變體
                key_pattern = r'\{\s*"?' + re.escape(key) + r'"?\s*\}'
                result = re.sub(key_pattern, value, result)

            logger.info(f"✅ 成功格式化提示詞: {prompt_id}")
            return result

        except Exception as e:
            logger.error(f"❌ 格式化失敗: {e}")
            raise
        
    def reload_prompts(self):
        """手動重新載入 Google Sheet 中的 prompt"""
        try:
            # 重置連接狀態，強制重新初始化
            self.target_sheet = None
            self._initialization_error = None
            # 清空 prompts 字典，強制下次讀取時重新載入
            self.prompts = {}
            logger.info(f"🔄 已清空 prompts 快取和連接，下次讀取時將重新載入")
        except Exception as e:
            logger.error(f"❌ 重新載入提示詞失敗: {str(e)}")