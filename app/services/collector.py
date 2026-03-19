from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, Field

from app.services.normalizer import QueryType, SearchInput
from app.services.telegram_client import TelegramClientService, TelegramClientServiceError, TelegramEntityUnavailableError

PHONE_TEXT_PATTERN = re.compile(
    r"(?P<value>(?<!\w)(?:\+?\d[\d\s().-]{4,}\d|\(\d{2,5}\)[\d\s().-]{3,}\d)(?!\w))"
)


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
    scanned_source_count: int = 0
    scanned_message_count: int = 0


class PublicTelegramCollector:
    """Collects public Telegram messages through a shared Telethon client."""

    def __init__(
        self,
        telegram_client: TelegramClientService,
        public_phone_sources: list[str] | None = None,
    ) -> None:
        self.telegram_client = telegram_client
        self.public_phone_sources = self._deduplicate_sources(public_phone_sources or [])

    async def collect(self, query: SearchInput, depth: int) -> CollectedPayload:
        if query.query_type == QueryType.USERNAME:
            return await self.collect_username_data(query.normalized_value, depth, query)
        if query.query_type == QueryType.LINK:
            target = query.target_path.split("/", maxsplit=1)[0] if query.target_path else query.normalized_value
            return await self.collect_link_data(target, depth, query)
        return await self.collect_phone_mentions(query, depth)

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

    async def collect_phone_mentions(self, query: SearchInput, depth: int) -> CollectedPayload:
        if not self.public_phone_sources:
            return self._empty_payload(
                query=query,
                depth=depth,
                status="not_configured",
                message="Додайте публічні Telegram-джерела в TG_PUBLIC_PHONE_SOURCES.",
            )

        variants = self._build_phone_variants(query.normalized_digits or query.normalized_value)
        matched_items: list[CollectedTextItem] = []
        scanned_source_count = 0
        scanned_message_count = 0

        for source_index, configured_source in enumerate(self.public_phone_sources, start=1):
            try:
                entity = await self.telegram_client.resolve_entity(configured_source)
            except TelegramEntityUnavailableError:
                continue
            except TelegramClientServiceError as exc:
                return self._empty_payload(
                    query=query,
                    depth=depth,
                    status="error",
                    message=str(exc),
                    scanned_source_count=scanned_source_count,
                    scanned_message_count=scanned_message_count,
                )

            if entity is None or not self.telegram_client.is_public_entity(entity):
                continue

            try:
                messages = await self.telegram_client.fetch_messages(entity, limit=depth)
            except TelegramEntityUnavailableError:
                continue
            except TelegramClientServiceError as exc:
                return self._empty_payload(
                    query=query,
                    depth=depth,
                    status="error",
                    message=str(exc),
                    scanned_source_count=scanned_source_count,
                    scanned_message_count=scanned_message_count,
                )

            scanned_source_count += 1
            scanned_message_count += len(messages)

            source_title = self.telegram_client.build_entity_title(entity) or configured_source
            source_url = self.telegram_client.build_entity_reference(entity, configured_source)

            for message_index, item in enumerate(messages, start=1):
                if not self._message_contains_phone(item.text, variants):
                    continue

                matched_items.append(
                    CollectedTextItem(
                        source_id=f"phone:{source_index}:{message_index}",
                        source_type="telegram_public",
                        source_title=source_title,
                        source_url=source_url,
                        text=item.text,
                        published_at=item.date,
                    )
                )

        if scanned_source_count == 0:
            return self._empty_payload(
                query=query,
                depth=depth,
                status="unavailable",
                message="Налаштовані джерела недоступні або не є публічними.",
                scanned_source_count=0,
                scanned_message_count=0,
            )

        return CollectedPayload(
            query=query,
            depth=depth,
            items=matched_items,
            status="ok",
            scanned_source_count=scanned_source_count,
            scanned_message_count=scanned_message_count,
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
            return self._empty_payload(
                query,
                depth,
                "no_messages",
                "Повідомлення не знайдені.",
                scanned_source_count=1,
                scanned_message_count=0,
            )

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
            scanned_source_count=1,
            scanned_message_count=len(messages),
        )

    def _empty_payload(
        self,
        query: SearchInput,
        depth: int,
        status: str,
        message: str,
        scanned_source_count: int = 0,
        scanned_message_count: int = 0,
    ) -> CollectedPayload:
        return CollectedPayload(
            query=query,
            depth=depth,
            status=status,
            message=message,
            scanned_source_count=scanned_source_count,
            scanned_message_count=scanned_message_count,
        )

    def _deduplicate_sources(self, sources: list[str]) -> list[str]:
        unique_sources: list[str] = []
        seen: set[str] = set()

        for source in sources:
            prepared = self.telegram_client.prepare_source_target(source).lower()
            if not prepared or prepared in seen:
                continue

            seen.add(prepared)
            unique_sources.append(source.strip())

        return unique_sources

    def _build_phone_variants(self, digits: str) -> set[str]:
        variants = {digits}

        if len(digits) == 10 and digits.startswith("0"):
            variants.add(f"380{digits[1:]}")

        if len(digits) == 12 and digits.startswith("380"):
            variants.add(f"0{digits[3:]}")

        return variants

    def _message_contains_phone(self, text: str, variants: set[str]) -> bool:
        for match in PHONE_TEXT_PATTERN.finditer(text):
            candidate_digits = self._normalize_phone_digits(match.group("value"))
            if candidate_digits in variants:
                return True

        return False

    def _normalize_phone_digits(self, value: str) -> str:
        digits = re.sub(r"\D", "", value)
        if digits.startswith("00") and len(digits) > 2:
            return digits[2:]
        return digits
