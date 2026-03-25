"""OpenAI Provider - uses the Responses API."""

import logging
from typing import Optional
from openai import AsyncOpenAI
from ai_provider import CompletionResult

logger = logging.getLogger(__name__)


class OpenAIProvider:
    """OpenAI implementation using the Responses API."""

    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)
        logger.info("OpenAI provider initialized")

    def _supports_temperature(self, model: str) -> bool:
        """檢查模型是否支援 temperature 參數"""
        model_lower = model.lower()
        if model_lower.startswith("gpt-5") or model_lower.startswith("o1") or model_lower.startswith("o3"):
            return False
        return True

    async def complete(
        self,
        prompt: str,
        model: str,
        system_instruction: str = "",
        json_mode: bool = False,
        temperature: Optional[float] = None,
    ) -> CompletionResult:
        """Standard completion using OpenAI Responses API."""
        params = {
            "model": model,
            "input": [{"role": "user", "content": prompt}],
            "store": True,
        }
        if system_instruction:
            params["instructions"] = system_instruction
        if json_mode:
            params["text"] = {"format": {"type": "json_object"}}
        if temperature is not None and self._supports_temperature(model):
            params["temperature"] = temperature

        result = await self.client.responses.create(**params)
        return CompletionResult(
            text=result.output_text,
            raw_response=result,
        )

    async def web_search(
        self,
        query: str,
        model: str,
    ) -> CompletionResult:
        """Web search using OpenAI's web_search tool or reasoning API for o3 models."""
        model_lower = model.lower()

        if model_lower.startswith("o3"):
            # O3 / o3-mini / o3-pro 模型使用 reasoning API
            logger.info("Using OpenAI reasoning format (o3)")
            response = await self.client.responses.create(
                model=model,
                input=[{"role": "user", "content": query}],
                reasoning={"effort": "medium", "summary": "auto"},
                store=True,
            )
        else:
            # 其他模型使用 web_search tool
            logger.info("Using OpenAI web_search tool")
            params = {
                "model": model,
                "input": [{"role": "user", "content": query}],
                "tools": [{"type": "web_search", "search_context_size": "medium"}],
                "top_p": 1,
                "store": True,
            }
            if self._supports_temperature(model):
                params["temperature"] = 0
            response = await self.client.responses.create(**params)

        # 提取文字內容
        text_content = ""
        if hasattr(response, 'output_text'):
            text_content = response.output_text
        elif hasattr(response, 'output') and isinstance(response.output, list) and response.output:
            text_content = str(response.output[0])

        # 提取引用
        citations = []
        if hasattr(response, 'citations'):
            citations = response.citations or []

        return CompletionResult(
            text=text_content,
            citations=citations,
            raw_response=response,
        )
