"""Multi-provider LLM service for agent chat completions.

Mirrors the EmbeddingService pattern: provider selected via LLM_PROVIDER env var.
Supports Gemini (default, free tier) and OpenAI.

Dual-model support:
  - "default" model (gemini-2.0-flash) for complex/creative tasks
  - "lite" model (gemini-2.0-flash-lite) for simple tasks
A class-level rate limiter enforces a 15-second gap between API calls to
stay within free-tier RPM limits.
"""
import json
import logging
import threading
import time
from typing import Optional

from ..config import settings

logger = logging.getLogger(__name__)

GEMINI_MODEL_DEFAULT = "gemini-2.0-flash"
GEMINI_MODEL_LITE = "gemini-2.0-flash-lite"

_LLM_DEFAULTS = {
    "gemini": {"model": GEMINI_MODEL_DEFAULT, "model_lite": GEMINI_MODEL_LITE},
    "openai": {"model": "gpt-4o-mini", "model_lite": "gpt-4o-mini"},
}

# Rate-limit interval in seconds (shared across all LLMService instances)
_THROTTLE_SECONDS = 15


class LLMService:
    """Generates chat completions via the configured LLM provider."""

    # Class-level rate limiter shared across all instances
    _lock = threading.Lock()
    _last_call_time: float = 0.0

    def __init__(self):
        self.provider = (settings.llm_provider or "gemini").lower()
        defaults = _LLM_DEFAULTS.get(self.provider, _LLM_DEFAULTS["gemini"])
        self.model = settings.llm_model or defaults["model"]
        self.model_lite = settings.llm_model_lite or defaults["model_lite"]

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
            "LLMService initialised: provider=%s  model=%s  model_lite=%s",
            self.provider, self.model, self.model_lite,
        )

    # ------------------------------------------------------------------
    # Model resolution
    # ------------------------------------------------------------------

    def _resolve_model(self, model: Optional[str]) -> str:
        """Resolve model alias to actual model name.

        - None  → self.model (default/heavy)
        - "lite" → self.model_lite
        - anything else → passed through as-is
        """
        if model is None:
            return self.model
        if model == "lite":
            return self.model_lite
        return model

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------

    @classmethod
    def _throttle(cls) -> None:
        """Block until at least _THROTTLE_SECONDS have elapsed since the last call."""
        with cls._lock:
            now = time.monotonic()
            elapsed = now - cls._last_call_time
            if elapsed < _THROTTLE_SECONDS:
                wait = _THROTTLE_SECONDS - elapsed
                logger.info("[LLM] throttle: waiting %.1fs to respect RPM limit", wait)
                time.sleep(wait)
            cls._last_call_time = time.monotonic()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chat(self, system_prompt: str, user_prompt: str, *, model: Optional[str] = None) -> str:
        """Single-turn chat completion returning plain text."""
        resolved_model = self._resolve_model(model)
        logger.info(
            "[LLM] chat START  provider=%s  model=%s  user_prompt_len=%d",
            self.provider, resolved_model, len(user_prompt),
        )
        self._throttle()
        if self.provider == "gemini":
            result = self._chat_gemini(system_prompt, user_prompt, resolved_model)
        else:
            result = self._chat_openai(system_prompt, user_prompt, resolved_model)
        logger.info("[LLM] chat END  response_len=%d", len(result))
        return result

    def chat_json(self, system_prompt: str, user_prompt: str, *, model: Optional[str] = None) -> dict:
        """Chat completion expecting a JSON response. Parses and returns dict."""
        json_system = (
            system_prompt + "\n\nIMPORTANT: Respond ONLY with valid JSON. "
            "No markdown fences, no extra text."
        )
        raw = self.chat(json_system, user_prompt, model=model)
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines).strip()
        return json.loads(cleaned)

    # ------------------------------------------------------------------
    # Provider implementations
    # ------------------------------------------------------------------

    def _chat_gemini(self, system_prompt: str, user_prompt: str, model: str) -> str:
        from google.genai import types

        response = self._genai_client.models.generate_content(
            model=model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.3,
                max_output_tokens=4096,
            ),
        )
        return response.text

    def _chat_openai(self, system_prompt: str, user_prompt: str, model: str) -> str:
        response = self._openai.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=4096,
        )
        return response.choices[0].message.content
