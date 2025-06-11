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
    
    async def save_deal(self, deal_data, doc_url):
        """Save simplified deal info (opportunity, description, log, deck) to Google Sheets."""
        service = build('sheets', 'v4', credentials=self.credentials, cache_discovery=False)

        # 擷取必要資料
        opportunity = deal_data.get('company_name', 'N/A')  # Opportunity (公司名稱)
        description = deal_data.get('company_info', {}).get('company_introduction_one_liner', 'N/A')  # Description
        deck_link_raw = deal_data.get('Deck Link', '')  # Deck 連結

        # 格式化超連結
        log_link = f'=HYPERLINK("{doc_url}", "Log")' if doc_url else "N/A"
        deck_link = f'=HYPERLINK("{deck_link_raw}", "Deck")' if deck_link_raw else "N/A"
        
        # Prepare row data
        row_data = [
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # Timestamp
            "",
            "",
            opportunity,
            description,
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            log_link,
            deck_link
        ]

        # Check and update headers if needed
        headers = [
            'Opportunity',
            'Description',
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            '',
            'Log',
            'Deck'
        ]
        
        # Get the first row to check headers
        header_range = 'Deals!A1:M1'  # Update range to include new column
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
        range_name = 'Deals!A:M'  # Update range to include new column
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
        
        # Return the spreadsheet URL
        return f"https://docs.google.com/spreadsheets/d/{self.SPREADSHEET_ID}"
