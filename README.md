# VC Deal Sourcing Bot

自動化的 VC deal sourcing 工作流程，通過 Telegram Bot（或潛在尋源管道） 接收並搜查案源基本資訊，使用 OpenAI 進行智能分析，並自動整理到使用者指定的 Google Doc 與 Sheets。

## 功能特點

- 通過 Telegram Bot 接收投資機會訊息
- 使用 OpenAI GPT 進行智能分析：
  - 自動提取公司名稱、產品描述、創始人信息等
  - 智能理解業務進展（Traction）
  - 分析相關網址、簡報內容和附件
  - **自動產生觀察（Observation）**：AI 分析創辦人背景和公司資訊後的關鍵洞察
  - **自動產生建議問題（Suggested Questions）**：為首次會談準備的智能問題清單
- 使用 OpenAI 的網路搜索功能：
  - 提示詞可線上更動
  - 自動搜索並驗證公司信息
  - 獲取最新的公司動態 
  - 提供可信的信息來源引用
- 自動整理到 Google Docs：
  - 結構化提供公司資訊
  - 結構化提供創辦人資訊
  - **AI 觀察重點（Observation）**
  - **智能建議問題清單（Suggested Questions）**
- 自動整理到 Google Sheets：
  - 結構化的數據展示
  - 可點擊的參考來源
  - 自動格式化的表格
- 可調整的 AI 使用情境
  - 可調整「資訊整理」與「次級資料搜尋」所使用的 AI 模型
  - 可調整「資訊整理」與「次級資料搜尋」所使用的 AI Prompt

## 支援的資料來源

系統可以同時處理多種資料來源，自動識別並擷取內容：

1. **DocSend 文件**
   - 自動填入 email 和密碼（支援 `pw:` 或 `password:` 格式）
   - 擷取投影片內容和圖片
   - 支援 OCR 圖片文字辨識

2. **PDF/PPTX 附件**
   - 直接上傳到 Telegram
   - 自動提取文字內容
   - 圖片型 PDF 支援 OCR

3. **Google Drive 檔案**
   - 支援 Google Drive 和 Google Docs 連結
   - 自動下載並分析內容

4. **一般網站**
   - 自動擷取網頁內容
   - 支援多分頁網站（如 GitBook、Notion）
   - 智能識別 Pitch Deck 頁面

5. **純文字訊息**
   - 直接分析文字內容
   - 提取關鍵資訊

## 系統要求

- Python 3.8 或更高版本
- OpenAI API 密鑰（支持 GPT-4）
- Google Cloud Service Account（開啟 Docs + Sheets API）
- Telegram Bot Token

## 專案結構

```
VC_CRM/
├── main.py                      # 主程式入口點，啟動 Telegram Bot
├── deal_analyzer.py             # 核心分析模組，處理 AI 分析與內容提取
├── sheets_manager.py            # Google Sheets 管理模組
├── doc_manager.py               # Google Docs 建立與格式化模組
├── deck_browser.py              # DocSend 與網頁內容擷取模組
├── prompt_manager.py            # AI 提示詞管理模組
├── 
├── tests/                       # 測試檔案目錄
│   ├── test_full_workflow.py    # 完整工作流程測試
│   ├── test_observation_*.py    # 觀察功能相關測試
│   ├── test_railway_*.py        # Railway 部署測試
│   └── test_*.py               # 其他功能測試
├── 
├── utils/                       # 工具模組目錄
├── VC_CRM/                      # 專案資源目錄
├── Process Chart/               # 流程圖資源
├── 
├── service_account.json         # Google Cloud Service Account 金鑰
├── requirements.txt             # Python 相依套件清單
├── Dockerfile                   # Docker 容器設定
├── nixpacks.toml               # Nixpacks 部署設定
├── install.py                   # 自動安裝腳本
├── 
├── diagnose_service_account.py  # Service Account 診斷工具
├── fix_railway_deployment.md    # Railway 部署故障排除
├── service_account_regeneration_guide.md  # Service Account 重新產生指南
├── 
└── .env                        # 環境變數設定檔（需自行建立）
```

### 核心模組說明

- **main.py**: Telegram Bot 主程式，負責接收訊息並協調各模組
- **deal_analyzer.py**: 核心 AI 分析引擎，整合 OpenAI API 進行智能分析
- **sheets_manager.py**: 管理 Google Sheets 的資料寫入與格式化
- **doc_manager.py**: 負責建立和格式化 Google Docs 文件
- **deck_browser.py**: 處理 DocSend、PDF 和各種網頁內容的擷取
- **prompt_manager.py**: 管理 AI 提示詞的載入和更新

