import os
from datetime import datetime
from google.oauth2.credentials import Credentials
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
    
    async def save_deal(self, deal_data, deck_data):
        """Save deal information to Google Sheets."""
        service = build('sheets', 'v4', credentials=self.credentials, cache_discovery=False)

        #獲取founder_names
        first_founder_name = deal_data["founder_name"][0]["name"] if deal_data["founder_name"] else ""
        
        #引入founder_info並獲取各個欄位
        founder_info = deal_data.get('founder_info', [])
        founder_titles = founder_info.get('title', 'N/A')
        founder_backgrounds = founder_info.get('background', 'N/A')
        founder_companies = founder_info.get('previous_companies', 'N/A')
        founder_education = founder_info.get('education', 'N/A')
        founder_achievements = founder_info.get('achievements', 'N/A')
        founder_linkedin = founder_info.get('linkedin', 'N/A')
        
        # Format URLs as clickable links
        sources = deal_data.get('sources', [])
        formatted_sources = []
        for url in sources:
            if url:
                formatted_sources.append(f'=HYPERLINK("{url}", "{url}")')
        
        # Format company information
        company_name = deal_data.get('company_name', [])
        company_info = deal_data.get("company_info", {}).get("company_introduction", "N/A")
        funding_info = deal_data.get('funding_info', [])
        deck_summary_str = json.dumps(deck_data, ensure_ascii=False, indent=2)
        
        
        # Prepare row data
        row_data = [
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # Timestamp
            ''.join(company_name) or 'N/A',
            ''.join(company_info) or 'N/A',
            ''.join(funding_info) or 'N/A',
            ''.join(first_founder_name) or 'N/A',
            ''.join(founder_titles) or 'N/A',
            ''.join(founder_backgrounds) or 'N/A',
            ''.join(founder_companies) or 'N/A',
            ''.join(founder_education) or 'N/A',
            ''.join(founder_achievements) or 'N/A',
            ''.join(founder_linkedin) or 'N/A',
            ''.join(deck_summary_str) or 'N/A'
        ]

        # Check and update headers if needed
        headers = [
            'Timestamp',
            'Company Name',
            'Company Introduction',
            'Funding Information',  
            'Founder Names',
            'Founder Titles',
            'Founder Background',
            'Previous Companies',
            'Education',
            'Achievements',
            'Founder\'s LinkedIn',
            'Deck Summary'
        ]
        
        # Get the first row to check headers
        header_range = 'Deals!A1:L1'  # Update range to include new column
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
        range_name = 'Deals!A:L'  # Update range to include new column
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
