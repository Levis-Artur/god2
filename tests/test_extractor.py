from app.services.extractor import TextArtifactExtractor


def test_extract_single_artifact() -> None:
    extractor = TextArtifactExtractor()

    result = extractor.extract("Деталі: https://Example.com/path?x=1.")

    assert [item.value for item in result.urls] == ["https://example.com/path?x=1"]
    assert [item.original_value for item in result.urls] == ["https://Example.com/path?x=1"]
    assert [item.value for item in result.domains] == ["example.com"]
    assert result.emails == []
    assert result.phone_numbers == []
    assert result.mentions == []
    assert result.hashtags == []


def test_extract_multiple_artifacts() -> None:
    extractor = TextArtifactExtractor()
    text = (
        "Контакти: test@example.com, +380 (67) 123-45-67, @Support, #Новини, "
        "сайт t.me/Example/123 і домен Example.org"
    )

    result = extractor.extract(text)

    assert [item.value for item in result.urls] == ["https://t.me/Example/123"]
    assert [item.value for item in result.domains] == ["t.me", "example.com", "example.org"]
    assert [item.value for item in result.emails] == ["test@example.com"]
    assert [item.value for item in result.phone_numbers] == ["380671234567"]
    assert [item.value for item in result.mentions] == ["@support"]
    assert [item.value for item in result.hashtags] == ["#новини"]


def test_extract_deduplicated_artifacts() -> None:
    extractor = TextArtifactExtractor()
    text = (
        "Дубль https://example.com і https://EXAMPLE.com. "
        "Email A@Example.com та a@example.com. "
        "@Team і @team. #Tag та #tag. "
        "+1 (202) 555-0100 і 12025550100"
    )

    result = extractor.extract(text)

    assert [item.value for item in result.urls] == ["https://example.com"]
    assert [item.value for item in result.domains] == ["example.com"]
    assert [item.value for item in result.emails] == ["a@example.com"]
    assert [item.value for item in result.phone_numbers] == ["12025550100"]
    assert [item.value for item in result.mentions] == ["@team"]
    assert [item.value for item in result.hashtags] == ["#tag"]


def test_extract_mixed_language_text() -> None:
    extractor = TextArtifactExtractor()
    text = "Український текст, email SUPPORT@Example.UA, згадка @NewsBot, хештег #Київ і сайт example.ua."

    result = extractor.extract(text)

    assert [item.value for item in result.urls] == []
    assert [item.value for item in result.domains] == ["example.ua"]
    assert [item.value for item in result.emails] == ["support@example.ua"]
    assert [item.value for item in result.mentions] == ["@newsbot"]
    assert [item.value for item in result.hashtags] == ["#київ"]


def test_extract_empty_text() -> None:
    extractor = TextArtifactExtractor()

    result = extractor.extract("")

    assert result.urls == []
    assert result.domains == []
    assert result.emails == []
    assert result.phone_numbers == []
    assert result.mentions == []
    assert result.hashtags == []


def test_extract_noisy_text() -> None:
    extractor = TextArtifactExtractor()
    text = "Шум: @@, http:/broken, #, @, ++++, домен..com, номер 1234."

    result = extractor.extract(text)

    assert result.urls == []
    assert result.domains == []
    assert result.emails == []
    assert result.phone_numbers == []
    assert result.mentions == []
    assert result.hashtags == []
