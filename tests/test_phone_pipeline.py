import asyncio
from dataclasses import dataclass
from datetime import datetime

from app.services.analyzer import TelegramAnalyzer
from app.services.collector import PublicTelegramCollector
from app.services.extractor import TextArtifactExtractor
from app.services.normalizer import InputNormalizer, QueryType
from app.services.telegram_client import TelegramMessageItem


@dataclass
class FakeEntity:
    username: str
    title: str | None = None


class FakeTelegramClient:
    def __init__(self, source_messages: dict[str, list[tuple[str, datetime]]]) -> None:
        self.source_messages = source_messages

    async def resolve_entity(self, target: str):
        prepared = self.prepare_source_target(target)
        if prepared not in self.source_messages:
            return None
        return FakeEntity(username=prepared, title=f"@{prepared}")

    async def fetch_messages(self, entity, limit: int):
        rows = self.source_messages.get(entity.username, [])[:limit]
        return [TelegramMessageItem(text=text, date=published_at) for text, published_at in rows]

    def is_public_entity(self, entity) -> bool:
        return bool(getattr(entity, "username", None))

    def build_entity_title(self, entity) -> str | None:
        return entity.title

    def build_entity_reference(self, entity, fallback: str | None = None) -> str | None:
        return f"https://t.me/{entity.username}"

    def prepare_source_target(self, target: str) -> str:
        value = target.strip()
        value = value.removeprefix("https://").removeprefix("http://")
        value = value.removeprefix("t.me/").removeprefix("www.t.me/")
        value = value.removeprefix("telegram.me/").removeprefix("www.telegram.me/")
        value = value.removeprefix("@")
        return value.split("/", maxsplit=1)[0]


def test_phone_collector_returns_not_configured_without_sources() -> None:
    collector = PublicTelegramCollector(
        telegram_client=FakeTelegramClient(source_messages={}),
        public_phone_sources=[],
    )
    query = InputNormalizer().normalize(QueryType.PHONE, "098 133 50 62")

    payload = asyncio.run(collector.collect_phone_mentions(query, depth=20))

    assert payload.status == "not_configured"
    assert payload.message == "Додайте публічні Telegram-джерела в TG_PUBLIC_PHONE_SOURCES."
    assert payload.items == []
    assert payload.scanned_source_count == 0
    assert payload.scanned_message_count == 0


def test_phone_analyzer_returns_not_found_when_matches_absent() -> None:
    client = FakeTelegramClient(
        source_messages={
            "source_one": [
                ("Оновлення каналу без номера", datetime(2026, 3, 1, 10, 0)),
                ("Ще одне повідомлення без збігів", datetime(2026, 3, 2, 11, 0)),
            ]
        }
    )
    analyzer = TelegramAnalyzer(
        normalizer=InputNormalizer(),
        collector=PublicTelegramCollector(client, public_phone_sources=["@source_one"]),
        extractor=TextArtifactExtractor(),
    )

    result = asyncio.run(analyzer.analyze(QueryType.PHONE, "098 133 50 62", depth=20))

    assert result.found is False
    assert result.status == "збігів не знайдено"
    assert result.source_count == 1
    assert result.message_count == 2
    assert result.mention_count == 0
    assert result.summary == "У налаштованих відкритих Telegram-джерелах згадок не виявлено."


def test_phone_analyzer_finds_mentions_in_public_text_variants() -> None:
    client = FakeTelegramClient(
        source_messages={
            "source_one": [
                ("Контакт: 098 133 50 62 https://example.com #sale", datetime(2026, 3, 1, 9, 30)),
                ("Без номера", datetime(2026, 3, 1, 10, 0)),
            ],
            "source_two": [
                ("Для зв’язку: +380981335062 @shop", datetime(2026, 3, 2, 12, 15)),
                ("Ще згадка: +38 098 133 50 62 #promo", datetime(2026, 3, 3, 14, 45)),
            ],
        }
    )
    analyzer = TelegramAnalyzer(
        normalizer=InputNormalizer(),
        collector=PublicTelegramCollector(
            client,
            public_phone_sources=["@source_one", "https://t.me/source_two"],
        ),
        extractor=TextArtifactExtractor(),
    )

    result = asyncio.run(analyzer.analyze(QueryType.PHONE, "098 133 50 62", depth=20))

    assert result.found is True
    assert result.status == "знайдено 3 згадки"
    assert result.source_count == 2
    assert result.message_count == 4
    assert result.mention_count == 3
    assert result.url_count == 1
    assert result.hashtag_count == 2
    assert [source.title for source in result.sources] == ["@source_one", "@source_two"]
    assert result.timeline_start == datetime(2026, 3, 1, 9, 30)
    assert result.timeline_end == datetime(2026, 3, 3, 14, 45)
