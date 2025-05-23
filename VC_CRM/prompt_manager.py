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
        load_dotenv()
        sheet_id = spreadsheet_name or os.getenv('PROMPT_MANAGER')
        logger.info(f"使用的試算表 ID: {sheet_id}")
        
        if not sheet_id:
            raise ValueError("未設定 PROMPT_MANAGER 環境變數")
        
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        current_dir = os.path.dirname(os.path.abspath(__file__))
        service_account_path = os.path.join(current_dir, 'service_account.json')
        logger.info(f"服務帳號文件路徑: {service_account_path}")
        
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name(service_account_path, scope)
            client = gspread.authorize(creds)
            logger.info("成功授權 Google Sheets API")
            
            # 列出所有可訪問的試算表
            available_sheets = client.openall()
            logger.info(f"可訪問的試算表數量: {len(available_sheets)}")
            
            # 找到目標試算表
            target_sheet = None
            for sheet in available_sheets:
                logger.info(f"試算表標題: {sheet.title}, ID: {sheet.id}")
                if sheet.id == sheet_id:
                    target_sheet = sheet
                    break
            
            if not target_sheet:
                raise ValueError(f"找不到 ID 為 {sheet_id} 的試算表")
            
            logger.info(f"成功找到試算表: {target_sheet.title}")
            
            # 列出所有工作表
            worksheets = target_sheet.worksheets()
            logger.info(f"試算表中的工作表數量: {len(worksheets)}")
            for i, ws in enumerate(worksheets):
                logger.info(f"工作表 {i}: {ws.title}")
            
            # 使用第一個工作表
            sheet = worksheets[0]
            logger.info(f"使用工作表: {sheet.title}")
            
            records = sheet.get_all_records()
            logger.info(f"讀取到的記錄數量: {len(records)}")
            if records:
                logger.info(f"第一條記錄的列名: {list(records[0].keys())}")
            
            # 清理提示詞中的換行符號
            self.prompts = {}
            for row in records:
                prompt_id = row['prompt_id']
                prompt_text = row['prompt_text']
                # 清理換行符號和空格
                prompt_text = prompt_text.replace('\r\n', ' ').replace('\n', ' ').strip()
                self.prompts[prompt_id] = prompt_text
            
            logger.info(f"成功載入的提示詞數量: {len(self.prompts)}")
            logger.info(f"可用的提示詞 ID: {list(self.prompts.keys())}")
            
        except Exception as e:
            logger.error(f"初始化時發生錯誤: {str(e)}", exc_info=True)
            raise

    def get_prompt(self, prompt_id: str) -> str:
        prompt = self.prompts.get(prompt_id)
        if prompt is None:
            logger.warning(f"找不到提示詞: {prompt_id}")
        return prompt

    def get_prompt_and_format(self, prompt_id: str, **kwargs) -> str:
        raw = self.get_prompt(prompt_id)
        if not raw:
            raise ValueError(f"Prompt '{prompt_id}' not found.")
        try:
            # 記錄原始提示詞
            logger.info(f"原始提示詞 ({prompt_id}): {raw}")
            logger.info(f"提供的參數: {kwargs}")
            
            # 清理參數中的換行符號和空格
            cleaned_kwargs = {}
            for key, value in kwargs.items():
                if isinstance(value, (list, dict)):
                    # 如果是列表或字典，轉換為字符串
                    cleaned_kwargs[key] = str(value)
                elif value is None:
                    cleaned_kwargs[key] = ""
                else:
                    # 清理換行符號和空格
                    cleaned_kwargs[key] = str(value).replace('\r\n', ' ').replace('\n', ' ').strip()
            
            # 清理提示詞模板中的參數名稱（移除多餘的空格和引號）
            pattern = r'{\s*"?(\w+)"?\s*}'
            cleaned_raw = re.sub(pattern, r'{\1}', raw)
            logger.info(f"清理後的提示詞: {cleaned_raw}")
            
            # 使用 str.format 進行格式化
            formatted_prompt = cleaned_raw.format(**cleaned_kwargs)
            logger.info(f"成功格式化提示詞: {prompt_id}")
            return formatted_prompt
            
        except KeyError as e:
            logger.error(f"格式化提示詞時缺少參數: {e}")
            # 修正語法錯誤
            pattern = r'{\s*"?(\w+)"?\s*}'
            params_in_prompt = re.findall(pattern, raw)
            logger.error(f"提示詞中的參數: {params_in_prompt}")
            logger.error(f"提供的參數: {list(cleaned_kwargs.keys())}")
            raise ValueError(f"Missing parameter for prompt '{prompt_id}': {e}")
        except Exception as e:
            logger.error(f"格式化提示詞時發生錯誤: {e}")
            raise