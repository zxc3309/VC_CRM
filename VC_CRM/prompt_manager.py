import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from dotenv import load_dotenv
import logging
import re

# 設置日誌
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GoogleSheetPromptManager:
    def __init__(self, spreadsheet_name: str = None, sheet_index: int = 0):
        load_dotenv(override=True)
        sheet_id = spreadsheet_name or os.getenv('PROMPT_MANAGER')
        
        if not sheet_id:
            raise ValueError("未設定 PROMPT_MANAGER 環境變數")
        
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        current_dir = os.path.dirname(os.path.abspath(__file__))
        service_account_path = os.path.join(current_dir, 'service_account.json')
        
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name(service_account_path, scope)
            client = gspread.authorize(creds)
            
            # 找到目標試算表
            target_sheet = None
            for sheet in client.openall():
                if sheet.id == sheet_id:
                    target_sheet = sheet
                    break
            
            if not target_sheet:
                raise ValueError(f"找不到 ID 為 {sheet_id} 的試算表")
            
            # 使用第一個工作表
            sheet = target_sheet.worksheets()[0]
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
            logger.error(f"❌ 初始化失敗: {str(e)}")
            raise

    def get_prompt(self, prompt_id: str) -> str:
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
            
            # 清理提示詞模板中的參數名稱
            pattern = r'{\s*"?(\w+)"?\s*}'
            cleaned_raw = re.sub(pattern, r'{\1}', raw)
            
            # 使用 str.format 進行格式化
            formatted_prompt = cleaned_raw.format(**cleaned_kwargs)
            logger.info(f"✅ 成功格式化提示詞: {prompt_id}")
            return formatted_prompt
            
        except KeyError as e:
            logger.error(f"❌ 格式化失敗: 缺少參數 {e}")
            raise ValueError(f"Missing parameter for prompt '{prompt_id}': {e}")
        except Exception as e:
            logger.error(f"❌ 格式化失敗: {e}")
            raise