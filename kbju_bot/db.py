from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

from .nutrition import NUTRIENT_FIELDS, Nutrients
from .parser import normalize_name


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS foods (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  serving_g REAL,
  kcal REAL NOT NULL,
  protein_g REAL NOT NULL,
  fat_g REAL NOT NULL,
  carbs_g REAL NOT NULL,
  fiber_g REAL NOT NULL,
  sugars_g REAL NOT NULL,
  saturated_fat_g REAL NOT NULL,
  sodium_mg REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS food_aliases (
  alias TEXT PRIMARY KEY,
  food_id INTEGER NOT NULL REFERENCES foods(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS goals (
  user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  kcal REAL,
  protein_min_g REAL,
  fat_min_g REAL,
  fat_max_g REAL,
  carbs_min_g REAL,
  carbs_max_g REAL,
  fiber_min_g REAL,
  sugars_max_g REAL,
  saturated_fat_max_g REAL,
  salt_max_g REAL
);

CREATE TABLE IF NOT EXISTS meal_entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  grams REAL NOT NULL,
  kcal REAL NOT NULL,
  protein_g REAL NOT NULL,
  fat_g REAL NOT NULL,
  carbs_g REAL NOT NULL,
  fiber_g REAL NOT NULL,
  sugars_g REAL NOT NULL,
  saturated_fat_g REAL NOT NULL,
  sodium_mg REAL NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dishes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  weight_g REAL NOT NULL,
  UNIQUE(user_id, name)
);

CREATE TABLE IF NOT EXISTS recipe_templates (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(user_id, name)
);

CREATE TABLE IF NOT EXISTS recipe_template_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  template_id INTEGER NOT NULL REFERENCES recipe_templates(id) ON DELETE CASCADE,
  food_id INTEGER NOT NULL REFERENCES foods(id),
  label TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recipe_batches (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  template_id INTEGER REFERENCES recipe_templates(id) ON DELETE SET NULL,
  name TEXT NOT NULL,
  edible_weight_g REAL NOT NULL,
  active INTEGER NOT NULL DEFAULT 1,
  kcal REAL NOT NULL,
  protein_g REAL NOT NULL,
  fat_g REAL NOT NULL,
  carbs_g REAL NOT NULL,
  fiber_g REAL NOT NULL,
  sugars_g REAL NOT NULL,
  saturated_fat_g REAL NOT NULL,
  sodium_mg REAL NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS recipe_batch_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  batch_id INTEGER NOT NULL REFERENCES recipe_batches(id) ON DELETE CASCADE,
  food_id INTEGER NOT NULL REFERENCES foods(id),
  grams REAL NOT NULL
);
"""


SEED_FOODS = [
    ("вівсянка", 0, 389, 16.9, 6.9, 66.3, 10.6, 0.9, 1.2, 2, ["овсянка", "oats"]),
    ("гречка варена", 0, 92, 3.4, 0.6, 19.9, 2.7, 0.9, 0.1, 4, ["гречка", "buckwheat cooked"]),
    ("рис варений", 0, 130, 2.7, 0.3, 28.2, 0.4, 0.1, 0.1, 1, ["рис"]),
    ("куряче філе", 0, 120, 22.5, 2.6, 0, 0, 0, 0.7, 70, ["курка", "філе куряче"]),
    ("яйце", 50, 143, 12.6, 9.5, 0.7, 0, 0.4, 3.1, 142, ["яйця", "egg"]),
    ("сир кисломолочний 5%", 0, 121, 17.2, 5, 1.8, 0, 1.8, 3.2, 41, ["сир 5%", "творог 5%", "творог"]),
    ("йогурт грецький 2%", 0, 73, 9.5, 2, 3.7, 0, 3.7, 1.3, 36, ["йогурт", "грецький йогурт"]),
    ("манка", 0, 360, 12.7, 1.1, 72.8, 3.9, 0.4, 0.2, 1, ["крупа манна"]),
    ("цукор", 0, 387, 0, 0, 100, 0, 100, 0, 1, ["sugar"]),
    ("банан", 0, 89, 1.1, 0.3, 22.8, 2.6, 12.2, 0.1, 1, ["banana"]),
    ("яблуко", 0, 52, 0.3, 0.2, 13.8, 2.4, 10.4, 0, 1, ["apple"]),
    ("огірок", 0, 15, 0.7, 0.1, 3.6, 0.5, 1.7, 0, 2, ["огурец"]),
    ("помідор", 0, 18, 0.9, 0.2, 3.9, 1.2, 2.6, 0, 5, ["томат"]),
    ("авокадо", 0, 160, 2, 14.7, 8.5, 6.7, 0.7, 2.1, 7, ["avocado"]),
    ("оливкова олія", 0, 884, 0, 100, 0, 0, 0, 13.8, 2, ["олія", "масло оливковое"]),
]


class Database:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")

    def init(self) -> None:
        self.conn.executescript(SCHEMA)
        self.seed_foods()
        self.conn.commit()

    def ensure_user(self, user_id: int) -> None:
        self.conn.execute("INSERT OR IGNORE INTO users(id) VALUES (?)", (user_id,))
        self.conn.execute("INSERT OR IGNORE INTO goals(user_id) VALUES (?)", (user_id,))
        self.conn.commit()

    def seed_foods(self) -> None:
        for name, serving_g, *rest in SEED_FOODS:
            aliases = rest.pop()
            nutrients = rest
            self.conn.execute(
                f"""
                INSERT OR IGNORE INTO foods
                (name, serving_g, {", ".join(NUTRIENT_FIELDS)})
                VALUES (?, ?, {", ".join("?" for _ in NUTRIENT_FIELDS)})
                """,
                (name, serving_g or None, *nutrients),
            )
            food_id = self.conn.execute("SELECT id FROM foods WHERE name = ?", (name,)).fetchone()["id"]
            for alias in [name, *aliases]:
                self.conn.execute(
                    "INSERT OR IGNORE INTO food_aliases(alias, food_id) VALUES (?, ?)",
                    (normalize_name(alias), food_id),
                )

    def find_food(self, name: str) -> sqlite3.Row | None:
        normalized = normalize_name(name)
        row = self.conn.execute(
            """
            SELECT f.* FROM food_aliases a
            JOIN foods f ON f.id = a.food_id
            WHERE a.alias = ?
            """,
            (normalized,),
        ).fetchone()
        if row:
            return row
        return self.conn.execute(
            "SELECT * FROM foods WHERE lower(name) LIKE ? ORDER BY length(name) LIMIT 1",
            (f"%{normalized}%",),
        ).fetchone()

    def active_batch_by_name(self, user_id: int, name: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM recipe_batches WHERE user_id = ? AND active = 1 AND lower(name) = ? ORDER BY id DESC LIMIT 1",
            (user_id, normalize_name(name)),
        ).fetchone()

    def add_meal(self, user_id: int, name: str, grams: float, nutrients: Nutrients) -> None:
        self.conn.execute(
            f"""
            INSERT INTO meal_entries
            (user_id, name, grams, {", ".join(NUTRIENT_FIELDS)})
            VALUES (?, ?, ?, {", ".join("?" for _ in NUTRIENT_FIELDS)})
            """,
            (user_id, name, grams, *[getattr(nutrients, field) for field in NUTRIENT_FIELDS]),
        )
        self.conn.commit()

    def today_totals(self, user_id: int) -> Nutrients:
        row = self.conn.execute(
            f"""
            SELECT {", ".join(f"COALESCE(SUM({field}), 0) AS {field}" for field in NUTRIENT_FIELDS)}
            FROM meal_entries
            WHERE user_id = ? AND date(created_at, 'localtime') = date('now', 'localtime')
            """,
            (user_id,),
        ).fetchone()
        return Nutrients.from_row(row)

    def today_entries(self, user_id: int) -> list[sqlite3.Row]:
        return list(
            self.conn.execute(
                """
                SELECT id, name, grams, kcal FROM meal_entries
                WHERE user_id = ? AND date(created_at, 'localtime') = date('now', 'localtime')
                ORDER BY id
                """,
                (user_id,),
            )
        )

    def delete_meal(self, user_id: int, entry_id: int) -> bool:
        cur = self.conn.execute("DELETE FROM meal_entries WHERE user_id = ? AND id = ?", (user_id, entry_id))
        self.conn.commit()
        return cur.rowcount > 0

    def list_foods(self) -> list[str]:
        return [row["name"] for row in self.conn.execute("SELECT name FROM foods ORDER BY name")]

    def set_goal(self, user_id: int, key: str, value: float) -> bool:
        allowed = {
            "kcal": "kcal",
            "ккал": "kcal",
            "калорії": "kcal",
            "білки": "protein_min_g",
            "protein": "protein_min_g",
            "жири_min": "fat_min_g",
            "жири_max": "fat_max_g",
            "вуглеводи_min": "carbs_min_g",
            "вуглеводи_max": "carbs_max_g",
            "клітковина": "fiber_min_g",
            "цукри": "sugars_max_g",
            "насичені": "saturated_fat_max_g",
            "сіль": "salt_max_g",
        }
        column = allowed.get(normalize_name(key))
        if not column:
            return False
        self.conn.execute(f"UPDATE goals SET {column} = ? WHERE user_id = ?", (value, user_id))
        self.conn.commit()
        return True

    def goals(self, user_id: int) -> sqlite3.Row:
        return self.conn.execute("SELECT * FROM goals WHERE user_id = ?", (user_id,)).fetchone()

    def upsert_dish(self, user_id: int, name: str, weight_g: float) -> None:
        self.conn.execute(
            """
            INSERT INTO dishes(user_id, name, weight_g) VALUES (?, ?, ?)
            ON CONFLICT(user_id, name) DO UPDATE SET weight_g = excluded.weight_g
            """,
            (user_id, normalize_name(name), weight_g),
        )
        self.conn.commit()

    def dish(self, user_id: int, name: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM dishes WHERE user_id = ? AND name = ?",
            (user_id, normalize_name(name)),
        ).fetchone()

    def dishes(self, user_id: int) -> list[sqlite3.Row]:
        return list(self.conn.execute("SELECT * FROM dishes WHERE user_id = ? ORDER BY name", (user_id,)))

    def create_template(self, user_id: int, name: str, food_ids: Iterable[tuple[int, str]]) -> int:
        cur = self.conn.execute(
            "INSERT INTO recipe_templates(user_id, name) VALUES (?, ?)",
            (user_id, normalize_name(name)),
        )
        template_id = cur.lastrowid
        self.conn.executemany(
            "INSERT INTO recipe_template_items(template_id, food_id, label) VALUES (?, ?, ?)",
            [(template_id, food_id, label) for food_id, label in food_ids],
        )
        self.conn.commit()
        return int(template_id)

    def template(self, user_id: int, name: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM recipe_templates WHERE user_id = ? AND name = ?",
            (user_id, normalize_name(name)),
        ).fetchone()

    def template_items(self, template_id: int) -> list[sqlite3.Row]:
        return list(
            self.conn.execute(
                """
                SELECT rti.*, f.name AS food_name, f.serving_g, f.kcal, f.protein_g, f.fat_g, f.carbs_g,
                       f.fiber_g, f.sugars_g, f.saturated_fat_g, f.sodium_mg
                FROM recipe_template_items rti
                JOIN foods f ON f.id = rti.food_id
                WHERE rti.template_id = ?
                ORDER BY rti.id
                """,
                (template_id,),
            )
        )

    def list_templates(self, user_id: int) -> list[sqlite3.Row]:
        return list(self.conn.execute("SELECT * FROM recipe_templates WHERE user_id = ? ORDER BY name", (user_id,)))

    def create_batch(
        self,
        user_id: int,
        template_id: int | None,
        name: str,
        edible_weight_g: float,
        total: Nutrients,
        items: Iterable[tuple[int, float]],
    ) -> int:
        per_100 = total.per_100_from_total(edible_weight_g)
        cur = self.conn.execute(
            f"""
            INSERT INTO recipe_batches
            (user_id, template_id, name, edible_weight_g, {", ".join(NUTRIENT_FIELDS)})
            VALUES (?, ?, ?, ?, {", ".join("?" for _ in NUTRIENT_FIELDS)})
            """,
            (user_id, template_id, normalize_name(name), edible_weight_g, *[getattr(per_100, f) for f in NUTRIENT_FIELDS]),
        )
        batch_id = int(cur.lastrowid)
        self.conn.executemany(
            "INSERT INTO recipe_batch_items(batch_id, food_id, grams) VALUES (?, ?, ?)",
            [(batch_id, food_id, grams) for food_id, grams in items],
        )
        self.conn.commit()
        return batch_id

    def finish_batch(self, user_id: int, name: str) -> bool:
        cur = self.conn.execute(
            "UPDATE recipe_batches SET active = 0 WHERE user_id = ? AND name = ? AND active = 1",
            (user_id, normalize_name(name)),
        )
        self.conn.commit()
        return cur.rowcount > 0

    def active_batches(self, user_id: int) -> list[sqlite3.Row]:
        return list(
            self.conn.execute(
                "SELECT * FROM recipe_batches WHERE user_id = ? AND active = 1 ORDER BY created_at DESC",
                (user_id,),
            )
        )
