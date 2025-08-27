#!/usr/bin/env python3
"""
專門測試 Observation 和 Questions 產生的簡化測試
不依賴 Google API，只測試核心邏輯
"""
import asyncio
import json
import logging
import sys
import os

# 添加 VC_CRM 目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'VC_CRM'))

from dotenv import load_dotenv
from openai import AsyncOpenAI
from prompt_manager import GoogleSheetPromptManager

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TestDocManager:
    """簡化的 DocManager 類別，專門測試 suggest_questions_with_gpt"""
    
    def __init__(self):
        load_dotenv(override=True)
        self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.prompt_manager = GoogleSheetPromptManager()
    
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

            # 使用 GoogleSheetPromptManager 獲取提示詞
            prompt = self.prompt_manager.get_prompt_and_format(
                'suggest_questions',
                deal_data=json.dumps(deal_data, ensure_ascii=False),
                question_list1=question_list1,
                question_list2=question_list2,
                question_list3=question_list3,
                question_list4=question_list4
            )

            # 取得 AI model
            ai_model = input_data.get('ai_model') or "gpt-4o-mini"  # 使用便宜的模型測試

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
            logger.info(f"[suggest_questions] AI 原始回應內容: {result[:500]}...")
            
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

            return questions, observation
        except Exception as e:
            logger.error(f"生成問題時發生錯誤：{str(e)}")
            return [], []

async def test_observation_and_questions():
    """專門測試 observation 和 questions 的產生"""
    
    print("=" * 80)
    print("🧪 測試 Observation 和 Questions 產生")
    print("=" * 80)
    
    # 測試數據
    test_deal_data = {
        "company_name": "TrueNorth",
        "founder_name": ["Willy", "Alex"],
        "company_info": {
            "company_introduction": "Crypto's first AI discovery engine using agentic technology to unlock a symbiotic user journey - from intent straight to outcome"
        },
        "founder_info": {
            "title": "Co-founders",
            "background": "Serial entrepreneur, Forbes 30 Under 30, PhD in AI",
            "previous_companies": "WOO, McKinsey, Temasek, Enflame, Iluvatar",
            "education": "PhD in AI & Domain-Specific Computing",
            "achievements": "Successful M&A exit, Forbes 30 Under 30"
        },
        "funding_info": "Backed by Cyber Fund, Delphi Labs and founders, GPs from Layerzero, Virtuals, SEI",
        "company_category": "AI/Crypto"
    }
    
    test_input_data = {
        "ai_model": "gpt-4o-mini",
        "search_model": "gpt-4o-mini"
    }
    
    try:
        print("🔧 初始化測試組件...")
        doc_manager = TestDocManager()
        print("✅ 初始化完成")
        
        print("\n🤖 開始產生 Observation 和 Questions...")
        questions, observations = await doc_manager.suggest_questions_with_gpt(
            test_deal_data, 
            test_input_data
        )
        
        print(f"\n📊 結果統計:")
        print(f"  - Questions: {len(questions)} 個")
        print(f"  - Observations: {len(observations)} 個")
        
        if questions:
            print("\n✅ Questions 成功產生!")
            print("🤔 問題內容:")
            for i, q in enumerate(questions, 1):
                print(f"  {i}. {q}")
        else:
            print("\n❌ Questions 未產生")
            
        if observations:
            print("\n✅ Observations 成功產生!")
            print("👁️ 觀察內容:")
            for i, obs in enumerate(observations, 1):
                print(f"  {i}. {obs}")
        else:
            print("\n❌ Observations 未產生")
        
        # 測試格式化功能
        if questions or observations:
            print("\n🎨 測試格式化功能...")
            formatted_questions = doc_manager.format_questions(questions)
            formatted_observations = doc_manager.format_observation(observations)
            
            print("\n📋 格式化後的 Questions:")
            print(formatted_questions)
            
            print("\n👁️ 格式化後的 Observations:")  
            print(formatted_observations)
        
        # 檢查儲存的內容
        ai_content5 = test_input_data.get("AI Content5", "")
        if ai_content5:
            print(f"\n💾 AI Content5 已儲存，長度: {len(ai_content5)} 字符")
            try:
                saved_data = json.loads(ai_content5)
                print(f"📦 儲存的欄位: {list(saved_data.keys())}")
            except:
                print("⚠️ 儲存的內容無法解析為 JSON")
        
        # 最終結果
        print("\n" + "=" * 80)
        if questions and observations:
            print("🎉 測試成功！Observation 和 Questions 都已正確產生")
            print("✅ 在實際的 Google Doc 中應該會看到這些內容")
        elif questions or observations:
            print("⚠️ 測試部分成功，但有些內容未產生")
        else:
            print("❌ 測試失敗，未產生任何 Observation 或 Questions")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 測試過程中發生錯誤: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_observation_and_questions())