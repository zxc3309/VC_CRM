import os
import json
import logging
from typing import Dict, Any
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
    
class DealAnalyzer:
   
    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()
        
        # 設置 API key
        api_key = os.getenv("OPENAI_API_KEY")
        
        # 初始化日誌
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
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
        
        # 設置搜索模型
        self.search_model = "gpt-4.1"  # 使用 gpt-4.1 模型


    async def analyze_deal(self, message_text: str, deck_data) -> Dict[str, Any]:
        """
        Analyze the deal based on the provided message text.
        
        Parameters:
        message_text: The text containing deal information
        
        Returns:
        A dictionary containing analyzed deal data
        """
        try:
            self.logger.info("Analyzing deal information...")

            initial_info = await self._extract_initial_info(message_text)
            company_name = initial_info.get("company_name", "")
            founder_names = initial_info.get("founder_names", [])
            raw_company_info = initial_info.get("company_info", "")
            if isinstance(deck_data, list) and len(deck_data) > 0 and isinstance(deck_data[0], dict):
                raw_company_info_funding_team = deck_data[0].get("funding_team", "")
            else:
                self.logger.error("deck_data is not a list of dict or empty.")
                raw_company_info_funding_team = ""
            funding_info = initial_info.get("funding_info", "")
            
            #轉換Deck內容為可供GenAI閱讀的形式
            formatted_deck_text = self.format_deck_summary(deck_data)
            
            # 如果未找到公司名稱，返回有限的結果
            if not company_name:
                self.logger.warning("未找到公司名稱，分析終止")
            
            self.logger.info(f"找到公司名稱: {company_name}")
            
            # Search for additional founder names if not found
            if not founder_names:
                founder_info = await self._search_founder_names(company_name, raw_company_info_funding_team)
                founder_names = founder_info.get("founder_names", [])
            
            self.logger.info(f"找到創辦人名稱: {founder_names}")
            
            #尋找更多公司信息
            company_info = await self._get_company_details(company_name, founder_names, raw_company_info, formatted_deck_text)
            self.logger.info(f"獲取到公司 {company_name} 的額外信息")
            
            #尋找更多創辦人信息
            founder_info = await self._research_founder_background(founder_names, company_name, raw_company_info_funding_team)
            self.logger.info(f"獲取到創辦人 {founder_names} 的額外信息")
            
            # Compile the deal data
            deal_data = {
                "company_name": company_name,
                "founder_name": [{"name": name} for name in founder_names] if founder_names else [],
                "company_info": company_info,
                "founder_info": founder_info,
                "funding_info": funding_info
            }
            
            self.logger.info("Deal analysis complete.")
            return deal_data
            
        except Exception as e:
            self.logger.error(f"Error analyzing deal: {str(e)}", exc_info=True)
            return {}
        #到此主程序完成

    def format_deck_summary(self, deck_data: list[dict]) -> str:
        if not deck_data or not isinstance(deck_data[0], dict):
            return ''
        
        deck_dict = deck_data[0]
        return '\n'.join(f"[{key.capitalize()}] {value}" for key, value in deck_dict.items())

    async def _extract_initial_info(self, message_text: str) -> Dict[str, Any]:
        """
        從文本消息中萃取公司名稱、創始人名稱、既有公司資訊與募資資訊
        
        參數:
        message_text: 包含交易信息的文本
        
        返回:
        包含公司名稱、創始人名稱、既有公司資訊與募資資訊的字典
        """
        try:
            self.logger.info("從消息中提取初始信息")
            
            system_prompt = """提取消息中的公司名稱、創始人名稱、既有公司資訊與募資資訊。
            返回 JSON 格式:
            {
                "company_name": "公司全名",
                "founder_names": ["創始人1", "創始人2", ...]
                "company_info": "公司資訊",
                "funding_info": "募資資訊(金額或是其他)"
            }
            
            如果找不到相關信息，返回空字符串或空列表。
            盡量提取完整的公司名稱，而不是縮寫。"""

            completion = await self.openai_client.chat.completions.create(
                model="gpt-4.1",
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message_text}
                ]
            )
            
            # Log the raw response for debugging
            self.logger.info(f"Raw completion response: {completion.choices[0].message.content}")
            
            result = json.loads(completion.choices[0].message.content)
            self.logger.info(f"提取結果: 公司名稱={result.get('company_name', '')}, "
                         f"創始人名稱={result.get('founder_names', '')}")
            
            return result
           
        except Exception as e:
            self.logger.error(f"提取初始信息時出錯: {str(e)}", exc_info=True)
            return {"company_name": "", "founder_names": []}
 
    async def _search_founder_names(self, company_name: str, raw_company_info_funding_team: str) -> Dict[str, Any]:
        """
        如果初始文本中沒有創始人信息，使用網絡搜索查找
        
        參數:
        company_name: 公司名稱
        
        返回:
        包含創始人名稱和職稱的字典
        """
        try:
            self.logger.info(f"搜索 {company_name} 的創始人")
            
            # 使用不同的搜索查詢
            search_queries = [
                f"{company_name} founder CEO title position who founded",
                f"{company_name} 創始人 CEO 職位 誰創立了"
            ]
            
            found_info = {
                'founder_names': [],
                'founder_titles': []
            }
            
            for query in search_queries:
                search_results = await self._web_search(query)
                
                if not search_results or (not search_results.get('content') and not search_results.get('citations')):
                    continue
                
                # 提取創始人名稱和職稱
                founder_prompt = f"""根據以下搜索結果，識別 {company_name} 的創始人和他的職稱。
                只返回以下 JSON 格式:
                {{
                    "founders": [
                        {{
                            "name": "創始人",
                            "title": "職稱"
                        }}
                    ]
                }}
                
                規則:
                1. 只包含實際創始人，不包括其他團隊成員
                2. 提供最新的職稱
                3. 如果找不到創始人，返回空列表
                4. 精確 - 只包含已確認的信息
                5. 如果找不到職稱，使用 "N/A"
                
                搜索結果:
                {search_results.get('content', '')}
                {raw_company_info_funding_team}
                """
                
                completion = await self.openai_client.chat.completions.create(
                    model="gpt-4.1",
                    messages=[
                        {"role": "system", "content": "你是一個專門提取創始人信息的 AI 分析師。"},
                        {"role": "user", "content": founder_prompt}
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

    async def _get_company_details(self, company_name: str, founder_name: str, raw_company_info: str, formatted_deck_text: str) -> Dict[str, Any]:
        """
        獲取公司的詳細信息，使用公司名稱和創始人名稱
        
        參數:
        company_name: 公司名稱
        founder_name: 創始人名稱 (可選)
        
        返回:
        包含公司詳細信息的字典
        """
        try:
            self.logger.info(f"獲取 {company_name} 的詳細信息")

            search_query = f"{company_name} company profile, business overview, financial data, , products&services description, market position, financials, key milestones, news"
            if founder_name:
                search_query += f", founded by {founder_name}"
            
            # 搜索公司信息
            search_results = await self._web_search(search_query)
            
            if not search_results or not search_results.get('content'):
                self.logger.warning(f"無法找到 {company_name} 的詳細信息")
                return {}
            
            # 提取結構化信息           
            company_prompt = f"""根據以下搜索結果，提供 {company_name} 的全面信息。
            返回以下 JSON 格式:
            {{
                "company_introduction": "公司簡介與背景",
                "business_model": "營運與商業模式",
                "products_services": "產品或服務內容",
                "market_position": "市場定位與競爭優勢",
                "financials": "財務狀況（如有）",
                "key_milestones": "重要的里程碑或新聞事件"
            }}
            
            規則:
            1. 如果找不到信息，使用 "N/A"
            2. 保持回應豐富度和基於事實
            3. 盡可能列出之前的公司產品與服務內容
            4. 請使用英文回應
            
            
            搜索結果:
            {search_results.get('content', '')}
            {raw_company_info}
            {formatted_deck_text}
            """
            
            completion = await self.openai_client.chat.completions.create(
                model="gpt-4.1",
                messages=[
                    {"role": "system", "content": "你是一個專門分析公司信息的 AI 分析師。"},
                    {"role": "user", "content": company_prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            # 解析分析結果
            company_info = json.loads(completion.choices[0].message.content)
            
            # 返回結構化信息
            # 合併所有欄位成一個字串
            full_company_summary = f"""
Introduction】
{company_info.get('company_introduction', 'N/A')}

【Business Model】
{company_info.get('business_model', 'N/A')}

【Product & Services】
{company_info.get('products_services', 'N/A')}

【Market Position】
{company_info.get('market_position', 'N/A')}

【Financials】
{company_info.get('financials', 'N/A')}

【Milestones】
{company_info.get('key_milestones', 'N/A')}
            """.strip()

            # 最終只保留整理後的綜合介紹在 company_info
            result = {
                "company_introduction": full_company_summary
            }
            
            self.logger.info(f"成功提取 {company_name} 的公司信息")
            return result
                
        except Exception as e:
            self.logger.error(f"獲取公司詳細信息時出錯: {str(e)}", exc_info=True)
            return {}

    async def _research_founder_background(self, founder_name: str, company_name: str, raw_company_info_funding_team: str) -> Dict[str, Any]:
        """
        研究創始人的詳細背景
        
        參數:
        founder_name: 創始人名稱
        company_name: 公司名稱
        
        返回:
        包含創始人背景信息的內容
        """
        try:
            self.logger.info(f"研究 {founder_name} 的背景")
            
            # 構建搜索查詢
            search_query = f"{founder_name} {company_name} founder biography, career history, education background, achievements awards, LinkedIn URL"
            
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
            
            # 提取結構化信息
            founder_prompt = f"""根據以下搜索結果，提取 {founder_name} 的詳細信息。
            返回以下 JSON 格式:
            {{
                "title": "當前職位",
                "background": "當前角色和專業摘要",
                "previous_companies": "以時間順序排列的之前公司和職位",
                "education": "包括學位和院校的教育背景",
                "achievements": "顯著成就、獎項和認可",
                "linkedin": "LinkedIn URL"
            }}
            

            
            規則:
            1. 如果找不到信息，使用 "N/A"
            2. 保持回應簡潔和基於事實
            3. 盡可能列出之前的公司和職位，並依照時間順序排列
            4. 包括教育的具體細節（學位、院校、可用時年份）
            5. 專注於已驗證的成就和認可
            6. 請使用英文回應
            
            搜索結果:
            {search_results.get('content', '')}
            {raw_company_info_funding_team}
            """
            
            completion = await self.openai_client.chat.completions.create(
                model="gpt-4.1",
                messages=[
                    {"role": "system", "content": "你是一個專門提取專業背景信息的 AI 分析師。"},
                    {"role": "user", "content": founder_prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            # 解析分析結果
            founder_info = json.loads(completion.choices[0].message.content)
            
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
