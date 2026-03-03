"""
llm/router.py
Single entry point for all LLM calls across all agents.
Implements primary → fallback 1 → fallback 2 with exponential backoff.
"""
import asyncio
import time
from backend.config import (
    GEMINI_API_KEY, GEMINI_MODEL,
    GROQ_API_KEY, GROQ_MODEL,
    MISTRAL_API_KEY, MISTRAL_MODEL,
)


class LLMRouter:
    """
    Usage:
        router = LLMRouter()
        response = await router.call(prompt="...", task="structured_parse")

    task types:
        "structured_parse"  — needs reliable JSON output → prefer Gemini
        "content_gen"       — creative text generation → Groq is fine
        "reasoning"         — complex multi-step reasoning → prefer Gemini
    """

    async def call(self, prompt: str, task: str = "general", max_tokens: int = 1000) -> str:
        providers = self._get_provider_order(task)
        last_error = None

        for attempt, provider_fn in enumerate(providers):
            try:
                wait = 2 ** attempt  # 1s, 2s, 4s
                if attempt > 0:
                    await asyncio.sleep(wait)
                result = await provider_fn(prompt, max_tokens)
                return result
            except Exception as e:
                last_error = e
                print(f"[LLMRouter] {provider_fn.__name__} failed (attempt {attempt+1}): {e}")
                continue

        raise RuntimeError(f"All LLM providers failed. Last error: {last_error}")

    def _get_provider_order(self, task: str):
        """Route task type to optimal provider order."""
        if task in ("structured_parse", "reasoning"):
            return [self._call_gemini, self._call_groq, self._call_mistral]
        elif task == "content_gen":
            return [self._call_groq, self._call_gemini, self._call_mistral]
        else:
            return [self._call_gemini, self._call_groq, self._call_mistral]

    async def _call_gemini(self, prompt: str, max_tokens: int) -> str:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(max_output_tokens=max_tokens)
        )
        return response.text

    async def _call_groq(self, prompt: str, max_tokens: int) -> str:
        from groq import AsyncGroq
        client = AsyncGroq(api_key=GROQ_API_KEY)
        response = await client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    async def _call_mistral(self, prompt: str, max_tokens: int) -> str:
        from mistralai import Mistral
        client = Mistral(api_key=MISTRAL_API_KEY)
        response = await client.chat.complete_async(
            model=MISTRAL_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content


# Singleton — import and use anywhere
llm_router = LLMRouter()
