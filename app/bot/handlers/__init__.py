from aiogram import Router

from app.bot.handlers.analysis import router as analysis_router
from app.bot.handlers.common import router as common_router
from app.bot.handlers.history import router as history_router
from app.bot.handlers.settings import router as settings_router


def get_routers() -> tuple[Router, ...]:
    return (
        common_router,
        history_router,
        settings_router,
        analysis_router,
    )
