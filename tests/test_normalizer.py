import pytest

from app.core.texts import (
    LINK_INVALID_ERROR,
    LINK_PRIVATE_ERROR,
    LINK_UNSUPPORTED_ERROR,
    PHONE_INVALID_ERROR,
    USERNAME_FLOW_ONLY_ERROR,
    USERNAME_INVALID_ERROR,
)
from app.services.normalizer import (
    InputNormalizationError,
    InputNormalizer,
    LinkTargetType,
    QueryType,
)


@pytest.fixture
def normalizer() -> InputNormalizer:
    return InputNormalizer()


@pytest.mark.parametrize(
    ("raw_value", "normalized_value", "display_value"),
    [
        ("@Example", "example", "@example"),
        ("example", "example", "@example"),
        ("Example_Name1", "example_name1", "@example_name1"),
    ],
)
def test_valid_username_inputs(
    normalizer: InputNormalizer,
    raw_value: str,
    normalized_value: str,
    display_value: str,
) -> None:
    result = normalizer.normalize(QueryType.USERNAME, raw_value)

    assert result.query_type == QueryType.USERNAME
    assert result.raw_value == raw_value
    assert result.normalized_value == normalized_value
    assert result.display_value == display_value
    assert result.public_reference == f"https://t.me/{normalized_value}"
    assert result.link_target_type == LinkTargetType.PROFILE
    assert result.target_path == normalized_value


@pytest.mark.parametrize(
    ("raw_value", "expected_error"),
    [
        ("ab", USERNAME_INVALID_ERROR),
        ("1example", USERNAME_INVALID_ERROR),
        ("name!", USERNAME_INVALID_ERROR),
        ("t.me/example", USERNAME_FLOW_ONLY_ERROR),
        ("name/test", USERNAME_FLOW_ONLY_ERROR),
    ],
)
def test_invalid_username_inputs(
    normalizer: InputNormalizer,
    raw_value: str,
    expected_error: str,
) -> None:
    with pytest.raises(InputNormalizationError, match=expected_error):
        normalizer.normalize(QueryType.USERNAME, raw_value)


@pytest.mark.parametrize(
    ("raw_value", "normalized_url", "target_type", "target_path", "message_id"),
    [
        (
            "https://t.me/example",
            "https://t.me/example",
            LinkTargetType.CHANNEL_OR_GROUP,
            "example",
            None,
        ),
        (
            "http://t.me/Example",
            "https://t.me/example",
            LinkTargetType.CHANNEL_OR_GROUP,
            "example",
            None,
        ),
        (
            "t.me/example/123",
            "https://t.me/example/123",
            LinkTargetType.POST,
            "example/123",
            123,
        ),
    ],
)
def test_valid_telegram_links(
    normalizer: InputNormalizer,
    raw_value: str,
    normalized_url: str,
    target_type: LinkTargetType,
    target_path: str,
    message_id: int | None,
) -> None:
    result = normalizer.normalize(QueryType.LINK, raw_value)

    assert result.query_type == QueryType.LINK
    assert result.raw_value == raw_value
    assert result.normalized_url == normalized_url
    assert result.normalized_value == normalized_url
    assert result.display_value == normalized_url
    assert result.link_target_type == target_type
    assert result.target_path == target_path
    assert result.message_id == message_id


@pytest.mark.parametrize(
    ("raw_value", "expected_error"),
    [
        ("https://example.com/test", LINK_INVALID_ERROR),
        ("https://t.me/joinchat/abc123", LINK_PRIVATE_ERROR),
        ("https://t.me/+abc123", LINK_PRIVATE_ERROR),
        ("https://t.me/example/not-a-number", LINK_UNSUPPORTED_ERROR),
        ("https://t.me/", LINK_INVALID_ERROR),
    ],
)
def test_invalid_telegram_links(
    normalizer: InputNormalizer,
    raw_value: str,
    expected_error: str,
) -> None:
    with pytest.raises(InputNormalizationError, match=expected_error):
        normalizer.normalize(QueryType.LINK, raw_value)


@pytest.mark.parametrize(
    ("raw_value", "normalized_digits", "display_value"),
    [
        ("+380 (67) 123-45-67", "380671234567", "+380 67 123 45 67"),
        ("067 123 45 67", "0671234567", "067 123 45 67"),
        ("0049 30 123456", "4930123456", "+4930123456"),
    ],
)
def test_valid_phone_strings(
    normalizer: InputNormalizer,
    raw_value: str,
    normalized_digits: str,
    display_value: str,
) -> None:
    result = normalizer.normalize(QueryType.PHONE, raw_value)

    assert result.query_type == QueryType.PHONE
    assert result.raw_value == raw_value
    assert result.normalized_value == normalized_digits
    assert result.normalized_digits == normalized_digits
    assert result.display_value == display_value


@pytest.mark.parametrize(
    "raw_value",
    [
        "12",
        "+38067abc123",
        "номер телефону",
        "++++",
    ],
)
def test_invalid_phone_strings(
    normalizer: InputNormalizer,
    raw_value: str,
) -> None:
    with pytest.raises(InputNormalizationError, match=PHONE_INVALID_ERROR):
        normalizer.normalize(QueryType.PHONE, raw_value)
