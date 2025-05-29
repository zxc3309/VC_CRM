# 使用 Python 3.11 slim 作為基礎映像
FROM python:3.11-slim

# 環境變數設置
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 安裝系統依賴（Tesseract + Chromium 依賴 + Node.js）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gnupg ca-certificates wget tesseract-ocr tesseract-ocr-chi-tra libtesseract-dev \
    libglib2.0-0 libnss3 libatk1.0-0 libatk-bridge2.0-0 libxcomposite1 libxdamage1 \
    libxrandr2 libgbm1 libxss1 libasound2 libpangocairo-1.0-0 libpango-1.0-0 libcairo2 \
    fonts-liberation libappindicator1 libjpeg-dev zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# 安裝 Node.js（Playwright 需要）
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g npm@latest && \
    npm cache clean --force

# 設定工作目錄
WORKDIR /app

# 複製程式碼
COPY . .

# 安裝 Python 套件（包括 Playwright）
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        requests==2.31.0 \
        beautifulsoup4==4.12.2 \
        "openai>=1.0.0,<2.0.0" \
        python-dotenv==1.1.0 \
        python-telegram-bot==22.0 \
        playwright==1.51.0 \
        google-api-python-client==2.66.0 \
        google-auth==2.38.0 \
        google-auth-oauthlib==1.1.0 \
        pytesseract==0.3.10 \
        "Pillow>=10.0.0,<12.0.0" \
        PyMuPDF==1.23.7 \
        python-pptx==0.6.21 \
        nest_asyncio==1.6.0 \
        gspread==5.12.4 \
        oauth2client==4.1.3

# ✅ Playwright install（不要加 --with-deps）
RUN playwright install chromium

# 啟動指令
CMD ["python", "main.py"]
