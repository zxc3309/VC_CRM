# install.py
import subprocess
import sys
import os
from shutil import which

REQUIREMENTS = [
    "requests==2.31.0",
    "beautifulsoup4==4.12.2",
    "openai==1.70.0",
    "python-dotenv==1.1.0",
    "python-telegram-bot==22.0",
    "playwright==1.51.0",
    "google-api-python-client==2.66.0",
    "google-auth==2.38.0",
    "google-auth-oauthlib",
    "pytesseract==0.3.10",
    "Pillow==9.5.0",
    "PyMuPDF",
    "python-pptx",
    "nest_asyncio"
]

ENV_TEMPLATE = """
# ========= 基本設定 =========
OPENAI_API_KEY=
DOCSEND_EMAIL=
TESSERACT=

# ========= Telegram Bot =========
TELEGRAM_BOT_TOKEN=
WORKING_DIRECTORY=.
"""

def install_packages():
    print("📦 安裝 Python requirements...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
    for pkg in REQUIREMENTS:
        print(f"🔧 安裝 {pkg} ...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

def install_playwright_browser():
    print("🌐 安裝 Playwright 瀏覽器依賴（Chromium）...")
    subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])

def check_tesseract():
    print("🧠 檢查 Tesseract 是否已安裝...")
    if which("tesseract") is None:
        print("⚠️ 尚未安裝 Tesseract OCR。請手動安裝：")
        if sys.platform.startswith("darwin"):
            print("👉 使用 Homebrew: brew install tesseract")
        elif sys.platform.startswith("win"):
            print("👉 從 https://github.com/tesseract-ocr/tesseract/releases 下載 Windows 安裝器")
        elif sys.platform.startswith("linux"):
            print("👉 使用 apt: sudo apt install tesseract-ocr")
    else:
        print("✅ 已偵測到 Tesseract")

def generate_env_file():
    if not os.path.exists(".env"):
        print("📝 尚未找到 .env 檔，正在建立範本...")
        with open(".env", "w", encoding="utf-8") as f:
            f.write(ENV_TEMPLATE.strip())
        print("✅ .env 已建立，請填入你的 OPENAI_API_KEY、TELEGRAM_BOT_TOKEN 等資訊。")
    else:
        print("✅ 已偵測到 .env 檔案，跳過建立。")

if __name__ == "__main__":
    install_packages()
    install_playwright_browser()
    check_tesseract()
    generate_env_file()
    print("\n🎉 安裝完成！請編輯 .env 並執行你的 Telegram Bot。")
