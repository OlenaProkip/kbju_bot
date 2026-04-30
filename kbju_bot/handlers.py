from __future__ import annotations

import re

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from .db import Database
from .nutrition import NUTRIENT_FIELDS, Nutrients, fmt_grams, format_nutrients
from .parser import parse_food_items, parse_key_value_chunks


def build_router(db: Database) -> Router:
    router = Router()

    @router.message(Command("start"))
    async def start(message: Message) -> None:
        db.ensure_user(message.from_user.id)
        await message.answer(
            "Привіт. Я бот для КБЖВ, клітковини, цукрів, насичених жирів і солі.\n\n"
            "Спробуй:\n"
            "/add вівсянка 80г, банан 120г\n"
            "/today\n"
            "/goals\n\n"
            "Додати продукт з етикетки:\n"
            "/food фета | ккал=264 | б=14 | ж=21 | в=4 | клітковина=0 | цукри=4 | насичені=15 | сіль=2.8\n\n"
            "Рецепти:\n"
            "/template запіканка | сир 5%, яйце, манка, йогурт, цукор\n"
            "/cook запіканка | сир 5%=580г, яйце=100г, манка=47г, йогурт=170г, цукор=25г | gross=1420г | dish=форма"
        )

    @router.message(Command("help"))
    async def help_command(message: Message) -> None:
        await message.answer(HELP_TEXT)

    @router.message(Command("foods"))
    async def foods(message: Message) -> None:
        db.ensure_user(message.from_user.id)
        await message.answer("Продукти в базі:\n" + "\n".join(f"- {name}" for name in db.list_foods()))

    @router.message(Command("food"))
    async def food(message: Message) -> None:
        db.ensure_user(message.from_user.id)
        payload = command_payload(message.text)
        if not payload or "|" not in payload:
            await message.answer(
                "Формат на 100 г:\n"
                "/food фета | ккал=264 | б=14 | ж=21 | в=4 | клітковина=0 | цукри=4 | насичені=15 | сіль=2.8"
            )
            return
        try:
            name, nutrients, aliases = parse_food_definition(payload)
        except ValueError as exc:
            await message.answer(str(exc))
            return
        db.upsert_food(name, nutrients, aliases)
        await message.answer(f"Зберегла продукт: {name}\n\nНа 100 г:\n{format_nutrients(nutrients)}")

    @router.message(Command("add"))
    async def add(message: Message) -> None:
        db.ensure_user(message.from_user.id)
        text = command_payload(message.text)
        if not text:
            await message.answer("Напиши так: /add вівсянка 80г, банан 120г")
            return

        try:
            parsed_items = parse_food_items(text)
            total = Nutrients()
            lines = []
            for item in parsed_items:
                name, grams, nutrients = resolve_item(db, message.from_user.id, item.name, item.amount, item.unit)
                total = total.add(nutrients)
                db.add_meal(message.from_user.id, name, grams, nutrients)
                lines.append(f"- {name}: {fmt_grams(grams)} г")
        except ValueError as exc:
            await message.answer(str(exc))
            return

        today = db.today_totals(message.from_user.id)
        await message.answer(
            "Додано:\n"
            + "\n".join(lines)
            + "\n\nРазом у цьому додаванні:\n"
            + format_nutrients(total)
            + "\n\nСьогодні:\n"
            + format_nutrients(today)
            + "\n\n"
            + goals_hint(db, message.from_user.id, today)
        )

    @router.message(Command("today"))
    async def today(message: Message) -> None:
        db.ensure_user(message.from_user.id)
        entries = db.today_entries(message.from_user.id)
        total = db.today_totals(message.from_user.id)
        if entries:
            entry_text = "\n".join(
                f"#{row['id']} {row['name']} {fmt_grams(row['grams'])} г, {fmt_grams(row['kcal'])} ккал"
                for row in entries
            )
        else:
            entry_text = "Сьогодні ще нічого не додано."
        await message.answer(
            entry_text
            + "\n\nПідсумок:\n"
            + format_nutrients(total)
            + "\n\n"
            + goals_hint(db, message.from_user.id, total)
        )

    @router.message(Command("delete"))
    async def delete(message: Message) -> None:
        db.ensure_user(message.from_user.id)
        payload = command_payload(message.text)
        if not payload or not payload.isdigit():
            await message.answer("Напиши ID запису: /delete 12. ID видно в /today.")
            return
        deleted = db.delete_meal(message.from_user.id, int(payload))
        await message.answer("Видалила запис." if deleted else "Не знайшла такий запис за сьогодні.")

    @router.message(Command("goals"))
    async def goals(message: Message) -> None:
        db.ensure_user(message.from_user.id)
        await message.answer(format_goals(db.goals(message.from_user.id)))

    @router.message(Command("setgoal"))
    async def set_goal(message: Message) -> None:
        db.ensure_user(message.from_user.id)
        payload = command_payload(message.text)
        match = re.match(r"(.+?)\s+(\d+(?:[.,]\d+)?)$", payload)
        if not match:
            await message.answer("Формат: /setgoal ккал 1900 або /setgoal клітковина 30")
            return
        key, value = match.groups()
        ok = db.set_goal(message.from_user.id, key, float(value.replace(",", ".")))
        await message.answer("Ціль оновлена.\n\n" + format_goals(db.goals(message.from_user.id)) if ok else "Не знаю таку ціль. Напиши /goals.")

    @router.message(Command("dish"))
    async def dish(message: Message) -> None:
        db.ensure_user(message.from_user.id)
        payload = command_payload(message.text)
        match = re.match(r"(.+?)\s+(\d+(?:[.,]\d+)?)\s*г?$", payload, re.I)
        if not match:
            await message.answer("Формат: /dish форма скляна 520г")
            return
        name, weight = match.groups()
        db.upsert_dish(message.from_user.id, name, float(weight.replace(",", ".")))
        await message.answer(f"Зберегла посуд: {name.strip()} — {weight} г")

    @router.message(Command("dishes"))
    async def dishes(message: Message) -> None:
        db.ensure_user(message.from_user.id)
        rows = db.dishes(message.from_user.id)
        if not rows:
            await message.answer("Посуд ще не збережений. Додай так: /dish форма скляна 520г")
            return
        await message.answer("Твій посуд:\n" + "\n".join(f"- {row['name']}: {fmt_grams(row['weight_g'])} г" for row in rows))

    @router.message(Command("template"))
    async def template(message: Message) -> None:
        db.ensure_user(message.from_user.id)
        payload = command_payload(message.text)
        if "|" not in payload:
            await message.answer("Формат: /template запіканка | сир 5%, яйце, манка, йогурт, цукор")
            return
        name, raw_items = [part.strip() for part in payload.split("|", 1)]
        food_ids = []
        missing = []
        for raw_name in re.split(r"[,;\n]+", raw_items):
            food_name = raw_name.strip()
            if not food_name:
                continue
            food = db.find_food(food_name)
            if not food:
                missing.append(food_name)
            else:
                food_ids.append((food["id"], food["name"]))
        if missing:
            await message.answer("Не знайшла продукти: " + ", ".join(missing) + "\nПодивись /foods.")
            return
        try:
            db.create_template(message.from_user.id, name, food_ids)
        except Exception:
            await message.answer("Такий шаблон уже є. Можемо потім додати редагування, а поки створи іншу назву.")
            return
        await message.answer(f"Створила шаблон: {name.strip()}\nІнгредієнтів: {len(food_ids)}")

    @router.message(Command("templates"))
    async def templates(message: Message) -> None:
        db.ensure_user(message.from_user.id)
        rows = db.list_templates(message.from_user.id)
        if not rows:
            await message.answer("Шаблонів ще нема. Створи так: /template запіканка | сир 5%, яйце, манка")
            return
        await message.answer("Шаблони:\n" + "\n".join(f"- {row['name']}" for row in rows))

    @router.message(Command("cook"))
    async def cook(message: Message) -> None:
        db.ensure_user(message.from_user.id)
        payload = command_payload(message.text)
        if "|" not in payload:
            await message.answer(
                "Формат:\n"
                "/cook запіканка | сир 5%=580г, яйце=100г | gross=1420г | dish=форма"
            )
            return
        try:
            reply = cook_recipe(db, message.from_user.id, payload)
        except ValueError as exc:
            await message.answer(str(exc))
            return
        await message.answer(reply)

    @router.message(Command("batches"))
    async def batches(message: Message) -> None:
        db.ensure_user(message.from_user.id)
        rows = db.active_batches(message.from_user.id)
        if not rows:
            await message.answer("Активних партій рецепту нема.")
            return
        await message.answer(
            "Активні партії:\n"
            + "\n\n".join(
                f"{row['name']} — {fmt_grams(row['edible_weight_g'])} г готової страви\n"
                + format_nutrients(Nutrients.from_row(row), prefix="  ")
                for row in rows
            )
        )

    @router.message(Command("finish"))
    async def finish(message: Message) -> None:
        db.ensure_user(message.from_user.id)
        name = command_payload(message.text)
        if not name:
            await message.answer("Формат: /finish запіканка")
            return
        ok = db.finish_batch(message.from_user.id, name)
        await message.answer("Партію архівовано." if ok else "Не знайшла активну партію з такою назвою.")

    @router.message()
    async def fallback_add(message: Message) -> None:
        db.ensure_user(message.from_user.id)
        if not message.text:
            return
        try:
            parsed_items = parse_food_items(message.text)
        except ValueError:
            await message.answer("Не зрозуміла. Для прикладів напиши /help.")
            return

        total = Nutrients()
        lines = []
        try:
            for item in parsed_items:
                name, grams, nutrients = resolve_item(db, message.from_user.id, item.name, item.amount, item.unit)
                total = total.add(nutrients)
                db.add_meal(message.from_user.id, name, grams, nutrients)
                lines.append(f"- {name}: {fmt_grams(grams)} г")
        except ValueError as exc:
            await message.answer(str(exc))
            return
        await message.answer("Додано:\n" + "\n".join(lines) + "\n\n" + format_nutrients(total))

    return router


