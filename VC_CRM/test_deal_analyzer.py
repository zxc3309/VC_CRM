import asyncio
import json
from deal_analyzer import DealAnalyzer

async def test_deal_analyzer():
    # 初始化 DealAnalyzer
    analyzer = DealAnalyzer()
    
    # 測試數據
    message_text = """
    Butter is also governance related project and working with Uniswap and Optimism foundation for bringing Futarchy (prediction market style govnernance framework) on web3
    If you're interested in Butter feel free to lmk. Happy to connect with you and the team :
    - Blurb: Butter is a governance project which is building Conditional Funding Markets with Uniswap and Optimism foundation.
    - Deck: https://pitch.com/v/speculate-to-allocate-sjwkjp/79c2235c-f6b1-497f-9c64-d6ed63b6b1c4
    """
    
    # deck_data 應該是一個列表，包含一個字典
    deck_data = [{
    "company": "Butter",
    "problem": "Decision-making and allocation of capital in organizations, especially in grant-making and governance, is inefficient and often lacks mechanisms to accurately reflect stakeholders' information, leading to suboptimal outcomes.",
    "solution": "Butter is building information finance tools to enable speculation-driven allocation. Leveraging mechanisms like futarchy (markets to predict outcomes of policy decisions), Butter allows organizations to use prediction markets and mechanism design to drive better decision-making and resource allocation.",
    "business_model": "Butter provides a platform and tools for organizations, DAOs, and grant programs to deploy information markets and mechanism design for their capital allocation processes. Revenue streams may include SaaS subscriptions, transaction fees, and enterprise partnerships.",
    "financials": "No explicit financials provided in the deck. However, past funding/grants mentioned include Flashbots Bill Grants and support from Allo.Capital, indicating initial external validation.",
    "market": "Butter targets the rapidly growing digital organizations market — specifically DAOs, grant-giving foundations, corporate governance structures, and other decision-heavy groups who seek to optimize resource allocation through more accurate, data-driven methods. The presence of partners like Allo.Capital and mentions of organizations like Dow Jones suggests a global and institutional ambition.",
    "funding_team": "CEO & Cofounder: Vaughn McKenzie (2x founder in legaltech, French govtech, elite engineering grande école); CTO & Cofounder: Alex Hajjar (Aave Grants DAO); Architect: Robin Hanson (creator of futarchy, Professor of Economics at George Mason University, 2x founder, Series B CPO, Forbes 30u30, Techstars alum); Mechanism Design: Yiling Chen (Harvard, Gordon McKay Professor of Computer Science & Economics); Research Associate: Alex (Gitcoin); Events & Partnerships: Laura. The team is led by proven builders and advised by pioneers in decision markets and mechanism design."       
}]
    
    try:
        # 執行分析
        result = await analyzer.analyze_deal(message_text, deck_data)
        
        # 打印結果
        print("\n=== 分析結果 ===")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
    except Exception as e:
        print(f"分析過程中發生錯誤: {str(e)}")
    finally:
        # 清理資源
        import gc
        gc.collect()

if __name__ == "__main__":
    try:
        asyncio.run(test_deal_analyzer())
    except KeyboardInterrupt:
        print("\n程式被使用者中斷")
    except Exception as e:
        print(f"發生嚴重錯誤: {str(e)}")
    finally:
        # 確保所有資源都被釋放
        import gc
        gc.collect() 