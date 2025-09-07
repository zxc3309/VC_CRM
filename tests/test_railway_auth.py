#!/usr/bin/env python3
"""
Railway 部署認證測試腳本
用於診斷 Google Service Account 認證問題
"""
import os
import json
import base64
import logging
from dotenv import load_dotenv
from google.oauth2 import service_account
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime

# 設置詳細日誌
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)

def test_environment_variables():
    """測試環境變數設定"""
    logger.info("=== 測試環境變數 ===")
    
    load_dotenv(override=True)
    
    required_vars = [
        'PROMPT_MANAGER',
        'SERVICE_ACCOUNT_BASE64',
        'GOOGLE_SHEETS_ID'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            logger.info(f"✅ {var}: 已設定 ({'*' * min(10, len(value))}...)")
        else:
            logger.error(f"❌ {var}: 未設定")
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"缺少必要環境變數: {missing_vars}")
    
    return True

def test_base64_decoding():
    """測試 base64 解碼"""
    logger.info("=== 測試 Base64 解碼 ===")
    
    base64_content = os.getenv('SERVICE_ACCOUNT_BASE64')
    
    try:
        # 驗證 base64 格式
        import string
        valid_chars = string.ascii_letters + string.digits + '+/='
        if not all(c in valid_chars for c in base64_content.strip()):
            raise ValueError("包含非 base64 字符")
        
        logger.info("✅ Base64 格式檢查通過")
        
        # 嘗試解碼
        decoded_content = base64.b64decode(base64_content).decode('utf-8')
        logger.info(f"✅ Base64 解碼成功，內容長度: {len(decoded_content)}")
        
        # 解析 JSON
        service_account_info = json.loads(decoded_content)
        logger.info("✅ JSON 解析成功")
        
        # 檢查必要欄位
        required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
        missing_fields = [field for field in required_fields if field not in service_account_info]
        
        if missing_fields:
            raise ValueError(f"缺少必要欄位: {missing_fields}")
        
        logger.info("✅ 服務帳戶資訊格式檢查通過")
        logger.info(f"   專案 ID: {service_account_info.get('project_id')}")
        logger.info(f"   客戶端信箱: {service_account_info.get('client_email')}")
        logger.info(f"   私鑰 ID: {service_account_info.get('private_key_id')}")
        
        return service_account_info
        
    except Exception as e:
        logger.error(f"❌ Base64 處理失敗: {str(e)}")
        raise

def test_google_credentials(service_account_info):
    """測試 Google 認證"""
    logger.info("=== 測試 Google 認證 ===")
    
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive',
        'https://spreadsheets.google.com/feeds'
    ]
    
    try:
        # 測試新版認證方式
        logger.info("測試 google.oauth2.service_account...")
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info,
            scopes=scopes
        )
        logger.info("✅ 新版認證物件建立成功")
        
        # 測試舊版認證方式
        logger.info("測試 oauth2client.service_account...")
        creds = ServiceAccountCredentials.from_json_keyfile_dict(
            service_account_info,
            scopes
        )
        logger.info("✅ 舊版認證物件建立成功")
        
        return creds
        
    except Exception as e:
        logger.error(f"❌ Google 認證建立失敗: {str(e)}")
        raise

def test_gspread_connection(creds):
    """測試 gspread 連線"""
    logger.info("=== 測試 gspread 連線 ===")
    
    try:
        client = gspread.authorize(creds)
        logger.info("✅ gspread 客戶端建立成功")
        
        # 測試直接開啟試算表 (新方法)
        sheet_id = os.getenv('PROMPT_MANAGER')
        logger.info(f"嘗試開啟試算表 ID: {sheet_id}")
        
        sheet = client.open_by_key(sheet_id)
        logger.info(f"✅ 成功開啟試算表: {sheet.title}")
        
        # 測試讀取第一個工作表
        worksheet = sheet.worksheets()[0]
        logger.info(f"✅ 成功取得工作表: {worksheet.title}")
        
        # 嘗試讀取一些資料 (不會實際修改)
        try:
            records = worksheet.get_all_records()
            logger.info(f"✅ 成功讀取資料，共 {len(records)} 筆記錄")
            
            if records:
                first_record = records[0]
                logger.info(f"   第一筆記錄欄位: {list(first_record.keys())}")
                
        except Exception as e:
            logger.warning(f"⚠️ 讀取資料失敗: {str(e)}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ gspread 連線失敗: {str(e)}")
        raise

def test_system_info():
    """測試系統資訊"""
    logger.info("=== 系統資訊 ===")
    
    logger.info(f"系統時間: {datetime.datetime.now()}")
    logger.info(f"UTC 時間: {datetime.datetime.utcnow()}")
    
    # Railway 特定環境變數
    railway_vars = [
        'RAILWAY_ENVIRONMENT',
        'RAILWAY_PROJECT_ID',
        'RAILWAY_SERVICE_ID',
        'RAILWAY_DEPLOYMENT_ID'
    ]
    
    for var in railway_vars:
        value = os.getenv(var)
        if value:
            logger.info(f"{var}: {value}")

def main():
    """主要測試函數"""
    try:
        logger.info("🚀 開始 Railway 認證測試")
        
        # 測試系統資訊
        test_system_info()
        
        # 測試環境變數
        test_environment_variables()
        
        # 測試 base64 解碼
        service_account_info = test_base64_decoding()
        
        # 測試 Google 認證
        creds = test_google_credentials(service_account_info)
        
        # 測試 gspread 連線
        test_gspread_connection(creds)
        
        logger.info("🎉 所有測試通過！認證設定正確。")
        
    except Exception as e:
        logger.error(f"💥 測試失敗: {str(e)}")
        logger.error("請檢查以上錯誤訊息並修正設定")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)