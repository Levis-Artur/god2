from __future__ import annotations

from datetime import datetime

from app.services.analyzer import AnalysisResult, SourceSummary
from app.services.normalizer import QueryType


class ResultFormatter:
    """Formats short Ukrainian Telegram bot responses."""

    def format(self, result: AnalysisResult) -> str:
        if result.query.query_type == QueryType.PHONE:
            return self._format_phone_result(result)
        if result.error_message:
            return self._format_error_result(result)
        if result.found:
            return self._format_found_result(result)
        return self._format_empty_result(result)

    def format_validation_error(self, message: str) -> str:
        return "\n".join(["Помилка введення", self._clean_text(message)])

    def build_result_status(self, result: AnalysisResult) -> str:
        return self._clean_text(result.status)

    def build_short_preview(self, result: AnalysisResult, limit: int = 140) -> str:
        if result.query.query_type == QueryType.PHONE:
            preview = self._build_phone_preview(result)
        else:
            preview = result.error_message or result.summary or self._build_found_preview(result)
        return self._truncate(self._clean_text(preview), limit)

    def _format_phone_result(self, result: AnalysisResult) -> str:
        lines = [
            f"Об’єкт: {result.query.display_value}",
            "Тип: номер телефону",
            "Режим: пошук публічних згадок",
            "",
            f"Статус: {result.status}",
        ]

        if result.source_count:
            lines.append(f"Перевірено джерел: {result.source_count}")

        if result.error_message:
            lines.extend(["", self._clean_text(result.error_message)])
            return "\n".join(lines)

        if not result.found:
            lines.extend(
                [
                    "",
                    self._clean_text(result.summary or "У налаштованих відкритих Telegram-джерелах згадок не виявлено."),
                ]
            )
            return "\n".join(lines)

        top_sources = self._top_sources(result.sources)
        if top_sources:
            lines.extend(["", "Де знайдено:"])
            lines.extend(f"• {source.title}" for source in top_sources)

        lines.extend(["", "Коротко:"])
        lines.append(f"• проаналізовано {result.message_count} повідомлень")
        lines.append(f"• збігів: {result.mention_count}")

        if result.timeline_start:
            lines.append(f"• перша згадка: {self._format_datetime(result.timeline_start)}")
        if result.timeline_end:
            lines.append(f"• остання згадка: {self._format_datetime(result.timeline_end)}")

        return "\n".join(lines)

    def _format_found_result(self, result: AnalysisResult) -> str:
        lines = [
            f"Об’єкт: {result.query.display_value}",
            f"Тип: {self._type_label(result.query.query_type)}",
            f"Статус: {result.status}",
            "",
            "Коротко:",
            f"• проаналізовано {result.message_count} повідомлень",
            f"• знайдено {result.mention_count} згадок",
            f"• URL: {result.url_count}",
            f"• хештеги: {result.hashtag_count}",
        ]
        return "\n".join(lines)

    def _format_empty_result(self, result: AnalysisResult) -> str:
        lines = [
            f"Об’єкт: {result.query.display_value}",
            f"Тип: {self._type_label(result.query.query_type)}",
            f"Статус: {result.status}",
            "",
            result.summary or "Публічних згадок або артефактів не виявлено.",
        ]
        return "\n".join(lines)

    def _format_error_result(self, result: AnalysisResult) -> str:
        lines = [
            f"Об’єкт: {result.query.display_value}",
            f"Тип: {self._type_label(result.query.query_type)}",
            f"Статус: {result.status}",
            "",
            self._clean_text(result.error_message or result.summary),
        ]
        return "\n".join(lines)

    def _build_phone_preview(self, result: AnalysisResult) -> str:
        if result.error_message:
            return result.error_message
        if result.found:
            return f"Перевірено джерел: {result.source_count}, збігів: {result.mention_count}."
        return result.summary or "У налаштованих відкритих Telegram-джерелах згадок не виявлено."

    def _type_label(self, query_type: QueryType) -> str:
        if query_type == QueryType.USERNAME:
            return "username"
        if query_type == QueryType.LINK:
            return "посилання"
        return "номер телефону"

    def _build_found_preview(self, result: AnalysisResult) -> str:
        return (
            f"Проаналізовано {result.message_count} повідомлень, "
            f"згадок: {result.mention_count}, URL: {result.url_count}, "
            f"хештегів: {result.hashtag_count}."
        )

    def _top_sources(self, sources: list[SourceSummary], limit: int = 3) -> list[SourceSummary]:
        return sources[:limit]

    def _format_datetime(self, value: datetime) -> str:
        return value.strftime("%d.%m.%Y %H:%M")

    def _clean_text(self, value: str) -> str:
        return " ".join(value.replace("\n", " ").split())

    def _truncate(self, value: str, limit: int) -> str:
        if len(value) <= limit:
            return value
        return f"{value[: limit - 1]}…"
