from aiogram.types import User

from app.core.constants import DEFAULT_DEPTH
from app.db.repo import HistoryRepo


def sync_user_profile(history_repo: HistoryRepo, telegram_user: User | None) -> int | None:
    """Ensure the Telegram user exists in SQLite before further work."""

    if telegram_user is None:
        return None

    history_repo.create_or_get_user(
        telegram_user_id=telegram_user.id,
        username=telegram_user.username,
        first_name=telegram_user.first_name,
    )
    return telegram_user.id


def get_user_depth(history_repo: HistoryRepo, telegram_user: User | None) -> int:
    """Return per-user depth or the default value when user context is missing."""

    if telegram_user is None:
        return DEFAULT_DEPTH

    return history_repo.get_search_depth(
        telegram_user_id=telegram_user.id,
        username=telegram_user.username,
        first_name=telegram_user.first_name,
    )