HELP_TEXT = """
Основні команди:
/add вівсянка 80г, банан 120г
/today
/delete 12
/foods

Додати продукт з етикетки на 100 г:
/food фета | ккал=264 | б=14 | ж=21 | в=4 | клітковина=0 | цукри=4 | насичені=15 | сіль=2.8

Цілі:
/goals
/setgoal ккал 1900
/setgoal білки 130
/setgoal клітковина 30
/setgoal цукри 50
/setgoal насичені 20
/setgoal сіль 5

Посуд:
/dish форма скляна 520г
/dishes

Рецепти:
/template запіканка | сир 5%, яйце, манка, йогурт, цукор
/cook запіканка | сир 5%=580г, яйце=100г, манка=47г, йогурт=170г, цукор=25г | gross=1420г | dish=форма скляна
/batches
/finish запіканка
""".strip()


def command_payload(text: str | None) -> str:
    if not text:
        return ""
    parts = text.split(maxsplit=1)
    return parts[1].strip() if len(parts) > 1 else ""


def amount_to_grams(food_row, amount: float, unit: str) -> float:
    if unit not in {"г", "гр", "g", "gram", "grams"}:
        raise ValueError("Рахуємо тільки точну вагу в грамах.")
    return amount


def resolve_item(db: Database, user_id: int, item_name: str, amount: float, unit: str) -> tuple[str, float, Nutrients]:
    batch = db.active_batch_by_name(user_id, item_name)
    if batch:
        grams = amount
        nutrients = Nutrients.from_row(batch).scale(grams)
        return batch["name"], grams, nutrients

    food = db.find_food(item_name)
    if not food:
        raise ValueError(f"Не знайшла продукт: {item_name}. Подивись /foods.")
    grams = amount_to_grams(food, amount, unit)
    nutrients = Nutrients.from_row(food).scale(grams)
    return food["name"], grams, nutrients


