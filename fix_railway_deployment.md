# Railway 部署認證問題修復指南

## 問題描述
Railway 部署時出現 "Invalid JWT Signature" 錯誤，導致 Google Service Account 認證失敗。

## 已實施的修復

### 1. 移除 `openall()` 調用
- **問題**: `client.openall()` 需要列出所有試算表，消耗大量 API 配額且容易觸發認證錯誤
- **解決**: 改用 `client.open_by_key(sheet_id)` 直接開啟指定試算表
- **檔案**: `prompt_manager.py:53`

### 2. 增強錯誤處理和驗證
- 新增 base64 格式驗證
- 新增服務帳戶 JSON 結構驗證  
- 新增詳細的錯誤診斷訊息
- **檔案**: `prompt_manager.py`, `doc_manager.py`, `sheets_manager.py`

### 3. 新增 Railway 環境診斷
- 記錄環境變數設定狀態
- 記錄系統時間資訊
- 檢測 Railway 特定環境變數
- **檔案**: `prompt_manager.py:_log_environment_info()`

### 4. 建立測試工具
- **檔案**: `test_railway_auth.py`
- 完整的認證鏈測試
- 詳細的錯誤診斷

## 修復後的部署流程

### 步驟 1: 驗證環境變數
在 Railway 中確認以下環境變數已正確設定:
- `SERVICE_ACCOUNT_BASE64`: Google 服務帳戶金鑰的 base64 編碼
- `PROMPT_MANAGER`: Google Sheets ID  
- `GOOGLE_SHEETS_ID`: 主要資料表 ID
- `TELEGRAM_BOT_TOKEN`: Telegram Bot Token
- `OPENAI_API_KEY`: OpenAI API 金鑰

### 步驟 2: 重新生成服務帳戶金鑰
如果問題持續，可能需要:
1. 在 Google Cloud Console 重新生成服務帳戶金鑰
2. 確認服務帳戶有正確權限:
   - Google Sheets API
   - Google Drive API  
   - Google Docs API
3. 重新編碼為 base64 並更新環境變數

### 步驟 3: 使用測試腳本診斷
部署前可以執行:
```bash
python3 test_railway_auth.py
```

### 步驟 4: 監控部署日誌
新的錯誤處理會提供更詳細的診斷資訊，協助快速定位問題。

## 預期結果
- ✅ 更快的初始化 (無需列出所有試算表)
- ✅ 更清楚的錯誤訊息
- ✅ 更穩定的認證流程
- ✅ 更容易的問題診斷

## 注意事項
如果 "Invalid JWT Signature" 錯誤仍然出現，通常表示:
1. 服務帳戶金鑰已過期或被撤銷
2. base64 編碼有問題
3. Railway 伺服器與 Google 伺服器時間不同步

這些情況下需要更新 `SERVICE_ACCOUNT_BASE64` 環境變數。