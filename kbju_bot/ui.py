from __future__ import annotations

from aiogram.types import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


BOT_COMMANDS = [
    BotCommand(command="start", description="Відкрити меню"),
    BotCommand(command="today", description="Підсумок за сьогодні"),
    BotCommand(command="add", description="Додати їжу"),
    BotCommand(command="food", description="Додати продукт з етикетки"),
    BotCommand(command="goals", description="Показати цілі"),
    BotCommand(command="setgoal", description="Змінити ціль"),
    BotCommand(command="dish", description="Зберегти вагу посуду"),
    BotCommand(command="template", description="Створити шаблон рецепту"),
    BotCommand(command="cook", description="Приготувати партію рецепту"),
    BotCommand(command="batches", description="Активні партії рецептів"),
    BotCommand(command="help", description="Приклади команд"),
]


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Сьогодні"), KeyboardButton(text="Цілі")],
            [KeyboardButton(text="Продукти"), KeyboardButton(text="Рецепти")],
            [KeyboardButton(text="Допомога")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Напиши їжу: вівсянка 80г, банан 120г",
    )


def quick_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Підсумок за сьогодні", callback_data="menu:today"),
                InlineKeyboardButton(text="Цілі", callback_data="menu:goals"),
            ],
            [
                InlineKeyboardButton(text="Додати продукт", callback_data="menu:add_food_help"),
                InlineKeyboardButton(text="Рецепти", callback_data="menu:recipes"),
            ],
        ]
    )


def after_add_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Показати сьогодні", callback_data="menu:today")],
            [InlineKeyboardButton(text="Активні рецепти", callback_data="menu:batches")],
        ]
    )


def recipes_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Шаблони", callback_data="menu:templates"),
                InlineKeyboardButton(text="Активні партії", callback_data="menu:batches"),
            ],
            [InlineKeyboardButton(text="Як створити рецепт", callback_data="menu:recipe_help")],
        ]
    )
