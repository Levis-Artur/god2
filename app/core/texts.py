from app.core.constants import HISTORY_LIMIT

WELCOME_TEXT = (
    "Вітаю.\n"
    "Бот працює лише з відкритими Telegram-даними.\n"
    "Оберіть режим у меню."
)

HELP_TEXT = (
    "Що робить бот:\n"
    "• приймає юзернейм, публічне посилання або номер телефону\n"
    "• аналізує лише відкриті Telegram-джерела\n"
    "• у режимі «Номер» перевіряє тільки публічні текстові згадки у налаштованих відкритих джерелах, а не визначає особу\n"
    "• повертає короткий підсумок у чаті"
)

USERNAME_PROMPT = "Введіть username у форматі @name або name"
LINK_PROMPT = "Надішліть публічне посилання Telegram у форматі https://t.me/..."
PHONE_PROMPT = "Введіть номер телефону для перевірки згадок у відкритих Telegram-джерелах"

FALLBACK_TEXT = "Оберіть дію з меню."
TEXT_ONLY_INPUT_TEXT = "Надішліть текстове значення."
UNKNOWN_USER_TEXT = "Не вдалося визначити користувача."
HISTORY_EMPTY_TEXT = "Історія порожня."
REQUEST_NOT_FOUND_TEXT = "Деталі запиту не знайдено."
SETTINGS_SAVE_ERROR_TEXT = "Не вдалося зберегти налаштування."
INVALID_DEPTH_TEXT = "Недоступне значення глибини."

EMPTY_VALUE_ERROR = "Введіть значення для перевірки."
USERNAME_FLOW_ONLY_ERROR = "Для цього режиму введіть лише username: @name або name."
USERNAME_INVALID_ERROR = "Некоректний username. Введіть @name або name."
LINK_INVALID_ERROR = "Надішліть коректне публічне посилання у форматі https://t.me/..."
LINK_PRIVATE_ERROR = "Працюють лише публічні посилання t.me. Приватні запрошення не підтримуються."
LINK_UNSUPPORTED_ERROR = "Підтримуються лише публічні посилання виду https://t.me/name або https://t.me/name/123."
PHONE_INVALID_ERROR = "Некоректний номер. Введіть номер текстом."
UNSUPPORTED_QUERY_TYPE_ERROR = "Цей тип запиту поки не підтримується."


def get_query_type_label(query_type: str) -> str:
    return {
        "username": "Юзернейм",
        "link": "Посилання",
        "phone": "Номер",
    }.get(query_type, "Запит")


def build_settings_text(depth: int) -> str:
    return f"Налаштування\nПоточна глибина: {depth}"


def build_settings_saved_text(depth: int) -> str:
    return f"Глибину збережено: {depth}"


def build_settings_unchanged_text(depth: int) -> str:
    return f"Глибина вже встановлена: {depth}"


def build_history_header() -> str:
    return f"Останні {HISTORY_LIMIT} запитів:"


def shorten_value(value: str, limit: int = 42) -> str:
    if len(value) <= limit:
        return value
    return f"{value[: limit - 1]}…"


def build_result_details_text(
    query_type: str,
    normalized_query: str,
    depth: int,
    result_status: str | None = None,
    short_preview: str | None = None,
) -> str:
    lines = [
        "Деталі запиту",
        f"Тип: {get_query_type_label(query_type)}",
        f"Запит: {normalized_query}",
        f"Глибина: {depth}",
    ]

    if result_status:
        lines.append(f"Статус: {result_status}")

    if query_type == "phone":
        lines.append("Режим: лише публічні текстові згадки у налаштованих джерелах")

    if short_preview:
        lines.extend(["", f"Коротко: {short_preview}"])

    return "\n".join(lines)
