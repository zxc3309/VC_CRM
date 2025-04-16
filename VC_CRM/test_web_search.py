import asyncio
import logging
from deal_analyzer import DealAnalyzer

async def test_web_search():
    # 設置日誌級別
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    try:
        # 創建分析器實例
        analyzer = DealAnalyzer()
        
        # 測試查詢
        query = "OpenAI company information"
        logger.info(f"\n開始測試簡單查詢: {query}")
        
        # 執行搜索
        result = await analyzer._web_search(query)
        
        # 打印結果
        logger.info("\n搜索結果:")
        logger.info("-" * 50)
        logger.info(result.get('content', 'No content found'))
        
        # 打印引用
        logger.info("\n引用:")
        logger.info("-" * 50)
        for citation in result.get('citations', []):
            logger.info(f"URL: {citation.get('url', 'N/A')}")
            
    except Exception as e:
        logger.error(f"測試過程中出錯: {str(e)}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(test_web_search()) 