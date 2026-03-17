from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.handlers.utils import sync_user_profile
from app.bot.keyboards.reply import MENU_HISTORY, get_main_keyboard
from app.core.constants import HISTORY_LIMIT
from app.core.texts import (
    HISTORY_EMPTY_TEXT,
    build_history_header,
    get_query_type_label,
    shorten_value,
)
from app.db.repo import HistoryRepo

router = Router()


@router.message(F.text == MENU_HISTORY)
async def show_history(
    message: Message,
    state: FSMContext,
    history_repo: HistoryRepo,
) -> None:
    await state.clear()
    user_id = sync_user_profile(history_repo, message.from_user)
    if user_id is None:
        await message.answer(HISTORY_EMPTY_TEXT, reply_markup=get_main_keyboard())
        return

    items = history_repo.get_last_searches_for_user(
        telegram_user_id=user_id,
        limit=HISTORY_LIMIT,
    )
    if not items:
        await message.answer(HISTORY_EMPTY_TEXT, reply_markup=get_main_keyboard())
        return

    lines = [build_history_header()]
    for item in items:
        lines.append(
            f"• {item.created_at:%d.%m %H:%M} | "
            f"{get_query_type_label(item.search_type)} | "
            f"{shorten_value(item.normalized_query, 26)} | "
            f"{shorten_value(item.result_status, 18)}"
        )
        lines.append(shorten_value(item.short_result_preview, 84))

    await message.answer(
        "\n".join(lines),
        reply_markup=get_main_keyboard(),
        disable_web_page_preview=True,
    )
