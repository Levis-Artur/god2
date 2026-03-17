from aiogram import F, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.handlers.utils import sync_user_profile
from app.bot.keyboards.reply import (
    MENU_HELP,
    MENU_HISTORY,
    MENU_LINK,
    MENU_NUMBER,
    MENU_SETTINGS,
    MENU_USERNAME,
    get_main_keyboard,
)
from app.core.texts import FALLBACK_TEXT, HELP_TEXT, WELCOME_TEXT
from app.db.repo import HistoryRepo

router = Router()
MENU_BUTTONS = {
    MENU_USERNAME,
    MENU_LINK,
    MENU_NUMBER,
    MENU_HISTORY,
    MENU_SETTINGS,
    MENU_HELP,
}


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, history_repo: HistoryRepo) -> None:
    await state.clear()
    sync_user_profile(history_repo, message.from_user)
    await message.answer(WELCOME_TEXT, reply_markup=get_main_keyboard())


@router.message(Command("help"))
@router.message(F.text == MENU_HELP)
async def cmd_help(message: Message, state: FSMContext, history_repo: HistoryRepo) -> None:
    await state.clear()
    sync_user_profile(history_repo, message.from_user)
    await message.answer(HELP_TEXT, reply_markup=get_main_keyboard())


@router.message(StateFilter(None), F.text, ~F.text.in_(MENU_BUTTONS))
async def fallback_message(message: Message) -> None:
    await message.answer(FALLBACK_TEXT, reply_markup=get_main_keyboard())


@router.message(StateFilter(None), ~F.text)
async def fallback_non_text_message(message: Message) -> None:
    await message.answer(FALLBACK_TEXT, reply_markup=get_main_keyboard())
