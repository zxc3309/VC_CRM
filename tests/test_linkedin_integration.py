"""
測試 LinkedIn 整合功能

這個測試檔案用於驗證 Apify LinkedIn Scraper 的整合是否正常運作
"""

import os
import sys
import pytest
import asyncio
from dotenv import load_dotenv

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from apify_linkedin import LinkedInSearcher
from deal_analyzer import DealAnalyzer


class TestLinkedInSearcher:
    """測試 LinkedInSearcher 類別"""

    @pytest.fixture
    def searcher(self):
        """建立 LinkedInSearcher 實例"""
        load_dotenv(override=True)
        return LinkedInSearcher()

    @pytest.mark.asyncio
    async def test_linkedin_searcher_initialization(self, searcher):
        """測試 LinkedIn Searcher 初始化"""
        assert searcher is not None

        # 如果沒有 API token，client 應該是 None
        if not os.getenv('APIFY_API_TOKEN'):
            assert searcher.client is None
            print("⚠️  警告: APIFY_API_TOKEN 未設定，跳過實際搜尋測試")
        else:
            assert searcher.client is not None
            print("✅ LinkedIn Searcher 初始化成功")

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv('APIFY_API_TOKEN'),
        reason="需要 APIFY_API_TOKEN 環境變數"
    )
    async def test_search_founder_profile(self, searcher):
        """測試搜尋創始人 LinkedIn Profile"""
        # 使用真實的測試案例
        founder_name = "Brian Chesky"
        company_name = "Airbnb"

        result = await searcher.search_founder_profile(
            founder_name=founder_name,
            company_name=company_name
        )

        assert result is not None
        print(f"✅ 成功搜尋到 {founder_name} 的 LinkedIn Profile")
        print(f"   Profile URL: {result.get('url', 'N/A')}")

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv('APIFY_API_TOKEN'),
        reason="需要 APIFY_API_TOKEN 環境變數"
    )
    async def test_extract_experience_data(self, searcher):
        """測試提取經歷資料"""
        founder_name = "Elon Musk"
        company_name = "Tesla"

        # 先搜尋 Profile
        profile = await searcher.search_founder_profile(
            founder_name=founder_name,
            company_name=company_name
        )

        if not profile:
            pytest.skip(f"無法找到 {founder_name} 的 LinkedIn Profile")

        # 提取資料
        data = searcher.extract_experience_data(profile)

        # 驗證資料結構
        assert 'name' in data
        assert 'title' in data
        assert 'linkedin_url' in data
        assert 'experience' in data
        assert 'education' in data
        assert 'skills' in data

        # 驗證資料內容
        assert isinstance(data['experience'], list)
        assert isinstance(data['education'], list)
        assert isinstance(data['skills'], list)

        print(f"✅ 成功提取 {data.get('name')} 的經歷資料")
        print(f"   職位: {data.get('title', 'N/A')}")
        print(f"   經歷數量: {len(data['experience'])}")
        print(f"   教育數量: {len(data['education'])}")
        print(f"   技能數量: {len(data['skills'])}")

    def test_validate_founder_logic(self, searcher):
        """測試創始人驗證邏輯"""
        # 模擬搜尋結果
        mock_results = [
            {
                'fullName': 'John Doe',
                'headline': 'Founder & CEO at TestCo',
                'positions': {
                    'positionsHistory': [
                        {
                            'companyName': 'TestCo',
                            'title': 'CEO & Founder'
                        }
                    ]
                }
            },
            {
                'fullName': 'Jane Doe',
                'headline': 'Software Engineer at OtherCo',
                'positions': {
                    'positionsHistory': [
                        {
                            'companyName': 'OtherCo',
                            'title': 'Engineer'
                        }
                    ]
                }
            }
        ]

        # 測試驗證函數
        result = searcher._validate_founder(
            results=mock_results,
            company_name='TestCo',
            founder_name='John Doe'
        )

        assert result is not None
        assert result['fullName'] == 'John Doe'
        print("✅ Founder 驗證邏輯測試通過")

    def test_format_duration(self, searcher):
        """測試日期格式化"""
        # 測試完整日期
        position = {
            'start': {'month': 1, 'year': 2020},
            'end': {'month': 12, 'year': 2023}
        }
        duration = searcher._format_duration(position)
        assert duration == "Jan 2020 - Dec 2023"

        # 測試當前職位（沒有結束日期）
        position_current = {
            'start': {'month': 6, 'year': 2021},
            'end': None
        }
        duration_current = searcher._format_duration(position_current)
        assert duration_current == "Jun 2021 - Present"

        print("✅ 日期格式化測試通過")


class TestDealAnalyzerIntegration:
    """測試 DealAnalyzer 與 LinkedIn 整合"""

    @pytest.fixture
    def analyzer(self):
        """建立 DealAnalyzer 實例"""
        load_dotenv(override=True)
        return DealAnalyzer()

    def test_linkedin_searcher_initialized(self, analyzer):
        """測試 DealAnalyzer 中的 LinkedIn Searcher 初始化"""
        # 即使沒有 API token，linkedin_searcher 也應該被建立（可能是 None client）
        assert hasattr(analyzer, 'linkedin_searcher')

        if os.getenv('APIFY_API_TOKEN'):
            assert analyzer.linkedin_searcher is not None
            print("✅ DealAnalyzer 中的 LinkedIn Searcher 已初始化")
        else:
            print("⚠️  警告: APIFY_API_TOKEN 未設定")

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        not os.getenv('APIFY_API_TOKEN') or not os.getenv('OPENAI_API_KEY'),
        reason="需要 APIFY_API_TOKEN 和 OPENAI_API_KEY 環境變數"
    )
    async def test_research_founder_background_with_linkedin(self, analyzer):
        """測試完整的 Founder 背景研究流程（包含 LinkedIn）"""
        founder_name = "Reid Hoffman"
        company_name = "LinkedIn"

        # 執行 Founder 背景研究
        result = await analyzer._research_founder_background(
            founder_name=founder_name,
            company_name=company_name,
            deck_data="",
            industry_info="Professional Networking",
            message_text=""
        )

        # 驗證返回結果
        assert result is not None
        assert 'title' in result
        assert 'background' in result
        assert 'previous_companies' in result
        assert 'education' in result
        assert 'achievements' in result
        assert 'LinkedIn URL' in result

        # 驗證 LinkedIn URL 不是 N/A（如果搜尋成功）
        print(f"✅ Founder 背景研究完成")
        print(f"   名稱: {founder_name}")
        print(f"   職位: {result.get('title', 'N/A')}")
        print(f"   LinkedIn: {result.get('LinkedIn URL', 'N/A')}")


def test_environment_variables():
    """測試環境變數設定"""
    load_dotenv(override=True)

    print("\n環境變數檢查:")
    print(f"  APIFY_API_TOKEN: {'✅ 已設定' if os.getenv('APIFY_API_TOKEN') else '❌ 未設定'}")
    print(f"  OPENAI_API_KEY: {'✅ 已設定' if os.getenv('OPENAI_API_KEY') else '❌ 未設定'}")

    # 這個測試不會失敗，只是顯示警告
    if not os.getenv('APIFY_API_TOKEN'):
        print("\n⚠️  警告: 請在 .env 檔案中設定 APIFY_API_TOKEN 以啟用 LinkedIn 搜尋功能")


if __name__ == "__main__":
    """直接執行測試"""
    print("開始測試 LinkedIn 整合功能...\n")

    # 執行測試
    pytest.main([__file__, "-v", "-s"])
