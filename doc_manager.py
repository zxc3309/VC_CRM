import os
import json
import logging
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2 import service_account
from prompt_manager import GoogleSheetPromptManager
from ai_provider import create_ai_provider
from dotenv import load_dotenv
import base64

# 設置日誌
logger = logging.getLogger(__name__)

class DocManager:
    def __init__(self, prompt_manager: GoogleSheetPromptManager = None):
        load_dotenv(override=True)
        self.FOLDER_ID = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
        if not self.FOLDER_ID:
            raise ValueError("未設定 GOOGLE_DRIVE_FOLDER_ID 環境變數")
        
        self.SCOPES = [
            'https://www.googleapis.com/auth/drive.file',
            'https://www.googleapis.com/auth/documents'
        ]
        
        # 延遲初始化 - 先不連接 Google API
        self.credentials = None
        self.service = None
        self.docs_service = None
        self.drive_service = None
        self._initialized = False
        self._initialization_error = None
        
        # AI Provider 可以立即初始化 (不依賴 Google)
        self.ai_provider = create_ai_provider()
        
        # 使用傳入的 prompt_manager 或建立新的
        self.prompt_manager = prompt_manager or GoogleSheetPromptManager()
        
        logger.info("✅ DocManager 已建立 (延遲連接模式)")
    
    def _initialize_services(self):
        """延遲初始化 Google API 連接"""
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
            
            # 建立所有 Google API 服務
            self.service = build('drive', 'v3', credentials=self.credentials)
            self.docs_service = build('docs', 'v1', credentials=self.credentials, cache_discovery=False)
            self.drive_service = build('drive', 'v3', credentials=self.credentials, cache_discovery=False)
            
            self._initialized = True
            logger.info("✅ 成功連接到 Google Drive 和 Docs API")
            
        except Exception as e:
            logger.error(f"❌ Google API 初始化失敗: {str(e)}")
            if "Invalid JWT Signature" in str(e) or "invalid_grant" in str(e):
                logger.error("💡 請重新生成 Google Service Account 金鑰")
                logger.error("   詳見 service_account_regeneration_guide.md")
            self._initialization_error = e
            raise

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

    def format_questions(self, questions):
        """將問題列表格式化為數字列點形式"""
        formatted = []
        for i, question in enumerate(questions, 1):
            if isinstance(question, str):
                formatted.append(f"{i}. {question}")
            elif isinstance(question, dict):
                for key, value in question.items():
                    formatted.append(f"{i}. {key}: {value}")
        return "\n".join(formatted)
    
    def format_observation(self, observation):
        """將觀察列表格式化為數字列點形式"""
        if not isinstance(observation, list):
            return str(observation)
        formatted = []
        for i, obs in enumerate(observation, 1):
            if isinstance(obs, str):
                formatted.append(f"{i}. {obs}")
            elif isinstance(obs, dict):
                formatted.append(f"{i}. " + ", ".join(f"{k}: {v}" for k, v in obs.items()))
            else:
                formatted.append(f"{i}. {str(obs)}")
        return "\n".join(formatted)
    
    async def suggest_questions_with_gpt(self, deal_data, input_data) -> tuple[list[str], list[str]]:
        """根據 pitch deck 摘要，自動建議第一次接觸該新創應該問的問題"""
        logger.info("[suggest_questions] 🚀 開始執行問題與觀察生成")
        logger.info(f"[suggest_questions] 輸入的公司名稱: {deal_data.get('company_name', 'N/A')}")
        
        try:
            # 從 prompt manager 獲取問題列表
            logger.info("[suggest_questions] 📋 獲取問題列表模板...")
            question_list1 = self.prompt_manager.get_prompt('question_list1')
            question_list2 = self.prompt_manager.get_prompt('question_list2')
            question_list3 = self.prompt_manager.get_prompt('question_list3')
            question_list4 = self.prompt_manager.get_prompt('question_list4')
            
            # 檢查問題列表是否成功獲取
            lists_status = []
            for i, q_list in enumerate([question_list1, question_list2, question_list3, question_list4], 1):
                if q_list:
                    lists_status.append(f"question_list{i}: ✅")
                else:
                    lists_status.append(f"question_list{i}: ❌ 未找到")
            logger.info(f"[suggest_questions] 問題列表狀態: {', '.join(lists_status)}")

            # 使用 GoogleSheetPromptManager 獲取提示詞
            logger.info("[suggest_questions] 🔧 格式化主要 prompt...")
            prompt = self.prompt_manager.get_prompt_and_format(
                'suggest_questions',
                deal_data=json.dumps(deal_data, ensure_ascii=False),
                question_list1=question_list1,
                question_list2=question_list2,
                question_list3=question_list3,
                question_list4=question_list4
            )
            
            if not prompt:
                raise ValueError("無法獲取或格式化 suggest_questions prompt")
            
            logger.info(f"[suggest_questions] ✅ Prompt 格式化完成，長度: {len(prompt)} 字符")

            # 取得 AI model
            ai_model = getattr(self, 'ai_model', None) or input_data.get('ai_model') or "gpt-4.1"
            logger.info(f"[suggest_questions] 🤖 使用 AI 模型: {ai_model}")

            # 使用 AI Provider
            logger.info("[suggest_questions] 📡 調用 AI Provider...")
            response = await self.ai_provider.complete(
                prompt=prompt,
                model=ai_model,
                system_instruction="You are a professional VC analyst.",
                json_mode=True,
                temperature=0.7,
            )

            result = response.text
            logger.info(f"[suggest_questions] AI 原始回應長度: {len(result)} 字符")
            logger.debug(f"[suggest_questions] AI 原始回應內容: {result[:500]}...")  # 顯示前500字符
            
            # 初始化 result_json，避免後續引用錯誤
            result_json = {}
            
            try:
                result_json = json.loads(result)
                logger.info(f"[suggest_questions] 成功解析 JSON，包含欄位: {list(result_json.keys())}")
                
                questions = result_json.get("questions", [])
                observation = result_json.get("observation", [])
                
                logger.info(f"[suggest_questions] 提取到 {len(questions)} 個問題")
                logger.info(f"[suggest_questions] 提取到 {len(observation)} 個觀察")
                
                if not questions:
                    logger.warning("[suggest_questions] ⚠️ 未找到 'questions' 欄位或欄位為空")
                if not observation:
                    logger.warning("[suggest_questions] ⚠️ 未找到 'observation' 欄位或欄位為空")
                    
            except Exception as e:
                questions = []
                observation = []
                # 解析失敗時，設置空的 result_json
                result_json = {"questions": [], "observation": [], "error": str(e)}
                logger.error(f"[suggest_questions] ❌ 解析 AI 回傳問題/觀察時發生錯誤：{str(e)}")
                logger.error(f"[suggest_questions] AI 返回內容: {result[:200]}...")

            # 新增：把 prompt 和結果放到 input_data
            input_data["AI Prompt5"] = prompt
            input_data["AI Content5"] = json.dumps(result_json, ensure_ascii=False)

            logger.info(f"[suggest_questions] ✅ 成功完成問題與觀察生成！")
            return questions, observation
            
        except Exception as e:
            logger.error(f"[suggest_questions] ❌ 生成問題時發生錯誤：{str(e)}")
            logger.error(f"[suggest_questions] 錯誤類型: {type(e).__name__}")
            
            # 記錄錯誤到 input_data 以便追蹤
            input_data["AI Prompt5"] = f"Error occurred during suggest_questions: {str(e)}"
            input_data["AI Content5"] = json.dumps({
                "error": str(e),
                "error_type": type(e).__name__,
                "questions": [],
                "observation": []
            }, ensure_ascii=False)
            
            import traceback
            logger.error(f"[suggest_questions] 完整錯誤堆疊: {traceback.format_exc()}")
            return [], []

    async def create_doc(self, deal_data, input_data):
        # 確保 Google API 已初始化
        self._initialize_services()
        
        # 資料前處理
        all_founder_names = ", ".join(deal_data.get("founder_name", [])) if deal_data.get("founder_name") else "N/A"
        founder_info = deal_data.get("founder_info", {})
        founder_titles = self.stringify(founder_info.get("title", "N/A"))
        founder_backgrounds = self.stringify(founder_info.get("background", "N/A"))
        founder_companies = self.stringify(founder_info.get("previous_companies", "N/A"))
        founder_education = self.stringify(founder_info.get("education", "N/A"))
        founder_achievements = self.stringify(founder_info.get("achievements", "N/A"))
        founder_linkedin_url = self.stringify(founder_info.get("LinkedIn URL", "N/A"))
        company_name = self.stringify(deal_data.get("company_name", "N/A"))
        company_category= self.stringify(deal_data.get("company_category", "N/A"))
        company_info = self.stringify(deal_data.get("company_info", {}).get("company_introduction", "N/A"))
        funding_info = self.stringify(deal_data.get("funding_info", "N/A"))
        questions, observation = await self.suggest_questions_with_gpt(deal_data, input_data)
        founder_observation = self.format_observation(observation)
        suggested_questions = self.format_questions(questions)
        # 獲取 deck_link，如果是 N/A 則不創建超連結
        deck_link = deal_data.get("Deck Link", "N/A")
        # Reference Links 處理
        ref_links = deal_data.get("Reference Links", [])
        if isinstance(ref_links, list):
            ref_links_str = "\n".join(ref_links) if ref_links else "N/A"
        else:
            ref_links_str = str(ref_links) if ref_links else "N/A"

        doc_title = f"{company_name} Log"

        try:
            # 建立文件
            doc = self.docs_service.documents().create(body={'title': doc_title}).execute()
            document_id = doc['documentId']
            logger.info(f"✅ 成功建立文件: {doc_title}")

            # 移動文件至指定資料夾
            try:
                self.drive_service.files().update(
                    fileId=document_id,
                    addParents=self.FOLDER_ID,
                    removeParents='root',
                    fields='id, parents'
                ).execute()
                logger.info(f"✅ 成功移動文件到指定資料夾")
            except Exception as e:
                logger.error(f"❌ 移動文件失敗: {str(e)}")
                # 即使移動失敗，我們仍然繼續處理文件內容
        except Exception as e:
            logger.error(f"❌ 建立文件失敗: {str(e)}")
            raise

        try:
            # 準備內容段落
            sections = [
                ("Analysis Date：", datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                ("Company Name：", company_name),
                ("Company Category：", company_category),
                ("Brief Introduction", company_info),
                ("Funding Information", funding_info),
                ("Founder Name", all_founder_names),
                ("Founder Title", founder_titles),
                ("Founder Background", founder_backgrounds),
                ("Founder Experience", founder_companies),
                ("Founder Education", founder_education),
                ("Founder Achievements", founder_achievements),
                ("Founder LinkedIn Profile", founder_linkedin_url),
                ("Observation", founder_observation),
                ("Suggested Questions", suggested_questions),
                ("Deck Link：", deck_link),
                ("Reference Link：", ref_links_str)
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

            # 將請求分批處理，每批最多 20 個請求
            batch_size = 20
            for i in range(0, len(requests), batch_size):
                batch_requests = requests[i:i + batch_size]
                try:
                    self.docs_service.documents().batchUpdate(
                        documentId=document_id,
                        body={'requests': batch_requests}
                    ).execute()
                    logger.info(f"✅ 成功處理第 {i//batch_size + 1} 批請求")
                except Exception as e:
                    logger.error(f"❌ 處理第 {i//batch_size + 1} 批請求時失敗: {str(e)}")
                    raise

            return {
                "doc_url": f"https://docs.google.com/document/d/{document_id}",
            }
        except Exception as e:
            logger.error(f"❌ 插入內容時發生錯誤: {str(e)}")
            raise