import os
import json
import logging
from typing import Dict, Any, Optional
from openai import AsyncOpenAI
from dotenv import load_dotenv
from prompt_manager import GoogleSheetPromptManager
import traceback
import re
import asyncio
from playwright.async_api import async_playwright
import random
import urllib.parse
from bs4 import BeautifulSoup
from linkedin_sourcing import get_linkedin_profile_html

    
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
            "Category Prompt":"",
            "Category Content":"",
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
            "ai_model": "",  # 預設值
            "search_model": ""  # 預設值
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
        docsend_pattern = r'https?://(?:www\.)?docsend\.com/[^\s)"}]+'
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

            # 初始化 input_data 字典
            self.input_data = {
                "Category Prompt": "",
                "Category Content": "",
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
                "ai_model": "",  # 預設值
                "search_model": ""  # 預設值
            }
            
            # 載入新 input_data 字典

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
            try:
                initial_info = await self._extract_initial_info(message_text, deck_data)
            except Exception as e:
                self.logger.warning(str(e))
                return {
                    "error": str(e),
                    "deal_data": {},
                    "input_data": self.input_data
                }
            company_name = initial_info.get("company_name", "")
            founder_names = initial_info.get("founder_names", [])
            funding_info = initial_info.get("funding_info", "")
            
            # 取得 industry_info
            industry_info = initial_info.get("Industry_Info", "")
            
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
                founder_info = await self._search_founder_names(company_name, deck_data, industry_info)
                founder_names = founder_info.get("founder_names", [])
            else:
                # Skip one AI_prompt slot if founder names are already found
                for i in range(1, 6):
                    if not self.input_data[f"AI Prompt{i}"]:
                        self.input_data[f"AI Prompt{i}"] = "Skipped - Founder names already found"
                        self.input_data[f"AI Content{i}"] = json.dumps({"skipped": True, "reason": "Founder names already found"}, ensure_ascii=False)
                        break
                
                # Skip one Web_prompt slot if founder names are already found
                for i in range(1, 4):
                    if not self.input_data[f"Web Prompt{i}"]:
                        self.input_data[f"Web Prompt{i}"] = "Skipped - Founder names already found"
                        self.input_data[f"Web Content{i}"] = json.dumps({"skipped": True, "reason": "Founder names already found"}, ensure_ascii=False)
                        break
            
            self.logger.info(f"找到創辦人名稱: {founder_names}")
            
            #尋找更多公司信息
            company_info = await self._get_company_details(company_name, founder_names, message_text, deck_data, industry_info)
            company_category = company_info.get("company_category", "N/A")
            self.logger.info(f"獲取到公司 {company_name} 的額外信息")

            
            #為每個創辦人獨立研究背景
            if founder_names:
                # 只處理第一位創辦人（簡單解決方案）
                first_founder = founder_names[0]
                founder_info = await self._research_founder_background(first_founder, company_name, deck_data, industry_info, message_text)
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
                    self.input_data[f"Web Prompt{i}"] = f"Error detected, please view log"
                    self.input_data[f"Web Content{i}"] = "Error detected, please view log"
            
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
            result = await self._get_completion(prompt, "initial_info")
            # 如果 company_name 抓不到，raise Exception
            if not result.get("company_name"):
                raise ValueError("❌ 無法從訊息中擷取公司名稱，流程終止。請提供更明確的公司資訊。")
            return result
        except Exception as e:
            self.logger.error(f"提取初始信息時出錯: {str(e)}")
            self.logger.error(traceback.format_exc())
            raise  # 讓 analyze_deal 捕捉

    async def _search_founder_names(self, company_name: str, deck_data: str, industry_info: str) -> Dict[str, Any]:
        try:
            self.logger.info(f"搜索 {company_name} 的創始人")
            
            # 使用 prompt_manager 獲取搜索查詢
            search_queries = [
                self.prompt_manager.get_prompt_and_format(
                    'search_founder_names_web',
                    company_name=company_name,
                    industry_info=industry_info
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
                    deck_data=deck_data,
                    industry_info=industry_info
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
                
                # 修正：同時支援 founders 為 dict list 或 string list
                for founder in founders:
                    if isinstance(founder, dict):
                        name = founder.get('name')
                        title = founder.get('title', 'N/A')
                    else:
                        name = founder
                        title = 'N/A'
                    if name and name not in found_info['founder_names']:
                        found_info['founder_names'].append(name)
                        found_info['founder_titles'].append(title)
                    break  # 如果找到創始人，停止搜索
            
            return found_info
                
        except Exception as e:
            self.logger.error(f"搜索創始人時出錯: {str(e)}", exc_info=True)
            return {'founder_names': [], 'founder_titles': []}

    async def _get_company_details(self, company_name: str, founder_names: list, message_text: str, deck_data: str, industry_info: str) -> Dict[str, Any]:
        try:
            # 使用 prompt_manager 獲取搜索查詢
            search_query = self.prompt_manager.get_prompt_and_format(
                'get_company_search_query',
                company_name=company_name,
                founder_names=founder_names,
                industry_info=industry_info
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
                search_content=search_content,
                industry_info=industry_info
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

    async def _research_founder_background(self, founder_name: str, company_name: str, deck_data: str, industry_info: str, message_text: str) -> Dict[str, Any]:
        try:
            self.logger.info(f"研究 {founder_name} 的背景")
            # 先進行一次 web search
            web_query = f"{founder_name} {company_name} {industry_info} 創辦人背景 {deck_data[:100]}"
            web_result = await self._web_search(web_query)
            search_content = web_result.get('content', '') if web_result else ''

            # 直接呼叫 linkedin_sourcing 取得結構化 dict
            profile_url, ln_structured = await get_linkedin_profile_html(company_name, founder_name, return_structured=True)
            # 1. LinkedIn profile name 檢查
            profile_name = ln_structured.get("name") if ln_structured else None
            if not profile_name or profile_name.strip().lower() != founder_name.strip().lower():
                self.logger.warning(f"LinkedIn profile name '{profile_name}' does not match founder_name '{founder_name}'，停止 LinkedIn Research。")
                ln_structured = {}
            # ln_structured 會有 about/experience/education 等欄位
            prompt = self.prompt_manager.get_prompt_and_format(
                'research_founder_background',
                founder_name=founder_name,
                linkedin_structured=ln_structured,
                deck_data=deck_data,
                search_content=search_content,
                industry_info=industry_info,
                message_text=message_text
            )
            founder_info = await self._get_completion(prompt, "founder_background")
            return {
                **founder_info,
                "linkedin_structured": ln_structured,
                "LinkedIn URL": profile_url
            }
        except Exception as e:
            self.logger.error(f"研究創始人背景時出錯: {str(e)}", exc_info=True)
            return {
                'title': 'N/A',
                'background': 'N/A',
                'previous_companies': 'N/A',
                'education': 'N/A',
                'achievements': 'N/A',
                'sources': [],
                'LinkedIn URL': 'N/A',
                'linkedin_structured': {},
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
            
            # 根據模型類型選擇不同的 API 調用方式
            model_lower = self.search_model.lower()
            text_content = ""
            citations = []
            
            if model_lower.startswith("o3"):
                # O3 / o3-mini / o3-pro 模型使用 Format2
                self.logger.info("使用 Format2")
                response = await self.openai_client.responses.create(
                    model=self.search_model,
                    input=[{"role": "user", "content": query}],
                    reasoning={
                        "effort": "medium",
                        "summary": "auto"
                    },
                    store=True
                )
                
                # 獲取搜索結果
                if hasattr(response, 'output_text'):
                    text_content = response.output_text
                elif hasattr(response, 'output') and isinstance(response.output, list) and response.output:
                    text_content = str(response.output[0])
                
                # 檢查是否有引用
                if hasattr(response, 'citations'):
                    citations = response.citations
                    
            else:
                # GPT-4/3.5 使用 chat.completions.create API
                self.logger.info("使用 Format1")
                
                response = await self.openai_client.responses.create(
                    model=self.search_model,
                    input=[{"role": "user", "content": query}],
                    tools=[{
                            "type": "web_search",
                            "search_context_size": "medium"
                            }],
                    temperature=0,
                    top_p=1,
                    store=True
                    )
                
                # 獲取搜索結果
                if hasattr(response, 'output_text'):
                    text_content = response.output_text
                elif hasattr(response, 'output') and isinstance(response.output, list) and response.output:
                    text_content = str(response.output[0])
                
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
            
            return {
                'content': f"搜索失敗: {str(e)}",
                'citations': []
            }

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
            if result_type == "category":
                # 限制 Category Prompt 和 Content 長度，避免寫入 Sheets 時出錯
                maxlen = 1000
                safe_prompt = prompt[:maxlen] if len(prompt) > maxlen else prompt
                safe_content = json.dumps(response, ensure_ascii=False)
                if len(safe_content) > maxlen:
                    safe_content = safe_content[:maxlen]
                self.input_data["Category Prompt"] = safe_prompt
                self.input_data["Category Content"] = safe_content
            else:
                # 其他情況，找第一個空的 AI Prompt 位置
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

if __name__ == "__main__":
    import os
    import json
    import asyncio
    from prompt_manager import GoogleSheetPromptManager

    async def main():
        # 測試輸入
        message_text = """
        Superform
        CEO is Vikram Arun

        https://docsend.com/view/u89ffgabbsvugtud/d/gnakfcdzn52uvmq5

        pw: wealthy2025
        """
        deck_data = """'[Slide 3]\ni\nody |\n| * [I\n\nNormie Tech\n\nNo KYC fiat to stablecoin payments\n\n\n\n[Slide 6]\nPROBLEM\n\n>50M businesses struggle to\nreceive non-inflationary\ncurrency from their customers\n\nWe experienced this >)\n\nprevious startup\n\nTeaching customers to send\nStablecoins is too much friction ———\n\n=>\n\nNormie Tech\n\n\n[Slide 9]\nie Normie Tech\n\nDID YOU KNOW...\n\nThere is a way to send stablecoins\nwithout owning crypto or using an\nexchange!\n\n\n[Slide 12]\nSOLUTION\n\nCustomer Sees\n\nBilling information\n\nisiness purchase\n\nUnited States of America\n\nAlabama\n\nPayment Method\n\nVISA @®\n\nhave a coupon code\n\n| touches crypto so }\n! they\n\nSender never\n\ndon't KYC \'\n\nVY Payment Sent\n\nIN\n\n¢\n\niS\n"Se\n\nA checkout page that\nforwards card payments\nas stablecoins\n\nReceiver Sees\n\nTo Amount Token\n\nOxF7d4668d...1e8129DD6 100\n\nNormie Tech\n\n© USD Coin (USDC)\n\n\n[Slide 15]\nie Normie Tech\n\nWHAT MAKES US UNIQUE\n\nPe scsesersannonsy\nSS\nSS =D\n\n\n\n[Slide 18]\ni Normie Tech\n\nTRACTION\na4 i—t\n\n~ $70,000 $50,000 Oct 2024\nFounding date\n\nProcessed ARR Bootstrapped until March\n\nWe're just getting started\n\n\n[Slide 21]\nie Normie Tech\n\nMARKET\n\nIn organic stablecoin payments in 2023\n\nGrowth YOY\n\n2023 2030 2035\n\n\n[Slide 24]\nGTM\n\n-Web3 platforms\n-Software developers\n\n-Hotels in high inflation countries\n\na\n\n-Marketing to all businesses that want payments in stablecoins\n\nNormie Tech\n\n\n[Slide 27]\nie Normie Tech\n\nINSIGHTS FROM 8 PILOTS\n\nHow to Address Chargebacks with a Legally Binding 2FA\n\nHow To Go Where Stripe Cannot with Stablecoins Surpassing\n"Convert to Local Currency" Regulations\n\nHow Customers Are Different than Remitters - They Care\nMore About Ease and Familiarity than Fees\n\n\n[Slide 30]\nMEET THE TEAM\n\nWorked together for a\nyear on a previous\nblockchain startup\n\nNoah Chon Lee - CEO\n\n-Built a team of 70 as a founding\nmember of a startup with a senior\nresearcher from OpenAl\n\n-Managed a1M grant program for\nVitalik Buterin and repeatedly saw\nthe #1 issue of onboarding limiting\nhundreds of projects\n\n7 ee 2\ng a .-\nCat « ee-. -.\nce. 4 —\noe. ees \' Hi ds i qf\n\nDipanshu Singh - CTO\n\n-Built a top 3 trending app in\nNigeria at age 14\n\n-First job at a software firm by 15\n-Co-authored a blockchain\nresearch paper by 17\n\n-Winner of 5 blockchain\nhackathons\n\n-Founding engineer of 2 startups\n\nie Normie Tech\n\nNithin Varma\nSenior Developer\n\nAryan Tiwari\nSenior Developer\n\n\n[Slide 33]\nNormie Tech\n\nWHAT OUR CLIENTS SAY\n\nY@e Will Ruddick | Grassroots Economics\n\' last seen recently\n\ndude 04:54 aM\n\nit\'s all working 64-55 ayy Wednesday\n\nit\'s FUCKING amazing 94:55 ayy\n\nOMY 04:55 AM\nOMY 04:55 AM\nOMY 04:55 AM\n\nWOW 04:55 AM\n\nneed to do some announcements .... so excited 94-55 ayy\n\nthanks so much! 9y-55 ayy\n\nHELL YEAH! 99-99 am\n'}]"""
        analyzer = DealAnalyzer(prompt_manager=GoogleSheetPromptManager())
        result = await analyzer.analyze_deal(message_text, deck_data)
        print(json.dumps(result, ensure_ascii=False, indent=2))

    asyncio.run(main())
