from __future__ import annotations

from app.services.analyzer import AnalysisResult
from app.services.normalizer import QueryType


class ResultFormatter:
    """Formats short Ukrainian Telegram bot responses."""

    def format(self, result: AnalysisResult) -> str:
        if result.preview_only:
            return self._format_preview(result)
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
        if result.preview_only:
            preview = "Пошук публічних згадок ще не підключено."
        else:
            preview = result.error_message or result.summary or self._build_found_preview(result)
        return self._truncate(self._clean_text(preview), limit)

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
            result.summary or "Публічних згадок або артефактів не виявлено",
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

    def _format_preview(self, result: AnalysisResult) -> str:
        lines = [
            f"Об’єкт: {result.query.display_value}",
            f"Тип: {self._type_label(result.query.query_type)}",
            f"Режим: {self._preview_mode_label(result.query.query_type)}",
            "",
        ]

        if result.query.query_type == QueryType.PHONE:
            lines.extend(
                [
                    "Бот перевірятиме лише публічні текстові згадки у відкритих Telegram-джерелах.",
                    "Наразі джерела пошуку не підключені.",
                    "Після активації бот показуватиме лише:",
                    "• де знайдено номер",
                    "• скільки є згадок",
                    "• короткий контекст",
                ]
            )
        else:
            lines.append("Наразі джерела пошуку не підключені.")

        return "\n".join(lines)

    def _type_label(self, query_type: QueryType) -> str:
        if query_type == QueryType.USERNAME:
            return "username"
        if query_type == QueryType.LINK:
            return "посилання"
        return "номер телефону"

    def _preview_mode_label(self, query_type: QueryType) -> str:
        if query_type == QueryType.PHONE:
            return "пошук публічних згадок"
        return "аналіз публічних даних"

    def _build_found_preview(self, result: AnalysisResult) -> str:
        return (
            f"Проаналізовано {result.message_count} повідомлень, "
            f"згадок: {result.mention_count}, URL: {result.url_count}, "
            f"хештегів: {result.hashtag_count}."
        )

    def _clean_text(self, value: str) -> str:
        return " ".join(value.replace("\n", " ").split())

    def _truncate(self, value: str, limit: int) -> str:
        if len(value) <= limit:
            return value
        return f"{value[: limit - 1]}…"
