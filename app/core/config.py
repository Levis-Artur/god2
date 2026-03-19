import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parents[2]
APP_DIR = BASE_DIR / "app"

load_dotenv(BASE_DIR / ".env")
load_dotenv(APP_DIR / ".env")


def _default_database_url() -> str:
    database_path = (BASE_DIR / "bot.db").as_posix()
    return f"sqlite:///{database_path}"


def _optional_int_env(name: str) -> int | None:
    value = os.getenv(name, "").strip()
    if not value:
        return None
    return int(value)


def parse_public_phone_sources(raw_value: str) -> list[str]:
    """Parse a comma-separated list of public Telegram sources."""

    sources: list[str] = []
    seen: set[str] = set()

    for chunk in raw_value.split(","):
        source = chunk.strip()
        if not source:
            continue

        key = source.lower()
        if key in seen:
            continue

        seen.add(key)
        sources.append(source)

    return sources


class Settings(BaseModel):
    bot_token: str
    database_url: str = _default_database_url()
    log_level: str = "INFO"
    tg_api_id: int | None = None
    tg_api_hash: str = ""
    tg_session_name: str = "robocop_session"
    tg_public_phone_sources: list[str] = Field(default_factory=list)


@lru_cache
def get_settings() -> Settings:
    return Settings(
        bot_token=os.getenv("BOT_TOKEN", ""),
        database_url=os.getenv("DATABASE_URL", _default_database_url()),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        tg_api_id=_optional_int_env("TG_API_ID"),
        tg_api_hash=os.getenv("TG_API_HASH", "").strip(),
        tg_session_name=os.getenv("TG_SESSION_NAME", "robocop_session").strip() or "robocop_session",
        tg_public_phone_sources=parse_public_phone_sources(os.getenv("TG_PUBLIC_PHONE_SOURCES", "")),
    )
