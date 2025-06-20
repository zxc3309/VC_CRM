import os
import json
import logging
from typing import Dict, Any, Optional
from openai import AsyncOpenAI
from dotenv import load_dotenv
from prompt_manager import GoogleSheetPromptManager
import traceback
import re

    
class DealAnalyzer:
   
    def __init__(self, prompt_manager: GoogleSheetPromptManager = None):
        # Load environment variables from .env file
        load_dotenv(override=True)
        
        # 設置 API key
        api_key = os.getenv("OPENAI_API_KEY")
        
        # 初始化日誌
        self.logger = logging.getLogger(__name__)
        
        # 初始化 input_data 字典
        self.input_data = {
            "Web Prompt1": "",
            "Web Content1": "",
            "Web Prompt2": "",
            "Web Content2": "",
            "Web Prompt3": "",
            "Web Content3": "",
            "AI Prompt1": "",
            "AI Content1": "",
            "AI Prompt2": "",
            "AI Content2": "",
            "AI Prompt3": "",
            "AI Content3": "",
            "AI Prompt4": "",
            "AI Content4": "",
            "AI Prompt5": "",
            "AI Content5": "",
            "deck_data": "",
            "message_text": "",
            "ai_model": "gpt-4.1",  # 預設值
            "search_model": "gpt-4.1"  # 預設值
        }
        
        # 初始化 OpenAI 客戶端
        if api_key:
            # 只記錄 API key 是否存在，不記錄實際內容
            self.logger.info("API key is set")
            
            # 確保 API key 只包含 ASCII 字元
            api_key = api_key.encode('ascii', errors='ignore').decode('ascii')
            
            self.openai_client = AsyncOpenAI(api_key=api_key)
        else:
            self.logger.error("OPENAI_API_KEY environment variable is not set.")
            raise ValueError("API key is not set. Please set the OPENAI_API_KEY environment variable.")
        
        # 使用傳入的 prompt_manager 或建立新的
        self.prompt_manager = prompt_manager or GoogleSheetPromptManager()
        
        # 初始化 model 變數（會在需要時即時讀取）
        self.ai_model = None
        self.search_model = None


    def extract_deck_link(self, message: str) -> Optional[str]:
        """從消息中提取文檔連結"""
        if not message:
            return None
            
        # 使用正則表達式匹配各種可能的文檔連結
        docsend_pattern = r'https://docsend\.com/view/[a-zA-Z0-9]+'
        gdrive_pattern = r'https://(?:drive|docs)\.google\.com/(?:file/d/|presentation/)[\w\-/]+'
        notion_pattern = r'https://(?:www\.)?notion\.so/[a-zA-Z0-9\-]+'
        
        # 按優先順序檢查各種連結
        if re.search(docsend_pattern, message):
            return re.search(docsend_pattern, message).group(0)
        elif re.search(gdrive_pattern, message):
            return re.search(gdrive_pattern, message).group(0)
        elif re.search(notion_pattern, message):
            return re.search(notion_pattern, message).group(0)
        
        return None

    async def analyze_deal(self, message_text: str, deck_data: str) -> Dict[str, Any]:
        """
        Analyze the deal based on the provided message text.
        
        Parameters:
        message_text: The text containing deal information
        deck_data: OCR text extracted from the pitch deck
        
        Returns:
        A dictionary containing analyzed deal data and input data
        """
        try:
            self.logger.info("Analyzing deal information...")

            # 清空快取，即時讀取 ai_model 和 search_model
            self.prompt_manager.prompts = {}
            self.ai_model = self.prompt_manager.get_prompt('ai_model') or "gpt-4.1"
            self.input_data["ai_model"] = self.ai_model
            self.search_model = self.prompt_manager.get_prompt('search_model') or "gpt-4.1"
            self.input_data["search_model"] = self.search_model
            
            # 更新 input_data
            self.input_data["message_text"] = message_text
            self.input_data["deck_data"] = deck_data

            # 從 OCR 文本中提取公司名稱
            company_name = ""
            founder_names = []
            funding_info = ""
            
            # 使用 AI 從 OCR 文本中提取初始信息
            initial_info = await self._extract_initial_info(message_text, deck_data)
            company_name = initial_info.get("company_name", "")
            founder_names = initial_info.get("founder_names", [])
            funding_info = initial_info.get("funding_info", "")
            
            # 如果未找到公司名稱，返回有限的結果
            if not company_name:
                self.logger.warning("未找到公司名稱，分析終止")
                return {
                    "deal_data": {},
                    "input_data": self.input_data
                }
            
            self.logger.info(f"找到公司名稱: {company_name}")
            
            # Search for additional founder names if not found
            if not founder_names:
                founder_info = await self._search_founder_names(company_name, deck_data)
                founder_names = founder_info.get("founder_names", [])
            
            self.logger.info(f"找到創辦人名稱: {founder_names}")
            
            #尋找更多公司信息
            company_info = await self._get_company_details(company_name, founder_names, message_text, deck_data)
            company_category = company_info.get("company_category", "N/A")
            self.logger.info(f"獲取到公司 {company_name} 的額外信息")

            
            #為每個創辦人獨立研究背景
            if founder_names:
                # 只處理第一位創辦人（簡單解決方案）
                first_founder = founder_names[0]
                founder_info = await self._research_founder_background(first_founder, company_name, deck_data)
            else:
                # 如果沒有找到創辦人，生成空的創辦人信息
                founder_info = {
                    'title': 'N/A',
                    'background': 'N/A',
                    'previous_companies': 'N/A',
                    'education': 'N/A',
                    'achievements': 'N/A',
                    'LinkedIn URL': 'N/A'
                }
                # 生成空的 AI Prompt/Content 以保持結構完整
                for i in range(1, 6):
                    if not self.input_data[f"AI Prompt{i}"]:
                        self.input_data[f"AI Prompt{i}"] = f"No founder found for {company_name}"
                        self.input_data[f"AI Content{i}"] = json.dumps({"error": "No founder information available"}, ensure_ascii=False)
            
            # 確保 Web Prompt/Content 結構完整
            for i in range(1, 4):
                if not self.input_data[f"Web Prompt{i}"]:
                    self.input_data[f"Web Prompt{i}"] = f"General search for {company_name}"
                    self.input_data[f"Web Content{i}"] = "No additional information found"
            
            # 提取文檔連結
            deck_link = self.extract_deck_link(message_text)
            
            # Compile the deal data
            deal_data = {
                "company_name": company_name,
                "founder_name": founder_names if founder_names else [],
                "company_info": company_info,
                "founder_info": founder_info,
                "funding_info": funding_info,
                "company_category": company_category
            }
            
            # 如果有找到連結，添加到結果中
            if deck_link:
                deal_data["Deck Link"] = deck_link
            
            self.logger.info("Deal analysis complete.")
            return {
                "deal_data": deal_data,
                "input_data": self.input_data
            }
            
        except Exception as e:
            self.logger.error(f"Error analyzing deal: {str(e)}", exc_info=True)
            return {
                "deal_data": {},
                "input_data": self.input_data
            }

    async def _extract_initial_info(self, message_text: str, deck_data: str) -> Dict[str, Any]:
        """從消息和 OCR 文本中提取初始信息"""
        try:
            prompt = self.prompt_manager.get_prompt_and_format(
                'extract_initial_info',
                message_text=message_text,
                deck_data=deck_data
            )
            
            return await self._get_completion(prompt, "initial_info")
        except Exception as e:
            self.logger.error(f"提取初始信息時出錯: {str(e)}")
            self.logger.error(traceback.format_exc())
            return {
                "company_name": "",
                "founder_names": [],
                "company_info": "",
                "funding_info": ""
            }

    async def _search_founder_names(self, company_name: str, deck_data: str) -> Dict[str, Any]:
        try:
            self.logger.info(f"搜索 {company_name} 的創始人")
            
            # 使用 prompt_manager 獲取搜索查詢
            search_queries = [
                self.prompt_manager.get_prompt_and_format(
                    'search_founder_names',
                    company_name=company_name
                ),
            ]
            
            found_info = {
                'founder_names': [],
                'founder_titles': []
            }
            
            for query in search_queries:
                search_results = await self._web_search(query)
                
                if not search_results or (not search_results.get('content') and not search_results.get('citations')):
                    continue
                
                # 使用 GoogleSheetPromptManager 獲取提示詞
                prompt = self.prompt_manager.get_prompt_and_format(
                    'search_founder_names',
                    company_name=company_name,
                    search_content=search_results.get('content', ''),
                    deck_data=deck_data
                )
                
                completion = await self.openai_client.chat.completions.create(
                    model=self.ai_model,
                    messages=[
                        {"role": "system", "content": "你是一個專門提取創始人信息的 AI 分析師。"},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"}
                )
                
                result = json.loads(completion.choices[0].message.content)
                founders = result.get('founders', [])
                
                if founders:
                    self.logger.info(f"通過查詢 '{query}' 找到創始人信息")
                    for founder in founders:
                        name = founder.get('name')
                        title = founder.get('title', 'N/A')
                        if name and name not in found_info['founder_names']:
                            found_info['founder_names'].append(name)
                            found_info['founder_titles'].append(title)
                    break  # 如果找到創始人，停止搜索
            
            return found_info
                
        except Exception as e:
            self.logger.error(f"搜索創始人時出錯: {str(e)}", exc_info=True)
            return {'founder_names': [], 'founder_titles': []}

    async def _get_company_details(self, company_name: str, founder_names: list, message_text: str, deck_data: str) -> Dict[str, Any]:
        try:
            # 使用 prompt_manager 獲取搜索查詢
            search_query = self.prompt_manager.get_prompt_and_format(
                'get_company_search_query',
                company_name=company_name
            )
            
            # 執行網絡搜索
            search_results = await self._web_search(search_query)
            search_content = search_results.get('content', '') if search_results else ''

            prompt = self.prompt_manager.get_prompt_and_format(
                'get_company_details',
                company_name=company_name,
                founder_names=founder_names,
                message_text=message_text,
                deck_data=deck_data,
                search_content=search_content
            )
            
            company_info = await self._get_completion(prompt, "company_details")

            # 返回結構化信息
            full_company_summary = f"""【One Liner】
{company_info.get('company_introduction_one_liner', 'N/A')}

【Pain Point】
{company_info.get('painpoint', 'N/A')}

【Solution】
{company_info.get('solution', 'N/A')}

【Market Position】
{company_info.get('market_position', 'N/A')}

【Traction】
{company_info.get('traction', 'N/A')}

【Key Milestones】
{company_info.get('key_milestones', 'N/A')}""".strip()

            # 取得分類依據內容
            category_differentiation = self.prompt_manager.get_prompt('category_differentiation')
            company_category = "N/A"
            if category_differentiation:
                try:
                    category_prompt = (
                        f"請根據下列分類依據，判斷公司所屬分類，僅以 JSON 格式回傳：{{\"category\": \"分類名稱\"}}\n"
                        f"【分類依據】\n{category_differentiation}\n"
                        f"【公司資訊】\n{company_info}\n"
                    )
                    self.logger.info(f"分類判斷 prompt: {category_prompt}")
                    category_result = await self._get_completion(category_prompt, result_type="category")
                    self.logger.info(f"AI 回傳分類結果: {category_result}")
                    if isinstance(category_result, dict):
                        company_category = category_result.get('category') or list(category_result.values())[0]
                    elif isinstance(category_result, str):
                        company_category = category_result
                except Exception as e:
                    self.logger.error(f"分類判斷失敗: {str(e)}")
            else:
                self.logger.warning("未取得 category_differentiation 內容，無法自動分類")

            result = {
                "company_introduction": full_company_summary,
                "company_one_liner": company_info.get('company_introduction_one_liner', 'N/A'),
                "company_products": company_info.get('solution', 'N/A'),
                "company_market": company_info.get('market_position', 'N/A'),
                "company_traction": company_info.get('traction', 'N/A'),
                "company_milestones": company_info.get('key_milestones', 'N/A'),
                "company_category": company_category
            }
            
            self.logger.info(f"成功提取 {company_name} 的公司信息 (綜合來源)")
            return result
                
        except Exception as e:
            self.logger.error(f"獲取公司詳細信息時出錯: {str(e)}")
            self.logger.error(traceback.format_exc())
            return {
                "company_introduction": "Error retrieving company details",
                "company_one_liner": "N/A",
                "company_products": "N/A",
                "company_market": "N/A",
                "company_traction": "N/A",
                "company_milestones": "N/A",
                "company_category": "N/A"
            }

    async def _research_founder_background(self, founder_name: str, company_name: str, deck_data: str) -> Dict[str, Any]:
        try:
            self.logger.info(f"研究 {founder_name} 的背景")
            
            # 使用 prompt_manager 獲取搜索查詢
            search_query = self.prompt_manager.get_prompt_and_format(
                'research_founder_background_query',
                founder_name=founder_name,
                company_name=company_name
            )
            
            # 搜索創始人背景
            search_results = await self._web_search(search_query)
            
            if not search_results or not search_results.get('content'):
                self.logger.warning(f"無法找到 {founder_name} 的背景信息")
                return {
                    'title': 'N/A',
                    'background': 'N/A',
                    'previous_companies': 'N/A',
                    'education': 'N/A',
                    'achievements': 'N/A',
                    'sources': []
                }
            
            # 使用 GoogleSheetPromptManager 獲取提示詞
            prompt = self.prompt_manager.get_prompt_and_format(
                'research_founder_background',
                founder_name=founder_name,
                search_content=search_results.get('content', ''),
                deck_data=deck_data
            )
            
            founder_info = await self._get_completion(prompt, "founder_background")
            
            # 返回結構化信息
            result = {
                'title': founder_info.get('title', 'N/A'),
                'background': founder_info.get('background', 'N/A'),
                'previous_companies': founder_info.get('previous_companies', 'N/A'),
                'education': founder_info.get('education', 'N/A'),
                'achievements': founder_info.get('achievements', 'N/A'),
                'LinkedIn URL': founder_info.get('linkedin', 'N/A'),
            }
            
            self.logger.info(f"成功提取 {founder_name} 的背景信息")
            return result
                
        except Exception as e:
            self.logger.error(f"研究創始人背景時出錯: {str(e)}", exc_info=True)
            return {
                'title': 'N/A',
                'background': 'N/A',
                'previous_companies': 'N/A',
                'education': 'N/A',
                'achievements': 'N/A',
                'sources': []
            }

    async def _web_search(self, query: str) -> Dict[str, Any]:
        """
        執行網絡搜索並返回結果，包括引用
        
        參數:
        query: 搜索查詢
        
        返回:
        包含搜索結果和引用的字典
        """
        try:
            self.logger.info("\n==================================================")
            self.logger.info("開始網絡搜索")
            self.logger.info("==================================================")
            self.logger.info(f"搜索查詢: {query}")
            
            self.logger.info(f"使用模型: {self.search_model}")
            
            # 執行搜索
            response = await self.openai_client.responses.create(
                model=self.search_model,
                tools=[{
                    "type": "web_search_preview",
                    "search_context_size": "medium"
                }],
                input=query
            )
            
            # 獲取搜索結果
            text_content = ""
            citations = []
            
            # 檢查回應格式
            if hasattr(response, 'output_text'):
                text_content = response.output_text
            elif hasattr(response, 'choices') and response.choices:
                text_content = response.choices[0].message.content
            
            # 檢查是否有引用
            if hasattr(response, 'citations'):
                citations = response.citations
            
            # 更新 input_data
            # 找到第一個空的 Web Prompt 位置
            for i in range(1, 4):
                if not self.input_data[f"Web Prompt{i}"]:
                    self.input_data[f"Web Prompt{i}"] = query
                    self.input_data[f"Web Content{i}"] = text_content
                    break
            
            self.logger.info("\n回應內容:")
            self.logger.info(text_content)
            
            self.logger.info("\n==================================================")
            self.logger.info(f"搜索完成，找到 {len(citations)} 個引用")
            self.logger.info("==================================================\n")
            
            return {
                'content': text_content,
                'citations': citations
            }  
                
        except Exception as e:
            self.logger.error("\n==================================================")
            self.logger.error("搜索出錯")
            self.logger.error("==================================================")
            self.logger.error(f"錯誤類型: {type(e)}")
            self.logger.error(f"錯誤詳情: {str(e)}")
            self.logger.error("完整錯誤信息:", exc_info=True)

    async def _get_completion(self, prompt: str, result_type: str = "general") -> Dict[str, Any]:
        """使用 OpenAI API 獲取完成結果"""
        try:
            completion = await self.openai_client.chat.completions.create(
                model=self.ai_model,
                messages=[
                    {"role": "system", "content": "你是一個專門分析公司信息的 AI 分析師。"},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            # 解析 JSON 響應
            response = json.loads(completion.choices[0].message.content)
            
            # 更新 input_data
            # 找到第一個空的 AI Prompt 位置
            for i in range(1, 6):
                if not self.input_data[f"AI Prompt{i}"]:
                    self.input_data[f"AI Prompt{i}"] = prompt
                    self.input_data[f"AI Content{i}"] = json.dumps(response, ensure_ascii=False)
                    break
            
            self.logger.info(f"Raw completion response: {completion.choices[0].message.content}")
            return response
            
        except Exception as e:
            self.logger.error(f"獲取完成結果時出錯: {str(e)}")
            self.logger.error(traceback.format_exc())
            return {
                "company_name": "",
                "founder_names": "",
                "company_info": "",
                "funding_info": ""
            }
