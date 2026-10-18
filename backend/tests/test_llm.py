"""Tests for Gemma backends and structured JSON generation."""

from unittest.mock import Mock

import pytest
import requests
from pydantic import BaseModel

from src.llm import GemmaClient, GemmaClientError


class SampleAnswer(BaseModel):
    """Example response schema for JSON generation tests."""

    answer: str
    count: int


def configure_ollama(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configure a local Ollama backend for a test."""
    monkeypatch.setenv("GEMMA_BACKEND", "ollama")
    monkeypatch.setenv("GEMMA_MODEL", "gemma3:4b")
    monkeypatch.setenv("GEMMA_TIMEOUT_SECONDS", "5")
    monkeypatch.delenv("GEMMA_API_BASE_URL", raising=False)
    monkeypatch.delenv("GEMMA_API_KEY", raising=False)


def response_with_json(payload: dict[str, object]) -> Mock:
    """Build a successful mocked requests response."""
    response = Mock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def test_generate_uses_ollama_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Send expected options to Ollama and return its generated response."""
    configure_ollama(monkeypatch)
    post = Mock(return_value=response_with_json({"response": "Hello from Gemma."}))
    monkeypatch.setattr("src.llm.requests.post", post)

    result = GemmaClient().generate(
        "Say hello.", system="Be concise.", temperature=0.2, max_tokens=30
    )

    assert result == "Hello from Gemma."
    assert post.call_args.args[0] == "http://localhost:11434/api/generate"
    assert post.call_args.kwargs["timeout"] == 5
    assert post.call_args.kwargs["json"] == {
        "model": "gemma3:4b",
        "prompt": "Say hello.",
        "system": "Be concise.",
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 30},
    }


def test_generate_uses_configured_hosted_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Use the configured OpenAI-compatible endpoint and bearer key."""
    monkeypatch.setenv("GEMMA_BACKEND", "api")
    monkeypatch.setenv("GEMMA_MODEL", "hosted-gemma")
    monkeypatch.setenv("GEMMA_API_BASE_URL", "https://gemma.example/v1/")
    monkeypatch.setenv("GEMMA_API_KEY", "test-secret")
    post = Mock(
        return_value=response_with_json(
            {"choices": [{"message": {"content": "Hosted reply."}}]}
        )
    )
    monkeypatch.setattr("src.llm.requests.post", post)

    result = GemmaClient().generate(
        "Say hello.", system="Be brief.", max_tokens=20
    )

    assert result == "Hosted reply."
    assert post.call_args.args[0] == "https://gemma.example/v1/chat/completions"
    assert post.call_args.kwargs["headers"]["Authorization"] == "Bearer test-secret"
    assert post.call_args.kwargs["json"]["messages"] == [
        {"role": "system", "content": "Be brief."},
        {"role": "user", "content": "Say hello."},
    ]


def test_generate_retries_connection_failure_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Retry a transient failure once and give a clear error if unavailable."""
    configure_ollama(monkeypatch)
    post = Mock(side_effect=requests.ConnectionError("connection refused"))
    sleep = Mock()
    monkeypatch.setattr("src.llm.requests.post", post)
    monkeypatch.setattr("src.llm.time.sleep", sleep)

    with pytest.raises(GemmaClientError, match="after one retry"):
        GemmaClient().generate("Say hello.")

    assert post.call_count == 2
    sleep.assert_called_once_with(0.1)


def test_generate_json_strips_fence_and_validates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Parse fenced JSON into the requested Pydantic model."""
    configure_ollama(monkeypatch)
    post = Mock(
        return_value=response_with_json(
            {"response": '```json\n{"answer":"ok","count":3}\n```'}
        )
    )
    monkeypatch.setattr("src.llm.requests.post", post)

    result = GemmaClient().generate_json("Return a sample.", SampleAnswer)

    assert result == SampleAnswer(answer="ok", count=3)


def test_generate_json_retries_once_on_invalid_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prompt once more with the validation failure, then return valid data."""
    configure_ollama(monkeypatch)
    post = Mock(
        side_effect=[
            response_with_json({"response": "not json"}),
            response_with_json(
                {"response": '{"answer":"repaired","count":2}'}
            ),
        ]
    )
    monkeypatch.setattr("src.llm.requests.post", post)

    result = GemmaClient().generate_json("Return a sample.", SampleAnswer)

    assert result.answer == "repaired"
    assert result.count == 2
    assert post.call_count == 2
    assert "previous response was invalid" in post.call_args_list[1].kwargs["json"][
        "prompt"
    ]


def test_generate_json_reports_invalid_output_after_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Raise a clear error if both model responses fail schema validation."""
    configure_ollama(monkeypatch)
    post = Mock(return_value=response_with_json({"response": "not json"}))
    monkeypatch.setattr("src.llm.requests.post", post)

    with pytest.raises(GemmaClientError, match="after one retry"):
        GemmaClient().generate_json("Return a sample.", SampleAnswer)

    assert post.call_count == 2
