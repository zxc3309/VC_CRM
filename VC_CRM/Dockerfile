# 使用 Python 3.11 的輕量版本作為基礎映像
FROM python:3.11-slim

# 設定環境變數
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 安裝系統依賴：tesseract 與瀏覽器所需的 lib
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-chi-tra \
    libtesseract-dev \
    libglib2.0-0 \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libxss1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libpango-1.0-0 \
    libcairo2 \
    fonts-liberation \
    libappindicator1 \
    libjpeg-dev \
    zlib1g-dev \
    curl \
    gnupg \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 設定工作目錄
WORKDIR /app

# 複製專案檔案
COPY . .

# 安裝 Python 相依套件
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        requests==2.31.0 \
        beautifulsoup4==4.12.2 \
        openai>=1.0.0,<2.0.0 \
        python-dotenv==1.1.0 \
        python-telegram-bot==22.0 \
        playwright==1.51.0 \
        google-api-python-client==2.66.0 \
        google-auth==2.38.0 \
        google-auth-oauthlib==1.1.0 \
        pytesseract==0.3.10 \
        Pillow>=10.0.0,<12.0.0 \
        PyMuPDF==1.23.7 \
        python-pptx==0.6.21 \
        nest_asyncio==1.6.0 \
        gspread==5.12.4 \
        oauth2client==4.1.3

# 安裝 Playwright 瀏覽器（Chromium）
RUN playwright install --with-deps chromium

# 預設啟動指令（你可以視情況改為 app.py 或 bot.py）
CMD ["python", "main.py"]
