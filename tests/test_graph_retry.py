from app.agent.graph import _retry_transient_model_error


class ProviderError(Exception):
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


class OpenAIConnectionError(Exception):
    pass


def test_retries_server_errors() -> None:
    assert _retry_transient_model_error(ProviderError(502)) is True


def test_does_not_retry_client_errors() -> None:
    assert _retry_transient_model_error(ProviderError(400)) is False


def test_retries_nested_connection_errors() -> None:
    wrapper = RuntimeError("provider failed")
    wrapper.__cause__ = OpenAIConnectionError("connection closed")
    assert _retry_transient_model_error(wrapper) is True
