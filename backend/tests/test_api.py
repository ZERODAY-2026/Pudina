"""FastAPI endpoint and contract-fixture tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.api import (
    AskResponse,
    DatasetListResponse,
    ErrorResponse,
    HealthResponse,
    create_app,
)
from src.pipeline import AnswerResult


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT.parent / "docs" / "fixtures"
CONFIG_DIR = ROOT / "config"


class FakePipeline:
    """Pipeline stand-in returning one prepared response."""

    def __init__(self, result: AnswerResult):
        self.result = result
        self.calls: list[tuple[str, list[dict[str, str]]]] = []

    def ask(
        self,
        question: str,
        history: list[dict[str, str]] | None = None,
    ) -> AnswerResult:
        self.calls.append((question, list(history or [])))
        return self.result


class FakeSnowflake:
    """Context-managed stand-in for a reader Snowflake client."""

    def __init__(self, *, error: Exception | None = None):
        self.error = error
        self.queries: list[str] = []

    def __enter__(self) -> FakeSnowflake:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def run_query(self, sql: str) -> dict[str, Any]:
        self.queries.append(sql)
        if self.error:
            raise self.error
        return {"rows": [(1,)], "query_id": "health-query"}


class FakeGemma:
    """Stand-in for Gemma health checks."""

    def __init__(self, *, error: Exception | None = None):
        self.error = error

    def generate(self, *_args: object, **_kwargs: object) -> str:
        if self.error:
            raise self.error
        return "OK"


def answered_result(
    *,
    rows: list[tuple[object, ...]] | None = None,
    sql: str = 'SELECT "y" FROM BANK_MARKETING',
) -> AnswerResult:
    """Create a valid answer result with configurable rows."""
    return AnswerResult(
        status="answerable",
        answer="5,289 clients subscribed to a term deposit.",
        explanation="Counted rows in BANK_MARKETING where y = 'yes'.",
        assumptions=[],
        sql=sql,
        columns=["SUBSCRIBED_CLIENTS"],
        rows=rows if rows is not None else [(5289,)],
        query_id="query-123",
    )


def response_for(
    result: AnswerResult,
    *,
    pipeline_instances: list[FakePipeline] | None = None,
) -> TestClient:
    """Create an isolated client backed by the specified fake pipeline."""
    if pipeline_instances is None:
        pipeline_instances = []

    def make_pipeline(_path: Path) -> FakePipeline:
        pipeline = FakePipeline(result)
        pipeline_instances.append(pipeline)
        return pipeline

    app = create_app(
        config_dir=CONFIG_DIR,
        pipeline_factory=make_pipeline,
        snowflake_factory=FakeSnowflake,
        gemma_factory=FakeGemma,
    )
    return TestClient(app)


def ask_payload(
    *,
    question: str = "How many clients subscribed?",
    dataset: str = "bank-marketing",
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Build an ask request with the required contract fields."""
    return {
        "question": question,
        "dataset": dataset,
        "history": history if history is not None else [],
    }


def test_get_datasets_lists_configured_datasets() -> None:
    """Expose dataset metadata loaded from each YAML configuration."""
    client = response_for(answered_result())

    response = client.get("/api/datasets")

    assert response.status_code == 200
    body = DatasetListResponse.model_validate(response.json())
    assert len(body.datasets) == 2
    bank = next(dataset for dataset in body.datasets if dataset.id == "bank-marketing")
    assert bank.name == "UCI Bank Marketing"
    assert bank.example_questions


def test_get_datasets_discovers_tpch_config_automatically() -> None:
    """Expose the new config's own ID and questions without API code changes."""
    client = TestClient(create_app(config_dir=CONFIG_DIR))

    response = client.get("/api/datasets")

    assert response.status_code == 200
    datasets = DatasetListResponse.model_validate(response.json()).datasets
    tpch = next(dataset for dataset in datasets if dataset.id == "tpc-h-sf1")
    assert tpch.name == "TPC-H SF1"
    assert "Which three nations have the most orders?" in tpch.example_questions


def test_datasets_endpoint_matches_the_committed_fixture() -> None:
    """Keep the dataset example fixture synchronized with discovered configs."""
    client = response_for(answered_result())

    response = client.get("/api/datasets")

    assert response.status_code == 200
    fixture = json.loads((FIXTURES / "datasets.json").read_text(encoding="utf-8"))
    assert response.json() == fixture


