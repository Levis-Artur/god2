from datetime import datetime

from app.services.analyzer import AnalysisResult, SourceSummary
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
        "summary": "Публічних згадок або артефактів не виявлено.",
    }
    payload.update(overrides)
    return AnalysisResult(**payload)


def test_phone_not_configured_message_is_clear() -> None:
    formatter = ResultFormatter()
    result = _build_result(
        QueryType.PHONE,
        "098 133 50 62",
        status="джерела не налаштовані",
        summary="Додайте публічні Telegram-джерела в TG_PUBLIC_PHONE_SOURCES.",
        error_message="Додайте публічні Telegram-джерела в TG_PUBLIC_PHONE_SOURCES.",
    )

    message = formatter.format(result)

    assert "Об’єкт: 098 133 50 62" in message
    assert "Тип: номер телефону" in message
    assert "Режим: пошук публічних згадок" in message
    assert "Статус: джерела не налаштовані" in message
    assert "TG_PUBLIC_PHONE_SOURCES" in message
    assert "preview" not in message.lower()


def test_phone_found_message_contains_sources_and_timeline() -> None:
    formatter = ResultFormatter()
    result = _build_result(
        QueryType.PHONE,
        "098 133 50 62",
        found=True,
        status="знайдено 3 згадки",
        source_count=4,
        message_count=60,
        mention_count=3,
        summary="",
        sources=[
            SourceSummary(title="@source_one", source_type="telegram_public"),
            SourceSummary(title="@source_two", source_type="telegram_public"),
            SourceSummary(title="@source_three", source_type="telegram_public"),
            SourceSummary(title="@source_four", source_type="telegram_public"),
        ],
        timeline_start=datetime(2026, 3, 1, 9, 30),
        timeline_end=datetime(2026, 3, 7, 18, 45),
    )

    message = formatter.format(result)

    assert "Статус: знайдено 3 згадки" in message
    assert "Перевірено джерел: 4" in message
    assert "Де знайдено:" in message
    assert "• @source_one" in message
    assert "• @source_two" in message
    assert "• @source_three" in message
    assert "@source_four" not in message
    assert "• проаналізовано 60 повідомлень" in message
    assert "• збігів: 3" in message
    assert "• перша згадка: 01.03.2026 09:30" in message
    assert "• остання згадка: 07.03.2026 18:45" in message


def test_username_found_result_contains_compact_counters() -> None:
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
