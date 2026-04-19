"""OpenAI AI service for LLM interactions"""
import os
import logging
import httpx
from typing import Optional

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = "https://api.openai.com/v1"
MODEL = "gpt-4o-mini"


class AIService:
    """Service for interacting with OpenAI API"""

    def __init__(self, api_key: str = OPENAI_API_KEY):
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment")
        self.api_key = api_key
        self.base_url = OPENAI_BASE_URL
        self.model = MODEL
        self.timeout = 30

    async def _post(self, messages: list[dict], json_mode: bool = False) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1000,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                if "choices" in data and len(data["choices"]) > 0:
                    return data["choices"][0]["message"]["content"]
                raise ValueError("No response content from AI")
        except httpx.TimeoutException as e:
            logger.error(f"AI request timeout after {self.timeout}s: {e}")
            raise
        except httpx.HTTPError as e:
            logger.error(f"AI request failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in AI query: {e}")
            raise

    async def query(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return await self._post(messages)

    async def chat(self, history: list[dict], system_prompt: str) -> str:
        """Send a multi-turn conversation and return a JSON-mode response."""
        messages = [{"role": "system", "content": system_prompt}] + history
        return await self._post(messages, json_mode=True)


# Global instance
_ai_service: Optional[AIService] = None


def get_ai_service() -> AIService:
    """Get or initialize the AI service"""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service
