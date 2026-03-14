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
- **LinkedIn Profile 自動搜尋**（透過 Apify）：
  - 根據創辦人姓名 + 公司名稱自動搜尋 LinkedIn profile
  - 撈取完整經歷、學歷、技能等結構化資料
  - 作為 GPT 分析的優先參考來源
  - 零設定也能跑（沒有 Apify token 則跳過）
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
- OpenAI API 密鑰（支持 GPT-4 / GPT-5 系列，使用 Responses API）
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
├── linkedin_scraper.py          # LinkedIn Profile 搜尋模組（Apify 整合）
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
- **linkedin_scraper.py**: 透過 Apify API 搜尋創辦人的 LinkedIn profile 並撈取結構化資料

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

     # Apify Configuration (LinkedIn Profile Scraping - 選用)
     APIFY_API_TOKEN=your_apify_api_token
     APIFY_TIMEOUT=120
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

## 完整工作流程

```
┌─────────────────┐
│  Telegram Bot   │  使用者發送訊息（文字/連結/附件）
└────────┬────────┘
         ▼
┌─────────────────┐
│  deck_browser   │  擷取 DocSend / PDF / 網頁內容
└────────┬────────┘
         ▼
┌─────────────────┐
│  deal_analyzer  │  Step 1: 提取公司名稱、創辦人姓名
└────────┬────────┘
         │
         ├──────────────────────────────────┐
         ▼                                  ▼
┌─────────────────┐              ┌─────────────────┐
│ linkedin_scraper│              │   Web Search    │
│  (Apify API)    │              │  (OpenAI API)   │
│                 │              │                 │
│ 搜尋 founder    │              │ 搜尋公司資訊    │
│ LinkedIn profile│              │ + 創辦人背景    │
└────────┬────────┘              └────────┬────────┘
         │                                │
         └──────────────┬─────────────────┘
                        ▼
              ┌─────────────────┐
              │   GPT 分析      │  整合 LinkedIn + Web 資料
              │                 │  產生結構化 founder_info
              └────────┬────────┘
                       ▼
              ┌─────────────────┐
              │   doc_manager   │  產生 Observation + Questions
              │                 │  建立 Google Doc
              └────────┬────────┘
                       ▼
              ┌─────────────────┐
              │ sheets_manager  │  更新 Google Sheets
              └────────┬────────┘
                       ▼
              ┌─────────────────┐
              │  回覆 Telegram  │  提供 Doc + Sheets 連結
              └─────────────────┘
```

## 系統流程圖

![VC Bot 工作流程圖](VC_CRM/Process%20Chart/Process01.png)

## 注意事項

- 確保 OpenAI API key 有足夠的額度
- 保護好所有 API 密鑰和憑證
- 定期備份 Google Sheets 數據
- 注意 API 的使用限制和計費
- `apify-client>=1.6.0`：LinkedIn profile 搜尋（選用）