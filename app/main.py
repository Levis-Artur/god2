import asyncio
import logging

from aiogram import Bot, Dispatcher

from app.bot.handlers import get_routers
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.repo import HistoryRepo
from app.services.analyzer import TelegramAnalyzer
from app.services.collector import PublicTelegramCollector
from app.services.extractor import TextArtifactExtractor
from app.services.formatter import ResultFormatter
from app.services.normalizer import InputNormalizer
from app.services.telegram_client import TelegramClientService


async def main() -> None:
    settings = get_settings()
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN не задано. Скопіюйте .env.example у .env і вкажіть токен бота.")

    setup_logging(settings.log_level)

    history_repo = HistoryRepo(settings.database_url)
    history_repo.init_db()

    telegram_client = TelegramClientService(
        api_id=settings.tg_api_id,
        api_hash=settings.tg_api_hash,
        session_name=settings.tg_session_name,
    )
    await telegram_client.start()

    analyzer = TelegramAnalyzer(
        normalizer=InputNormalizer(),
        collector=PublicTelegramCollector(
            telegram_client=telegram_client,
            public_phone_sources=settings.tg_public_phone_sources,
        ),
        extractor=TextArtifactExtractor(),
    )
    formatter = ResultFormatter()

    bot = Bot(token=settings.bot_token)
    dispatcher = Dispatcher()

    for router in get_routers():
        dispatcher.include_router(router)

    logging.getLogger(__name__).info("Starting polling")

    try:
        await dispatcher.start_polling(
            bot,
            analyzer=analyzer,
            formatter=formatter,
            history_repo=history_repo,
        )
    finally:
        await telegram_client.stop()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