def test_post_ask_maps_answered_status_and_evidence() -> None:
    """Return full query evidence in the answered response."""
    client = response_for(answered_result())

    response = client.post("/api/ask", json=ask_payload())

    assert response.status_code == 200
    body = AskResponse.model_validate(response.json())
    assert body.status == "answered"
    assert body.sql == 'SELECT "y" FROM BANK_MARKETING'
    assert body.rows == [[5289]]
    assert body.columns == ["SUBSCRIBED_CLIENTS"]
    assert body.query_id == "query-123"
    assert body.explanation
    assert body.row_count == 1
    assert body.truncated is False


@pytest.mark.parametrize(
    ("pipeline_result", "expected_status"),
    (
        (
            AnswerResult(
                status="ambiguous",
                answer="A ranking needs a metric.",
                explanation="Several metrics could define best.",
                clarifying_question="Which metric should I use?",
            ),
            "clarify",
        ),
        (
            AnswerResult(
                status="unsupported",
                answer="I can't predict future outcomes. I can answer read-only "
                "questions about historical campaign data.",
                explanation="Future behavior is not in the dataset.",
            ),
            "unsupported",
        ),
        (
            AnswerResult(
                status="answerable",
                answer="No rows matched the requested criteria.",
                explanation="No BANK_MARKETING rows matched age > 200.",
                sql='SELECT "age" FROM BANK_MARKETING WHERE "age" > 200',
                columns=["age"],
                rows=[],
                query_id="empty-query",
            ),
            "empty",
        ),
        (
            AnswerResult(
                status="error",
                answer="I couldn't safely run this query.",
                explanation="Only read-only queries are supported.",
                warnings=["blocked"],
            ),
            "error",
        ),
    ),
)
def test_post_ask_maps_every_non_answered_status(
    pipeline_result: AnswerResult,
    expected_status: str,
) -> None:
    """Map all pipeline result variants to the corresponding API status."""
    client = response_for(pipeline_result)

    response = client.post("/api/ask", json=ask_payload())

    assert response.status_code == 200
    body = AskResponse.model_validate(response.json())
    assert body.status == expected_status
    if expected_status == "clarify":
        assert body.clarifying_question
        assert body.sql is None and body.query_id is None
    elif expected_status == "unsupported":
        assert body.answer and "can answer" in body.answer
        assert body.sql is None and body.query_id is None
    elif expected_status == "empty":
        assert body.answer and "no rows" in body.answer.casefold()
        assert body.rows == [] and body.row_count == 0
        assert body.sql and body.query_id
    elif expected_status == "error":
        assert body.answer and body.explanation


