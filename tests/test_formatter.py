from app.services.analyzer import AnalysisResult
from app.services.formatter import ResultFormatter
from app.services.normalizer import QueryType, SearchInput


def _build_result(query_type: QueryType, display_value: str, **overrides) -> AnalysisResult:
    payload = {
        "query": SearchInput(
            query_type=query_type,
            raw_value=display_value,
            normalized_value=display_value,
            display_value=display_value,
        ),
        "target": display_value,
        "target_type": query_type.value,
        "found": False,
        "depth": 20,
        "status": "не знайдено",
        "summary": "Публічних згадок або артефактів не виявлено",
    }
    payload.update(overrides)
    return AnalysisResult(**payload)


def test_phone_preview_message_is_operator_friendly() -> None:
    formatter = ResultFormatter()
    result = _build_result(
        QueryType.PHONE,
        "098 133 50 62",
        preview_only=True,
        status="джерела не підключені",
        summary="Наразі джерела пошуку не підключені.",
    )

    message = formatter.format(result)

    assert "Об’єкт: 098 133 50 62" in message
    assert "Тип: номер телефону" in message
    assert "Режим: пошук публічних згадок" in message
    assert "Бот перевірятиме лише публічні текстові згадки у відкритих Telegram-джерелах." in message
    assert "Наразі джерела пошуку не підключені." in message
    assert "• де знайдено номер" in message
    assert "• скільки є згадок" in message
    assert "• короткий контекст" in message
    assert "Номер нормалізовано" not in message
    assert "попередній режим" not in message


def test_username_preview_message_is_concise() -> None:
    formatter = ResultFormatter()
    result = _build_result(
        QueryType.USERNAME,
        "@example",
        preview_only=True,
        status="джерела не підключені",
        summary="Наразі джерела пошуку не підключені.",
    )

    message = formatter.format(result)

    assert "Тип: username" in message
    assert "Режим: аналіз публічних даних" in message
    assert "Наразі джерела пошуку не підключені." in message
    assert "Статус:" not in message


def test_found_result_contains_compact_counters() -> None:
    formatter = ResultFormatter()
    result = _build_result(
        QueryType.USERNAME,
        "@example",
        found=True,
        message_count=12,
        mention_count=3,
        url_count=2,
        hashtag_count=1,
        status="знайдено",
        summary="",
    )

    message = formatter.format(result)

    assert "Статус: знайдено" in message
    assert "Коротко:" in message
    assert "• проаналізовано 12 повідомлень" in message
    assert "• знайдено 3 згадок" in message
    assert "• URL: 2" in message
    assert "• хештеги: 1" in message
