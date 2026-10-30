from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = ""
    decider: Literal["mock", "llm_json"] = "mock"
    retriever: Literal["fixtures", "qdrant"] = "fixtures"
    writer: Literal["template", "openai"] = "template"
    models_yaml: Path = ROOT / "models.yaml"
    catalog_path: Path = ROOT / "fixtures" / "catalog.json"
    rag_dir: Path = ROOT / "fixtures" / "rag"
    gold_path: Path = ROOT / "fixtures" / "eval" / "gold.json"
    qdrant_url: str = "http://127.0.0.1:6333"
    qdrant_collection: str = "orvalho_stage_chunks"
    no_offer_until_turn: int = 4
    min_turns_between_offers: int = 3
    max_offers: int = 2


def get_settings() -> Settings:
    return Settings()
