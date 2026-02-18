"""Multi-provider LLM service for agent chat completions.

Mirrors the EmbeddingService pattern: provider selected via LLM_PROVIDER env var.
Supports Gemini (default, free tier) and OpenAI.
"""
import json
import logging
from typing import Optional

from ..config import settings

logger = logging.getLogger(__name__)

_LLM_DEFAULTS = {
    "gemini": {"model": "gemini-2.0-flash"},
    "openai": {"model": "gpt-4o-mini"},
}


class LLMService:
    """Generates chat completions via the configured LLM provider."""

    def __init__(self):
        self.provider = (settings.llm_provider or "gemini").lower()
        defaults = _LLM_DEFAULTS.get(self.provider, _LLM_DEFAULTS["gemini"])
        self.model = settings.llm_model or defaults["model"]

        if self.provider == "gemini":
            key = settings.gemini_api_key
            if key:
                logger.info("LLM GEMINI_API_KEY found (%s...%s)", key[:4], key[-4:])
            else:
                logger.error("GEMINI_API_KEY is NOT set — LLM calls will fail!")
            from google import genai
            self._genai_client = genai.Client(api_key=key)
        elif self.provider == "openai":
            key = settings.openai_api_key
            if key:
                logger.info("LLM OPENAI_API_KEY found (%s...%s)", key[:4], key[-4:])
            else:
                logger.error("OPENAI_API_KEY is NOT set — LLM calls will fail!")
            from openai import OpenAI
            self._openai = OpenAI(api_key=key)
        else:
            raise ValueError(f"Unsupported LLM_PROVIDER: {self.provider!r}")

        logger.info(
            "LLMService initialised: provider=%s  model=%s",
            self.provider, self.model,
        )

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        """Single-turn chat completion returning plain text."""
        logger.info(
            "[LLM] chat START  provider=%s  model=%s  user_prompt_len=%d",
            self.provider, self.model, len(user_prompt),
        )
        if self.provider == "gemini":
            result = self._chat_gemini(system_prompt, user_prompt)
        else:
            result = self._chat_openai(system_prompt, user_prompt)
        logger.info("[LLM] chat END  response_len=%d", len(result))
        return result

    def chat_json(self, system_prompt: str, user_prompt: str) -> dict:
        """Chat completion expecting a JSON response. Parses and returns dict."""
        json_system = (
            system_prompt + "\n\nIMPORTANT: Respond ONLY with valid JSON. "
            "No markdown fences, no extra text."
        )
        raw = self.chat(json_system, user_prompt)
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines).strip()
        return json.loads(cleaned)

    # ------------------------------------------------------------------
    # Provider implementations
    # ------------------------------------------------------------------

    def _chat_gemini(self, system_prompt: str, user_prompt: str) -> str:
        from google.genai import types

        response = self._genai_client.models.generate_content(
            model=self.model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.3,
                max_output_tokens=4096,
            ),
        )
        return response.text

    def _chat_openai(self, system_prompt: str, user_prompt: str) -> str:
        response = self._openai.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=4096,
        )
        return response.choices[0].message.content
