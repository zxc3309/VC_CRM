#!/usr/bin/env python3
"""
重置 Telegram Bot - 清除 webhook 和待處理的更新
"""
import os
import requests

# 直接從 .env 檔案讀取
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if not TELEGRAM_BOT_TOKEN:
    # 嘗試從 .env 檔案讀取
    try:
        with open('.env', 'r') as f:
            for line in f:
                if line.startswith('TELEGRAM_BOT_TOKEN='):
                    TELEGRAM_BOT_TOKEN = line.split('=', 1)[1].strip().strip('"').strip("'")
                    break
    except FileNotFoundError:
        pass

if not TELEGRAM_BOT_TOKEN:
    print("❌ 錯誤: 找不到 TELEGRAM_BOT_TOKEN")
    print("   請確認 .env 檔案存在且包含 TELEGRAM_BOT_TOKEN")
    exit(1)

def reset_bot():
    """重置 Telegram Bot 設定"""
    base_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

    print("🔄 正在重置 Telegram Bot...")

    # 1. 刪除 webhook
    print("\n1️⃣ 刪除 webhook...")
    response = requests.post(
        f"{base_url}/deleteWebhook",
        params={"drop_pending_updates": True}
    )
    result = response.json()
    print(f"   結果: {result}")

    # 2. 檢查當前 webhook 狀態
    print("\n2️⃣ 檢查 webhook 狀態...")
    response = requests.get(f"{base_url}/getWebhookInfo")
    webhook_info = response.json()
    print(f"   Webhook URL: {webhook_info.get('result', {}).get('url', 'None')}")
    print(f"   Pending updates: {webhook_info.get('result', {}).get('pending_update_count', 0)}")

    # 3. 測試 bot 連接
    print("\n3️⃣ 測試 bot 連接...")
    response = requests.get(f"{base_url}/getMe")
    bot_info = response.json()
    if bot_info.get('ok'):
        print(f"   ✅ Bot 連接正常: @{bot_info['result']['username']}")
    else:
        print(f"   ❌ Bot 連接失敗: {bot_info}")

    print("\n✅ 重置完成！現在可以重新啟動 Railway 部署。")

if __name__ == '__main__':
    reset_bot()
