from __future__ import annotations

from dataclasses import dataclass


NUTRIENT_FIELDS = (
    "kcal",
    "protein_g",
    "fat_g",
    "carbs_g",
    "fiber_g",
    "sugars_g",
    "saturated_fat_g",
    "sodium_mg",
)


@dataclass(frozen=True)
class Nutrients:
    kcal: float = 0
    protein_g: float = 0
    fat_g: float = 0
    carbs_g: float = 0
    fiber_g: float = 0
    sugars_g: float = 0
    saturated_fat_g: float = 0
    sodium_mg: float = 0

    @classmethod
    def from_row(cls, row: object) -> "Nutrients":
        return cls(**{field: float(row[field] or 0) for field in NUTRIENT_FIELDS})

    def scale(self, grams: float) -> "Nutrients":
        factor = grams / 100
        return Nutrients(**{field: getattr(self, field) * factor for field in NUTRIENT_FIELDS})

    def per_100_from_total(self, total_grams: float) -> "Nutrients":
        if total_grams <= 0:
            return Nutrients()
        factor = 100 / total_grams
        return Nutrients(**{field: getattr(self, field) * factor for field in NUTRIENT_FIELDS})

    def add(self, other: "Nutrients") -> "Nutrients":
        return Nutrients(**{field: getattr(self, field) + getattr(other, field) for field in NUTRIENT_FIELDS})


def fmt_grams(value: float) -> str:
    if abs(value - round(value)) < 0.05:
        return str(int(round(value)))
    return f"{value:.1f}"


def salt_g_from_sodium_mg(sodium_mg: float) -> float:
    return sodium_mg * 2.5 / 1000


def format_nutrients(nutrients: Nutrients, *, prefix: str = "") -> str:
    salt_g = salt_g_from_sodium_mg(nutrients.sodium_mg)
    return "\n".join(
        (
            f"{prefix}{fmt_grams(nutrients.kcal)} ккал",
            f"{prefix}Б: {fmt_grams(nutrients.protein_g)} г",
            f"{prefix}Ж: {fmt_grams(nutrients.fat_g)} г",
            f"{prefix}В: {fmt_grams(nutrients.carbs_g)} г",
            f"{prefix}Клітковина: {fmt_grams(nutrients.fiber_g)} г",
            f"{prefix}Цукри: {fmt_grams(nutrients.sugars_g)} г",
            f"{prefix}Насичені жири: {fmt_grams(nutrients.saturated_fat_g)} г",
            f"{prefix}Сіль: {salt_g:.2f} г",
        )
    )
