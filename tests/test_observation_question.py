#!/usr/bin/env python3
"""
測試腳本：驗證 Google Sheet 的 prompt 是否正確產生 observation 和 question
"""
import asyncio
import json
import logging
import sys
import os
# 添加父目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dotenv import load_dotenv
from prompt_manager import GoogleSheetPromptManager
from openai import AsyncOpenAI

# 設置日誌
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_suggest_questions_prompt():
    """測試 suggest_questions prompt 是否正確產生 JSON 格式的 observation 和 questions"""
    
    # 強制重新載入環境變數
    load_dotenv(override=True)
    
    print(f"📁 工作目錄: {os.getcwd()}")
    print(f"🔍 .env 檔案存在: {os.path.exists('.env')}")
    
    # 初始化
    prompt_manager = GoogleSheetPromptManager()
    openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # 測試資料
    test_deal_data = {
        "company_name": "TrueNorth",
        "founder_name": ["Willy", "Alex"],
        "company_info": {
            "company_introduction": "Crypto's first AI discovery engine using agentic technology"
        },
        "founder_info": {
            "title": "Co-founders",
            "background": "Serial entrepreneur, Forbes 30 Under 30",
            "previous_companies": "WOO, McKinsey, Temasek",
            "education": "PhD in AI",
            "achievements": "Successful M&A exit"
        },
        "funding_info": "Backed by Cyber Fund, Delphi Labs",
        "company_category": "AI/Crypto"
    }
    
    # 從 prompt manager 獲取問題列表
    question_list1 = prompt_manager.get_prompt('question_list1') or "Default question list 1"
    question_list2 = prompt_manager.get_prompt('question_list2') or "Default question list 2"
    question_list3 = prompt_manager.get_prompt('question_list3') or "Default question list 3"
    question_list4 = prompt_manager.get_prompt('question_list4') or "Default question list 4"
    
    logger.info("=" * 80)
    logger.info("開始測試 suggest_questions prompt")
    logger.info("=" * 80)
    
    # 獲取並顯示 prompt
    try:
        prompt = prompt_manager.get_prompt_and_format(
            'suggest_questions',
            deal_data=json.dumps(test_deal_data, ensure_ascii=False),
            question_list1=question_list1,
            question_list2=question_list2,
            question_list3=question_list3,
            question_list4=question_list4
        )
        
        logger.info("\n📝 使用的 Prompt:")
        logger.info("-" * 40)
        logger.info(prompt[:500] + "..." if len(prompt) > 500 else prompt)
        logger.info("-" * 40)
        
    except Exception as e:
        logger.error(f"❌ 無法獲取 prompt: {e}")
        logger.error("請確認 Google Sheet 中有 'suggest_questions' prompt")
        return
    
    # 呼叫 OpenAI API
    try:
        logger.info("\n🤖 呼叫 OpenAI API...")
        
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",  # 使用較便宜的模型進行測試
            messages=[
                {"role": "system", "content": "You are a professional VC analyst."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        raw_content = response.choices[0].message.content
        logger.info("\n📄 AI 原始回應:")
        logger.info("-" * 40)
        logger.info(raw_content[:1000] + "..." if len(raw_content) > 1000 else raw_content)
        logger.info("-" * 40)
        
        # 解析 JSON
        try:
            result_json = json.loads(raw_content)
            logger.info("\n✅ 成功解析 JSON")
            
            # 檢查必要欄位
            has_questions = "questions" in result_json
            has_observation = "observation" in result_json
            
            logger.info(f"\n📊 欄位檢查:")
            logger.info(f"  - 'questions' 欄位: {'✅ 存在' if has_questions else '❌ 缺失'}")
            logger.info(f"  - 'observation' 欄位: {'✅ 存在' if has_observation else '❌ 缺失'}")
            
            if has_questions:
                questions = result_json["questions"]
                logger.info(f"\n  📌 Questions (共 {len(questions)} 個):")
                for i, q in enumerate(questions[:3], 1):  # 只顯示前3個
                    logger.info(f"     {i}. {q}")
                if len(questions) > 3:
                    logger.info(f"     ... (還有 {len(questions)-3} 個)")
            
            if has_observation:
                observations = result_json["observation"]
                logger.info(f"\n  👁️ Observations (共 {len(observations)} 個):")
                for i, o in enumerate(observations[:3], 1):  # 只顯示前3個
                    logger.info(f"     {i}. {o}")
                if len(observations) > 3:
                    logger.info(f"     ... (還有 {len(observations)-3} 個)")
            
            # 診斷結果
            logger.info("\n" + "=" * 80)
            if has_questions and has_observation:
                logger.info("✅ 測試成功！Prompt 正確產生了 questions 和 observation")
            else:
                logger.info("⚠️ 測試失敗！Prompt 沒有產生預期的欄位")
                logger.info("\n建議修改 Google Sheet 中的 'suggest_questions' prompt，確保包含以下指示：")
                logger.info("""
請務必以下列 JSON 格式返回結果：
{
  "questions": [
    "問題1",
    "問題2",
    ...
  ],
  "observation": [
    "觀察1",
    "觀察2",
    ...
  ]
}
                """)
            logger.info("=" * 80)
            
        except json.JSONDecodeError as e:
            logger.error(f"\n❌ 無法解析 JSON: {e}")
            logger.error("AI 返回的不是有效的 JSON 格式")
            logger.error("\n建議在 prompt 中加入明確的 JSON 格式要求")
            
    except Exception as e:
        logger.error(f"\n❌ API 呼叫失敗: {e}")
        
if __name__ == "__main__":
    asyncio.run(test_suggest_questions_prompt())