### 診斷工具

- **diagnose_service_account.py**: 診斷 Google Service Account 設定問題
- **fix_railway_deployment.md**: Railway 平台部署的故障排除指南
- **service_account_regeneration_guide.md**: Service Account 重新設定教學

## 安裝步驟（若已線上部屬則可跳過）

1. 克隆專案：
```bash
git clone [your-repo-url]
cd vc-crm
```

2. 使用安裝腳本快速安裝：
```bash
python install.py
```
此步驟會自動：
- 安裝 Python 套件需求
- 安裝 Playwright 瀏覽器引擎
- 檢查是否已安裝 Tesseract

3. 配置環境變數：
   - 複製 `.env.example` 到 `.env`
   - 填入必要的配置信息：(若為線上部屬請放置部屬平台中的 Variables 欄位)
     ```
     # Telegram Bot Token
     # Google Sheets Configuration
     # OpenAI Configuration
     # Email for DocSend access
     # Bot Function Folder
     # OCR Function(線上部屬可省略)
     # Google Drive Folder
     # Google Sheet_Prompt Manager
     # Google Service Account Container(Base64 格式)
     ```

4. 建立 Google Sheets 與 Docs 權限：
   - 創建 "提示詞" 的工作表，並授權給你的 Service Account，格式請參考（https://docs.google.com/spreadsheets/d/1Y4xi0EvZNm20iDnUGrdG4RFoM5AoNz1sqNFQw1-kjnw/edit?gid=422006238#gid=422006238）
   - 創建新的 Google Sheets，並將其 TAB 名稱填充至"提示詞"中的"main_sheet_name"
   - 創建名為 "Prompt Engineering" 的工作表，並授權給你的 Service Account
   - 創建新的 Google Drive Folder，並授權給你的 Service Account
   - 分享給你的 Google Service Account 郵箱（編輯權限）

## 使用方法

1. 運行機器人（線上部屬可跳過）：
```bash
python main.py
```

2. 在 Telegram 中：
   - 搜索你的機器人
   - 直接發送投資機會相關信息（支援文字、連結、附件）
   - 機器人會自動執行以下流程：
     1. **資料擷取**：識別並處理各種資料來源（DocSend、PDF、網站等）
     2. **內容分析**：使用 AI 分析公司和創辦人資訊
     3. **網路搜索**：搜索並驗證公司相關資訊
     4. **智能洞察**：產生觀察重點和建議問題
     5. **文件產生**：建立結構化的 Google Doc
     6. **資料儲存**：更新 Google Sheets 資料庫
     7. **回覆結果**：提供 Doc 和 Sheets 連結

   #### 支援指令
   - `/reload_prompt`：重新載入 Google Sheets 的提示詞（Prompt），適用於你在 Google Sheets 更新了 prompt 後，想讓 bot 立即同步最新內容。
   - `/show_prompt`：查詢目前可用的 prompt 列表，方便檢查與調整 prompt 設定。

   #### 訊息範例
   ```
   TrueNorth 是一家 AI 公司
   創辦人：John Doe
   
   Deck: https://docsend.com/view/example
   pw: password123
   
   網站：https://truenorth.com
   ```

## API 使用說明

### OpenAI API
- 使用"使用者自定義 AI 模型"進行文本分析
- 使用"使用者自定義 AI 模型"進行網路搜索
- 自動提供信息來源引用

### Google Sheets API
- 使用服務帳號進行身份驗證
- 自動創建和格式化表格
- 支持公式和超連結
- 自動調整列寬和格式

### Google Sheets 自動建立與格式化說明

- **自動補齊表頭**：  
  系統在每次寫入 Google Sheets 前，會自動檢查目標工作表（如 `Web3 Pipeline (Current)` 或 `Prompt Engineering`）的表頭（第一行欄位名稱）。若表頭不存在或不完整，系統會自動補齊下列所有欄位名稱，確保資料正確結構化。

- **自動補齊欄位名稱（表頭）**：  
  - Status
  - Next Meeting
  - Opportunity
  - Description
  - Updates
  - DRI
  - Co-AA
  - Partner
  - Round Size
  - Pre-M
  - Log
  - Deck
  - Source
  - Source Tag
  - Location
  - Category
  - Created Time

