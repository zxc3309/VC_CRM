"""Google Gemini Provider - uses the Google Generative AI SDK."""

import logging
from typing import Optional
from ai_provider import CompletionResult

logger = logging.getLogger(__name__)


class GeminiProvider:
    """Google Gemini implementation using google-generativeai SDK."""

    def __init__(self, api_key: str):
        try:
            from google import genai
            self.genai = genai
            self.client = genai.Client(api_key=api_key)
            logger.info("Gemini provider initialized")
        except ImportError:
            raise ImportError(
                "google-genai package is required for Gemini provider. "
                "Install it with: pip install google-genai"
            )

    async def complete(
        self,
        prompt: str,
        model: str,
        system_instruction: str = "",
        json_mode: bool = False,
        temperature: Optional[float] = None,
    ) -> CompletionResult:
        """Standard completion using Gemini API."""
        from google.genai import types

        config_params = {}
        if system_instruction:
            config_params["system_instruction"] = system_instruction
        if json_mode:
            config_params["response_mime_type"] = "application/json"
        if temperature is not None:
            config_params["temperature"] = temperature

        config = types.GenerateContentConfig(**config_params) if config_params else None

        response = await self.client.aio.models.generate_content(
            model=model,
            contents=prompt,
            config=config,
        )

        return CompletionResult(
            text=response.text,
            raw_response=response,
        )

    async def web_search(
        self,
        query: str,
        model: str,
    ) -> CompletionResult:
        """Web search using Gemini's Google Search grounding."""
        from google.genai import types

        logger.info("Using Gemini Google Search grounding")

        google_search_tool = types.Tool(
            google_search=types.GoogleSearch()
        )

        config = types.GenerateContentConfig(
            tools=[google_search_tool],
        )

        response = await self.client.aio.models.generate_content(
            model=model,
            contents=query,
            config=config,
        )

        # 提取引用 (grounding metadata)
        citations = []
        if response.candidates and response.candidates[0].grounding_metadata:
            grounding = response.candidates[0].grounding_metadata
            if grounding.grounding_chunks:
                for chunk in grounding.grounding_chunks:
                    if hasattr(chunk, 'web') and chunk.web:
                        citations.append({
                            'title': getattr(chunk.web, 'title', ''),
                            'url': getattr(chunk.web, 'uri', ''),
                        })

        return CompletionResult(
            text=response.text,
            citations=citations,
            raw_response=response,
        )
