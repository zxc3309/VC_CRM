# install.py
import subprocess
import sys
import os
from shutil import which

REQUIREMENTS = [
    "requests==2.31.0",
    "beautifulsoup4==4.12.2",
    "openai>=1.0.0,<2.0.0",
    "python-dotenv==1.1.0",
    "python-telegram-bot==22.0",
    "playwright==1.51.0",
    "google-api-python-client==2.66.0",
    "google-auth==2.38.0",
    "google-auth-oauthlib==1.1.0",
    "pytesseract==0.3.10",
    "Pillow>=10.0.0,<12.0.0",
    "PyMuPDF==1.23.7",
    "python-pptx==0.6.21",
    "nest_asyncio==1.6.0",
    "gspread==5.12.4",
    "oauth2client==4.1.3"
]

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
    path = which("tesseract")
    if path is None:
        print("⚠️ 尚未安裝 Tesseract OCR。請手動安裝：")
        if sys.platform.startswith("darwin"):
            print("👉 使用 Homebrew: brew install tesseract")
        elif sys.platform.startswith("win"):
            print("👉 從 https://github.com/tesseract-ocr/tesseract/releases 下載 Windows 安裝器")
        elif sys.platform.startswith("linux"):
            print("👉 使用 apt: sudo apt install tesseract-ocr")
        return None
    else:
        print(f"✅ 已傳查到 Tesseract: {path}")
        return path

def install_system_dependencies():
    print("🔧 檢查並安裝 system 依賴套件...")
    if sys.platform.startswith("darwin"):
        brew_exists = which("brew") is not None
        if not brew_exists:
            print("⚠️ 未檢測到 Homebrew。請先手動安裝 Homebrew: https://brew.sh")
        else:
            subprocess.call(["brew", "install", "pkg-config", "poppler", "tesseract"])
    elif sys.platform.startswith("linux"):
        subprocess.call(["sudo", "apt", "update"])
        subprocess.call(["sudo", "apt", "install", "-y", "libpoppler-cpp-dev", "tesseract-ocr"])
    else:
        print("⚠️ 非 macOS/Linux 環境，請手動安裝 poppler 與 tesseract")

if __name__ == "__main__":
    install_packages()
    install_playwright_browser()
    tesseract_path = check_tesseract()
    install_system_dependencies()
    print("📂 當前工作目錄（working directory）：", os.getcwd())
    print("\n🎉 安裝完成！Tesseract 路徑：", tesseract_path or "未找到")
