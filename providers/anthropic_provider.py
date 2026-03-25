"""Anthropic Claude Provider - uses the Anthropic SDK."""

import logging
from typing import Optional
from ai_provider import CompletionResult

logger = logging.getLogger(__name__)


class AnthropicProvider:
    """Anthropic Claude implementation using the Anthropic SDK."""

    def __init__(self, api_key: str):
        try:
            from anthropic import AsyncAnthropic
            self.client = AsyncAnthropic(api_key=api_key)
            logger.info("Anthropic provider initialized")
        except ImportError:
            raise ImportError(
                "anthropic package is required for Anthropic provider. "
                "Install it with: pip install anthropic"
            )

    async def complete(
        self,
        prompt: str,
        model: str,
        system_instruction: str = "",
        json_mode: bool = False,
        temperature: Optional[float] = None,
    ) -> CompletionResult:
        """Standard completion using Anthropic Messages API."""
        kwargs = {
            "model": model,
            "max_tokens": 8192,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system_instruction:
            # 如果開啟 json_mode，在 system instruction 中加入 JSON 指示
            if json_mode:
                system_instruction += "\n\nIMPORTANT: You must respond with valid JSON only. No other text."
            kwargs["system"] = system_instruction
        elif json_mode:
            kwargs["system"] = "IMPORTANT: You must respond with valid JSON only. No other text."

        if temperature is not None:
            kwargs["temperature"] = temperature

        response = await self.client.messages.create(**kwargs)

        # 提取文字內容
        text_parts = []
        for block in response.content:
            if hasattr(block, 'text'):
                text_parts.append(block.text)
        text = "\n".join(text_parts)

        return CompletionResult(
            text=text,
            raw_response=response,
        )

    async def web_search(
        self,
        query: str,
        model: str,
    ) -> CompletionResult:
        """Web search using Anthropic's server-side web search tool."""
        logger.info("Using Anthropic web search tool")

        response = await self.client.messages.create(
            model=model,
            max_tokens=8192,
            tools=[{
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": 5,
            }],
            messages=[{"role": "user", "content": query}],
        )

        # 提取文字和引用
        text_parts = []
        citations = []
        for block in response.content:
            if hasattr(block, 'text'):
                text_parts.append(block.text)
                # 提取引用 (如果有 citations 屬性)
                if hasattr(block, 'citations') and block.citations:
                    for cite in block.citations:
                        if hasattr(cite, 'url'):
                            citations.append({
                                'title': getattr(cite, 'title', ''),
                                'url': cite.url,
                            })

        return CompletionResult(
            text="\n".join(text_parts),
            citations=citations,
            raw_response=response,
        )