def test_post_ask_truncates_rows_at_configured_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Limit returned rows and report truncation and returned-row count."""
    monkeypatch.setenv("API_MAX_ROWS", "3")
    result = answered_result(rows=[(index,) for index in range(5)])
    client = response_for(result)

    response = client.post("/api/ask", json=ask_payload())

    assert response.status_code == 200
    body = AskResponse.model_validate(response.json())
    assert body.rows == [[0], [1], [2]]
    assert body.row_count == 3
    assert body.truncated is True


def test_post_ask_caps_history_to_last_ten_messages() -> None:
    """Pass only the ten most recent submitted history entries to the pipeline."""
    instances: list[FakePipeline] = []
    client = response_for(
        answered_result(),
        pipeline_instances=instances,
    )
    history = [
        {"role": "user" if index % 2 == 0 else "assistant", "content": str(index)}
        for index in range(14)
    ]

    response = client.post("/api/ask", json=ask_payload(history=history))

    assert response.status_code == 200
    assert len(instances) == 1
    assert instances[0].calls[0][1] == history[-10:]


def test_pipeline_is_cached_per_config_per_app() -> None:
    """Reuse one initialized pipeline for repeated requests to one dataset."""
    instances: list[FakePipeline] = []
    client = response_for(answered_result(), pipeline_instances=instances)

    first = client.post("/api/ask", json=ask_payload())
    second = client.post("/api/ask", json=ask_payload())

    assert first.status_code == second.status_code == 200
    assert len(instances) == 1
    assert len(instances[0].calls) == 2


@pytest.mark.parametrize(
    "payload",
    (
        {"question": "", "dataset": "bank-marketing", "history": []},
        {"question": "x" * 1001, "dataset": "bank-marketing", "history": []},
        {"question": "  ", "dataset": "bank-marketing", "history": []},
        {"question": "valid", "dataset": "bank-marketing"},
        {
            "question": "valid",
            "dataset": "bank-marketing",
            "history": [{"role": "system", "content": "not allowed"}],
        },
        {
            "question": "valid",
            "dataset": "bank-marketing",
            "history": [],
            "extra": "not allowed",
        },
    ),
)
def test_post_ask_returns_contract_validation_error(payload: dict[str, Any]) -> None:
    """Reject invalid fields with the documented error envelope."""
    client = response_for(answered_result())

    response = client.post("/api/ask", json=payload)

    assert response.status_code == 400
    body = ErrorResponse.model_validate(response.json())
    assert body.error.code == "VALIDATION_ERROR"


def test_post_ask_unknown_dataset_returns_contract_error() -> None:
    """Reject a dataset ID not present in the config catalog."""
    client = response_for(answered_result())

    response = client.post(
        "/api/ask",
        json=ask_payload(dataset="unknown-dataset"),
    )

    assert response.status_code == 404
    body = ErrorResponse.model_validate(response.json())
    assert body.error.code == "UNKNOWN_DATASET"


def test_post_ask_timeout_returns_contract_error() -> None:
    """Map upstream timeouts to the HTTP timeout error envelope."""

    def timeout_pipeline(_path: Path) -> Any:
        class TimeoutPipeline:
            def ask(self, _question: str, history: list[dict[str, str]]) -> AnswerResult:
                raise TimeoutError("sensitive upstream timeout")

        return TimeoutPipeline()

    client = TestClient(
        create_app(
            config_dir=CONFIG_DIR,
            pipeline_factory=timeout_pipeline,
            snowflake_factory=FakeSnowflake,
            gemma_factory=FakeGemma,
        )
    )
    response = client.post("/api/ask", json=ask_payload())

    assert response.status_code == 504
    body = ErrorResponse.model_validate(response.json())
    assert body.error.code == "UPSTREAM_TIMEOUT"
    assert "sensitive" not in body.error.message


@pytest.mark.parametrize(
    ("snowflake_error", "gemma_error", "expected_status"),
    (
        (RuntimeError("credential secret"), None, "degraded"),
        (None, TimeoutError("secret timeout"), "degraded"),
        (RuntimeError("snowflake"), RuntimeError("gemma"), "down"),
        (None, None, "ok"),
    ),
)
def test_health_reports_each_dependency_failure_safely(
    snowflake_error: Exception | None,
    gemma_error: Exception | None,
    expected_status: str,
) -> None:
    """Report health checks independently without exposing exception content."""
    snowflake = FakeSnowflake(error=snowflake_error)
    gemma = FakeGemma(error=gemma_error)
    client = TestClient(
        create_app(
            config_dir=CONFIG_DIR,
            pipeline_factory=lambda _path: FakePipeline(answered_result()),
            snowflake_factory=lambda: snowflake,
            gemma_factory=lambda: gemma,
        )
    )

    response = client.get("/api/health")

    assert response.status_code == 200
    body = HealthResponse.model_validate(response.json())
    assert body.status == expected_status
    assert body.checks["config"].ok
    assert body.checks["snowflake"].ok is (snowflake_error is None)
    assert body.checks["gemma"].ok is (gemma_error is None)
    assert "secret" not in response.text
    if snowflake_error is None:
        assert snowflake.queries == ["SELECT 1 AS HEALTH_CHECK"]


def test_health_config_failure_is_down() -> None:
    """Mark the service down if no usable dataset catalog can be loaded."""
    client = TestClient(
        create_app(
            config_dir=ROOT / "missing-config",
            pipeline_factory=lambda _path: FakePipeline(answered_result()),
            snowflake_factory=FakeSnowflake,
            gemma_factory=FakeGemma,
        )
    )

    body = HealthResponse.model_validate(client.get("/api/health").json())

    assert body.status == "down"
    assert body.checks["config"].ok is False


@pytest.mark.parametrize(
    ("gemma_error", "fixture_name"),
    (
        (None, "health_ok.json"),
        (RuntimeError("private Gemma error"), "health_degraded.json"),
    ),
)
def test_health_endpoints_match_committed_fixtures(
    gemma_error: Exception | None,
    fixture_name: str,
) -> None:
    """Keep health status messages and checks aligned with their examples."""
    client = TestClient(
        create_app(
            config_dir=CONFIG_DIR,
            pipeline_factory=lambda _path: FakePipeline(answered_result()),
            snowflake_factory=FakeSnowflake,
            gemma_factory=lambda: FakeGemma(error=gemma_error),
        )
    )

    response = client.get("/api/health")

    assert response.status_code == 200
    fixture = json.loads((FIXTURES / fixture_name).read_text(encoding="utf-8"))
    assert response.json() == fixture


def test_cors_uses_only_configured_origins(monkeypatch: pytest.MonkeyPatch) -> None:
    """Allow the configured frontend origin and reject other origins."""
    monkeypatch.setenv("CORS_ORIGINS", "https://frontend.example")
    client = response_for(answered_result())

    allowed = client.options(
        "/api/datasets",
        headers={
            "Origin": "https://frontend.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    denied = client.options(
        "/api/datasets",
        headers={
            "Origin": "https://attacker.example",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert allowed.headers["access-control-allow-origin"] == "https://frontend.example"
    assert "access-control-allow-origin" not in denied.headers


def test_built_frontend_is_served_after_api_routes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Serve built frontend files at root without shadowing API endpoints."""
    frontend_dist = tmp_path / "dist"
    frontend_dist.mkdir()
    (frontend_dist / "index.html").write_text(
        "<!doctype html><title>DataMind integrated</title>",
        encoding="utf-8",
    )
    monkeypatch.setattr("src.api._DEFAULT_FRONTEND_DIST", frontend_dist)
    client = TestClient(
        create_app(
            config_dir=CONFIG_DIR,
            pipeline_factory=lambda _path: FakePipeline(answered_result()),
            snowflake_factory=FakeSnowflake,
            gemma_factory=FakeGemma,
        )
    )

    assert "DataMind integrated" in client.get("/").text
    assert "DataMind integrated" in client.get("/chat").text
    assert client.get("/api/datasets").status_code == 200


