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
    
    async def save_deal(self, deal_data, deck_data):
        """Save deal information to Google Sheets."""
        service = build('sheets', 'v4', credentials=self.credentials, cache_discovery=False)

        #獲取所有創辦人名字，使用逗號連接
        all_founder_names = ", ".join([founder["name"] for founder in deal_data.get("founder_name", [])]) if deal_data.get("founder_name") else "N/A"
        
        #引入founder_info並獲取各個欄位
        founder_info = deal_data.get('founder_info', {})  # 確保獲取字典
        founder_titles = founder_info.get('title', 'N/A')
        founder_backgrounds = founder_info.get('background', 'N/A')
        founder_companies = founder_info.get('previous_companies', 'N/A')
        founder_education = founder_info.get('education', 'N/A')
        founder_achievements = founder_info.get('achievements', 'N/A')
        founder_linkedin = founder_info.get('LinkedIn URL', 'N/A')  # 注意可能需要調整鍵名
        
        # ---- 修改後的 stringify 函數 ----
        def stringify(field):
            if isinstance(field, list):
                # 檢查列表中的元素類型
                processed_items = []
                for item in field:
                    if isinstance(item, dict):
                        # 如果是字典，嘗試格式化（可以根據實際字典結構調整）
                        # 假設字典有 'company', 'role', 'year' 鍵
                        # 您可以根據 deal_analyzer 返回的實際鍵名調整這裡
                        parts = []
                        if 'company' in item: parts.append(item['company'])
                        if 'role' in item: parts.append(f"({item['role']})")
                        if 'position' in item and 'role' not in item: parts.append(f"({item['position']})") # 備用職位鍵名
                        if 'title' in item and 'role' not in item and 'position' not in item: parts.append(f"({item['title']})") # 另一個備用職位鍵名
                        if 'years' in item: parts.append(f"[{item['years']}]")
                        elif 'year' in item: parts.append(f"[{item['year']}]") # 備用年份鍵名
                        
                        item_str = " ".join(parts)
                        processed_items.append(item_str.strip())
                        
                    elif isinstance(item, str):
                        # 如果是字串，直接使用
                        processed_items.append(item)
                    else:
                        # 其他類型，轉為字串
                        processed_items.append(str(item))
                return ", ".join(processed_items) # 連接處理過的字串
            # 如果不是列表，直接轉為字串
            return str(field)


        founder_titles       = stringify(founder_titles)
        founder_backgrounds  = stringify(founder_backgrounds)
        founder_companies    = stringify(founder_companies) # 現在可以處理字典列表了
        founder_education    = stringify(founder_education)
        founder_achievements = stringify(founder_achievements)
        founder_linkedin     = stringify(founder_linkedin)
        # ---- 扁平化完成 ----
        
        # Format URLs as clickable links
        sources = deal_data.get('sources', [])
        formatted_sources = []
        for url in sources:
            if url:
                formatted_sources.append(f'=HYPERLINK("{url}", "{url}")')
        
        # Format company information
        company_name = deal_data.get('company_name', [])
        company_info = deal_data.get("company_info", {}).get("company_introduction", "N/A")
        # ---- 修改：確保 company_name, company_info, funding_info 是字串 ----
        company_name_str = stringify(company_name)
        company_info_str = stringify(company_info)
        funding_info_str = stringify(deal_data.get('funding_info', 'N/A'))
        # ---- 修改完成 ----
        deck_summary_str = json.dumps(deck_data, ensure_ascii=False, indent=2)
        
        
        # Prepare row data
        row_data = [
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # Timestamp
            company_name_str, # 使用處理過的字串
            company_info_str, # 使用處理過的字串
            funding_info_str, # 使用處理過的字串
            all_founder_names,  # 所有創辦人名字
            founder_titles,
            founder_backgrounds,
            founder_companies, # 已處理為字串
            founder_education,
            founder_achievements,
            founder_linkedin,
            deck_summary_str # deck_summary 已經是 JSON 字串
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