def format_goals(row) -> str:
    return "\n".join(
        (
            "Твої цілі:",
            f"Ккал: {fmt_goal(row['kcal'])}",
            f"Білки min: {fmt_goal(row['protein_min_g'], 'г')}",
            f"Жири: {fmt_goal(row['fat_min_g'], 'г')} - {fmt_goal(row['fat_max_g'], 'г')}",
            f"Вуглеводи: {fmt_goal(row['carbs_min_g'], 'г')} - {fmt_goal(row['carbs_max_g'], 'г')}",
            f"Клітковина min: {fmt_goal(row['fiber_min_g'], 'г')}",
            f"Цукри max: {fmt_goal(row['sugars_max_g'], 'г')}",
            f"Насичені жири max: {fmt_goal(row['saturated_fat_max_g'], 'г')}",
            f"Сіль max: {fmt_goal(row['salt_max_g'], 'г')}",
        )
    )


def fmt_goal(value: float | None, unit: str = "") -> str:
    if value is None:
        return "не задано"
    return f"{fmt_grams(float(value))} {unit}".strip()


def goals_hint(db: Database, user_id: int, total: Nutrients) -> str:
    row = db.goals(user_id)
    hints = []
    if row["kcal"]:
        hints.append(f"Ккал: {fmt_grams(total.kcal)} / {fmt_grams(row['kcal'])}")
    if row["protein_min_g"]:
        hints.append(f"Білки: {fmt_grams(total.protein_g)} / {fmt_grams(row['protein_min_g'])} г")
    if row["fiber_min_g"]:
        hints.append(f"Клітковина: {fmt_grams(total.fiber_g)} / {fmt_grams(row['fiber_min_g'])} г")
    if row["salt_max_g"]:
        from .nutrition import salt_g_from_sodium_mg

        hints.append(f"Сіль: {salt_g_from_sodium_mg(total.sodium_mg):.2f} / {fmt_grams(row['salt_max_g'])} г")
    return "\n".join(hints) if hints else "Цілі ще не задані. Напиши /goals."


