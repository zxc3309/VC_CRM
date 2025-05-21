import os
import json
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2 import service_account
from openai import AsyncOpenAI

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
        self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

    def format_questions(self, questions):
        """將問題列表格式化為純文字段落"""
        formatted = []
        for question in questions:
            if isinstance(question, str):
                formatted.append(question)
            elif isinstance(question, dict):
                for key, value in question.items():
                    formatted.append(f"{key}: {value}")
        return "\n".join(formatted)
    
    async def suggest_questions_with_gpt(self, deal_data, deck_summary: str) -> list[str]:
        """根據 pitch deck 摘要，自動建議第一次接觸該新創應該問的問題"""
        system_prompt = """你是一位資深創投分析師，根據以下 pitch deck 摘要，請列出第一次會談時應該問這間新創團隊的 5 個關鍵問題，問題要具體、實用、有洞察力。
            返回 JSON 格式:
            {
            "questions": [
                "問題 1：問題內容敘述",
                "問題 2：問題內容敘述",
                ...
            ]
            }
            """
        
        user_prompt = f"Pitch Deck 摘要如下：\n公司資訊如下：\n{json.dumps(deal_data, indent=2, ensure_ascii=False)}\n\nPitch Deck 摘要如下：\n{deck_summary}\n請列出建議問題："

        response = await self.openai_client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )


        result = response.choices[0].message.content
        try:
            questions = json.loads(result).get("questions", [])
        except Exception:
            # fallback in case not JSON-formatted
            questions = [line.strip("- ").strip() for line in result.strip().split("\n") if line]

        return questions

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
        suggested_questions = self.format_questions(await self.suggest_questions_with_gpt(deal_data, deck_summary_str))

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
            ("Suggested Questions", suggested_questions)
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
            if len(title.strip()) > 0:
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
            index += len(title) + 1

            # 插入內文
            requests.append({
                'insertText': {
                    'location': {'index': index},
                    'text': f"{content}\n\n"
                }
            })

            if len(content.strip()) > 0:
                requests.append({
                    'updateTextStyle': {
                        'range': {
                            'startIndex': index,
                            'endIndex': index + len(content)
                        },
                        'textStyle': {
                            'fontSize': {'magnitude': 12, 'unit': 'PT'}
                        },
                        'fields': 'fontSize'
                    }
                })

            content_bytes = content.encode('utf-16-le')
            index += len(content_bytes) // 2 + 2  # 每個字 2 bytes，加上 2 個換行

        # 執行 batchUpdate 插入並套用格式
        self.docs_service.documents().batchUpdate(
            documentId=document_id,
            body={'requests': requests}
        ).execute()

        return {
            "doc_url": f"https://docs.google.com/document/d/{document_id}",
            "deck_summary_str": deck_summary_str
        }