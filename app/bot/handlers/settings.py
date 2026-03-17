from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.utils import get_user_depth
from app.bot.keyboards.inline import get_settings_keyboard
from app.bot.keyboards.reply import MENU_SETTINGS
from app.core.constants import DEPTH_OPTIONS
from app.core.texts import (
    INVALID_DEPTH_TEXT,
    SETTINGS_SAVE_ERROR_TEXT,
    build_settings_saved_text,
    build_settings_text,
    build_settings_unchanged_text,
)
from app.db.repo import HistoryRepo

router = Router()


@router.message(F.text == MENU_SETTINGS)
async def show_settings(
    message: Message,
    state: FSMContext,
    history_repo: HistoryRepo,
) -> None:
    await state.clear()
    await message.answer(
        build_settings_text(get_user_depth(history_repo, message.from_user)),
        reply_markup=get_settings_keyboard(),
    )


@router.callback_query(F.data.startswith("settings:depth:"))
async def set_depth(callback: CallbackQuery, history_repo: HistoryRepo) -> None:
    raw_depth = (callback.data or "").split(":")[-1]
    if not raw_depth.isdigit():
        await callback.answer(INVALID_DEPTH_TEXT, show_alert=True)
        return

    depth = int(raw_depth)
    if depth not in DEPTH_OPTIONS:
        await callback.answer(INVALID_DEPTH_TEXT, show_alert=True)
        return

    if callback.from_user is None:
        await callback.answer(SETTINGS_SAVE_ERROR_TEXT, show_alert=True)
        return

    current_depth = get_user_depth(history_repo, callback.from_user)
    if current_depth == depth:
        await callback.answer(build_settings_unchanged_text(depth))
        return

    history_repo.update_search_depth(
        telegram_user_id=callback.from_user.id,
        depth=depth,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
    )
    await callback.answer(build_settings_saved_text(depth))

    if callback.message:
        await callback.message.edit_text(
            build_settings_text(depth),
            reply_markup=get_settings_keyboard(),
        )
