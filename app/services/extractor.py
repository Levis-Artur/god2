import re
from collections.abc import Callable, Iterable
from urllib.parse import urlparse, urlunparse

from pydantic import BaseModel, Field

URL_PATTERN = re.compile(
    r"(?P<value>(?:https?://|www\.|(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,63}/)[^\s<>{}\[\]|\\^`]+)",
    re.IGNORECASE,
)
EMAIL_PATTERN = re.compile(
    r"(?P<value>\b[a-zA-Z0-9._%+\-]+@(?:[a-zA-Z0-9-]+\.)+[A-Za-z]{2,63}\b)"
)
DOMAIN_PATTERN = re.compile(
    r"(?P<value>\b(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}\b)"
)
PHONE_PATTERN = re.compile(
    r"(?P<value>(?<!\w)(?:\+?\d[\d\s().-]{4,}\d|\(\d{2,5}\)[\d\s().-]{3,}\d)(?!\w))"
)
MENTION_PATTERN = re.compile(r"(?P<value>(?<!\w)@[A-Za-z0-9_]{2,32}\b)")
HASHTAG_PATTERN = re.compile(r"(?P<value>(?<!\w)#[\w_]{1,64})", re.UNICODE)
TRAILING_PUNCTUATION = ".,;:!?)]}>\"'"


class ArtifactItem(BaseModel):
    """Single extracted artifact with normalized and readable values."""

    value: str
    original_value: str


class ArtifactExtractionResult(BaseModel):
    """Structured regex-based extraction result for plain text."""

    source_text: str
    urls: list[ArtifactItem] = Field(default_factory=list)
    domains: list[ArtifactItem] = Field(default_factory=list)
    emails: list[ArtifactItem] = Field(default_factory=list)
    phone_numbers: list[ArtifactItem] = Field(default_factory=list)
    mentions: list[ArtifactItem] = Field(default_factory=list)
    hashtags: list[ArtifactItem] = Field(default_factory=list)


class Finding(BaseModel):
    """Compact finding item for the formatter."""

    title: str
    value: str


class TextArtifactExtractor:
    """Extracts explicit textual artifacts from plain text using regex."""

    def extract(self, text: str) -> ArtifactExtractionResult:
        """Extract normalized artifacts from plain text."""
        url_items, url_spans = self._extract_url_items(text)
        email_items, email_spans = self._extract_email_items(text)

        masked_text = self._mask_spans(text, [*url_spans, *email_spans])
        domain_items = self._extract_domain_items(masked_text, url_items, email_items)
        phone_items = self._extract_items(masked_text, PHONE_PATTERN, self._normalize_phone)
        mention_items = self._extract_items(masked_text, MENTION_PATTERN, self._normalize_mention)
        hashtag_items = self._extract_items(masked_text, HASHTAG_PATTERN, self._normalize_hashtag)

        return ArtifactExtractionResult(
            source_text=text,
            urls=url_items,
            domains=domain_items,
            emails=email_items,
            phone_numbers=phone_items,
            mentions=mention_items,
            hashtags=hashtag_items,
        )

    def _extract_url_items(self, text: str) -> tuple[list[ArtifactItem], list[tuple[int, int]]]:
        items: list[ArtifactItem] = []
        spans: list[tuple[int, int]] = []
        seen: dict[str, ArtifactItem] = {}

        for match in URL_PATTERN.finditer(text):
            original_value = self._strip_trailing_punctuation(match.group("value"))
            normalized_value = self._normalize_url(original_value)
            spans.append(match.span())
            if not normalized_value or normalized_value in seen:
                continue

            item = ArtifactItem(value=normalized_value, original_value=original_value)
            seen[normalized_value] = item
            items.append(item)

        return items, spans

    def _extract_email_items(self, text: str) -> tuple[list[ArtifactItem], list[tuple[int, int]]]:
        items: list[ArtifactItem] = []
        spans: list[tuple[int, int]] = []
        seen: dict[str, ArtifactItem] = {}

        for match in EMAIL_PATTERN.finditer(text):
            original_value = match.group("value")
            normalized_value = original_value.lower()
            spans.append(match.span())
            if normalized_value in seen:
                continue

            item = ArtifactItem(value=normalized_value, original_value=original_value)
            seen[normalized_value] = item
            items.append(item)

        return items, spans

    def _extract_domain_items(
        self,
        text: str,
        url_items: Iterable[ArtifactItem],
        email_items: Iterable[ArtifactItem],
    ) -> list[ArtifactItem]:
        items: list[ArtifactItem] = []
        seen: dict[str, ArtifactItem] = {}

        for item in url_items:
            host = self._domain_from_url(item.value)
            if host:
                self._add_item(items, seen, host, host)

        for item in email_items:
            host = item.value.split("@", maxsplit=1)[1]
            self._add_item(items, seen, host, host)

        for match in DOMAIN_PATTERN.finditer(text):
            original_value = match.group("value")
            normalized_value = original_value.lower().rstrip(".")
            self._add_item(items, seen, normalized_value, original_value)

        return items

    def _extract_items(
        self,
        text: str,
        pattern: re.Pattern[str],
        normalizer: Callable[[str], str | None],
    ) -> list[ArtifactItem]:
        items: list[ArtifactItem] = []
        seen: dict[str, ArtifactItem] = {}

        for match in pattern.finditer(text):
            original_value = self._strip_trailing_punctuation(match.group("value"))
            normalized_value = normalizer(original_value)
            if not normalized_value:
                continue
            self._add_item(items, seen, normalized_value, original_value)

        return items

    def _add_item(
        self,
        items: list[ArtifactItem],
        seen: dict[str, ArtifactItem],
        normalized_value: str,
        original_value: str,
    ) -> None:
        if normalized_value in seen:
            return

        item = ArtifactItem(value=normalized_value, original_value=original_value)
        seen[normalized_value] = item
        items.append(item)

    def _normalize_url(self, value: str) -> str | None:
        prepared_value = value if value.lower().startswith(("http://", "https://")) else f"https://{value}"
        parsed = urlparse(prepared_value)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
            return None

        return urlunparse(
            (
                parsed.scheme.lower(),
                parsed.netloc.lower(),
                parsed.path or "",
                "",
                parsed.query or "",
                "",
            )
        )

    def _normalize_phone(self, value: str) -> str | None:
        digits = re.sub(r"\D", "", value)
        if digits.startswith("00") and len(digits) > 2:
            digits = digits[2:]

        if len(digits) < 6 or len(digits) > 15:
            return None

        return digits

    def _normalize_mention(self, value: str) -> str | None:
        return value.lower()

    def _normalize_hashtag(self, value: str) -> str | None:
        return value.lower()

    def _domain_from_url(self, value: str) -> str | None:
        parsed = urlparse(value)
        if not parsed.netloc:
            return None
        return parsed.netloc.lower()

    def _mask_spans(self, text: str, spans: Iterable[tuple[int, int]]) -> str:
        masked = list(text)
        for start, end in spans:
            for index in range(start, end):
                masked[index] = " "
        return "".join(masked)

    def _strip_trailing_punctuation(self, value: str) -> str:
        return value.rstrip(TRAILING_PUNCTUATION)
