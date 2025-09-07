#!/usr/bin/env python3
"""
測試日誌設定是否正確減少冗餘訊息
"""
import os
import logging
from dotenv import load_dotenv

# 載入環境變數
load_dotenv(override=True)

# 模擬 main.py 的日誌設定
log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=getattr(logging, log_level)
)

# 降低第三方套件的日誌等級
loggers_to_quiet = [
    'httpx', 'telegram', 'urllib3', 'asyncio', 
    'playwright', 'websockets', 'aiohttp', 'requests',
    'telegram.ext.Application', 'telegram.ext.Updater'
]
for logger_name in loggers_to_quiet:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

# 測試不同等級的日誌
main_logger = logging.getLogger(__name__)
httpx_logger = logging.getLogger('httpx')
telegram_logger = logging.getLogger('telegram')

print("=== 日誌等級測試 ===")
print(f"主日誌等級: {log_level}")
print(f"httpx 日誌等級: {logging.getLevelName(httpx_logger.level)}")
print(f"telegram 日誌等級: {logging.getLevelName(telegram_logger.level)}")

print("\n=== 測試日誌輸出 ===")
print("應該顯示的訊息:")
main_logger.info("✅ 這是主程式的 INFO 訊息 - 應該顯示")
main_logger.warning("⚠️ 這是主程式的 WARNING 訊息 - 應該顯示")
main_logger.error("❌ 這是主程式的 ERROR 訊息 - 應該顯示")

print("\n應該被隱藏的訊息:")
httpx_logger.info("🔇 這是 httpx 的 INFO 訊息 - 應該被隱藏")
telegram_logger.info("🔇 這是 telegram 的 INFO 訊息 - 應該被隱藏")

print("\n第三方套件的重要訊息:")
httpx_logger.warning("⚠️ 這是 httpx 的 WARNING 訊息 - 應該顯示")
telegram_logger.error("❌ 這是 telegram 的 ERROR 訊息 - 應該顯示")

print("\n=== 測試完成 ===")
print("如果看不到標記為「應該被隱藏」的訊息，表示設定成功!")