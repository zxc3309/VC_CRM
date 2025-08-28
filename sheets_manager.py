import gspread
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
        
        # 延遲初始化 - 先不連接 Google API
        self.credentials = None
        self.client = None
        self.sheet = None
        self._initialized = False
        self._initialization_error = None
        
        # 儲存傳入的 prompt_manager
        self.prompt_manager = prompt_manager
        
        logger.info(f"✅ GoogleSheetsManager 已建立 (延遲連接模式)，Sheet ID: {self.SPREADSHEET_ID}")
    
    def _initialize_connection(self):
        """延遲初始化 Google Sheets 連接"""
        if self._initialized:
            return  # 已經初始化
        
        if self._initialization_error is not None:
            raise self._initialization_error  # 之前初始化失敗
        
        try:
            # 從環境變數讀取 base64 編碼的 service account
            base64_content = os.getenv('SERVICE_ACCOUNT_BASE64')
            if not base64_content:
                raise ValueError("未設定 SERVICE_ACCOUNT_BASE64 環境變數")
            
            # 解碼 base64 內容，增加錯誤處理
            try:
                decoded_content = base64.b64decode(base64_content).decode('utf-8')
                service_account_info = json.loads(decoded_content)
            except Exception as e:
                raise ValueError(f"SERVICE_ACCOUNT_BASE64 解碼失敗: {str(e)}")
            
            self.credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=self.SCOPES
            )
            
            self.client = gspread.authorize(self.credentials)
            self.sheet = self.client.open_by_key(self.SPREADSHEET_ID).sheet1
            
            self._initialized = True
            logger.info("✅ 成功連接到 Google Sheets")
            
        except Exception as e:
            logger.error(f"❌ Google Sheets 連接失敗: {str(e)}")
            if "Invalid JWT Signature" in str(e) or "invalid_grant" in str(e):
                logger.error("💡 請重新生成 Google Service Account 金鑰")
                logger.error("   詳見 service_account_regeneration_guide.md")
            self._initialization_error = e
            raise
    
    async def save_deal(self, deal_data, input_data, doc_url):
        """Save simplified deal info (opportunity, description, log, deck) to Google Sheets."""
        # 確保 Google Sheets 已初始化
        self._initialize_connection()
        
        service = build('sheets', 'v4', credentials=self.credentials, cache_discovery=False)

        # 使用傳入的 prompt_manager，避免重複建立
        sheet_name = self.prompt_manager.get_prompt('main_sheet_name') if self.prompt_manager else 'Sheet1'
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
        # 確保 Google Sheets 已初始化
        self._initialize_connection()
        
        service = build('sheets', 'v4', credentials=self.credentials, cache_discovery=False)
        
        # 準備要記錄的資訊
        timestamp = datetime.now().strftime('%m/%d/%Y')  # 只保留月/日/年
        company_name = deal_data.get('company_name', 'N/A')
        
        # 從新的 input_data 結構中提取資訊
        # 直接使用字串，不要用 list
        category_prompt = str(input_data.get('Category Prompt', ''))
        category_content = str(input_data.get('Category Content', ''))
        
        # 準備 web search 資訊
        web_prompts = []
        web_contents = []
        for i in range(1, 4):
            web_prompts.append(str(input_data.get(f'Web Prompt{i}', '')))
            web_contents.append(str(input_data.get(f'Web Content{i}', '')))
        
        # 準備 AI prompt 資訊
        ai_prompts = []
        ai_contents = []
        for i in range(1, 6):
            ai_prompts.append(str(input_data.get(f'AI Prompt{i}', '')))
            ai_contents.append(str(input_data.get(f'AI Content{i}', '')))
        
        # 組合所有資訊
        row_data = [
            timestamp,
            company_name,
            str({
                "AI Model": input_data.get("ai_model", "N/A"),
                "Search Model": input_data.get("search_model", "N/A")
            }),  # Model Usage
            category_prompt,
            category_content,
            None,  # Score - 不設置值以保留下拉選單
            web_prompts[0],  # Web Prompt1
            web_contents[0],  # Web Content1
            None,  # Score1
            web_prompts[1],  # Web Prompt2
            web_contents[1],  # Web Content2
            None,  # Score2
            web_prompts[2],  # Web Prompt3
            web_contents[2],  # Web Content3
            None,  # Score3
            ai_prompts[0],  # AI Prompt1
            ai_contents[0],  # AI Content1
            None,  # Score4
            ai_prompts[1],  # AI Prompt2
            ai_contents[1],  # AI Content2
            None,  # Score5
            ai_prompts[2],  # AI Prompt3
            ai_contents[2],  # AI Content3
            None,  # Score6
            ai_prompts[3],  # AI Prompt4
            ai_contents[3],  # AI Content4
            None,  # Score7
            ai_prompts[4],  # AI Prompt5
            ai_contents[4],  # AI Content5
            None  # Score8
        ]
        
        # 檢查並更新表頭
        headers = [
            'Timestamp',
            'Company Name',
            'Model Usage',
            'Category Prompt',
            'Category Content',
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
        header_range = "'Prompt Engineering'!A1:AC1"  # 更新範圍以包含所有列
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
        range_name = "'Prompt Engineering'!A:AC"  # 更新範圍以包含所有列
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


