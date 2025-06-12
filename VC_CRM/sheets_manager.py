import os
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2 import service_account
import json

class SheetsManager:
    def __init__(self):
        self.SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        self.SPREADSHEET_ID = os.getenv('GOOGLE_SHEETS_ID')
        
        # Load credentials from service account file
        self.credentials = service_account.Credentials.from_service_account_file(
            'service_account.json',
            scopes=self.SCOPES
        )
    
    async def save_deal(self, deal_data, input_data, doc_url):
        """Save simplified deal info (opportunity, description, log, deck) to Google Sheets."""
        service = build('sheets', 'v4', credentials=self.credentials, cache_discovery=False)

        # 擷取必要資料
        opportunity = deal_data.get('company_name', 'N/A')  # Opportunity (公司名稱)
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
            None,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Timestamp
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
            'Deck'
            'Source',
            'Source Tag',
            'Location',
            'Category',
            'Created Time'
        ]
        
        # Get the first row to check headers
        header_range = 'Deals!A1:Q1'  # Update range to include new column
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
        range_name = 'Deals!A:Q'  # Update range to include new column
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
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
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
        header_range = 'Prompt Engineering!A1:Z1'
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
        range_name = 'Prompt Engineering!A:Z'
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
