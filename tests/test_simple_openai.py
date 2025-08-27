#!/usr/bin/env python3
"""
簡單的 OpenAI API 測試
"""
import asyncio
import os
from dotenv import load_dotenv
from openai import AsyncOpenAI

async def test_simple_openai():
    print("🔧 測試 OpenAI API 連接...")
    
    # 強制重新載入 .env 檔案
    load_dotenv(override=True)
    api_key = os.getenv("OPENAI_API_KEY")
    
    print(f"📁 工作目錄: {os.getcwd()}")
    print(f"🔍 .env 檔案存在: {os.path.exists('.env')}")
    
    if not api_key:
        print("❌ 未找到 OPENAI_API_KEY")
        return
    
    print(f"✅ API Key 存在，長度: {len(api_key)} 字符")
    
    # 檢查 API key 是否包含非 ASCII 字符
    try:
        api_key.encode('ascii')
        print("✅ API Key 是純 ASCII 字符")
    except UnicodeEncodeError as e:
        print(f"❌ API Key 包含非 ASCII 字符: {e}")
        # 清理 API key
        api_key = api_key.encode('ascii', errors='ignore').decode('ascii')
        print(f"🔧 清理後的 API Key 長度: {len(api_key)}")
    
    try:
        client = AsyncOpenAI(api_key=api_key)
        
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": "Hello, please respond with a simple JSON: {\"test\": \"success\"}"}
            ],
            response_format={"type": "json_object"}
        )
        
        result = response.choices[0].message.content
        print(f"✅ OpenAI API 測試成功")
        print(f"📄 回應: {result}")
        
    except Exception as e:
        print(f"❌ OpenAI API 測試失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_simple_openai())