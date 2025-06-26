import os
from openai import OpenAI
from typing import Optional

def universal_web_search(client: OpenAI, model: str, prompt: str, effort: str = "medium") -> Optional[str]:
    """
    通用 web_search 函式，根據模型自動選擇 API 與參數。
    支援 O3 (responses API) 及 GPT-4o/4/3.5 (chat.completions API)。

    :param client: OpenAI client 實例
    :param model: 模型名稱 (如 'o3', 'gpt-4o', 'gpt-4', 'gpt-3.5-turbo')
    :param prompt: 查詢內容
    :param effort: O3 專用推理強度 ('low', 'medium', 'high')
    :return: 回傳搜尋結果字串，或 None
    """
    try:
        model_lower = model.lower()
        # O3/Omni 3 專用
        if model_lower.startswith("o3"):
            response = client.responses.create(
                model=model,
                reasoning={"effort": effort},
                tools=[{"type": "web_search"}],
                input=[{"role": "user", "content": prompt}]
            )
            return getattr(response, "output_text", str(response))
        # GPT-4o/4/3.5
        else:
            # tools 參數僅 GPT-4o/4 支援，3.5 不支援
            tools = None
            if "4o" in model_lower or ("4" in model_lower and "3.5" not in model_lower):
                tools = [{"type": "web_search"}]
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                **({"tools": tools} if tools else {})
            )
            # chat 回傳格式
            return response.choices[0].message.content
    except Exception as e:
        print(f"[universal_web_search] Error: {e}")
        return None 