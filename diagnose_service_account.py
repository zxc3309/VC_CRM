#!/usr/bin/env python3
"""
Google Service Account 診斷和修復工具
用於解決 Invalid JWT Signature 錯誤
"""
import os
import json
import base64
import logging
from dotenv import load_dotenv
from datetime import datetime, timezone
import subprocess
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_service_account_validity():
    """檢查服務帳戶有效性"""
    logger.info("=== 檢查服務帳戶資訊 ===")
    
    load_dotenv(override=True)
    base64_content = os.getenv('SERVICE_ACCOUNT_BASE64')
    
    if not base64_content:
        logger.error("❌ SERVICE_ACCOUNT_BASE64 未設定")
        return False
    
    try:
        # 解碼並檢查
        decoded = base64.b64decode(base64_content).decode('utf-8')
        service_account_info = json.loads(decoded)
        
        logger.info(f"✅ 專案 ID: {service_account_info.get('project_id')}")
        logger.info(f"✅ 客戶端信箱: {service_account_info.get('client_email')}")
        logger.info(f"✅ 私鑰 ID: {service_account_info.get('private_key_id')}")
        
        # 檢查私鑰格式
        private_key = service_account_info.get('private_key', '')
        if not private_key.startswith('-----BEGIN PRIVATE KEY-----'):
            logger.error("❌ 私鑰格式不正確")
            return False
        
        logger.info("✅ 私鑰格式正確")
        return service_account_info
        
    except Exception as e:
        logger.error(f"❌ 解碼失敗: {e}")
        return False

def generate_new_service_account_guide():
    """生成重新建立服務帳戶的指南"""
    guide = """
# Google Service Account 重新建立指南

## 步驟 1: 建立新的服務帳戶
1. 前往 Google Cloud Console: https://console.cloud.google.com/
2. 選擇你的專案或建立新專案
3. 前往「IAM 與管理」>「服務帳戶」
4. 點擊「建立服務帳戶」

## 步驟 2: 設定服務帳戶
- 服務帳戶名稱: vc-crm-bot
- 服務帳戶 ID: vc-crm-bot
- 說明: VC CRM Telegram Bot Service Account

## 步驟 3: 授與權限
為服務帳戶添加以下角色:
- Editor (編輯者)
- Service Account User (服務帳戶使用者)

## 步驟 4: 建立金鑰
1. 點擊剛建立的服務帳戶
2. 前往「金鑰」分頁
3. 點擊「新增金鑰」>「建立新金鑰」
4. 選擇「JSON」格式
5. 下載金鑰檔案

## 步驟 5: 啟用 API
確保以下 API 已啟用:
- Google Sheets API
- Google Drive API  
- Google Docs API

## 步驟 6: 編碼為 Base64
在終端機執行:
```bash
base64 -w 0 path/to/your/service-account-key.json
```

## 步驟 7: 更新環境變數
在 Railway 中更新 SERVICE_ACCOUNT_BASE64 環境變數為上述 base64 字串

## 步驟 8: 設定試算表權限
將服務帳戶的 email 地址添加到你的 Google Sheets 的共享設定中，權限設為「編輯者」
    """
    
    with open('/tmp/service_account_setup_guide.md', 'w', encoding='utf-8') as f:
        f.write(guide)
    
    logger.info("📝 已生成服務帳戶設定指南: /tmp/service_account_setup_guide.md")
    return guide

def test_clock_sync():
    """測試系統時間同步"""
    logger.info("=== 檢查時間同步 ===")
    
    local_time = datetime.now()
    utc_time = datetime.now(timezone.utc)
    
    logger.info(f"本地時間: {local_time}")
    logger.info(f"UTC 時間: {utc_time}")
    
    # 檢查時間差是否過大
    time_diff = abs((local_time - utc_time.replace(tzinfo=None)).total_seconds())
    
    if time_diff > 300:  # 5分鐘
        logger.warning(f"⚠️ 系統時間可能不同步，差異: {time_diff} 秒")
        return False
    else:
        logger.info("✅ 系統時間同步正常")
        return True

def create_minimal_test():
    """建立最小化測試，避免複雜依賴"""
    logger.info("=== 建立最小化認證測試 ===")
    
    service_account_info = check_service_account_validity()
    if not service_account_info:
        return False
    
    try:
        # 只測試基本認證，不實際連接 API
        from google.oauth2 import service_account
        
        scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
        
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=scopes
        )
        
        logger.info("✅ 基本認證物件建立成功")
        
        # 嘗試刷新 token (這裡會實際與 Google 通信)
        from google.auth.transport.requests import Request
        request = Request()
        
        logger.info("嘗試刷新認證 token...")
        credentials.refresh(request)
        
        logger.info("✅ 認證 token 刷新成功")
        logger.info("🎉 服務帳戶認證完全正常!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 認證測試失敗: {e}")
        
        if "invalid_grant" in str(e) or "Invalid JWT Signature" in str(e):
            logger.error("💡 這表示服務帳戶金鑰本身有問題，需要重新生成")
            generate_new_service_account_guide()
        
        return False

def main():
    """主要診斷流程"""
    logger.info("🔍 開始 Google Service Account 診斷")
    
    # 檢查環境變數
    if not check_service_account_validity():
        logger.error("💥 服務帳戶資訊無效")
        generate_new_service_account_guide()
        return False
    
    # 檢查時間同步
    test_clock_sync()
    
    # 進行最小化測試
    if create_minimal_test():
        logger.info("🎉 診斷完成 - 認證正常")
        return True
    else:
        logger.error("💥 診斷完成 - 需要重新設定服務帳戶")
        generate_new_service_account_guide()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)