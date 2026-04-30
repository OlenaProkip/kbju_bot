from __future__ import annotations

import re
from dataclasses import dataclass


GRAM_UNITS = {"г", "гр", "g", "gram", "grams"}


@dataclass(frozen=True)
class ParsedItem:
    name: str
    amount: float
    unit: str


def normalize_name(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def parse_food_items(text: str) -> list[ParsedItem]:
    items: list[ParsedItem] = []
    for raw_part in re.split(r"[,;\n]+", text):
        part = raw_part.strip()
        if not part:
            continue
        match = re.search(r"(.+?)\s+(\d+(?:[.,]\d+)?)\s*(г|гр|g|gram|grams)\.?$", part, re.I)
        if not match:
            raise ValueError(f"Не бачу вагу в: {part}")
        name, amount, unit = match.groups()
        items.append(ParsedItem(normalize_name(name), float(amount.replace(",", ".")), unit.lower()))
    return items


def parse_key_value_chunks(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for chunk in re.split(r"[|,;\n]+", text):
        if "=" not in chunk:
            continue
        key, value = chunk.split("=", 1)
        result[normalize_name(key)] = value.strip()
    return result
