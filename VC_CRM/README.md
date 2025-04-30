# VC Deal Sourcing Bot

自動化的 VC deal sourcing 工作流程，通過 Telegram Bot 接收並分析潛在投資機會，使用 OpenAI GPT-4 進行智能分析，並自動整理到 Google Sheets。

## 功能特點

- 通過 Telegram Bot 接收投資機會訊息
- 使用 OpenAI GPT-4 進行智能分析：
  - 自動提取公司名稱、產品描述、創始人信息等
  - 智能理解業務進展（Traction）
  - 分析相關網址和附件
- 使用 OpenAI 的網路搜索功能：
  - 自動搜索並驗證公司信息
  - 獲取最新的公司動態
  - 提供可信的信息來源引用
- 自動整理到 Google Sheets：
  - 結構化的數據展示
  - 可點擊的參考來源
  - 自動格式化的表格

## 系統要求

- Python 3.7.1 或更高版本
- OpenAI API 密鑰（支持 GPT-4）
- Google Cloud 項目和服務帳號
- Telegram Bot Token

## 安裝步驟

1. 克隆專案：
```bash
git clone [your-repo-url]
cd vc-crm
```

2. 安裝依賴：
```bash
pip install -r requirements.txt
```

3. 配置環境變數：
   - 複製 `.env.example` 到 `.env`
   - 填入必要的配置信息：
     ```
     # Telegram Bot Token (從 @BotFather 獲取)
     TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

     # Google Sheets 配置
     SPREADSHEET_ID=your_google_spreadsheet_id_here
     GOOGLE_SERVICE_ACCOUNT_FILE=path_to_your_service_account_json_file.json

     # OpenAI 配置
     OPENAI_API_KEY=your_openai_api_key_here
     ```

4. 設置 Google Sheets：
   - 創建新的 Google Sheets
   - 創建名為 "Deals" 的工作表
   - 系統會自動創建並格式化以下欄位：
     - Timestamp
     - Company Name
     - Product Description
     - Founders
     - Traction
     - Company Description
     - Founded Year
     - Location
     - Funding Information
     - Market/Industry
     - Key Achievements
     - URLs
     - Sources (含引用連結)
     - Additional Metrics
     - Raw Message
   - 分享表格給你的 Google Service Account 郵箱（編輯權限）

## 使用方法

1. 運行機器人：
```bash
python main.py
```

2. 在 Telegram 中：
   - 搜索你的機器人
   - 發送 `/start` 開始使用
   - 直接發送投資機會相關信息
   - 機器人會自動：
     1. 分析訊息內容
     2. 搜索並驗證公司信息
     3. 整理所有信息到 Google Sheets
     4. 回覆處理結果和表格連結

## API 使用說明

### OpenAI API
- 使用 GPT-4 進行文本分析
- 使用 `gpt-4o-search-preview` 模型進行網路搜索
- 支持高質量上下文搜索（search_context_size: "high"）
- 自動提供信息來源引用

### Google Sheets API
- 使用服務帳號進行身份驗證
- 自動創建和格式化表格
- 支持公式和超連結
- 自動調整列寬和格式

## 注意事項

- 確保 OpenAI API key 有足夠的額度
- 保護好所有 API 密鑰和憑證
- 定期備份 Google Sheets 數據
- 注意 API 的使用限制和計費

## 故障排除

如果遇到問題：
1. 檢查環境變數是否正確設置
2. 確認 API 密鑰是否有效
3. 查看日誌文件了解詳細錯誤信息
4. 確保網絡連接正常

## 貢獻指南

歡迎提交 Pull Requests 來改進這個項目。請確保：
1. 代碼符合 PEP 8 規範
2. 添加適當的測試
3. 更新文檔以反映更改

## 授權

[Your License]

## 環境設定

### 必要軟體安裝

1. **Python 相依套件**
   ```bash
   pip install -r requirements.txt
   ```

2. **Tesseract OCR 安裝**
   - **macOS**：
     ```bash
     brew install tesseract
     ```
   - **Windows**：
     - 下載並安裝 [Tesseract-OCR installer](https://github.com/UB-Mannheim/tesseract/wiki)
     - 預設安裝路徑：`C:\Program Files\Tesseract-OCR\tesseract.exe`
   - **Linux**：
     ```bash
     sudo apt-get install tesseract-ocr
     ```

### 環境變數設定

1. 複製 `.env.example` 到 `.env`：
   ```bash
   cp .env.example .env
   ```

2. 在 `.env` 中設定必要的環境變數：
   - `TELEGRAM_BOT_TOKEN`：你的 Telegram Bot Token
   - `GOOGLE_SHEETS_ID`：Google Sheets ID
   - `OPENAI_API_KEY`：OpenAI API 金鑰
   - `DOCSEND_EMAIL`：用於存取 DocSend 的 email
   - `WORKING_DIRECTORY`：工作目錄路徑
   - `TESSERACT_CMD`：Tesseract OCR 執行檔路徑
     - Windows：`C:\\Program Files\\Tesseract-OCR\\tesseract.exe`
     - macOS：`/usr/local/bin/tesseract`
     - Linux：`/usr/bin/tesseract`

### Tesseract OCR 設定說明

Tesseract OCR 用於從圖片中提取文字，主要用於：
- PDF 檔案中的圖片文字辨識
- DocSend 文件中的圖片內容辨識
- 投影片中的圖片文字擷取

確保 `TESSERACT_CMD` 環境變數指向正確的 Tesseract 執行檔路徑：

1. **檢查安裝**：
   ```bash
   # macOS/Linux
   which tesseract
   
   # Windows (PowerShell)
   Get-Command tesseract
   ```

2. **驗證設定**：
   ```python
   import pytesseract
   print(pytesseract.get_tesseract_version())
   ```

如果遇到問題，請確認：
1. Tesseract 已正確安裝
2. 環境變數路徑正確
3. 執行檔有適當的執行權限 