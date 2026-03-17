from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

MENU_USERNAME = "🔍 Юзернейм"
MENU_LINK = "🔗 Посилання"
MENU_NUMBER = "📱 Номер"
MENU_HISTORY = "🕘 Історія"
MENU_SETTINGS = "⚙️ Налаштування"
MENU_HELP = "ℹ️ Допомога"


def get_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=MENU_USERNAME),
                KeyboardButton(text=MENU_LINK),
            ],
            [
                KeyboardButton(text=MENU_NUMBER),
                KeyboardButton(text=MENU_HISTORY),
            ],
            [
                KeyboardButton(text=MENU_SETTINGS),
                KeyboardButton(text=MENU_HELP),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Оберіть дію",
    )
