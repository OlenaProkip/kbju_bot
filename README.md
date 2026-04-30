# KBJU Telegram Bot

Telegram bot for tracking calories, protein, fat, carbs, fiber, sugars, saturated fat, and salt.

## What it does

- Adds food entries from messages like `вівсянка 80г, банан 120г`.
- Shows daily totals with `/today`.
- Stores goals with `/setgoal`.
- Stores dish/tare weights with `/dish`.
- Supports recipe templates and cooked batches.

## Setup

1. Create a bot via Telegram `@BotFather`.
2. Copy `.env.example` to `.env`.
3. Put your token into `BOT_TOKEN`.
4. Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

5. Run:

```bash
python -m kbju_bot.main
```

The bot uses polling, so it does not need HTTPS or a server for local testing.

## Commands

```text
/start
/help
/foods
/add вівсянка 80г, банан 120г
/today
/delete 12
```

Goals:

```text
/goals
/setgoal ккал 1900
/setgoal білки 130
/setgoal клітковина 30
/setgoal цукри 50
/setgoal насичені 20
/setgoal сіль 5
```

Dishes:

```text
/dish форма скляна 520г
/dishes
```

Recipes:

```text
/template запіканка | сир 5%, яйце, манка, йогурт, цукор
/cook запіканка | сир 5%=580г, яйце=100г, манка=47г, йогурт=170г, цукор=25г | gross=1420г | dish=форма скляна
/batches
/finish запіканка
```

After cooking a batch, add it like regular food:

```text
/add запіканка 180г
```
