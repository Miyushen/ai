from app.core.config import Settings


def test_key_is_optional_for_healthcheck() -> None:
    settings = Settings(openai_api_key=None)
    assert settings.has_openai_key is False


def test_key_detection() -> None:
    settings = Settings(openai_api_key="test-key")
    assert settings.has_openai_key is True


def test_reasoning_options_are_disabled_by_default() -> None:
    settings = Settings(
        openai_reasoning_effort="",
        openai_verbosity="",
        openai_max_completion_tokens=0,
    )
    assert settings.openai_reasoning_effort == ""
    assert settings.openai_verbosity == ""
    assert settings.openai_max_completion_tokens == 0