def parse_food_definition(payload: str) -> tuple[str, Nutrients, list[str]]:
    chunks = [chunk.strip() for chunk in payload.split("|") if chunk.strip()]
    if len(chunks) < 2:
        raise ValueError("Дай назву і нутрієнти на 100 г. Приклад є в /help.")
    name = chunks[0]
    values = parse_key_value_chunks("|".join(chunks[1:]))
    missing = [label for label in ("ккал", "б", "ж", "в") if label not in values]
    if missing:
        raise ValueError("Не бачу обов'язкові поля: " + ", ".join(missing))

    salt_g = parse_float(values.get("сіль", "0"))
    nutrients = Nutrients(
        kcal=parse_float(values["ккал"]),
        protein_g=parse_float(values["б"]),
        fat_g=parse_float(values["ж"]),
        carbs_g=parse_float(values["в"]),
        fiber_g=parse_float(values.get("клітковина", "0")),
        sugars_g=parse_float(values.get("цукри", "0")),
        saturated_fat_g=parse_float(values.get("насичені", "0")),
        sodium_mg=salt_g * 1000 / 2.5,
    )
    aliases = []
    if values.get("aliases"):
        aliases.extend(alias.strip() for alias in values["aliases"].split(","))
    if values.get("аліаси"):
        aliases.extend(alias.strip() for alias in values["аліаси"].split(","))
    return name, nutrients, aliases


def parse_float(value: str) -> float:
    cleaned = value.strip().lower().replace(",", ".")
    cleaned = re.sub(r"\s*(ккал|г|гр|g|мг|mg)\s*$", "", cleaned)
    try:
        return float(cleaned)
    except ValueError as exc:
        raise ValueError(f"Не можу прочитати число: {value}") from exc


def cook_recipe(db: Database, user_id: int, payload: str) -> str:
    chunks = [chunk.strip() for chunk in payload.split("|") if chunk.strip()]
    name = chunks[0]
    template = db.template(user_id, name)
    if not template:
        raise ValueError("Не знайшла шаблон. Спочатку створи його через /template.")

    values = parse_key_value_chunks("|".join(chunks[1:]))
    gross_text = values.get("gross") or values.get("готова") or values.get("вага")
    if not gross_text:
        raise ValueError("Не бачу gross=... Наприклад: gross=1420г")
    gross_g = parse_single_amount(gross_text)

    dish_weight = 0.0
    dish_name = values.get("dish") or values.get("посуд")
    if dish_name:
        dish = db.dish(user_id, dish_name)
        if not dish:
            raise ValueError(f"Не знаю посуд {dish_name}. Додай його: /dish {dish_name} 520г")
        dish_weight = float(dish["weight_g"])

    edible_weight = gross_g - dish_weight
    if edible_weight <= 0:
        raise ValueError("Готова їстівна вага вийшла <= 0. Перевір gross і посуд.")

    template_items = db.template_items(template["id"])
    total = Nutrients()
    batch_items = []
    missing = []
    for item in template_items:
        item_value = values.get(item["label"]) or values.get(item["food_name"])
        if not item_value:
            missing.append(item["label"])
            continue
        amount, unit = parse_amount_and_unit(item_value)
        grams = amount_to_grams(item, amount, unit)
        total = total.add(Nutrients.from_row(item).scale(grams))
        batch_items.append((item["food_id"], grams))
    if missing:
        raise ValueError("Не бачу вагу для: " + ", ".join(missing))

    db.create_batch(user_id, template["id"], name, edible_weight, total, batch_items)
    per_100 = total.per_100_from_total(edible_weight)
    return (
        f"Партію створено: {name}\n"
        f"Готова їстівна вага: {fmt_grams(edible_weight)} г"
        + (f" ({fmt_grams(gross_g)} г мінус {fmt_grams(dish_weight)} г посуд)" if dish_weight else "")
        + "\n\nНа 100 г:\n"
        + format_nutrients(per_100)
    )


def parse_single_amount(text: str) -> float:
    amount, _unit = parse_amount_and_unit(text)
    return amount


def parse_amount_and_unit(text: str) -> tuple[float, str]:
    match = re.match(r"\s*(\d+(?:[.,]\d+)?)\s*(г|гр|g|gram|grams)\.?\s*$", text, re.I)
    if not match:
        raise ValueError(f"Не розумію вагу: {text}")
    amount, unit = match.groups()
    return float(amount.replace(",", ".")), unit.lower()
