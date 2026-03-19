from app.core.config import parse_public_phone_sources


def test_parse_public_phone_sources_compact_list() -> None:
    result = parse_public_phone_sources(" @source_one, https://t.me/source_two, @SOURCE_ONE, , @source_three ")

    assert result == ["@source_one", "https://t.me/source_two", "@source_three"]


def test_parse_public_phone_sources_empty_value() -> None:
    assert parse_public_phone_sources(" , , ") == []
