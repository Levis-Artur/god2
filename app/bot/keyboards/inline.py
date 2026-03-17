from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.core.constants import DEPTH_OPTIONS


def get_settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"Глибина: {depth}",
                    callback_data=f"settings:depth:{depth}",
                )
            ]
            for depth in DEPTH_OPTIONS
        ]
    )


def get_result_keyboard(request_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Деталі",
                    callback_data=f"result:details:{request_id}",
                )
            ]
        ]
    )
