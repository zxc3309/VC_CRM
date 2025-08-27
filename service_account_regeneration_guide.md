# Google Service Account 重新生成完整指南

## 🚨 診斷結果
根據錯誤分析，你的 Google Service Account 金鑰已失效，出現 "Invalid JWT Signature" 錯誤。這需要重新生成新的服務帳戶金鑰。

## 📋 完整解決步驟

### 步驟 1: 前往 Google Cloud Console
1. 打開 [Google Cloud Console](https://console.cloud.google.com/)
2. 選擇你的專案 `total-pad-451905-i5` (或建立新專案)

### 步驟 2: 檢查現有服務帳戶
1. 左側選單 → 「IAM 與管理」 → 「服務帳戶」
2. 找到 `vc-crm-bot@total-pad-451905-i5.iam.gserviceaccount.com`
3. 如果不存在，需要建立新的服務帳戶

### 步驟 3A: 建立新服務帳戶 (如果不存在)
1. 點擊「建立服務帳戶」
2. 填入資訊:
   - **服務帳戶名稱**: `vc-crm-bot`
   - **服務帳戶 ID**: `vc-crm-bot`
   - **說明**: `VC CRM Telegram Bot Service Account`
3. 點擊「建立並繼續」

### 步驟 3B: 設定服務帳戶權限
為服務帳戶添加以下角色:
- **Editor** (編輯者) - 允許編輯專案資源
- **Service Account User** (服務帳戶使用者) - 允許使用服務帳戶

### 步驟 4: 啟用必要 API
確保以下 API 已啟用 (左側選單 → 「API 和服務」 → 「程式庫」):
- ✅ **Google Sheets API**
- ✅ **Google Drive API**
- ✅ **Google Docs API**

### 步驟 5: 生成新金鑰
1. 回到「服務帳戶」頁面
2. 點擊你的服務帳戶 `vc-crm-bot`
3. 前往「金鑰」分頁
4. 點擊「新增金鑰」 → 「建立新金鑰」
5. 選擇 **JSON** 格式
6. 點擊「建立」下載金鑰檔案

### 步驟 6: 轉換為 Base64
#### 在 macOS/Linux:
```bash
base64 -w 0 path/to/your/service-account-key.json
```

#### 在 Windows (PowerShell):
```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes("path\to\your\service-account-key.json"))
```

### 步驟 7: 更新 Railway 環境變數
1. 前往 [Railway Dashboard](https://railway.app/dashboard)
2. 選擇你的專案
3. 前往「Variables」分頁  
4. 更新 `SERVICE_ACCOUNT_BASE64` 為步驟 6 生成的 base64 字串

### 步驟 8: 設定 Google Sheets 權限
**重要**: 必須將服務帳戶的 email 地址添加到你的 Google Sheets 中:

1. 開啟你的 Google Sheets:
   - Prompt Manager: `1Y4xi0EvZNm20iDnUGrdG4RFoM5AoNz1sqNFQw1-kjnw` 
   - Main Data Sheet: 你的 `GOOGLE_SHEETS_ID`
   
2. 點擊右上角「共用」按鈕

3. 添加服務帳戶 email: `vc-crm-bot@total-pad-451905-i5.iam.gserviceaccount.com`

4. 設定權限為「編輯者」

5. 點擊「傳送」

### 步驟 9: 測試連接
在本地測試新金鑰是否有效:
```bash
# 更新你的 .env 檔案中的 SERVICE_ACCOUNT_BASE64
# 然後執行測試
python3 diagnose_service_account.py
```

### 步驟 10: 重新部署 Railway
1. 確認環境變數已更新
2. 觸發重新部署或等待自動部署
3. 檢查日誌確認連接成功

## ⚠️ 重要注意事項

1. **刪除舊金鑰**: 在新金鑰正常運作後，記得在 Google Cloud Console 中刪除舊的金鑰

2. **安全保管**: 
   - 不要將 JSON 金鑰檔案提交到 Git
   - 不要在程式碼中硬編碼金鑰
   - 只使用環境變數存儲 base64 編碼

3. **權限檢查**: 確保服務帳戶有足夠權限存取你需要的 Google Sheets 和 Drive 資源

## 🔧 故障排除

### 如果仍然出現 "Invalid JWT Signature"
- 檢查 base64 編碼是否正確 (沒有換行符號)
- 確認 JSON 金鑰是否完整
- 檢查系統時間是否同步

### 如果出現權限錯誤
- 確認服務帳戶 email 已添加到 Google Sheets
- 檢查 Google Cloud APIs 是否已啟用
- 確認服務帳戶有適當的 IAM 角色

### 測試工具
使用提供的診斷腳本:
```bash
python3 diagnose_service_account.py
python3 test_railway_auth.py
```

## ✅ 成功指標
當一切設定正確時，你應該看到:
- Railway 日誌中出現 "✅ 成功初始化 Prompt Manager"
- 診斷腳本顯示 "🎉 所有測試通過！認證設定正確"
- Bot 能夠正常回應 Telegram 訊息