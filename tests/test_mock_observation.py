#!/usr/bin/env python3
"""
Mock 版本測試：不依賴 Google Sheets，用模擬 prompt 測試 observation 和 questions
"""
import asyncio
import json
import logging
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MockPromptManager:
    """模擬的 Prompt Manager，不依賴 Google Sheets"""
    
    def __init__(self):
        # 模擬的 prompts
        self.prompts = {
            'question_list1': 'Heart questions: motivation, passion, vision',
            'question_list2': 'Head questions: strategy, market, competition',
            'question_list3': 'Hand questions: execution, team, operations',
            'question_list4': 'Delta questions: risks, challenges, pivots',
            'suggest_questions': """You are a senior VC analyst. Based on the pitch deck summary and founder information provided, please list your observations about the company and founders, and write 10 key questions to ask this startup team during the first meeting.

Please follow this analysis process:
1. Reference common question examples, review which questions are already answered in the data, and provide your observations based on existing data
2. Identify what information in the pitch deck or founder data is unclear, lacks detail, or cannot be answered
3. Propose suggested questions based on gaps, especially regarding founder experience and expertise gaps
4. Avoid repetitive or overly generic questions, ensure they are specific and insightful
5. For questions, please classify them as Heart, Head, Hand, or Delta categories
6. Please respond in English

---

Please focus on analyzing the "founder_info" section in "deal_data":
- Check if they have previous entrepreneurial experience, if so, ask specific questions about that experience
- Check if their background is unusual, or if there are significant changes in academic/career paths, or transitions between very different industries/positions

---

Please respond in JSON format:
{{
  "observation": [
    "Observation 1",
    "Observation 2", 
    "Observation 3"
  ],
  "questions": [
    "Question 1",
    "Question 2",
    ...
  ]
}}

Company Information:
{deal_data}

Reference Questions:
{question_list1}
{question_list2}
{question_list3}
{question_list4}"""
        }
    
    def get_prompt(self, prompt_id: str) -> str:
        return self.prompts.get(prompt_id, "")
    
    def get_prompt_and_format(self, prompt_id: str, **kwargs) -> str:
        raw_prompt = self.get_prompt(prompt_id)
        if not raw_prompt:
            raise ValueError(f"Prompt '{prompt_id}' not found.")
        
        # 確保所有參數都是 ASCII 安全的
        safe_kwargs = {}
        for key, value in kwargs.items():
            if isinstance(value, str):
                # 將中文字符轉為 ASCII 安全格式
                safe_kwargs[key] = value.encode('ascii', errors='ignore').decode('ascii')
            else:
                safe_kwargs[key] = str(value).encode('ascii', errors='ignore').decode('ascii')
        
        return raw_prompt.format(**safe_kwargs)

