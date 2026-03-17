from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.utils import get_user_depth
from app.bot.keyboards.inline import get_result_keyboard
from app.bot.keyboards.reply import MENU_LINK, MENU_NUMBER, MENU_USERNAME, get_main_keyboard
from app.core.texts import (
    LINK_PROMPT,
    PHONE_PROMPT,
    REQUEST_NOT_FOUND_TEXT,
    TEXT_ONLY_INPUT_TEXT,
    UNKNOWN_USER_TEXT,
    USERNAME_PROMPT,
    build_result_details_text,
)
from app.db.repo import HistoryRepo
from app.services.analyzer import TelegramAnalyzer
from app.services.formatter import ResultFormatter
from app.services.normalizer import InputNormalizationError, QueryType

router = Router()


class AnalysisState(StatesGroup):
    waiting_for_username = State()
    waiting_for_link = State()
    waiting_for_phone = State()


@router.message(F.text == MENU_USERNAME)
async def request_username(message: Message, state: FSMContext) -> None:
    await _start_input_flow(message, state, AnalysisState.waiting_for_username, USERNAME_PROMPT)


@router.message(F.text == MENU_LINK)
async def request_link(message: Message, state: FSMContext) -> None:
    await _start_input_flow(message, state, AnalysisState.waiting_for_link, LINK_PROMPT)


@router.message(F.text == MENU_NUMBER)
async def request_phone(message: Message, state: FSMContext) -> None:
    await _start_input_flow(message, state, AnalysisState.waiting_for_phone, PHONE_PROMPT)


@router.message(AnalysisState.waiting_for_username, F.text)
async def handle_username_input(
    message: Message,
    state: FSMContext,
    analyzer: TelegramAnalyzer,
    formatter: ResultFormatter,
    history_repo: HistoryRepo,
) -> None:
    await _handle_analysis(message, state, analyzer, formatter, history_repo, QueryType.USERNAME)


@router.message(AnalysisState.waiting_for_link, F.text)
async def handle_link_input(
    message: Message,
    state: FSMContext,
    analyzer: TelegramAnalyzer,
    formatter: ResultFormatter,
    history_repo: HistoryRepo,
) -> None:
    await _handle_analysis(message, state, analyzer, formatter, history_repo, QueryType.LINK)


@router.message(AnalysisState.waiting_for_phone, F.text)
async def handle_phone_input(
    message: Message,
    state: FSMContext,
    analyzer: TelegramAnalyzer,
    formatter: ResultFormatter,
    history_repo: HistoryRepo,
) -> None:
    await _handle_analysis(message, state, analyzer, formatter, history_repo, QueryType.PHONE)


@router.message(AnalysisState.waiting_for_username, ~F.text)
@router.message(AnalysisState.waiting_for_link, ~F.text)
@router.message(AnalysisState.waiting_for_phone, ~F.text)
async def reject_non_text_input(message: Message) -> None:
    await message.answer(TEXT_ONLY_INPUT_TEXT, reply_markup=get_main_keyboard())


@router.callback_query(F.data.startswith("result:details:"))
async def show_result_details(callback: CallbackQuery, history_repo: HistoryRepo) -> None:
    raw_request_id = (callback.data or "").split(":")[-1]
    if not raw_request_id.isdigit() or callback.from_user is None:
        await callback.answer(REQUEST_NOT_FOUND_TEXT, show_alert=True)
        return

    item = history_repo.get_search_request_for_user(
        request_id=int(raw_request_id),
        telegram_user_id=callback.from_user.id,
    )
    if item is None:
        await callback.answer(REQUEST_NOT_FOUND_TEXT, show_alert=True)
        return

    await callback.answer()
    if callback.message:
        await callback.message.answer(
            build_result_details_text(
                query_type=item.search_type,
                normalized_query=item.normalized_query,
                depth=get_user_depth(history_repo, callback.from_user),
                result_status=item.result_status,
                short_preview=item.short_result_preview,
            )
        )


async def _start_input_flow(
    message: Message,
    state: FSMContext,
    next_state: State,
    prompt: str,
) -> None:
    await state.set_state(next_state)
    await message.answer(prompt, reply_markup=get_main_keyboard())


async def _handle_analysis(
    message: Message,
    state: FSMContext,
    analyzer: TelegramAnalyzer,
    formatter: ResultFormatter,
    history_repo: HistoryRepo,
    query_type: QueryType,
) -> None:
    if message.from_user is None:
        await message.answer(
            formatter.format_validation_error(UNKNOWN_USER_TEXT),
            reply_markup=get_main_keyboard(),
        )
        return

    raw_value = (message.text or "").strip()
    depth = get_user_depth(history_repo, message.from_user)

    try:
        result = await analyzer.analyze(query_type=query_type, raw_value=raw_value, depth=depth)
    except InputNormalizationError as exc:
        await message.answer(
            formatter.format_validation_error(str(exc)),
            reply_markup=get_main_keyboard(),
        )
        return

    saved_request = history_repo.save_search_request(
        telegram_user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        search_type=result.query.query_type.value,
        original_query=result.query.raw_value,
        normalized_query=result.query.display_value,
        result_status=formatter.build_result_status(result),
        short_result_preview=formatter.build_short_preview(result),
    )

    await state.clear()
    await message.answer(
        formatter.format(result),
        reply_markup=get_result_keyboard(saved_request.id),
        disable_web_page_preview=True,
    )