- **自動補齊 Prompt Engineering 日誌表頭**：  
  - Timestamp
  - Company Name
  - Model Usage
  - Web Prompt1
  - Web Content1
  - Score
  - Web Prompt2
  - Web Content2
  - Score
  - Web Prompt3
  - Web Content3
  - Score
  - AI Prompt1
  - AI Content1
  - Score
  - AI Prompt2
  - AI Content2
  - Score
  - AI Prompt3
  - AI Content3
  - Score
  - AI Prompt4
  - AI Content4
  - Score
  - AI Prompt5
  - AI Content5
  - Score

- **注意事項**：
  - 系統**不會自動建立 Google Sheets 檔案本身**，請先手動建立 Google Sheets 並設定好權限（將 Service Account 加入為編輯者）。
  - 欄位的進階格式（如欄寬、顏色、下拉選單）需手動設定，系統僅自動補齊欄位名稱。
  - 若表頭已存在但不完整，系統會自動補齊缺少的欄位。

## 系統流程圖

![VC Bot 工作流程圖](VC_CRM/Process%20Chart/Process01.png)

### 詳細流程說明

1. **訊息接收**：Telegram Bot 接收使用者訊息（文字/連結/附件）
2. **資料來源識別**：自動識別 DocSend、PDF、Google Drive、網站或純文字
3. **內容擷取**：
   - DocSend：自動填入密碼，擷取投影片內容
   - PDF/PPTX：提取文字，必要時使用 OCR
   - 網站：智能擷取網頁內容
4. **AI 分析**：提取公司名稱、創辦人資訊、業務描述
5. **網路搜索**：驗證並補充公司資訊
6. **智能洞察**：
   - 產生觀察重點（Observation）
   - 建議會談問題（Suggested Questions）
7. **文件產出**：建立結構化 Google Doc
8. **資料庫更新**：儲存至 Google Sheets
9. **結果回覆**：提供文件連結給使用者

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

### 特定問題排除

#### 觀察和問題不顯示
如果 Google Doc 中沒有顯示 "Observation" 和 "Suggested Questions"：
1. 檢查日誌中是否有 `[suggest_questions]` 相關訊息
2. 確認 Google Sheet 中的 `suggest_questions` prompt 格式正確
3. 可執行測試腳本驗證：
   ```bash
   python3 test_observation_question.py
   ```

#### DocSend 無法存取
1. 確認環境變數中的 `DOCSEND_EMAIL` 已設定
2. 檢查訊息中是否包含正確的密碼格式（`pw:` 或 `password:`）
3. 查看日誌中的 DocSend 處理訊息

#### 附件處理失敗
1. 確認 Tesseract OCR 已正確安裝
2. 檢查檔案大小是否超過 Telegram 限制（20MB）
3. 確認檔案格式為支援的類型（PDF、PPTX、PPT）

## 測試與開發

### 執行測試

專案包含多種測試檔案，位於 `tests/` 目錄中：

```bash
# 執行所有測試
python -m pytest tests/

# 執行特定測試
python tests/test_full_workflow.py
python tests/test_observation_question.py
python tests/test_railway_auth.py
```

### 測試檔案說明

- **test_full_workflow.py**: 完整工作流程整合測試
- **test_observation_*.py**: AI 觀察與問題產生功能測試
- **test_railway_*.py**: Railway 平台部署相關測試
- **test_*_init.py**: 系統初始化與懶載入測試
- **test_graceful_degradation.py**: 系統優雅降級測試
- **test_ocr_handling.py**: OCR 文字識別功能測試
- **test_logging.py**: 日誌系統設定測試

### 診斷工具使用

#### Service Account 診斷
```bash
python diagnose_service_account.py
```
此工具可診斷 Google Service Account 設定問題，包括：
- JWT 簽章驗證
- API 權限檢查
- 憑證格式驗證

#### 開發環境設定
1. 複製環境變數設定檔：
   ```bash
   cp .env.example .env
   ```
2. 編輯 `.env` 填入開發用 API 金鑰
3. 執行測試確保環境正確：
   ```bash
   python tests/test_simple_openai.py
   ```

### 程式碼品質檢查

建議在提交程式碼前執行以下檢查：

```bash
# 檢查程式碼格式
flake8 *.py

# 檢查類型提示（如果專案使用 mypy）
mypy *.py

# 執行完整測試套件
python -m pytest tests/ -v
```

### 偵錯提示

