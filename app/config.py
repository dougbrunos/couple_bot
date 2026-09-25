import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///data/app.db").strip()
    TIMEZONE: str = os.getenv("TIMEZONE", "America/Sao_Paulo").strip()

    @classmethod
    def validate(cls) -> None:
        if not cls.TELEGRAM_BOT_TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN is not configured in .env file.")

        if cls.DATABASE_URL.startswith("sqlite:///"):
            db_path = cls.DATABASE_URL.replace("sqlite:///", "")
            if not os.path.isabs(db_path):
                full_db_path = BASE_DIR / db_path
                full_db_path.parent.mkdir(parents=True, exist_ok=True)


config = Config()