class MockDocManager:
    """模擬的 DocManager，測試 observation 和 questions 產生"""
    
    def __init__(self):
        # 從父目錄載入 .env 檔案
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
        if os.path.exists(env_path):
            load_dotenv(env_path, override=True)
            logger.info(f"✅ 從 {env_path} 載入環境變數")
        else:
            # 嘗試從當前目錄載入
            load_dotenv(override=True)
        
        # 取得並檢查 API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("未設定 OPENAI_API_KEY 環境變數")
        
        logger.info(f"✅ 已載入 OPENAI_API_KEY，長度: {len(api_key)} 字符")
        
        self.openai_client = AsyncOpenAI(api_key=api_key)
        self.prompt_manager = MockPromptManager()
    
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
    
    async def suggest_questions_with_gpt(self, deal_data, input_data):
        """根據 pitch deck 摘要，自動建議第一次接觸該新創應該問的問題"""
        try:
            # 從 prompt manager 獲取問題列表
            question_list1 = self.prompt_manager.get_prompt('question_list1')
            question_list2 = self.prompt_manager.get_prompt('question_list2')
            question_list3 = self.prompt_manager.get_prompt('question_list3')
            question_list4 = self.prompt_manager.get_prompt('question_list4')

            # 使用 prompt_manager 獲取提示詞
            # 將 deal_data 轉為 ASCII 安全的字符串
            deal_data_str = json.dumps(deal_data, ensure_ascii=True, indent=2)
            
            prompt = self.prompt_manager.get_prompt_and_format(
                'suggest_questions',
                deal_data=deal_data_str,
                question_list1=question_list1,
                question_list2=question_list2,
                question_list3=question_list3,
                question_list4=question_list4
            )

            # 取得 AI model
            ai_model = input_data.get('ai_model') or "gpt-4o-mini"

            logger.info(f"📝 使用的 prompt 長度: {len(prompt)} 字符")
            logger.info(f"🤖 使用的模型: {ai_model}")

            response = await self.openai_client.chat.completions.create(
                model=ai_model,
                messages=[
                    {"role": "system", "content": "You are a professional VC analyst."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )

            result = response.choices[0].message.content
            logger.info(f"[suggest_questions] AI 原始回應長度: {len(result)} 字符")
            
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
                logger.error(f"[suggest_questions] AI 返回內容: {result[:500]}...")

            # 新增：把 prompt 和結果放到 input_data
            input_data["AI Prompt5"] = prompt
            input_data["AI Content5"] = json.dumps(result_json, ensure_ascii=False)

            return questions, observation
        except Exception as e:
            logger.error(f"生成問題時發生錯誤：{str(e)}")
            import traceback
            logger.error("詳細錯誤追蹤:")
            logger.error(traceback.format_exc())
            return [], []

async def test_mock_observation():
    """使用模擬 prompt 測試 observation 和 questions"""
    
    print("=" * 80)
    print("🧪 Mock 測試：Observation 和 Questions 產生")
    print("=" * 80)
    
    # 測試數據 - 使用純 ASCII 字符
    test_deal_data = {
        "company_name": "TrueNorth",
        "founder_name": ["Willy", "Alex"],
        "company_info": {
            "company_introduction": "Crypto first AI discovery engine using agentic technology to unlock a symbiotic user journey from intent straight to outcome"
        },
        "founder_info": {
            "title": "Co-founders",
            "background": "Willy is a serial entrepreneur, Forbes 30 Under 30, ex-COO of WOO. Alex has PhD in AI, ex-McKinsey, ex-Temasek",
            "previous_companies": "WOO, McKinsey, Temasek, Enflame, Iluvatar",
            "education": "PhD in AI and Domain-Specific Computing",
            "achievements": "Successful M&A exit, Forbes 30 Under 30"
        },
        "funding_info": "Backed by Cyber Fund, Delphi Labs",
        "company_category": "AI/Crypto"
    }
    
    test_input_data = {
        "ai_model": "gpt-4o-mini"
    }
    
    try:
        print("🔧 初始化 Mock 組件...")
        doc_manager = MockDocManager()
        print("✅ 初始化完成（使用模擬 prompts）")
        
        print(f"\n📊 測試數據：")
        print(f"  公司: {test_deal_data['company_name']}")
        print(f"  創辦人: {test_deal_data['founder_name']}")
        print(f"  類別: {test_deal_data['company_category']}")
        
        print("\n🤖 開始產生 Observation 和 Questions...")
        questions, observations = await doc_manager.suggest_questions_with_gpt(
            test_deal_data, 
            test_input_data
        )
        
        print(f"\n📊 結果統計:")
        print(f"  - Questions: {len(questions)} 個")
        print(f"  - Observations: {len(observations)} 個")
        
        success = False
        
        if questions:
            print("\n✅ Questions 成功產生!")
            print("🤔 問題內容:")
            for i, q in enumerate(questions[:5], 1):  # 只顯示前5個
                print(f"  {i}. {q}")
            if len(questions) > 5:
                print(f"  ... (還有 {len(questions)-5} 個問題)")
            success = True
        else:
            print("\n❌ Questions 未產生")
            
        if observations:
            print("\n✅ Observations 成功產生!")
            print("👁️ 觀察內容:")
            for i, obs in enumerate(observations, 1):
                print(f"  {i}. {obs}")
            success = True
        else:
            print("\n❌ Observations 未產生")
        
        # 測試格式化功能
        if questions or observations:
            print("\n🎨 測試格式化功能...")
            formatted_questions = doc_manager.format_questions(questions)
            formatted_observations = doc_manager.format_observation(observations)
            
            print("\n📄 這就是會寫入 Google Doc 的格式:")
            print("\n【Suggested Questions】")
            print(formatted_questions)
            
            print("\n【Observation】")  
            print(formatted_observations)
        
        # 檢查儲存的內容
        ai_content5 = test_input_data.get("AI Content5", "")
        if ai_content5:
            print(f"\n💾 AI Content5 已儲存，長度: {len(ai_content5)} 字符")
        
        # 最終結果
        print("\n" + "=" * 80)
        if success:
            print("🎉 測試成功！")
            print("✅ 這表示您的系統邏輯是正確的")
            print("✅ 在實際的 Telegram Bot 中，Google Doc 應該會包含這些內容")
            print("💡 如果實際使用時看不到內容，可能是 Google API 憑證問題")
        else:
            print("❌ 測試失敗，未產生任何 Observation 或 Questions")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 測試過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mock_observation())