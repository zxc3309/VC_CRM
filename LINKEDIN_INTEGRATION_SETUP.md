# LinkedIn Integration Setup Guide

本指南說明如何設定 LinkedIn Founder 背景搜尋功能。

## 📋 概述

這個整合使用 Apify 的 LinkedIn Profile Search Actor 來搜尋並提取創始人的 LinkedIn 資料，包括：
- 完整工作經歷
- 教育背景
- 技能
- LinkedIn Profile URL

## 🔧 設定步驟

### 1. 取得 Apify API Token

1. 前往 [Apify](https://apify.com/) 註冊帳號
2. 進入 Settings → Integrations
3. 複製你的 API Token
4. 在 `.env` 檔案中新增：
   ```bash
   APIFY_API_TOKEN=your_apify_api_token_here
   ```

### 2. 安裝相依套件

```bash
pip install -r requirements.txt
```

這會安裝 `apify-client>=1.7.0`

### 3. 在 Google Sheets Prompt Manager 中新增 Prompt

請在你的 Prompt Manager Google Sheets 中新增以下 Prompt：

#### Prompt ID: `research_founder_background_with_linkedin`

**內容**:
```
你現在有兩個來源的創始人資料：

1. **網路搜尋結果**:
{search_content}

2. **LinkedIn 完整資料**:
{linkedin_data}

請整合這兩個來源，提取以下資訊並以 JSON 格式返回：

{{
  "title": "當前職位",
  "background": "詳細背景描述（100-200 字，用繁體中文撰寫）",
  "previous_companies": [
    {{
      "company": "公司名稱",
      "role": "職位",
      "duration": "時間期間"
    }}
  ],
  "education": "教育背景（學校、學位、年份）",
  "achievements": [
    "主要成就1",
    "主要成就2"
  ],
  "sources": ["來源1", "來源2"]
}}

**重要指示**:
1. **優先使用 LinkedIn 資料**（更準確、更完整）
2. **用網路搜尋補充** LinkedIn 沒有的資訊（例如：特殊成就、獎項）
3. **previous_companies 必須按時間倒序排列**（最新的在前）
4. **background 應該包含**：
   - 創始人的核心專長領域
   - 在 {company_name} 之前的主要經歷
   - 為什麼適合做這個產品/服務
5. **如果 LinkedIn 資料為空或不完整**，完全依賴網路搜尋結果
6. **所有描述使用繁體中文**，除非是專有名詞或公司/產品名稱

**產業資訊**: {industry_info}
**公司名稱**: {company_name}
**創始人名稱**: {founder_name}
**Deck 資料**: {deck_data}
**訊息文字**: {message_text}

請務必返回有效的 JSON 格式。
```

### 4. 設定說明

1. 開啟你的 Prompt Manager Google Sheets
2. 找到 prompt 定義的位置（通常是一個兩欄的表格：prompt_id | content）
3. 新增一行：
   - **Column A (prompt_id)**: `research_founder_background_with_linkedin`
   - **Column B (content)**: 貼上上面的 Prompt 內容

### 5. 驗證設定

執行測試來確認整合是否正常：

```bash
cd tests
python test_linkedin_integration.py
```

## 🚀 使用方式

整合完成後，系統會自動在分析 Deal 時執行以下流程：

1. **Web Search**: 使用 OpenAI 搜尋創始人資訊
2. **LinkedIn Search**: 使用 Apify 搜尋 LinkedIn Profile
3. **AI 分析**: 合併兩個來源的資料並生成結構化資訊
4. **輸出**:
   - Google Doc 中會顯示 "Founder LinkedIn Profile" 區塊
   - Google Sheets 中會有 "Founder LinkedIn" 欄位（超連結）

## 📊 資料流向

```
Telegram 訊息
    ↓
提取 Founder 名字 + 公司名稱
    ↓
並行執行：
    ├─ OpenAI Web Search
    └─ Apify LinkedIn Search
    ↓
AI 整合分析（使用 research_founder_background_with_linkedin prompt）
    ↓
輸出到：
    ├─ Google Doc（完整背景資料 + LinkedIn URL）
    └─ Google Sheets（LinkedIn 超連結）
```

## 🔍 搜尋策略

系統使用 **"Founder Name + Company Name"** 的搜尋查詢來確保找到正確的人。

**驗證機制**:
1. 檢查 current_company 是否包含目標公司名稱
2. 檢查 job_title 是否包含 "Founder" / "CEO" / "Co-founder"
3. 選擇評分最高的結果

## ⚠️ 注意事項

### 成本估算
- LinkedIn Profile Search: 約 $0.5-2 per 100 profiles
- 每次分析 1 個 Founder ≈ $0.005-0.02
- 月成本（假設 100 個 Deals）≈ $0.5-2

### 降級策略
如果 LinkedIn 搜尋失敗（API 錯誤、找不到 Profile 等），系統會自動降級為：
- 只使用 Web Search 結果
- LinkedIn URL 顯示為 "N/A"
- 不會中斷整個分析流程

### LinkedIn 政策
- 只抓取公開的 Profile 資料
- 遵守 Apify 和 LinkedIn 的使用條款
- 不要過度頻繁呼叫 API

## 🐛 故障排除

### LinkedIn 搜尋未執行
**檢查**:
1. `APIFY_API_TOKEN` 是否正確設定在 `.env`
2. Apify 帳號是否有足夠的額度
3. 查看 log 中的錯誤訊息

### 找不到正確的 Founder
**可能原因**:
1. LinkedIn Profile 設定為私密
2. Founder 名字拼寫不同（例如：中文 vs 英文名）
3. 公司名稱不完整

**解決方案**:
- 確認訊息中的 Founder 名字和公司名稱正確
- 系統會在找不到時自動降級為 Web Search

### Prompt 找不到
**錯誤訊息**: `Prompt 'research_founder_background_with_linkedin' not found`

**解決**:
1. 確認已在 Google Sheets Prompt Manager 中新增該 prompt
2. Prompt ID 必須完全相同（區分大小寫）
3. 重新載入 Prompt Manager：重啟應用程式

## 📝 範例輸出

### Google Doc 輸出

```
Founder LinkedIn Profile
https://www.linkedin.com/in/elonmusk/

Founder Experience
• CEO & Product Architect at Tesla (2008 - Present)
• CEO & CTO at SpaceX (2002 - Present)
• Co-founder at PayPal (1999 - 2002)
```

### Google Sheets 輸出

| Opportunity | Description | Log | Deck | Founder LinkedIn |
|-------------|-------------|-----|------|------------------|
| Tesla       | Electric vehicles | [Log](link) | [Deck](link) | [LinkedIn](https://linkedin.com/in/elonmusk) |

## 🎉 完成！

設定完成後，每次分析 Deal 時都會自動搜尋 LinkedIn 資料並整合到報告中。

如有問題，請查看 `test_linkedin_integration.py` 中的測試案例。
