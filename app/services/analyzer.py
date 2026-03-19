from __future__ import annotations

from collections import OrderedDict
from datetime import datetime

from pydantic import BaseModel, Field

from app.services.collector import CollectedPayload, CollectedTextItem, PublicTelegramCollector
from app.services.extractor import ArtifactExtractionResult, ArtifactItem, TextArtifactExtractor
from app.services.normalizer import InputNormalizer, QueryType, SearchInput


class SourceSummary(BaseModel):
    """Compact public-source summary for formatter output."""

    title: str
    url: str | None = None
    source_type: str
    published_at: datetime | None = None


class AnalysisResult(BaseModel):
    """Aggregated analysis result for formatter and persistence."""

    query: SearchInput
    target: str
    target_type: str
    found: bool
    source_count: int = 0
    message_count: int = 0
    mention_count: int = 0
    url_count: int = 0
    hashtag_count: int = 0
    sources: list[SourceSummary] = Field(default_factory=list)
    artifact_result: ArtifactExtractionResult | None = None
    depth: int
    status: str
    summary: str
    error_message: str | None = None
    timeline_start: datetime | None = None
    timeline_end: datetime | None = None


class TelegramAnalyzer:
    """Async analysis pipeline for public Telegram collection."""

    def __init__(
        self,
        normalizer: InputNormalizer,
        collector: PublicTelegramCollector,
        extractor: TextArtifactExtractor,
    ) -> None:
        self.normalizer = normalizer
        self.collector = collector
        self.extractor = extractor

    async def analyze(self, query_type: QueryType, raw_value: str, depth: int) -> AnalysisResult:
        normalized_input = self.normalizer.normalize(query_type=query_type, raw_value=raw_value)
        collected_payload = await self.collector.collect(normalized_input, depth)

        if collected_payload.status != "ok":
            return self._build_error_result(normalized_input, depth, collected_payload)

        extracted_payloads = [self.extractor.extract(item.text) for item in collected_payload.items if item.text.strip()]
        aggregated_artifacts = self._merge_artifact_results(extracted_payloads)
        sources = self._build_source_summaries(collected_payload.items)
        timeline_start, timeline_end = self._build_timeline(collected_payload.items)

        source_count = collected_payload.scanned_source_count or len(sources)
        message_count = collected_payload.scanned_message_count or len(collected_payload.items)
        url_count = len(aggregated_artifacts.urls)
        hashtag_count = len(aggregated_artifacts.hashtags)

        if normalized_input.query_type == QueryType.PHONE:
            mention_count = len(collected_payload.items)
            found = mention_count > 0
            status = self._build_phone_status(mention_count) if found else "збігів не знайдено"
            summary = (
                f"У налаштованих відкритих Telegram-джерелах знайдено {self._format_match_count(mention_count)}."
                if found
                else "У налаштованих відкритих Telegram-джерелах згадок не виявлено."
            )
        else:
            mention_count = len(aggregated_artifacts.mentions)
            found = any([mention_count, url_count, hashtag_count])
            status = "знайдено" if found else "не знайдено"
            summary = "" if found else "Публічних згадок або артефактів не виявлено."

        return AnalysisResult(
            query=normalized_input,
            target=normalized_input.display_value,
            target_type=self._resolve_target_type(normalized_input),
            found=found,
            source_count=source_count,
            message_count=message_count,
            mention_count=mention_count,
            url_count=url_count,
            hashtag_count=hashtag_count,
            sources=sources,
            artifact_result=aggregated_artifacts,
            depth=depth,
            status=status,
            summary=summary,
            timeline_start=timeline_start,
            timeline_end=timeline_end,
        )

    def _build_error_result(
        self,
        query: SearchInput,
        depth: int,
        payload: CollectedPayload,
    ) -> AnalysisResult:
        return AnalysisResult(
            query=query,
            target=query.display_value,
            target_type=self._resolve_target_type(query),
            found=False,
            source_count=payload.scanned_source_count,
            message_count=payload.scanned_message_count,
            depth=depth,
            status=self._map_status(payload.status),
            summary=payload.message or "Не вдалося отримати дані з Telegram.",
            error_message=payload.message,
        )

    def _merge_artifact_results(self, results: list[ArtifactExtractionResult]) -> ArtifactExtractionResult:
        merged = ArtifactExtractionResult(source_text="")
        merged.urls = self._merge_artifact_items(results, "urls")
        merged.domains = self._merge_artifact_items(results, "domains")
        merged.emails = self._merge_artifact_items(results, "emails")
        merged.phone_numbers = self._merge_artifact_items(results, "phone_numbers")
        merged.mentions = self._merge_artifact_items(results, "mentions")
        merged.hashtags = self._merge_artifact_items(results, "hashtags")
        return merged

    def _merge_artifact_items(
        self,
        results: list[ArtifactExtractionResult],
        field_name: str,
    ) -> list[ArtifactItem]:
        merged: OrderedDict[str, ArtifactItem] = OrderedDict()
        for result in results:
            for item in getattr(result, field_name):
                merged.setdefault(item.value, item)
        return list(merged.values())

    def _build_source_summaries(self, items: list[CollectedTextItem]) -> list[SourceSummary]:
        summaries: OrderedDict[str, SourceSummary] = OrderedDict()
        for item in items:
            key = item.source_url or item.source_id
            summaries.setdefault(
                key,
                SourceSummary(
                    title=item.source_title,
                    url=item.source_url,
                    source_type=item.source_type,
                    published_at=item.published_at,
                ),
            )
        return list(summaries.values())

    def _build_timeline(
        self,
        items: list[CollectedTextItem],
    ) -> tuple[datetime | None, datetime | None]:
        dates = [item.published_at for item in items if item.published_at is not None]
        if not dates:
            return None, None
        return min(dates), max(dates)

    def _map_status(self, status: str) -> str:
        return {
            "not_found": "не знайдено",
            "unavailable": "недоступно",
            "no_messages": "без повідомлень",
            "not_configured": "джерела не налаштовані",
            "error": "помилка",
        }.get(status, "не знайдено")

    def _resolve_target_type(self, query: SearchInput) -> str:
        if query.query_type == QueryType.USERNAME:
            return "username"
        if query.query_type == QueryType.PHONE:
            return "номер телефону"
        return "посилання"

    def _build_phone_status(self, mention_count: int) -> str:
        return f"знайдено {self._format_match_count(mention_count)}"

    def _format_match_count(self, count: int) -> str:
        if count % 10 == 1 and count % 100 != 11:
            return f"{count} згадку"
        if count % 10 in {2, 3, 4} and count % 100 not in {12, 13, 14}:
            return f"{count} згадки"
        return f"{count} згадок"