def test_contract_fixtures_validate_against_response_models() -> None:
    """Keep every committed success/error fixture aligned with Pydantic contract."""
    for path in sorted(FIXTURES.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if path.name.startswith("ask_"):
            AskResponse.model_validate(payload)
        elif path.name.startswith("health_"):
            HealthResponse.model_validate(payload)
        elif path.name == "datasets.json":
            DatasetListResponse.model_validate(payload)
        elif path.name.startswith("http_"):
            ErrorResponse.model_validate(payload)


def test_contract_fixtures_have_exact_keys_and_types() -> None:
    """Validate all documented fixture roots and ask response key/type contracts."""
    expected_ask_keys = {
        "status",
        "answer",
        "explanation",
        "assumptions",
        "sql",
        "columns",
        "rows",
        "row_count",
        "truncated",
        "query_id",
        "clarifying_question",
        "elapsed_ms",
    }
    for path in sorted(FIXTURES.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if path.name.startswith("ask_"):
            assert set(payload) == expected_ask_keys
            validated = AskResponse.model_validate(payload)
            assert isinstance(validated.assumptions, list)
            assert isinstance(validated.columns, list)
            assert isinstance(validated.rows, list)
            assert isinstance(validated.row_count, int)
            assert isinstance(validated.truncated, bool)
            assert isinstance(validated.elapsed_ms, int)
        elif path.name.startswith("health_"):
            assert set(payload) == {"status", "checks"}
            assert set(payload["checks"]) == {"config", "snowflake", "gemma"}
        elif path.name == "datasets.json":
            assert set(payload) == {"datasets"}
        elif path.name.startswith("http_"):
            assert set(payload) == {"error"}
            assert set(payload["error"]) == {"code", "message"}


def test_invalid_response_invariants_are_rejected() -> None:
    """Response models enforce required evidence by application status."""
    payload = json.loads((FIXTURES / "ask_answered.json").read_text(encoding="utf-8"))
    payload["query_id"] = None

    with pytest.raises(ValidationError):
        AskResponse.model_validate(payload)
