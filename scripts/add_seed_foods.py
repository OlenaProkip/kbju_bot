from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kbju_bot.db import Database


def main() -> None:
    load_dotenv()
    db = Database(os.getenv("DATABASE_PATH", "kbju.sqlite3"))
    db.init()
    print("Seed foods are up to date.")


if __name__ == "__main__":
    main()
