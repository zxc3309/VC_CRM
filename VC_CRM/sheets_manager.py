import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from dotenv import load_dotenv
import logging
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2 import service_account
import json
import base64
from prompt_manager import GoogleSheetPromptManager

# 設置日誌
logger = logging.getLogger(__name__)

class GoogleSheetsManager:
    def __init__(self, prompt_manager: GoogleSheetPromptManager = None):
        load_dotenv(override=True)
        self.SPREADSHEET_ID = os.getenv('GOOGLE_SHEETS_ID')
        if not self.SPREADSHEET_ID:
            raise ValueError("未設定 GOOGLE_SHEETS_ID 環境變數")
        
        # 更新權限範圍
        self.SCOPES = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive',
            'https://spreadsheets.google.com/feeds'
        ]
        
        try:
            # 從環境變數讀取 base64 編碼的 service account
            base64_content = os.getenv('SERVICE_ACCOUNT_BASE64')
            if not base64_content:
                raise ValueError("未設定 SERVICE_ACCOUNT_BASE64 環境變數")
            
            # 解碼 base64 內容
            service_account_info = json.loads(base64.b64decode(base64_content).decode())
            
            self.credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=self.SCOPES
            )
            
            creds = ServiceAccountCredentials.from_json_keyfile_dict(
                service_account_info,
                self.SCOPES
            )
            self.client = gspread.authorize(creds)
            self.sheet = self.client.open_by_key(self.SPREADSHEET_ID).sheet1
            logger.info("✅ 成功連接到 Google Sheets")
            
        except Exception as e:
            logger.error(f"❌ 初始化失敗: {str(e)}")
            raise
    
    async def save_deal(self, deal_data, input_data, doc_url):
        """Save simplified deal info (opportunity, description, log, deck) to Google Sheets."""
        service = build('sheets', 'v4', credentials=self.credentials, cache_discovery=False)

        # 使用正確的工作表名稱
        prompt_manager = GoogleSheetPromptManager()
        sheet_name = prompt_manager.get_prompt('main_sheet_name')
        print(sheet_name)

        # 擷取必要資料
        opportunity = deal_data.get('company_name', 'N/A')  # Opportunity (公司名稱)
        category = deal_data.get('company_category', 'N/A')
        description = deal_data.get('company_info', {}).get('company_one_liner', 'N/A')  # Description
        deck_link_raw = deal_data.get('Deck Link', '')  # Deck 連結

        # 格式化超連結
        log_link = f'=HYPERLINK("{doc_url}", "Log")' if doc_url else "N/A"
        deck_link = f'=HYPERLINK("{deck_link_raw}", "Deck")' if deck_link_raw else "N/A"
        
        # Prepare row data
        row_data = [
            None,
            None,
            opportunity,
            description,
            None,
            None,
            None,
            None,
            None,
            None,
            log_link,
            deck_link,
            None,
            None,
            None,
            category,
            datetime.now().strftime('%m/%d/%Y'),  # 只保留月/日/年
            None
        ]

        # Check and update headers if needed
        headers = [
            'Status',
            'Next Meeting',
            'Opportunity',
            'Description',
            'Updates',
            'DRI',
            'Co-AA',
            'Partner',
            'Round Size',
            'Pre-M',
            'Log',
            'Deck',
            'Source',
            'Source Tag',
            'Location',
            'Category',
            'Created Time'
            'Updated Date'
        ]
        
        # Get the first row to check headers
        header_range = f"'{sheet_name}'!A1:Q1"  # 使用單引號包裹工作表名稱
        header_result = service.spreadsheets().values().get(
            spreadsheetId=self.SPREADSHEET_ID,
            range=header_range
        ).execute()
        
        # Add headers if they don't exist or are incomplete
        if 'values' not in header_result or len(header_result['values'][0]) < len(headers):
            service.spreadsheets().values().update(
                spreadsheetId=self.SPREADSHEET_ID,
                range=header_range,
                valueInputOption='RAW',
                body={'values': [headers]}
            ).execute()
        
        # Append row to sheet
        range_name = f"'{sheet_name}'!A:Q"  # 使用單引號包裹工作表名稱
        value_input_option = 'USER_ENTERED'
        insert_data_option = 'INSERT_ROWS'
        
        value_range_body = {
            'values': [row_data]
        }
        
        request = service.spreadsheets().values().append(
            spreadsheetId=self.SPREADSHEET_ID,
            range=range_name,
            valueInputOption=value_input_option,
            insertDataOption=insert_data_option,
            body=value_range_body
        )
        response = request.execute()
        
        # 同時保存 prompt engineering 日誌
        await self.save_log(deal_data, input_data)
        
        # Return the spreadsheet URL
        return f"https://docs.google.com/spreadsheets/d/{self.SPREADSHEET_ID}"

    async def save_log(self, deal_data, input_data):
        """Save prompt engineering logs to the 'Prompt Engineering' tab."""
        service = build('sheets', 'v4', credentials=self.credentials, cache_discovery=False)
        
        # 準備要記錄的數據
        timestamp = datetime.now().strftime('%m/%d/%Y')  # 只保留月/日/年
        
        # 獲取公司名稱（從 deal_data 中）
        company_name = deal_data.get('company_name', 'N/A')
        
        # 準備 web search 數據
        web_prompts = []
        web_contents = []
        
        # 從新的 input_data 結構中提取 web search 數據
        for i in range(1, 4):
            web_prompts.append(input_data.get(f'Web Prompt{i}', ''))
            web_contents.append(input_data.get(f'Web Content{i}', ''))
        
        # 準備 AI prompt 數據
        ai_prompts = []
        ai_contents = []
        
        # 從新的 input_data 結構中提取 AI prompt 數據
        for i in range(1, 6):
            ai_prompts.append(input_data.get(f'AI Prompt{i}', ''))
            ai_contents.append(input_data.get(f'AI Content{i}', ''))
        
        # 組合所有數據
        row_data = [
            timestamp,
            company_name,
            json.dumps({
                "AI Model": input_data.get("ai_model", "N/A"),
                "Search Model": input_data.get("search_model", "N/A")
            }, ensure_ascii=False),  # Model Usage
            web_prompts[0],  # Web Prompt1
            web_contents[0],  # Web Content1
            None,  # Score1 - 不設置值以保留下拉選單
            web_prompts[1],  # Web Prompt2
            web_contents[1],  # Web Content2
            None,  # Score2 - 不設置值以保留下拉選單
            web_prompts[2],  # Web Prompt3
            web_contents[2],  # Web Content3
            None,  # Score3 - 不設置值以保留下拉選單
            ai_prompts[0],  # AI Prompt1
            ai_contents[0],  # AI Content1
            None,  # Score4 - 不設置值以保留下拉選單
            ai_prompts[1],  # AI Prompt2
            ai_contents[1],  # AI Content2
            None,  # Score5 - 不設置值以保留下拉選單
            ai_prompts[2],  # AI Prompt3
            ai_contents[2],  # AI Content3
            None,  # Score6 - 不設置值以保留下拉選單
            ai_prompts[3],  # AI Prompt4
            ai_contents[3],  # AI Content4
            None,  # Score7 - 不設置值以保留下拉選單
            ai_prompts[4],  # AI Prompt5
            ai_contents[4],  # AI Content5
            None   # Score8 - 不設置值以保留下拉選單
        ]
        
        # 檢查並更新表頭
        headers = [
            'Timestamp',
            'Company Name',
            'Model Usage',
            'Web Prompt1',
            'Web Content1',
            'Score',
            'Web Prompt2',
            'Web Content2',
            'Score',
            'Web Prompt3',
            'Web Content3',
            'Score',
            'AI Prompt1',
            'AI Content1',
            'Score',
            'AI Prompt2',
            'AI Content2',
            'Score',
            'AI Prompt3',
            'AI Content3',
            'Score',
            'AI Prompt4',
            'AI Content4',
            'Score',
            'AI Prompt5',
            'AI Content5',
            'Score'
        ]
        
        # 獲取第一行來檢查表頭
        header_range = "'Prompt Engineering'!A1:AA1"  # 更新範圍以包含所有列
        try:
            header_result = service.spreadsheets().values().get(
                spreadsheetId=self.SPREADSHEET_ID,
                range=header_range
            ).execute()
            
            # 如果表頭不存在或不完整，添加表頭
            if 'values' not in header_result or len(header_result['values'][0]) < len(headers):
                service.spreadsheets().values().update(
                    spreadsheetId=self.SPREADSHEET_ID,
                    range=header_range,
                    valueInputOption='RAW',
                    body={'values': [headers]}
                ).execute()
        except Exception as e:
            # 如果表不存在，創建表並添加表頭
            service.spreadsheets().values().update(
                spreadsheetId=self.SPREADSHEET_ID,
                range=header_range,
                valueInputOption='RAW',
                body={'values': [headers]}
            ).execute()
        
        # 添加數據行
        range_name = "'Prompt Engineering'!A:AA"  # 更新範圍以包含所有列
        value_input_option = 'USER_ENTERED'
        insert_data_option = 'INSERT_ROWS'
        
        value_range_body = {
            'values': [row_data]
        }
        
        request = service.spreadsheets().values().append(
            spreadsheetId=self.SPREADSHEET_ID,
            range=range_name,
            valueInputOption=value_input_option,
            insertDataOption=insert_data_option,
            body=value_range_body
        )
        request.execute()


