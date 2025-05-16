import os
from io import BytesIO  # 移到最上面
import logging
from dotenv import load_dotenv
from utils.path_helper import PathHelper
import re
import asyncio
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Page
from typing import Optional, List, Dict, Literal, Any
import random
from PIL import Image
import pytesseract
import requests
from openai import AsyncOpenAI
import json
import fitz  # PyMuPDF for PDF
import tempfile
from pptx import Presentation

# Load environment variables
load_dotenv()

# Pytesseract Path
pytesseract.pytesseract.tesseract_cmd = os.getenv('TESSERACT')


# 配置日誌
logger = logging.getLogger(__name__)
print("OPENAI_API_KEY:", os.getenv("OPENAI_API_KEY"))
# 5. 配置 Tesseract 路徑
tesseract_path = os.getenv('TESSERACT')

logger.info(f"Final Tesseract path: {pytesseract.pytesseract.tesseract_cmd}")

class DeckBrowser:
    """DocSend 文檔讀取器"""
    
    def __init__(self):
        """Initialize the DeckBrowser."""
        self.browser = None
        self.logger = logging.getLogger(__name__)
        self.email = os.getenv("DOCSEND_EMAIL")  # 替換為您的電子郵件
        self.path_helper = PathHelper()

    #決定流程
    SourceType = Literal["docsend", "attachment", "gdrive", "unknown"]
    
    @staticmethod
    def detect_source_type(message: str, attachments: Optional[list] = None) -> "DeckBrowser.SourceType":
        if "docsend.com" in message.lower():
            return "docsend"
        elif attachments and any(
            att.get("name", "").lower().endswith(('.pdf', '.pptx', '.ppt'))
            for att in attachments if isinstance(att, dict)
        ):
            return "attachment"
        elif re.search(r"https://(?:drive|docs)\.google\.com/(?:file/d/|presentation/)[\w\-/]+", message):
            return "gdrive"
        else:
            return "unknown"
    
    async def process_input(self, message: str, attachments: Optional[list] = None):
        source_type = self.detect_source_type(message, attachments)

        if source_type == "docsend":
            self.logger.info(f"開始處理 Docsend")
            return await self.run_docsend_analysis(message)
        elif source_type == "attachment":
            self.logger.info(f"開始處理 Attachment")
            return await self.run_file_analysis(attachments)
        elif source_type == "gdrive":
            self.logger.info(f"開始處理 Google Drive")
            return await self.run_gdrive_analysis(message)
        else:
            # 新增：允許純文字直接丟給 GPT
            self.logger.info("未偵測到連結或附件，直接分析純文字內容")
            summary = await summarize_pitch_deck(message)
            return [summary] if summary else [{"error": "❌ 純文字分析失敗"}]

    async def run_gdrive_analysis(self, message: str) -> Dict[str, Any]:
        self.logger.info(f"📥 開始處理 Google Drive 連結: {message}")

        gdrive_match = re.search(r"https://drive\.google\.com/file/d/([\w-]+)", message)
        if not gdrive_match:
            gdrive_match = re.search(r"id=([\w-]+)", message)

        if not gdrive_match:
            return {"error": "❌ 無法從訊息中擷取 Google Drive 檔案 ID。請確認連結格式。"}

        file_id = gdrive_match.group(1)
        export_url = f"https://drive.google.com/uc?export=download&id={file_id}"

        try:
            response = requests.get(export_url)
            response.raise_for_status()

            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(response.content)
                tmp_path = tmp.name

            self.logger.info(f"📄 成功下載 PDF 檔案至 {tmp_path}，開始執行分析...")

            return await self.run_file_analysis([{"path": tmp_path, "name": "gdrive.pdf"}])

        except Exception as e:
            self.logger.error(f"❌ 下載或處理 Google Drive 檔案時發生錯誤：{str(e)}")
            return {"error": f"❌ Google Drive 檔案處理失敗：{str(e)}"}
            
    async def run_file_analysis(self, attachments: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        處理 PDF/PPTX 附件：執行 OCR 或結構化摘要
        """
        results = []

        for file in attachments:
            path = file.get("path")
            name = file.get("name", "unnamed")
            suffix = self.path_helper.get(name).suffix.lower()

            self.logger.info(f"📂 開始分析附件: {name}")

            extracted_text = ""

            try:
                # Check file size before processing
                file_path_obj = self.path_helper.get(path)
                if not file_path_obj.exists() or file_path_obj.stat().st_size < 1024:
                    self.logger.error(f"❌ 檔案 {name} ({path}) 太小或不存在，可能下載失敗。")
                    results.append({"error": f"❌ 檔案 {name} 下載失敗或不是有效的檔案。"})
                    continue

                if suffix == ".pdf":
                    doc = fitz.open(str(file_path_obj))
                    for page in doc:
                        extracted_text += page.get_text("text") + "\n"
                    doc.close()

                elif suffix == ".pptx":
                    try:
                        prs = Presentation(str(file_path_obj))
                    except Exception as e:
                        self.logger.error(f"❌ 無法開啟 PPTX 檔案 {name}: {type(e).__name__}: {e}")
                        results.append({"error": f"❌ 無法開啟 PPTX 檔案 {name}: {type(e).__name__}: {e}"})
                        continue
                    for i, slide in enumerate(prs.slides):
                        for shape in slide.shapes:
                            if hasattr(shape, "text"):
                                extracted_text += f"[Slide {i+1}]\n{shape.text}\n"

                if not extracted_text.strip():
                    self.logger.warning(f"⚠️ {name} 沒有擷取到文字，開始執行 OCR 圖片辨識")

                    image_urls = []
                    if suffix == ".pdf":
                        doc = fitz.open(str(file_path_obj))
                        for page_num, page in enumerate(doc):
                            pix = page.get_pixmap(dpi=200)
                            img_path_obj = self.path_helper.get(f"{file_path_obj}_page_{page_num}.png")
                            pix.save(str(img_path_obj))
                            image_urls.append(f"file://{img_path_obj}")
                        doc.close()

                    elif suffix == ".pptx":
                        self.logger.warning("❌ 尚未實作 PPTX 頁面轉圖片的 OCR fallback")
                        continue

                    if image_urls:
                        ocr_text = await ocr_images_from_urls(image_urls)
                        if ocr_text:
                            summary = await summarize_pitch_deck(ocr_text)
                            if summary:
                                results.append(summary)
                                continue

                else:
                    summary = await summarize_pitch_deck(extracted_text)
                    if summary:
                        results.append(summary)

            except Exception as e:
                self.logger.error(f"❌ 分析檔案 {name} 發生錯誤：{e}")
                results.append({"error": f"❌ 分析失敗: {name}"})

        return results if results else [{"error": "❌ 沒有成功處理任何附件內容"}]

    #主要 Docsend 驅動式
    async def run_docsend_analysis(self, message: str) -> Dict[str, Any]:
        """
        封裝完整流程：初始化 -> 擷取 URL -> 抽取內容 -> 關閉瀏覽器 -> 回傳結果
        """
        await self.initialize()
        
        results = []  # List to store JSON results
        urls = await self.extract_docsend_links(message)
        for url in urls:
            content = await self.read_docsend_document(url)
            if isinstance(content, dict):
                results.append(content)
            elif isinstance(content, str):
                summarized = await summarize_pitch_deck(content)
                if summarized:
                    results.append(summarized)

        await self.close()
        
        return results if results else [{"error": "❌ 沒有成功擷取任何 DocSend 文檔內容"}]

    async def initialize(self):
        """Initialize the browser instance asynchronously."""
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=False)
            self.logger.info("Browser initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize browser: {str(e)}")
            raise

    async def close(self):
        """關閉瀏覽器"""
        if self.browser:
            await self.browser.close()
            self.browser = None
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
    
    async def extract_docsend_links(self, text: str) -> List[str]:
        """從文本中提取 DocSend 連結"""
        docsend_pattern = r'https?://(?:www\.)?docsend\.com/[^\s)"}]+'
        return re.findall(docsend_pattern, text)
    
    async def _get_page(self, url: str) -> Page:
        """Get a new page with configured User-Agent and other settings."""
        page = await self.browser.new_page()
        await page.set_viewport_size({'width': 1920, 'height': 1080})
        await page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'sec-ch-ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"macOS"'
        })
        
        return page

    async def read_docsend_document(self, url: str) -> Optional[str]:
        """讀取 DocSend 文檔的內容"""
        try:
            self.logger.info(f"正在從 DocSend 連結讀取內容: {url}")
            
            # 創建新頁面
            page = await self._get_page(url)
            
            # 訪問 DocSend 頁面
            response = await page.goto(url, wait_until='networkidle', timeout=30000)
            
            self.logger.info(f"訪問狀態碼: {response.status}")
            
            if response.status == 403:
                self.logger.error("訪問被拒絕 (403 Forbidden)")
                await page.close()
                return None
            
            # 隨機等待 2-5 秒
            await asyncio.sleep(random.uniform(2, 5))
            
            # 檢查是否需要填寫電子郵件
            email_input = await page.query_selector('input[type="email"]')
            if email_input:
                self.logger.info("需要填寫電子郵件才能訪問文檔")
                await page.type('input[type="email"]', self.email, delay=random.uniform(100, 200))
                try:
                    self.logger.info("嘗試點擊提交按鈕")
                    await page.locator('button:has-text("Continue")').wait_for(state='visible', timeout=1000)
                    await page.locator('button:has-text("Continue")').click(timeout=1000)
                except Exception as e:
                    self.logger.warning(f"提交按鈕點擊失敗: {e}")
                await page.wait_for_load_state('networkidle', timeout=30000)
                
            # 嘗試判斷是否成功登入 DocSend 文件（加入更多 selector fallback）
            success_selectors = [
                '.document-content',
                '.viewer-content',
                '.page',
                '.ds-viewer-container',
            ]

            successfully_entered = False
            for selector in success_selectors:
                try:
                    if await page.query_selector(selector):
                        self.logger.info(f"✅ 成功進入 DocSend 文件，偵測到 selector: {selector}")
                        successfully_entered = True
                        break
                except Exception as e:
                    self.logger.warning(f"❌ 檢查 selector {selector} 發生錯誤: {e}")

            if not successfully_entered:
                self.logger.warning("⚠️ 沒有偵測到任何 DocSend 文件內容的 selector，可能登入失敗。")

            # 再次隨機等待（讓網頁有機會繼續載入）
            await asyncio.sleep(random.uniform(2, 5))
            
            # 截圖以便調試
            debug_screenshot_name = f"docsend_debug_{random.randint(1000, 9999)}.png"
            debug_screenshot_path = str(self.path_helper.get("tmp", debug_screenshot_name))
            self.path_helper.ensure_dir("tmp")
            await page.screenshot(path=debug_screenshot_path)
            self.logger.info(f"保存頁面截圖至: {debug_screenshot_path}")
            
            # Debug 將整頁 HTML 儲存下來
            html = await page.content()
            debug_html_path = self.path_helper.get("debug_docsend.html")
            with debug_html_path.open("w", encoding="utf-8") as f:
                f.write(html)

            # Debug 顯示目前頁面上的所有 iframe（若有）
            for frame in page.frames:
                print(f"[iframe] name: {frame.name}, url: {frame.url}")
            
            # 等待文檔內容加載
            # 嘗試從所有 iframe 中找到內容
            target_frame = None
            content_selectors = ['.document-content', '.page', '.viewer-content', '.ds-viewer-container']

            for frame in page.frames:
                frame_url = frame.url or ""
                # 根據 URL 判斷是主 DocSend iframe，而不是 dropbox 或 intercom 等雜訊
                if "docsend.com/view" in frame_url and "marketing.docsend.com" not in frame_url:
                    for selector in content_selectors:
                        try:
                            await frame.wait_for_selector(selector, timeout=5000)
                            self.logger.info(f"在 iframe 中找到內容: {selector}")
                            target_frame = frame
                            break
                        except:
                            continue
                if target_frame:
                    break

                if not target_frame:
                    self.logger.warning("⚠️ 未能找到含文字 selector，開始 debug 所有 iframe...")
                    await debug_all_iframes(page)

                    # 嘗試從所有 iframe 中擷取圖片做 OCR
                    for frame in page.frames:
                        try:
                            frame_html = await frame.content()
                            soup = BeautifulSoup(frame_html, "html.parser")
                            img_tags = soup.find_all("img")
                            image_urls = [img["src"] for img in img_tags if img.get("src")]
                            
                            if image_urls:
                                self.logger.info(f"✅ 在 iframe 中找到圖片：共 {len(image_urls)} 張，準備執行 OCR")
                                ocr_raw_text = await ocr_images_from_urls(image_urls)
                                if ocr_raw_text:
                                    summarized_text = await summarize_pitch_deck(ocr_raw_text)
                                    await page.close()
                                    return summarized_text
                        except Exception as e:
                            self.logger.warning(f"讀取 iframe 內容失敗：{e}")

                    self.logger.error("❌ 所有 iframe 均未能提供內容或圖片")
                    await page.close()
                    return None
                
            # 從 iframe 抓 HTML
            html = await target_frame.content()
            self.logger.info(f"獲取的HTML內容長度: {len(html)} 字符")
            
            # 解析 HTML
            soup = BeautifulSoup(html, 'html.parser')
            
            # 提取文檔標題
            title_elem = soup.find('title')

            # fallback：如果 iframe 沒有 title，嘗試從主頁 page 拿
            if not title_elem:
                self.logger.info("iframe 中未找到 <title>，嘗試從主頁抓取 title")
                main_html = await page.content()
                main_soup = BeautifulSoup(main_html, 'html.parser')
                title_elem = main_soup.find('title')

            # 最終取得 title
            title = title_elem.text.strip() if title_elem else "DocSend Document"
            self.logger.info(f"提取的文檔標題: {title}")
            
            # 提取文檔內容
            text_elements = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'div'])
            self.logger.info(f"找到 {len(text_elements)} 個文本元素")
            
            extracted_text = []
            
            for elem in text_elements:
                text = elem.get_text().strip()
                if text and len(text) > 10:  # 只保留有意義的文本
                    extracted_text.append(text)
            
            self.logger.info(f"篩選後提取了 {len(extracted_text)} 個有意義的文本段落")
            extracted_text = "\n\n".join(extracted_text)
            
            # 關閉頁面
            await page.close()
            
            if not extracted_text or len(extracted_text) < 100:
                self.logger.warning("⚠️ 文字內容過少，嘗試 OCR 圖片並用 GPT 摘要")
                img_tags = soup.find_all('img')
                image_urls = [img['src'] for img in img_tags if img.get('src')]

                if image_urls:
                    ocr_raw_text = await ocr_images_from_urls(image_urls)
                    if ocr_raw_text:
                        summarized_text = await summarize_pitch_deck(ocr_raw_text)
                        extracted_text = summarized_text
            
            # 記錄內容摘要
            content_preview = extracted_text[:100] + "..." if len(extracted_text) > 100 else extracted_text
            self.logger.info(f"提取文本預覽: {content_preview}")
            self.logger.info(f"總提取文本長度: {len(extracted_text)} 字符")
            
            # 格式化提取的內容
            formatted_content = f"--- DocSend 文檔: {title} ---\n\n{extracted_text}\n\n--- DocSend 文檔結束 ---"
            
            self.logger.info(f"成功從 DocSend 連結提取內容: {url}")
            return formatted_content
        
        except Exception as e:
            self.logger.error(f"讀取 DocSend 文檔時出錯: {str(e)}", exc_info=True)
            if 'page' in locals():
                await page.close()
            return None

        

#GPT 總結        
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def ocr_images_from_urls(image_urls: List[str]) -> str:
    """下載圖片並執行 OCR"""
    from pytesseract import pytesseract
    results = []

    for i, url in enumerate(image_urls):
        try:
            # 處理 base64 圖片
            if url.startswith('data:image/'):
                try:
                    import base64
                    # 取得 base64 編碼部分
                    header, encoded = url.split(",", 1)
                    img_data = base64.b64decode(encoded)
                    img = Image.open(BytesIO(img_data))
                except Exception as e:
                    logger.warning(f"❌ 無法解析 base64 圖片: {str(e)}")
                    continue
            # 處理一般 URL
            elif url.startswith("http"):
                response = requests.get(url)
                img = Image.open(BytesIO(response.content))
            else:
                logger.warning(f"❌ 不支援的圖片 URL 格式: {url[:100]}...")
                continue

            # 使用 UTF-8 編碼處理文字
            text = pytesseract.image_to_string(img, lang='eng')
            if text and text.strip():
                # 確保文字使用 UTF-8 編碼
                text_encoded = text.encode('utf-8', errors='ignore').decode('utf-8')
                results.append(f"[Slide {i+1}]\n{text_encoded}")
                
        except Exception as e:
            logger.warning(f"❌ 讀取圖片失敗: {str(e)}", exc_info=True)

    return "\n\n".join(results)

async def summarize_pitch_deck(ocr_text: str) -> Dict:
    """用 GPT 摘要 Pitch Deck OCR 文字為結構化大綱並回傳 dict"""
    # 確保輸入文字是 UTF-8 編碼
    if isinstance(ocr_text, str):
        ocr_text = ocr_text.encode('utf-8', errors='ignore').decode('utf-8')

    # 使用英文 prompt 避免編碼問題
    prompt = f"""
Based on the following Pitch Deck content, create a structured summary.
Return in the following JSON format:
{{
  "company": "company_name",
  "problem": "problem_statement",
  "solution": "solution_statement",
  "business_model": "how they do business",
  "financials": "financials_summary",
  "market": "what's the target market and it's description",
  "funding_team": "founding_team and their background",
}}

Pitch Deck Content:
{ocr_text}
"""

    try:
        completion = await openai_client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": "You are a professional analyst helping investors organize Pitch Deck information."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        raw_output = json.loads(completion.choices[0].message.content)
        logger.info(f"成功提取Deck信息")       
        return raw_output
    except Exception as e:
        logger.error(f"GPT 處理失敗：{str(e)}")
        return {
            "error": f"分析失敗: {str(e)}",
            "company": "未知公司",
            "summary": "分析失敗"
        }
    

async def debug_all_iframes(page):
    """
    儲存所有 iframe 的 HTML 並列出關鍵資訊（文字、圖片、canvas 數量）。
    """
    frames = page.frames
    print(f"\n🔍 檢測到 {len(frames)} 個 iframe。")

    for idx, frame in enumerate(frames):
        print(f"\n📦 解析 iframe [{idx}] URL: {frame.url}")

        try:
            # 儲存 HTML
            html = await frame.content()
            from utils.path_helper import PathHelper as _PH
            _ph = _PH()
            file_path = _ph.get(f"debug_frame_{idx}.html")
            with file_path.open("w", encoding="utf-8") as f:
                f.write(html)
            print(f"📝 已儲存 HTML 到 {file_path}")

            # 抓主要元素數量
            text_count = await frame.eval_on_selector_all('p', 'els => els.length')
            div_count = await frame.eval_on_selector_all('div', 'els => els.length')
            img_count = await frame.eval_on_selector_all('img', 'els => els.length')
            canvas_count = await frame.eval_on_selector_all('canvas', 'els => els.length')

            print(f"📊 內容統計：")
            print(f" - <p> 標籤：{text_count}")
            print(f" - <div> 標籤：{div_count}")
            print(f" - <img> 圖片：{img_count}")
            print(f" - <canvas> 元素：{canvas_count}")

            # 顯示可能性分析
            if canvas_count > 0:
                print("⚠️ 發現 canvas，可能是圖像渲染的 slide。")
            if text_count > 5 or div_count > 20:
                print("✅ 可能有文字內容。")
            if img_count > 5 and text_count < 2:
                print("🖼️ 很可能是純圖片型投影片。")

        except Exception as e:
            print(f"❌ 讀取 iframe {idx} 發生錯誤：{str(e)}")
    

#測試用驅動器
if __name__ == "__main__":

    async def main():
        message = """
        Normie Tech lets your customers pay you in stablecoins without an onramp
        Before this I managed a million dollar grant program for Vitalik and saw the number 1 issue repeatedly holding back web3: sending customers to exchanges where >3/4 give up. We built a solution for our own platform and other projects asked to hire us to do the same.
        Profitable from set up fees by month 4, raising a pre-seed to move faster.
        Here is the deck:
        https://docsend.com/view/sikphsrjbwpz8h82

        """
        
        reader = DeckBrowser()
        await reader.initialize()
        try:
            results = await reader.process_input(message)
            await reader.close()

            if results:
                print(json.dumps(results[0], ensure_ascii=False, indent=2))
            else:
                print("⚠️ 沒有擷取到任何結果")

        except Exception as e:
            print(results)
            print(f"❌ 發生錯誤: {e}")
            await reader.close()

    asyncio.run(main())
