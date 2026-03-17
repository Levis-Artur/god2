from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.services.normalizer import QueryType, SearchInput
from app.services.telegram_client import TelegramClientService, TelegramClientServiceError, TelegramEntityUnavailableError


class CollectedTextItem(BaseModel):
    """Single public text item prepared for downstream extraction."""

    source_id: str
    source_type: str
    source_title: str
    source_url: str | None = None
    text: str
    published_at: datetime | None = None


class CollectedPayload(BaseModel):
    """Collected public items and collector status for the analyzer."""

    query: SearchInput
    depth: int
    items: list[CollectedTextItem] = Field(default_factory=list)
    status: str = "ok"
    message: str | None = None
    title: str | None = None
    source_url: str | None = None
    preview_only: bool = False


class PublicTelegramCollector:
    """Collects public Telegram messages through a shared Telethon client."""

    def __init__(self, telegram_client: TelegramClientService) -> None:
        self.telegram_client = telegram_client

    async def collect(self, query: SearchInput, depth: int) -> CollectedPayload:
        if query.query_type == QueryType.USERNAME:
            return await self.collect_username_data(query.normalized_value, depth, query)
        if query.query_type == QueryType.LINK:
            target = query.target_path.split("/", maxsplit=1)[0] if query.target_path else query.normalized_value
            return await self.collect_link_data(target, depth, query)
        return self.collect_phone_preview(query, depth)

    async def collect_username_data(
        self,
        target: str,
        depth: int,
        query: SearchInput,
    ) -> CollectedPayload:
        return await self._collect_public_entity(
            query=query,
            depth=depth,
            target=target,
            source_url=query.public_reference,
            source_type="username",
        )

    async def collect_link_data(
        self,
        target: str,
        depth: int,
        query: SearchInput,
    ) -> CollectedPayload:
        return await self._collect_public_entity(
            query=query,
            depth=depth,
            target=target,
            source_url=query.normalized_url or query.public_reference,
            source_type="link",
        )

    def collect_phone_preview(self, query: SearchInput, depth: int) -> CollectedPayload:
        return CollectedPayload(
            query=query,
            depth=depth,
            status="not_supported",
            message="Наразі джерела пошуку не підключені.",
            preview_only=True,
        )

    async def _collect_public_entity(
        self,
        query: SearchInput,
        depth: int,
        target: str,
        source_url: str | None,
        source_type: str,
    ) -> CollectedPayload:
        try:
            entity = await self.telegram_client.resolve_entity(target)
        except TelegramEntityUnavailableError as exc:
            return self._empty_payload(query, depth, "unavailable", str(exc))
        except TelegramClientServiceError as exc:
            return self._empty_payload(query, depth, "error", str(exc))

        if entity is None:
            return self._empty_payload(query, depth, "not_found", "Об’єкт не знайдено.")

        if not self.telegram_client.is_public_entity(entity):
            return self._empty_payload(query, depth, "unavailable", "Об’єкт недоступний або не є публічним.")

        try:
            messages = await self.telegram_client.fetch_messages(entity, limit=depth)
        except TelegramEntityUnavailableError as exc:
            return self._empty_payload(query, depth, "unavailable", str(exc))
        except TelegramClientServiceError as exc:
            return self._empty_payload(query, depth, "error", str(exc))

        if not messages:
            return self._empty_payload(query, depth, "no_messages", "Повідомлення не знайдені.")

        title = self.telegram_client.build_entity_title(entity)
        source_title = title or query.display_value
        items = [
            CollectedTextItem(
                source_id=f"{source_type}:{index}",
                source_type="telegram_public",
                source_title=source_title,
                source_url=source_url,
                text=item.text,
                published_at=item.date,
            )
            for index, item in enumerate(messages, start=1)
        ]

        return CollectedPayload(
            query=query,
            depth=depth,
            items=items,
            status="ok",
            title=title,
            source_url=source_url,
        )

    def _empty_payload(
        self,
        query: SearchInput,
        depth: int,
        status: str,
        message: str,
    ) -> CollectedPayload:
        return CollectedPayload(
            query=query,
            depth=depth,
            status=status,
            message=message,
        )
