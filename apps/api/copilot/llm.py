import os
from typing import Optional

from fastapi import HTTPException

DEFAULT_GEMINI_MODEL = "gemini/gemini-3-flash-preview"


def get_env(*names: str) -> Optional[str]:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


def resolve_litellm_config() -> tuple[str, dict]:
    gemini_api_key = get_env("GEMINI_API_KEY", "GOOGLE_API_KEY")
    if not gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    extra_kwargs = {"api_key": gemini_api_key}
    gemini_api_base = os.getenv("GEMINI_API_BASE")
    if gemini_api_base:
        extra_kwargs["api_base"] = gemini_api_base
    return (
        os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL),
        extra_kwargs,
    )


def extract_text(response) -> str:
    content = response.choices[0].message.content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("text"):
                parts.append(item["text"])
        content = "\n".join(parts)
    return (content or "").strip()


def call_llm(
    prompt: str,
    _provider_text: str = "",
    max_tokens: int = 800,
    response_format: Optional[dict] = None,
) -> str:
    """Call LiteLLM. All business numbers must come from upstream services."""
    try:
        import litellm

        model, extra_kwargs = resolve_litellm_config()
        completion_kwargs = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.2,
            **extra_kwargs,
        }
        if response_format is not None:
            completion_kwargs["response_format"] = response_format
        response = litellm.completion(**completion_kwargs)
        text = extract_text(response)
        if not text:
            raise RuntimeError("LLM provider returned empty text")
        return text
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"LLM provider unavailable: {exc}") from exc


def invoke_llm(
    prompt: str,
    _provider_text: str = "",
    max_tokens: int = 800,
    response_format: Optional[dict] = None,
) -> str:
    """Compatibility wrapper for older tests/mocks that accept fewer kwargs."""
    try:
        return call_llm(
            prompt,
            _provider_text,
            max_tokens=max_tokens,
            response_format=response_format,
        )
    except TypeError as exc:
        if "unexpected keyword" not in str(exc):
            raise
        return call_llm(prompt, _provider_text)
