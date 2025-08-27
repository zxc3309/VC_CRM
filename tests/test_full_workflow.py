#!/usr/bin/env python3
"""
完整工作流程測試：模擬 Telegram Bot 完整處理流程
測試 Google Doc 中是否正確產生 Observation 和 Suggested Questions
"""
import asyncio
import json
import logging
import sys
import os
from datetime import datetime

# 添加 VC_CRM 目錄到路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'VC_CRM'))

from dotenv import load_dotenv
from deck_browser import DeckBrowser
from deal_analyzer import DealAnalyzer
from doc_manager import DocManager
from sheets_manager import GoogleSheetsManager
from prompt_manager import GoogleSheetPromptManager

# 設置詳細日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_full_workflow():
    """測試完整的工作流程"""
    
    print("=" * 80)
    print("🤖 開始完整工作流程測試")
    print("=" * 80)
    
    # 載入環境變數
    load_dotenv(override=True)
    
    # 測試訊息
    test_message = """TrueNorth
Crypto's first AI discovery engine that uses agentic technology to unlock a symbiotic user journey - from intent straight to outcome

Co-founders

Willy: Serial entrepreneur with a successful M&A exit (Series-B SaaS startup), Forbes 30 Under 30 China, ex-COO and acting CEO of WOO.

Alex: PhD in AI & Domain-Specific Computing, ex-McKinsey, ex-Temasek, Head of Product, Strategy and Capital Market at Enflame (~USD3b pre-IPO AI chip startup), and the Tech Founding Partner of Iluvatar (~USD2b pre-IPO AI chip startup).

Backed by
Cyber Fund, Delphi Labs and founders, GPs from Layerzero, Virtuals, Selini, SEI, Merlin, Presto, LTP, Initial, Generative and more.

Website
https://true-north.xyz/"""

    print(f"📝 測試訊息:")
    print("-" * 40)
    print(test_message)
    print("-" * 40)
    
    try:
        # 步驟 1: 初始化所有組件
        print("\n🔧 步驟 1: 初始化組件...")
        
        prompt_manager = GoogleSheetPromptManager()
        deck_browser = DeckBrowser(prompt_manager=prompt_manager)
        deal_analyzer = DealAnalyzer(prompt_manager=prompt_manager)
        doc_manager = DocManager(prompt_manager=prompt_manager)
        sheets_manager = GoogleSheetsManager(prompt_manager=prompt_manager)
        
        print("✅ 所有組件初始化完成")
        
        # 步驟 2: DeckBrowser 處理訊息
        print("\n📄 步驟 2: DeckBrowser 處理訊息...")
        deck_data = await deck_browser.process_input(test_message, attachments=None)
        print(f"✅ DeckBrowser 完成，擷取到 {len(deck_data)} 項結果")
        
        if deck_data:
            print(f"📊 DeckBrowser 結果預覽: {str(deck_data)[:200]}...")
        
        # 步驟 3: DealAnalyzer 分析
        print("\n🔍 步驟 3: DealAnalyzer 分析...")
        analysis_result = await deal_analyzer.analyze_deal(test_message, deck_data)
        
        if "error" in analysis_result:
            print(f"❌ 分析失敗: {analysis_result['error']}")
            return
            
        deal_data = analysis_result["deal_data"]
        input_data = analysis_result["input_data"]
        
        print(f"✅ DealAnalyzer 完成")
        print(f"📈 公司名稱: {deal_data.get('company_name', 'N/A')}")
        print(f"👥 創辦人: {deal_data.get('founder_name', [])}")
        print(f"🏷️ 分類: {deal_data.get('company_category', 'N/A')}")
        
        # 步驟 4: DocManager 創建文件（包含 observation 和 questions）
        print("\n📝 步驟 4: DocManager 創建 Google Doc...")
        print("⚠️  重要：這步驟會產生 observation 和 suggested questions")
        
        result = await doc_manager.create_doc(deal_data, input_data)
        doc_url = result["doc_url"]
        
        print(f"✅ Google Doc 創建完成!")
        print(f"🔗 文件連結: {doc_url}")
        
        # 步驟 5: 檢查 observation 和 questions 是否成功產生
        print("\n🔍 步驟 5: 驗證 Observation 和 Questions...")
        
        # 檢查 input_data 中是否有相關內容
        ai_prompt5 = input_data.get("AI Prompt5", "")
        ai_content5 = input_data.get("AI Content5", "")
        
        if ai_prompt5:
            print("✅ 找到 AI Prompt5（suggest_questions 的 prompt）")
            print(f"📝 Prompt 長度: {len(ai_prompt5)} 字符")
        else:
            print("❌ 未找到 AI Prompt5")
            
        if ai_content5:
            print("✅ 找到 AI Content5（AI 回應）")
            try:
                ai_response = json.loads(ai_content5)
                questions = ai_response.get("questions", [])
                observations = ai_response.get("observation", [])
                
                print(f"📊 統計:")
                print(f"  - Questions: {len(questions)} 個")
                print(f"  - Observations: {len(observations)} 個")
                
                if questions:
                    print("✅ Questions 成功產生")
                    print("🤔 前 3 個問題:")
                    for i, q in enumerate(questions[:3], 1):
                        print(f"    {i}. {q[:100]}...")
                else:
                    print("❌ Questions 未產生")
                    
                if observations:
                    print("✅ Observations 成功產生")
                    print("👁️ 觀察內容:")
                    for i, obs in enumerate(observations[:3], 1):
                        print(f"    {i}. {obs}")
                else:
                    print("❌ Observations 未產生")
                    
            except json.JSONDecodeError as e:
                print(f"❌ 無法解析 AI Content5: {e}")
                print(f"原始內容: {ai_content5[:200]}...")
        else:
            print("❌ 未找到 AI Content5")
        
        # 步驟 6: SheetsManager 儲存（可選）
        print("\n📊 步驟 6: SheetsManager 儲存到 Google Sheets...")
        try:
            sheet_url = await sheets_manager.save_deal(deal_data, input_data, doc_url)
            print(f"✅ Google Sheets 更新完成")
            print(f"📋 Sheets 連結: {sheet_url}")
        except Exception as e:
            print(f"⚠️ Sheets 儲存失敗（可能是權限問題）: {e}")
        
        # 最終結果
        print("\n" + "=" * 80)
        print("🎉 測試完成！")
        print("=" * 80)
        print(f"📄 Google Doc: {doc_url}")
        print("\n💡 請檢查 Google Doc 是否包含以下區塊:")
        print("  ✓ Company Name")
        print("  ✓ Founder Information") 
        print("  ✓ Observation（AI 觀察）")
        print("  ✓ Suggested Questions（建議問題）")
        print("\n🔍 如果缺少 Observation 或 Questions，請查看上方的驗證結果")
        
    except Exception as e:
        print(f"\n❌ 測試過程中發生錯誤: {e}")
        import traceback
        print("詳細錯誤資訊:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_full_workflow())