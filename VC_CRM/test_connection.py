import os
import asyncio
from dotenv import load_dotenv
from sheets_manager import SheetsManager
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build

async def clear_sheet():
    # Load environment variables
    load_dotenv()
    
    try:
        # Setup credentials
        credentials = service_account.Credentials.from_service_account_file(
            os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE'),
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        
        # Build service
        service = build('sheets', 'v4', credentials=credentials)
        
        # Clear all content except headers
        service.spreadsheets().values().clear(
            spreadsheetId=os.getenv('SPREADSHEET_ID'),
            range='Deals!A2:O',
            body={}
        ).execute()
        
        print('Successfully cleared test data!')
        
    except Exception as e:
        print(f'Failed to clear sheet: {str(e)}')

if __name__ == '__main__':
    asyncio.run(clear_sheet()) 