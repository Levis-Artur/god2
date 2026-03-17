import re
from enum import Enum
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from app.core.texts import (
    EMPTY_VALUE_ERROR,
    LINK_INVALID_ERROR,
    LINK_PRIVATE_ERROR,
    LINK_UNSUPPORTED_ERROR,
    PHONE_INVALID_ERROR,
    UNSUPPORTED_QUERY_TYPE_ERROR,
    USERNAME_FLOW_ONLY_ERROR,
    USERNAME_INVALID_ERROR,
)

USERNAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]{4,31}$")
PHONE_ALLOWED_PATTERN = re.compile(r"^[\d\s\-\+\(\)\.]+$")
LINK_HOSTS = {"t.me", "telegram.me", "www.t.me", "www.telegram.me"}
PRIVATE_LINK_SEGMENTS = {"joinchat", "c"}


class QueryType(str, Enum):
    USERNAME = "username"
    LINK = "link"
    PHONE = "phone"


class LinkTargetType(str, Enum):
    PROFILE = "profile"
    CHANNEL_OR_GROUP = "channel_or_group"
    POST = "post"


class SearchInput(BaseModel):
    """Normalized user input ready for the analysis pipeline."""

    query_type: QueryType
    raw_value: str = Field(min_length=1)
    normalized_value: str = Field(min_length=1)
    display_value: str = Field(min_length=1)
    public_reference: str | None = None
    normalized_url: str | None = None
    link_target_type: LinkTargetType | None = None
    target_path: str | None = None
    message_id: int | None = None
    normalized_digits: str | None = None


class InputNormalizationError(ValueError):
    """Raised when user input cannot be normalized."""


class InputNormalizer:
    """Validates and normalizes username, public link, and phone input."""

    def normalize(self, query_type: QueryType, raw_value: str) -> SearchInput:
        value = raw_value.strip()
        if not value:
            raise InputNormalizationError(EMPTY_VALUE_ERROR)

        if query_type == QueryType.USERNAME:
            return self._normalize_username(value)
        if query_type == QueryType.LINK:
            return self._normalize_link(value)
        if query_type == QueryType.PHONE:
            return self._normalize_phone(value)

        raise InputNormalizationError(UNSUPPORTED_QUERY_TYPE_ERROR)

    def _normalize_username(self, value: str) -> SearchInput:
        if "/" in value or "t.me" in value.lower() or "telegram.me" in value.lower():
            raise InputNormalizationError(USERNAME_FLOW_ONLY_ERROR)

        candidate = value.removeprefix("@").strip()
        if not USERNAME_PATTERN.fullmatch(candidate):
            raise InputNormalizationError(USERNAME_INVALID_ERROR)

        canonical = candidate.lower()
        return SearchInput(
            query_type=QueryType.USERNAME,
            raw_value=value,
            normalized_value=canonical,
            display_value=f"@{canonical}",
            public_reference=f"https://t.me/{canonical}",
            link_target_type=LinkTargetType.PROFILE,
            target_path=canonical,
        )

    def _normalize_link(self, value: str) -> SearchInput:
        prepared_value = value if value.startswith(("http://", "https://")) else f"https://{value}"
        parsed = urlparse(prepared_value)

        host = parsed.netloc.lower()
        if host not in LINK_HOSTS:
            raise InputNormalizationError(LINK_INVALID_ERROR)

        path_parts = [part for part in parsed.path.split("/") if part]
        if not path_parts:
            raise InputNormalizationError(LINK_INVALID_ERROR)

        first_part = path_parts[0]
        if first_part in PRIVATE_LINK_SEGMENTS or first_part.startswith("+"):
            raise InputNormalizationError(LINK_PRIVATE_ERROR)

        if len(path_parts) == 1:
            target_name = self._normalize_link_target_name(first_part)
            normalized_url = f"https://t.me/{target_name}"
            return SearchInput(
                query_type=QueryType.LINK,
                raw_value=value,
                normalized_value=normalized_url,
                display_value=normalized_url,
                public_reference=normalized_url,
                normalized_url=normalized_url,
                link_target_type=LinkTargetType.CHANNEL_OR_GROUP,
                target_path=target_name,
            )

        if len(path_parts) == 2 and path_parts[1].isdigit():
            target_name = self._normalize_link_target_name(first_part)
            message_id = int(path_parts[1])
            if message_id <= 0:
                raise InputNormalizationError(LINK_INVALID_ERROR)

            normalized_url = f"https://t.me/{target_name}/{message_id}"
            return SearchInput(
                query_type=QueryType.LINK,
                raw_value=value,
                normalized_value=normalized_url,
                display_value=normalized_url,
                public_reference=normalized_url,
                normalized_url=normalized_url,
                link_target_type=LinkTargetType.POST,
                target_path=f"{target_name}/{message_id}",
                message_id=message_id,
            )

        raise InputNormalizationError(LINK_UNSUPPORTED_ERROR)

    def _normalize_phone(self, value: str) -> SearchInput:
        if not PHONE_ALLOWED_PATTERN.fullmatch(value):
            raise InputNormalizationError(PHONE_INVALID_ERROR)

        digits = re.sub(r"\D", "", value)
        if digits.startswith("00") and len(digits) > 2:
            digits = digits[2:]

        if len(digits) < 6 or len(digits) > 15:
            raise InputNormalizationError(PHONE_INVALID_ERROR)

        return SearchInput(
            query_type=QueryType.PHONE,
            raw_value=value,
            normalized_value=digits,
            display_value=self._format_phone_display(digits),
            normalized_digits=digits,
        )

    def _normalize_link_target_name(self, value: str) -> str:
        if not USERNAME_PATTERN.fullmatch(value):
            raise InputNormalizationError(LINK_INVALID_ERROR)
        return value.lower()

    def _format_phone_display(self, digits: str) -> str:
        if len(digits) == 12 and digits.startswith("380"):
            return f"+{digits[:3]} {digits[3:5]} {digits[5:8]} {digits[8:10]} {digits[10:12]}"

        if len(digits) == 10 and digits.startswith("0"):
            return f"{digits[:3]} {digits[3:6]} {digits[6:8]} {digits[8:10]}"

        if len(digits) >= 10:
            return f"+{digits}"

        return digits
