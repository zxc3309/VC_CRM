# 使用官方 Playwright + Python 映像（已內建瀏覽器與依賴）
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

# 設定工作目錄
WORKDIR /app

# 安裝 Tesseract OCR（含繁體中文語系）
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-chi-tra \
    libtesseract-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 複製專案檔案
COPY . .

# 安裝 Python 套件
RUN pip install --no-cache-dir -r requirements.txt

# ✅ 安裝 Playwright 瀏覽器
RUN playwright install --with-deps

# 設定 Tesseract 執行檔路徑
ENV TESSERACT=/root/.nix-profile/bin/tesseract

# 預設啟動命令
CMD ["python", "main.py"]
