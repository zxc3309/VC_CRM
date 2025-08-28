#!/usr/bin/env python3
"""
測試優雅降級和錯誤處理改進
確認 Bot 在 Google API 失敗時仍能運作
"""
import sys
import os
import logging
import asyncio
sys.path.insert(0, os.path.dirname(__file__))

from unittest.mock import Mock, AsyncMock, MagicMock

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_message_handling_with_google_failures():
    """測試當 Google API 失敗時的訊息處理"""
    logger.info("=== 測試 Google API 失敗時的訊息處理 ===")
    
    # 模擬必要的組件
    from main import DealSourcingBot
    
    try:
        # 建立 bot 實例
        logger.info("建立 DealSourcingBot...")
        bot = DealSourcingBot()
        logger.info("✅ Bot 建立成功")
        
        # 模擬 Telegram update 和 context
        update = Mock()
        update.message = Mock()
        update.message.chat_id = 123456
        update.message.text = "Test company information"
        update.message.caption = None
        update.message.document = None
        update.message.reply_text = AsyncMock()
        update.effective_user = Mock()
        update.effective_user.id = 123456
        
        context = Mock()
        context.bot = Mock()
        
        # 建立一個模擬的 processing_msg
        processing_msg = Mock()
        processing_msg.edit_text = AsyncMock()
        update.message.reply_text.return_value = processing_msg
        
        # 模擬 deck_browser 返回資料
        bot.deck_browser.process_input = AsyncMock(return_value="Test deck data")
        
        # 模擬 deal_analyzer 返回分析結果
        bot.deal_analyzer.analyze_deal = AsyncMock(return_value={
            "deal_data": {
                "company_name": "Test Company",
                "company_category": "SaaS",
                "company_info": {"company_one_liner": "Test description"},
                "founder_name": ["John Doe", "Jane Smith"]
            },
            "input_data": {}
        })
        
        # 模擬 doc_manager 失敗 (Google API 錯誤)
        bot.doc_manager.create_doc = AsyncMock(
            side_effect=Exception("Invalid JWT Signature")
        )
        
        # 模擬 sheets_manager 失敗 (Google API 錯誤)
        bot.sheets_manager.save_deal = AsyncMock(
            side_effect=Exception("Invalid JWT Signature")
        )
        
        logger.info("開始處理訊息...")
        await bot.handle_message(update, context)
        
        # 檢查是否有調用 edit_text
        assert processing_msg.edit_text.called, "應該要發送回應訊息"
        
        # 檢查回應訊息內容
        call_args = processing_msg.edit_text.call_args
        response_text = call_args[0][0] if call_args else ""
        
        logger.info(f"回應訊息:\n{response_text}")
        
        # 驗證訊息包含預期內容
        assert "Test Company" in response_text, "應包含公司名稱"
        assert "John Doe" in response_text or "Jane Smith" in response_text, "應包含創辦人"
        assert "Google services" in response_text or "Could not save" in response_text, "應提到 Google 服務問題"
        
        logger.info("✅ 訊息處理成功完成，即使 Google API 失敗")
        return True
        
    except Exception as e:
        logger.error(f"❌ 測試失敗: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def test_partial_google_failure():
    """測試部分 Google 服務失敗的情況"""
    logger.info("\n=== 測試部分 Google 服務失敗 ===")
    
    from main import DealSourcingBot
    
    try:
        bot = DealSourcingBot()
        
        # 模擬 update 和 context
        update = Mock()
        update.message = Mock()
        update.message.chat_id = 123456
        update.message.text = "Test partial failure"
        update.message.caption = None
        update.message.document = None
        update.message.reply_text = AsyncMock()
        update.effective_user = Mock()
        update.effective_user.id = 123456
        
        context = Mock()
        
        processing_msg = Mock()
        processing_msg.edit_text = AsyncMock()
        update.message.reply_text.return_value = processing_msg
        
        # 模擬基本功能正常
        bot.deck_browser.process_input = AsyncMock(return_value="Test deck")
        bot.deal_analyzer.analyze_deal = AsyncMock(return_value={
            "deal_data": {"company_name": "Partial Test Co"},
            "input_data": {}
        })
        
        # 模擬 doc_manager 成功
        bot.doc_manager.create_doc = AsyncMock(return_value={
            "doc_url": "https://docs.google.com/document/d/test123"
        })
        
        # 模擬 sheets_manager 失敗
        bot.sheets_manager.save_deal = AsyncMock(
            side_effect=Exception("Sheets API error")
        )
        
        await bot.handle_message(update, context)
        
        call_args = processing_msg.edit_text.call_args
        response_text = call_args[0][0] if call_args else ""
        
        logger.info(f"部分失敗回應:\n{response_text}")
        
        # 驗證包含成功和失敗的資訊
        assert "docs.google.com" in response_text, "應包含成功的 Doc URL"
        assert "Could not save to Google Sheets" in response_text or "partially complete" in response_text, "應提到 Sheets 失敗"
        
        logger.info("✅ 部分服務失敗處理正確")
        return True
        
    except Exception as e:
        logger.error(f"❌ 測試失敗: {e}")
        return False

async def main():
    logger.info("🧪 開始測試優雅降級和錯誤處理")
    
    success = True
    
    # 測試 1: 所有 Google 服務失敗
    success &= await test_message_handling_with_google_failures()
    
    # 測試 2: 部分 Google 服務失敗
    success &= await test_partial_google_failure()
    
    if success:
        logger.info("\n" + "="*50)
        logger.info("🎉 所有測試通過！")
        logger.info("✅ Bot 可以在 Google API 失敗時繼續運作")
        logger.info("✅ 用戶收到有用的錯誤訊息")
        logger.info("✅ 分析結果仍然顯示給用戶")
        logger.info("="*50)
    else:
        logger.error("\n💥 測試失敗")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)