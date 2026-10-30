"""Thin AsyncOpenAI factory. Critical path must not import LangChain."""

from __future__ import annotations

from functools import lru_cache

from openai import AsyncOpenAI

from app.settings import get_settings


@lru_cache(maxsize=1)
def get_async_openai() -> AsyncOpenAI:
    settings = get_settings()
    kwargs: dict[str, str] = {}
    if settings.openai_api_key:
        kwargs["api_key"] = settings.openai_api_key
    return AsyncOpenAI(**kwargs)