- 使用 `LOG_LEVEL=DEBUG` 環境變數以查看詳細日誌
- DocSend 處理失敗時，檢查是否有產生 debug HTML 檔案
- 測試 OCR 功能時，確認 Tesseract 路徑設定正確

## 貢獻指南

歡迎提交 Pull Requests 來改進這個項目。請確保：
1. 代碼符合 PEP 8 規範
2. 添加適當的測試
3. 更新文檔以反映更改

## 專案維護與清理

### 定期清理作業

為保持專案整潔，建議定期執行以下清理作業：

#### 移除臨時檔案
```bash
# 移除系統產生的臨時檔案
find . -name ".DS_Store" -delete
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null

# 清理 debug 檔案（如果產生的話）
rm -f debug_*.html
rm -rf tmp/
```

#### 整理測試檔案
- 所有測試檔案應放置於 `tests/` 目錄中
- 診斷工具保持在根目錄，但需在 README 中說明用途
- 移除過時的測試檔案

#### 備份管理
- 舊的備份目錄（如 `VC_CRM_backup_*`）可定期清理
- 重要設定檔變更前請先備份
- 建議使用 Git 而非本地備份目錄

### 檔案組織原則

#### 應保留的檔案
- **核心模組**: `main.py`, `deal_analyzer.py`, `sheets_manager.py` 等
- **設定檔案**: `requirements.txt`, `Dockerfile`, `.env.example`
- **診斷工具**: `diagnose_service_account.py`
- **文件指南**: `*.md` 檔案

#### 可清理的檔案類型
- 以 `debug_` 開頭的 HTML 檔案
- `tmp/` 目錄中的臨時檔案  
- 系統產生的 `.DS_Store` 檔案
- 舊的備份目錄
- 過時的測試檔案

#### 檔案位置規範
```
根目錄/
├── 核心程式檔案 (*.py)
├── 設定檔案 (*.txt, *.toml, Dockerfile)
├── 文件檔案 (*.md)
├── 診斷工具 (diagnose_*.py)
└── tests/           # 所有測試檔案
    └── test_*.py
```

### 環境維護

#### 依賴套件更新
```bash
# 檢查過時套件
pip list --outdated

# 更新 requirements.txt
pip freeze > requirements.txt
```

#### 環境變數檢查
定期檢查 `.env` 檔案是否包含所有必要設定：
- TELEGRAM_BOT_TOKEN
- OPENAI_API_KEY  
- GOOGLE_SHEETS_ID
- SERVICE_ACCOUNT_BASE64

### 效能監控

- 監控 OpenAI API 使用量和費用
- 檢查 Google Sheets API 配額使用情況
- 定期查看系統日誌檔案
- 檢查 Telegram Bot 回應時間

## 授權

[Your License]

## 環境設定

### 必要軟體安裝（線上部屬可以省略）

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
   - `TELEGRAM_BOT_TOKEN`：Telegram Bot Token（由 @BotFather 建立）
   - `GOOGLE_SHEETS_ID`：Google Sheets ID
   - `OPENAI_API_KEY`：OpenAI API 金鑰
   - `DOCSEND_EMAIL`：用於自動登入 DocSend 的 Email
   - `WORKING_DIRECTORY`：專案啟動時的工作資料夾路徑（影響下載與暫存目錄）
   - `TESSERACT`：Tesseract OCR 執行檔路徑（線上部屬請直接忽略此一 Variable）
     - Windows：`C:\\Program Files\\Tesseract-OCR\\tesseract.exe`
     - macOS：`/usr/local/bin/tesseract`
     - Linux：`/usr/bin/tesseract`
   - `GOOGLE_DRIVE_FOLDER_ID`：自動建立 Google Docs 檔案的雲端資料夾 ID
   - `PROMPT_MANAGER`=此為手動調整 Prompt 與使用者自訂 AI 模型面板，請填入 Google Sheets ID
   - `SERVICE_ACCOUNT_BASE64`=Service Account ，格式為 Base64，請使用 VC_CRM 中的 "Base64.py" ，貼上您的 Service_account.json 內容進行轉格式

### Tesseract OCR 設定說明

Tesseract OCR 用於從圖片中提取文字，主要用於：
- PDF 檔案中的圖片文字辨識
- DocSend 文件中的圖片內容辨識
- 投影片中的圖片文字擷取

確保 `TESSERACT` 環境變數指向正確的 Tesseract 執行檔路徑：

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
