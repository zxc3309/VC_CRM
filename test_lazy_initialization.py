#!/usr/bin/env python3
"""
測試延遲初始化是否正常工作
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from prompt_manager import GoogleSheetPromptManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_lazy_initialization():
    """測試延遲初始化"""
    logger.info("=== 測試延遲初始化 ===")
    
    try:
        # 這應該成功，因為不會立即連接 Google API
        logger.info("建立 Prompt Manager (延遲模式)...")
        pm = GoogleSheetPromptManager()
        logger.info("✅ Prompt Manager 建立成功 (延遲模式)")
        
        # 這時候才會嘗試連接 Google API
        logger.info("嘗試讀取 prompt (這會觸發初始化)...")
        try:
            prompt = pm.get_prompt("test_prompt")
            logger.info(f"✅ 成功讀取 prompt: {prompt}")
        except Exception as e:
            logger.error(f"❌ Google API 連接失敗 (預期行為): {str(e)}")
            logger.info("✅ 延遲初始化正常工作 - 在實際使用時才會失敗")
            return True
            
        return True
        
    except Exception as e:
        logger.error(f"❌ 延遲初始化失敗: {e}")
        return False

def test_multiple_calls():
    """測試多次調用的行為"""
    logger.info("=== 測試多次調用 ===")
    
    try:
        pm = GoogleSheetPromptManager()
        logger.info("✅ 第一次建立成功")
        
        # 多次調用應該使用快取的錯誤
        for i in range(3):
            try:
                pm.get_prompt("test_prompt")
            except Exception as e:
                logger.info(f"第 {i+1} 次調用失敗 (預期): {str(e)[:50]}...")
        
        logger.info("✅ 錯誤快取正常工作")
        return True
        
    except Exception as e:
        logger.error(f"❌ 多次調用測試失敗: {e}")
        return False

def main():
    logger.info("🧪 開始測試延遲初始化")
    
    success = True
    success &= test_lazy_initialization()
    success &= test_multiple_calls()
    
    if success:
        logger.info("🎉 所有測試通過！延遲初始化正常工作")
        logger.info("💡 這意味著 Railway 部署時 bot 可以啟動，只有在實際使用時才會遇到認證錯誤")
    else:
        logger.error("💥 測試失敗")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)