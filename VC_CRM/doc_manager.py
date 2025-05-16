import os
import json
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2 import service_account

class DocManager:
    def __init__(self):
        self.SCOPES = [
            'https://www.googleapis.com/auth/documents',
            'https://www.googleapis.com/auth/drive'
        ]
        self.FOLDER_ID = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
        self.credentials = service_account.Credentials.from_service_account_file(
            'service_account.json',
            scopes=self.SCOPES
        )
        self.docs_service = build('docs', 'v1', credentials=self.credentials, cache_discovery=False)
        self.drive_service = build('drive', 'v3', credentials=self.credentials, cache_discovery=False)

    def stringify(self, field):
        if isinstance(field, list):
            processed = []
            for item in field:
                if isinstance(item, dict):
                    parts = []
                    if 'company' in item: parts.append(item['company'])
                    if 'role' in item: parts.append(f"({item['role']})")
                    if 'position' in item and 'role' not in item: parts.append(f"({item['position']})")
                    if 'title' in item and 'role' not in item and 'position' not in item: parts.append(f"({item['title']})")
                    if 'years' in item: parts.append(f"[{item['years']}]")
                    elif 'year' in item: parts.append(f"[{item['year']}]")
                    processed.append(" ".join(parts).strip())
                else:
                    processed.append(str(item))
            return ", ".join(processed)
        return str(field)

    def format_deck_summary(self, deck_data):
        """將 deck_data 中的每個項目格式化為純文字段落"""
        formatted = []
        for item in deck_data:
            lines = []
            if 'company' in item:
                lines.append(f"Company: {item['company']}")
            if 'problem' in item:
                lines.append(f"Problem: {item['problem']}")
            if 'solution' in item:
                lines.append(f"Solution: {item['solution']}")
            if 'business_model' in item:
                lines.append(f"Business Model: {item['business_model']}")
            formatted.append("\n".join(lines))
        return "\n\n".join(formatted)

    async def create_doc(self, deal_data, deck_data):
        # 資料前處理
        all_founder_names = ", ".join([f["name"] for f in deal_data.get("founder_name", [])]) if deal_data.get("founder_name") else "N/A"
        founder_info = deal_data.get("founder_info", {})
        founder_titles = self.stringify(founder_info.get("title", "N/A"))
        founder_backgrounds = self.stringify(founder_info.get("background", "N/A"))
        founder_companies = self.stringify(founder_info.get("previous_companies", "N/A"))
        founder_education = self.stringify(founder_info.get("education", "N/A"))
        founder_achievements = self.stringify(founder_info.get("achievements", "N/A"))
        company_name = self.stringify(deal_data.get("company_name", "N/A"))
        company_info = self.stringify(deal_data.get("company_info", {}).get("company_introduction", "N/A"))
        funding_info = self.stringify(deal_data.get("funding_info", "N/A"))
        deck_summary_str = self.format_deck_summary(deck_data)

        doc_title = f"{company_name} Log"

        # 建立文件
        doc = self.docs_service.documents().create(body={'title': doc_title}).execute()
        document_id = doc['documentId']

        # 移動文件至指定資料夾
        self.drive_service.files().update(
            fileId=document_id,
            addParents=self.FOLDER_ID,
            removeParents='root',
            fields='id, parents'
        ).execute()

        # 準備內容段落
        sections = [
            ("Analysis Date：", datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            ("Company Name：", company_name),
            ("Brief Introduction", company_info),
            ("Funding Information：", funding_info),
            ("Founder Name", all_founder_names),
            ("Founder Title", founder_titles),
            ("Founder Background", founder_backgrounds),
            ("Founder Experience", founder_companies),
            ("Founder Education", founder_education),
            ("Founder Achievements", founder_achievements),
            ("Deck Summary", deck_summary_str),
        ]

        # 插入請求集合
        requests = []
        index = 1  # 開始於 index=1，插入在文件開頭之後

        for title, content in sections:
            # 插入標題
            requests.append({
                'insertText': {
                    'location': {'index': index},
                    'text': f"{title}\n"
                }
            })
            requests.append({
                'updateTextStyle': {
                    'range': {
                        'startIndex': index,
                        'endIndex': index + len(title)
                    },
                    'textStyle': {
                        'bold': True,
                        'fontSize': {'magnitude': 12, 'unit': 'PT'}
                    },
                    'fields': 'bold,fontSize'
                }
            })
            index += len(title) + 1  # 加上換行符

            # 插入內文
            requests.append({
                'insertText': {
                    'location': {'index': index},
                    'text': f"{content}\n\n"
                }
            })
            requests.append({
                'updateTextStyle': {
                    'range': {
                        'startIndex': index,
                        'endIndex': index + len(content)
                    },
                    'textStyle': {
                        'italic': True,
                        'fontSize': {'magnitude': 12, 'unit': 'PT'}
                    },
                    'fields': 'italic,fontSize'
                }
            })
            index += len(content) + 2  # 內文 + 兩個換行

        # 執行 batchUpdate 插入並套用格式
        self.docs_service.documents().batchUpdate(
            documentId=document_id,
            body={'requests': requests}
        ).execute()

        return {
            "doc_url": f"https://docs.google.com/document/d/{document_id}",
            "deck_summary_str": deck_summary_str
        }