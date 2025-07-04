import os
import json
import asyncio
from dotenv import load_dotenv
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

async def get_linkedin_profile_html(company, founder, return_structured=False):
    load_dotenv(override=True)
    query = f'{company} {founder}'
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900}
        )
        cookies_path = "linkedin_cookies.json"
        if os.path.exists(cookies_path):
            try:
                with open(cookies_path, "r", encoding="utf-8") as f:
                    cookies = json.load(f)
                await context.add_cookies(cookies)
                print("已載入 LinkedIn cookies，嘗試免登入...")
            except Exception as e:
                print(f"讀取 cookies 失敗: {e}")
        page = await context.new_page()
        email = os.getenv("LINKEDIN_EMAIL")
        password = os.getenv("LINKEDIN_PASSWORD")
        await page.goto("https://www.linkedin.com/feed/")
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2)
        logged_in = False
        if "feed" in page.url:
            try:
                await page.wait_for_selector('input[placeholder*="Search"]', timeout=4000)
                logged_in = True
            except Exception:
                logged_in = False
        if not logged_in:
            await page.goto("https://www.linkedin.com/login")
            await page.wait_for_selector('input#username', timeout=10000)
            await page.fill('input#username', email)
            await page.fill('input#password', password)
            await page.click('button[type="submit"]')
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(2)
            try:
                captcha_selectors = [
                    'input#captcha', '.captcha', '.verification-code',
                    'input[name*="captcha"]', 'input[name*="verification"]',
                ]
                found_captcha = False
                for sel in captcha_selectors:
                    if await page.query_selector(sel):
                        print(f"偵測到驗證碼欄位: {sel}，自動暫停，請手動輸入驗證碼後繼續 Playwright...")
                        await page.pause()
                        found_captcha = True
                        break
                if not found_captcha:
                    content = await page.content()
                    if any(x in content for x in ["驗證碼", "captcha", "驗證您的身份", "verification code"]):
                        print("偵測到驗證碼相關文字，自動暫停，請手動輸入驗證碼後繼續 Playwright...")
                        await page.pause()
            except Exception as e:
                print(f"驗證碼偵測失敗: {e}")
            await page.goto("https://www.linkedin.com/feed/")
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(2)
            try:
                await page.wait_for_selector('input[placeholder*="Search"]', timeout=4000)
                logged_in = True
            except Exception:
                logged_in = False
            if not logged_in:
                print("LinkedIn 自動登入失敗，請檢查帳號密碼或驗證碼。")
                await browser.close()
                return None, None
            try:
                cookies = await context.cookies()
                with open(cookies_path, "w", encoding="utf-8") as f:
                    json.dump(cookies, f, ensure_ascii=False, indent=2)
                print("已儲存 LinkedIn cookies。")
            except Exception as e:
                print(f"儲存 cookies 失敗: {e}")
        await page.goto("https://www.linkedin.com/feed/")
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(1)
        selectors = [
            'input[placeholder*="Search"]',
        ]
        search_box = None
        for sel in selectors:
            try:
                print(f"嘗試 LinkedIn selector: {sel}")
                search_box = await page.wait_for_selector(sel, timeout=5000)
                if search_box:
                    print(f"找到搜尋框: {sel}")
                    break
            except Exception as e:
                print(f"selector {sel} 失敗: {e}")
        if not search_box:
            await page.screenshot(path="linkedin_searchbox_notfound.png")
            print("LinkedIn 搜尋框找不到，已截圖。")
            await browser.close()
            return None, None
        await search_box.click()
        await asyncio.sleep(0.3)
        await search_box.fill("")
        for char in query:
            await search_box.type(char)
            await asyncio.sleep(0.08)
        await asyncio.sleep(0.5)
        await page.keyboard.press("Enter")
        await page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2)
        try:
            people_tab = await page.query_selector('button[aria-label*="人員"], button[aria-label*="People"]')
            if people_tab:
                await people_tab.click()
                await asyncio.sleep(1.5)
        except Exception as e:
            print("切換人員分頁失敗：", e)
        profile_url = None
        try:
            await asyncio.sleep(3)
            view_links = await page.query_selector_all('a:has-text("View full profile")')
            if not view_links:
                view_links = await page.query_selector_all('a[href*="/in/"]')
            for link in view_links:
                href = await link.get_attribute('href')
                if href and "/in/" in href:
                    profile_url = href
                    await link.click()
                    await page.wait_for_load_state("domcontentloaded")
                    for _ in range(6):
                        await page.mouse.wheel(0, 1000)
                        await asyncio.sleep(1)
                    await asyncio.sleep(2)
                    html = await page.content()
                    with open('debug_linkedin.html', 'w', encoding='utf-8') as f:
                        f.write(html)
                    # 解析內容
                    soup = BeautifulSoup(html, 'html.parser')
                    # 1. LinkedIn URL
                    result = {"linkedin_url": profile_url}
                    # 2. About
                    about = None
                    about_candidates = []
                    about_section = soup.find(attrs={"aria-label": lambda v: v and ("About" in v or "自我介紹" in v)})
                    if about_section:
                        about_candidates.append(about_section.get_text(" ", strip=True))
                    about_section2 = soup.find(id=lambda v: v and ("about" in v.lower() or "自我介紹" in v))
                    if about_section2:
                        about_candidates.append(about_section2.get_text(" ", strip=True))
                    about_section3 = soup.find('section', class_=lambda v: v and ("summary" in v or "about" in v))
                    if about_section3:
                        about_candidates.append(about_section3.get_text(" ", strip=True))
                    for span in soup.find_all('span', class_='visually-hidden'):
                        text = span.get_text(" ", strip=True)
                        if text and ("About" in text or "自我介紹" in text):
                            next_span = span.find_next('span', class_='visually-hidden')
                            if next_span:
                                about_candidates.append(next_span.get_text(" ", strip=True))
                    for section in soup.find_all('section'):
                        if section.get_text().strip().startswith(('About', '自我介紹')):
                            about_candidates.append(section.get_text(" ", strip=True))
                    about = next((a for a in about_candidates if a and len(a) > 10), None)
                    result["about"] = about
                    # 3. Experience
                    exp_section = soup.find('section', id='experience')
                    if not exp_section:
                        exp_section = soup.find('section', class_=lambda v: v and 'experience' in v)
                    if not exp_section:
                        for section in soup.find_all('section'):
                            text = section.get_text(" ", strip=True)
                            if "Experience" in text or "經歷" in text:
                                exp_section = section
                                break
                    if not exp_section:
                        print("[DEBUG] 找不到 Experience 區塊，以下是所有 section 的前 100 字：")
                        for section in soup.find_all('section'):
                            print(section.get_text(" ", strip=True)[:100])
                            print("="*40)
                    jobs = []
                    if exp_section:
                        exp_items = exp_section.find_all('li', class_=lambda v: v and 'artdeco-list__item' in v)
                        for item in exp_items:
                            # 只抓最外層主要內容
                            spans = item.find_all('span', attrs={'aria-hidden': 'true'})
                            # debug print
                            print("==== Experience item ====")
                            for idx, s in enumerate(spans):
                                print(f"span[{idx}]: {s.get_text(strip=True)}")
                            job_title = spans[0].get_text(strip=True) if len(spans) > 0 else None
                            company = spans[1].get_text(strip=True) if len(spans) > 1 else None
                            period = None
                            location = None
                            description = None
                            # 地名關鍵字
                            location_keywords = [
                                "United States", "On-site", "Remote", "Area", "City", "Country", "Province", "State","Global"
                            ]
                            for s in spans[2:]:
                                text = s.get_text(strip=True)
                                if not text:
                                    continue
                                if (not period) and (any(x in text for x in ["年", "月", "Present", "to", "-", "/", ".", "·"])):
                                    period = text
                                # location: 關鍵字優先，或短內容
                                elif (not location) and (
                                    any(x in text for x in location_keywords)
                                    or (len(text) < 40 and not any(p in text for p in '.!?，。；'))
                                ):
                                    location = text
                                elif (not description) and (len(text) > 30):
                                    description = text
                            if not description:
                                for tag in item.find_all(['p', 'div']):
                                    text = tag.get_text(strip=True)
                                    if len(text) > 30:
                                        description = text
                                        break
                            # 放寬條件：只要有職稱或公司就保留
                            if not job_title and not company:
                                continue
                            jobs.append({'job_title': job_title, 'company': company, 'period': period, 'location': location, 'description': description})
                        # 若 jobs 為空，debug print exp_section HTML
                        if not jobs:
                            print("[DEBUG] exp_section HTML 前 1000 字：")
                            print(exp_section.prettify()[:1000])
                    result["experience"] = jobs
                    # 4. Education
                    edu_section = soup.find('section', id='education')
                    if not edu_section:
                        edu_section = soup.find('section', class_=lambda v: v and 'education' in v)
                    if not edu_section:
                        for section in soup.find_all('section'):
                            text = section.get_text(" ", strip=True)
                            if "Education" in text or "學歷" in text or "學校" in text:
                                edu_section = section
                                break
                    if not edu_section:
                        print("[DEBUG] 找不到 Education 區塊，以下是所有 section 的前 100 字：")
                        for section in soup.find_all('section'):
                            print(section.get_text(" ", strip=True)[:100])
                            print("="*40)
                    educations = []
                    if edu_section:
                        for li in edu_section.find_all('li', class_=lambda v: v and 'artdeco-list__item' in v):
                            spans = li.find_all('span', attrs={'aria-hidden': 'true'})
                            # debug print
                            print("==== Education item ====")
                            for idx, s in enumerate(spans):
                                print(f"span[{idx}]: {s.get_text(strip=True)}")
                            school = spans[0].get_text(strip=True) if len(spans) > 0 else None
                            degree = spans[1].get_text(strip=True) if len(spans) > 1 else None
                            period = spans[2].get_text(strip=True) if len(spans) > 2 else None
                            if school:
                                educations.append({'school': school, 'degree': degree, 'period': period})
                        if not educations:
                            print("[DEBUG] edu_section HTML 前 1000 字：")
                            print(edu_section.prettify()[:1000])
                    result["education"] = educations
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                    with open('linkedin_debug_result.json', 'w', encoding='utf-8') as f:
                        json.dump(result, f, ensure_ascii=False, indent=2)
                    await browser.close()
                    if return_structured:
                        return profile_url, result
                    return profile_url, html
            all_links = await page.query_selector_all('a')
            print(f"搜尋結果頁所有 a 標籤共 {len(all_links)} 個")
            for i, a in enumerate(all_links[:30]):
                href = await a.get_attribute('href')
                class_name = await a.get_attribute('class')
                print(f"a[{i}]: href={href}, class={class_name}")
        except Exception as e:
            print("擷取 LinkedIn 個人頁面連結失敗：", e)
        await page.screenshot(path="linkedin_no_profile_found.png")
        print("LinkedIn 搜尋結果找不到個人頁面連結，已截圖。")
        await browser.close()
        return None, None

if __name__ == "__main__":
    import sys
    company = input("請輸入公司名: ").strip()
    founder = input("請輸入創辦人名: ").strip()
    asyncio.run(get_linkedin_profile_html(company, founder)) 