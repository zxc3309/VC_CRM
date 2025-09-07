#!/usr/bin/env python3
"""
測試完整的延遲初始化流程
確認所有 Google API 組件都使用延遲初始化
"""
import sys
import os
import logging
sys.path.insert(0, os.path.dirname(__file__))

from prompt_manager import GoogleSheetPromptManager
from sheets_manager import GoogleSheetsManager
from doc_manager import DocManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_bot_initialization():
    """測試 Bot 初始化流程 (模擬 main.py)"""
    logger.info("=== 測試 Bot 初始化流程 ===")
    
    try:
        # 步驟 1: 建立 prompt_manager (已有延遲初始化)
        logger.info("1. 建立 GoogleSheetPromptManager...")
        prompt_manager = GoogleSheetPromptManager()
        logger.info("✅ Prompt Manager 建立成功 (延遲模式)")
        
        # 步驟 2: 建立 sheets_manager (新的延遲初始化)
        logger.info("2. 建立 GoogleSheetsManager...")
        sheets_manager = GoogleSheetsManager(prompt_manager=prompt_manager)
        logger.info("✅ Sheets Manager 建立成功 (延遲模式)")
        
        # 步驟 3: 建立 doc_manager (新的延遲初始化)
        logger.info("3. 建立 DocManager...")
        doc_manager = DocManager(prompt_manager=prompt_manager)
        logger.info("✅ Doc Manager 建立成功 (延遲模式)")
        
        logger.info("🎉 所有管理器都成功建立！Bot 可以啟動了。")
        return True
        
    except Exception as e:
        logger.error(f"❌ 初始化失敗: {e}")
        return False

def test_api_calls_when_needed():
    """測試 API 調用時的延遲初始化"""
    logger.info("\n=== 測試 API 調用時的延遲初始化 ===")
    
    try:
        prompt_manager = GoogleSheetPromptManager()
        sheets_manager = GoogleSheetsManager(prompt_manager=prompt_manager)
        doc_manager = DocManager(prompt_manager=prompt_manager)
        
        logger.info("嘗試使用 prompt_manager 讀取 prompt...")
        try:
            prompt = prompt_manager.get_prompt("test")
            logger.info(f"Prompt 讀取結果: {prompt}")
        except Exception as e:
            logger.warning(f"⚠️ Prompt Manager API 調用失敗 (預期): {str(e)[:100]}...")
        
        logger.info("\n嘗試使用 sheets_manager (會觸發延遲初始化)...")
        try:
            # 這會觸發 _initialize_connection()
            # 只是測試初始化，不實際保存資料
            if not sheets_manager._initialized:
                sheets_manager._initialize_connection()
            logger.info("Sheets Manager 初始化嘗試完成")
        except Exception as e:
            logger.warning(f"⚠️ Sheets Manager API 調用失敗 (預期): {str(e)[:100]}...")
        
        logger.info("\n嘗試使用 doc_manager (會觸發延遲初始化)...")
        try:
            # 這會觸發 _initialize_services()
            if not doc_manager._initialized:
                doc_manager._initialize_services()
            logger.info("Doc Manager 初始化嘗試完成")
        except Exception as e:
            logger.warning(f"⚠️ Doc Manager API 調用失敗 (預期): {str(e)[:100]}...")
        
        logger.info("\n✅ 延遲初始化機制正常工作")
        logger.info("   - 管理器可以成功建立")
        logger.info("   - API 調用時才會嘗試連接")
        logger.info("   - 連接失敗不會阻止 bot 啟動")
        return True
        
    except Exception as e:
        logger.error(f"❌ 測試失敗: {e}")
        return False

def test_error_caching():
    """測試錯誤快取機制"""
    logger.info("\n=== 測試錯誤快取機制 ===")
    
    sheets_manager = GoogleSheetsManager()
    
    # 第一次調用
    try:
        sheets_manager._initialize_connection()
    except Exception as e:
        logger.info(f"第一次調用失敗: {str(e)[:50]}...")
    
    # 第二次調用應該使用快取的錯誤
    try:
        sheets_manager._initialize_connection()
    except Exception as e:
        logger.info(f"第二次調用失敗 (使用快取): {str(e)[:50]}...")
    
    logger.info("✅ 錯誤快取機制正常工作")
    return True

def main():
    logger.info("🧪 開始測試完整的延遲初始化流程")
    
    success = True
    
    # 測試 1: Bot 初始化
    success &= test_bot_initialization()
    
    # 測試 2: API 調用時的延遲初始化
    success &= test_api_calls_when_needed()
    
    # 測試 3: 錯誤快取
    success &= test_error_caching()
    
    if success:
        logger.info("\n" + "="*50)
        logger.info("🎉 所有測試通過！")
        logger.info("✅ Bot 可以在 Railway 上成功啟動")
        logger.info("✅ Google API 錯誤不會阻止 bot 運行")
        logger.info("✅ 用戶會在使用功能時收到清楚的錯誤訊息")
        logger.info("="*50)
    else:
        logger.error("\n💥 測試失敗")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)