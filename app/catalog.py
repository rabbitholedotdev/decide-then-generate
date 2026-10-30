from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.settings import ROOT, get_settings
from app.types import CatalogItem


class Catalog:
    def __init__(self, items: list[CatalogItem], shop_name: str = "Orvalho Atelier"):
        self.items = items
        self.shop_name = shop_name
        self._by_id = {item.id: item for item in items}

    def get(self, item_id: str) -> CatalogItem | None:
        return self._by_id.get(item_id)

    def require(self, item_id: str) -> CatalogItem:
        item = self.get(item_id)
        if item is None:
            raise KeyError(item_id)
        return item

    def names(self) -> set[str]:
        return {item.name.lower() for item in self.items}

    def ids(self) -> set[str]:
        return set(self._by_id)

    def filter_ids(self, ids: list[str]) -> list[str]:
        known = self.ids()
        return [item_id for item_id in ids if item_id in known]

    def by_tag(self, tag: str) -> list[CatalogItem]:
        return [item for item in self.items if tag in item.tags]

    def render_for_prompt(self, ids: list[str] | None = None) -> str:
        chosen = self.items if not ids else [self.require(i) for i in ids if i in self._by_id]
        lines = []
        for item in chosen:
            tags = ",".join(item.tags)
            lines.append(
                f"- {item.id} | {item.name} | {item.price_label} | {item.category} | {tags} | {item.blurb}"
            )
        return "\n".join(lines)


def load_catalog(path: Path | None = None) -> Catalog:
    catalog_path = path or get_settings().catalog_path
    raw = json.loads(catalog_path.read_text(encoding="utf-8"))
    items = [CatalogItem.model_validate(row) for row in raw["items"]]
    shop = raw.get("shop", {}).get("name", "Orvalho Atelier")
    return Catalog(items, shop_name=shop)


@lru_cache(maxsize=1)
def default_catalog() -> Catalog:
    return load_catalog(ROOT / "fixtures" / "catalog.json")
