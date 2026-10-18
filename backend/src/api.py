"""FastAPI backend for the DataMind frontend.

Run from the backend directory with:
    uvicorn src.api:app --reload --port 8000
"""

from __future__ import annotations

import logging
import os
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.staticfiles import StaticFiles
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_504_GATEWAY_TIMEOUT,
)
from yaml import YAMLError

from src.config_loader import DatasetConfig, load_dataset_config
from src.llm import GemmaClient
from src.pipeline import AnswerResult, Pipeline
from src.snowflake_client import SnowflakeClient


logger = logging.getLogger("datamind.api")
_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"
_DEFAULT_FRONTEND_DIST = _REPOSITORY_ROOT / "frontend" / "dist"
_DEFAULT_MAX_ROWS = 200


class HistoryMessage(BaseModel):
    """One prior frontend conversation message."""

    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str


class AskRequest(BaseModel):
    """Validated request body for a data question."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=1000)
    dataset: str = Field(min_length=1)
    history: list[HistoryMessage]

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        """Reject whitespace-only questions while preserving submitted text."""
        if not value.strip():
            raise ValueError("question must contain non-whitespace text.")
        return value

    @field_validator("dataset")
    @classmethod
    def dataset_must_not_be_blank(cls, value: str) -> str:
        """Reject whitespace-only dataset IDs."""
        if not value.strip():
            raise ValueError("dataset must contain non-whitespace text.")
        return value

    @field_validator("history", mode="before")
    @classmethod
    def retain_last_ten_messages(cls, value: object) -> object:
        """Cap supplied conversation context to the latest ten entries."""
        if isinstance(value, list):
            return value[-10:]
        return value


class AskResponse(BaseModel):
    """Contract response for every completed pipeline request."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["answered", "clarify", "unsupported", "empty", "error"]
    answer: str | None
    explanation: str | None
    assumptions: list[str]
    sql: str | None
    columns: list[str]
    rows: list[list[Any]]
    row_count: int = Field(ge=0)
    truncated: bool
    query_id: str | None
    clarifying_question: str | None
    elapsed_ms: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_status_fields(self) -> AskResponse:
        """Enforce the response invariants defined by the frontend contract."""
        if self.row_count != len(self.rows):
            raise ValueError("row_count must equal the number of returned rows.")
        if self.status == "answered":
            if (
                self.answer is None
                or self.explanation is None
                or self.sql is None
                or self.query_id is None
            ):
                raise ValueError(
                    "answered responses require answer, explanation, SQL, "
                    "and query_id."
                )
        elif self.status == "clarify":
            if self.clarifying_question is None or self.sql is not None or self.query_id is not None:
                raise ValueError(
                    "clarify responses require a clarifying question and no query evidence."
                )
        elif self.status == "unsupported":
            if self.answer is None or self.sql is not None or self.query_id is not None:
                raise ValueError(
                    "unsupported responses require an answer and no query evidence."
                )
        elif self.status == "empty":
            if (
                self.answer is None
                or "no rows" not in self.answer.casefold()
                or self.sql is None
                or self.query_id is None
                or self.rows
                or self.row_count != 0
            ):
                raise ValueError(
                    "empty responses require a no-rows answer, query evidence, "
                    "and zero rows."
                )
        elif self.status == "error" and not self.answer:
            raise ValueError("error responses require a friendly answer.")
        return self


class HealthCheck(BaseModel):
    """Outcome and safe diagnostic message for one dependency."""

    model_config = ConfigDict(extra="forbid")

    ok: bool
    message: str


class HealthResponse(BaseModel):
    """Aggregate state for required backend services."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok", "degraded", "down"]
    checks: dict[Literal["config", "snowflake", "gemma"], HealthCheck]


class DatasetSummary(BaseModel):
    """Public dataset metadata available to the frontend."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str
    example_questions: list[str]


class DatasetListResponse(BaseModel):
    """Available dataset summaries."""

    model_config = ConfigDict(extra="forbid")

    datasets: list[DatasetSummary]


class ErrorDetail(BaseModel):
    """Stable machine-readable and safe HTTP error."""

    model_config = ConfigDict(extra="forbid")

    code: Literal[
        "VALIDATION_ERROR",
        "UNKNOWN_DATASET",
        "UPSTREAM_TIMEOUT",
        "INTERNAL_ERROR",
    ]
    message: str


class ErrorResponse(BaseModel):
    """Consistent HTTP error envelope."""

    model_config = ConfigDict(extra="forbid")

    error: ErrorDetail


class ApiFailure(Exception):
    """Expected HTTP error without an unsafe or provider-specific message."""

    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message


class DatasetRegistryError(RuntimeError):
    """Raised when dataset configs cannot produce a unique API catalog."""


PipelineFactory = Callable[[Path], Pipeline]
SnowflakeFactory = Callable[[], SnowflakeClient]
GemmaFactory = Callable[[], GemmaClient]


class ApiService:
    """App-scoped dataset catalog and lazily cached pipelines."""

    def __init__(
        self,
        config_dir: Path,
        pipeline_factory: PipelineFactory,
        snowflake_factory: SnowflakeFactory,
        gemma_factory: GemmaFactory,
    ) -> None:
        self.config_dir = config_dir
        self.pipeline_factory = pipeline_factory
        self.snowflake_factory = snowflake_factory
        self.gemma_factory = gemma_factory
        self._pipeline_cache: dict[Path, Pipeline] = {}

    def catalog(self) -> dict[str, tuple[DatasetSummary, Path, DatasetConfig]]:
        """Load all configured YAML datasets and map stable IDs to config paths."""
        if not self.config_dir.is_dir():
            raise DatasetRegistryError("Dataset configuration directory is unavailable.")

        entries: dict[str, tuple[DatasetSummary, Path, DatasetConfig]] = {}
        for path in sorted(self.config_dir.glob("*.yaml")):
            try:
                config = load_dataset_config(path)
            except (OSError, ValueError, YAMLError) as exc:
                raise DatasetRegistryError(
                    "A dataset configuration could not be loaded."
                ) from exc
            dataset_id = _dataset_id(config.dataset_name)
            if dataset_id in entries:
                raise DatasetRegistryError("Dataset IDs must be unique.")
            summary = DatasetSummary(
                id=dataset_id,
                name=config.dataset_name,
                description=config.description,
                example_questions=config.example_questions,
            )
            entries[dataset_id] = (summary, path.resolve(), config)
        if not entries:
            raise DatasetRegistryError("No dataset configuration files were found.")
        return entries

    def pipeline_for(self, dataset_id: str) -> Pipeline:
        """Return the cached pipeline associated with the selected config."""
        entries = self.catalog()
        if dataset_id not in entries:
            raise ApiFailure(
                HTTP_404_NOT_FOUND,
                "UNKNOWN_DATASET",
                "The requested dataset was not found.",
            )
        config_path = entries[dataset_id][1]
        if config_path not in self._pipeline_cache:
            self._pipeline_cache[config_path] = self.pipeline_factory(config_path)
        return self._pipeline_cache[config_path]

    def max_rows(self) -> int:
        """Return the positive API response-row cap from environment settings."""
        raw_limit = os.getenv("API_MAX_ROWS", str(_DEFAULT_MAX_ROWS)).strip()
        try:
            limit = int(raw_limit)
        except ValueError as exc:
            raise ValueError("API_MAX_ROWS must be a positive integer.") from exc
        if limit < 1:
            raise ValueError("API_MAX_ROWS must be a positive integer.")
        return limit


def _dataset_id(name: str) -> str:
    """Create a stable lowercase hyphenated ID from the configured display name."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-")
    if slug.startswith("uci-"):
        slug = slug[4:]
    return slug


def _to_json_rows(rows: list[tuple[object, ...]]) -> list[list[Any]]:
    """Convert pipeline row tuples into JSON response row arrays."""
    return [list(row) for row in rows]


def _is_timeout(error: BaseException) -> bool:
    """Identify common timeout exceptions without exposing their messages."""
    current: BaseException | None = error
    visited: set[int] = set()
    while current is not None and id(current) not in visited:
        visited.add(id(current))
        if isinstance(current, (TimeoutError, requests.Timeout)):
            return True
        if "timeout" in type(current).__name__.casefold():
            return True
        text = str(current).casefold()
        if "timed out" in text or "timeout" in text:
            return True
        current = current.__cause__ or current.__context__
    return False


def _map_result(result: AnswerResult, max_rows: int, elapsed_ms: int) -> AskResponse:
    """Map pipeline statuses and row evidence into the frontend contract."""
    if result.status == "ambiguous":
        return AskResponse(
            status="clarify",
            answer=None,
            explanation=result.explanation,
            assumptions=result.assumptions,
            sql=None,
            columns=[],
            rows=[],
            row_count=0,
            truncated=False,
            query_id=None,
            clarifying_question=result.clarifying_question,
            elapsed_ms=elapsed_ms,
        )

    if result.status == "unsupported":
        return AskResponse(
            status="unsupported",
            answer=result.answer,
            explanation=result.explanation,
            assumptions=result.assumptions,
            sql=None,
            columns=[],
            rows=[],
            row_count=0,
            truncated=False,
            query_id=None,
            clarifying_question=None,
            elapsed_ms=elapsed_ms,
        )

    if result.status == "error":
        if any(_is_timeout(RuntimeError(warning)) for warning in result.warnings):
            raise ApiFailure(
                HTTP_504_GATEWAY_TIMEOUT,
                "UPSTREAM_TIMEOUT",
                "A required data service did not respond in time. Please try again.",
            )
        return _friendly_pipeline_error(elapsed_ms)

    if result.sql is None or result.query_id is None:
        raise RuntimeError("Pipeline returned an answer without query evidence.")

    rows = _to_json_rows(result.rows)
    truncated = len(rows) > max_rows
    response_rows = rows[:max_rows]
    status: Literal["answered", "empty"] = "empty" if not rows else "answered"
    answer = (
        "No rows matched the requested criteria."
        if status == "empty"
        else result.answer
    )
    return AskResponse(
        status=status,
        answer=answer,
        explanation=result.explanation,
        assumptions=result.assumptions,
        sql=result.sql,
        columns=result.columns,
        rows=response_rows,
        row_count=len(response_rows),
        truncated=truncated,
        query_id=result.query_id,
        clarifying_question=None,
        elapsed_ms=elapsed_ms,
    )


def _friendly_pipeline_error(elapsed_ms: int) -> AskResponse:
    """Return a safe error response without provider or database internals."""
    return AskResponse(
        status="error",
        answer="I couldn't complete that query right now. Please try again or rephrase your question.",
        explanation="The request could not be completed safely by the data pipeline.",
        assumptions=[],
        sql=None,
        columns=[],
        rows=[],
        row_count=0,
        truncated=False,
        query_id=None,
        clarifying_question=None,
        elapsed_ms=elapsed_ms,
    )


def _error_response(code: str, message: str) -> dict[str, dict[str, str]]:
    """Return the public HTTP error object."""
    return {"error": {"code": code, "message": message}}


def create_app(
    config_dir: str | Path | None = None,
    pipeline_factory: PipelineFactory | None = None,
    snowflake_factory: SnowflakeFactory | None = None,
    gemma_factory: GemmaFactory | None = None,
) -> FastAPI:
    """Create an app with isolated services and an app-scoped pipeline cache."""
    load_dotenv(_REPOSITORY_ROOT / ".env")
    service = ApiService(
        config_dir=Path(config_dir) if config_dir is not None else _DEFAULT_CONFIG_DIR,
        pipeline_factory=pipeline_factory or Pipeline,
        snowflake_factory=snowflake_factory or SnowflakeClient,
        gemma_factory=gemma_factory or GemmaClient,
    )
    application = FastAPI(title="DataMind API", version="1.0.0")
    application.state.datamind_service = service

    configured_origins = os.getenv("CORS_ORIGINS")
    if configured_origins is None:
        origins = ["http://localhost:5173"]
    else:
        origins = [origin.strip() for origin in configured_origins.split(",") if origin.strip()]
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @application.exception_handler(ApiFailure)
    async def api_failure_handler(
        _request: Request,
        exception: ApiFailure,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exception.status_code,
            content=_error_response(exception.code, exception.message),
        )

    @application.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        _request: Request,
        exception: StarletteHTTPException,
    ) -> JSONResponse:
        if exception.status_code == HTTP_404_NOT_FOUND:
            return JSONResponse(
                status_code=HTTP_404_NOT_FOUND,
                content=_error_response("UNKNOWN_DATASET", "The requested resource was not found."),
            )
        return JSONResponse(
            status_code=exception.status_code,
            content=_error_response("INTERNAL_ERROR", "The request could not be completed."),
        )

    @application.exception_handler(Exception)
    async def unexpected_exception_handler(
        _request: Request,
        _exception: Exception,
    ) -> JSONResponse:
        logger.error("Unhandled API failure")
        return JSONResponse(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_response(
                "INTERNAL_ERROR",
                "The server could not complete the request.",
            ),
        )

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request,
        _exception: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=HTTP_400_BAD_REQUEST,
            content=_error_response(
                "VALIDATION_ERROR",
                "The request body is invalid. Check required fields and value constraints.",
            ),
        )

    @application.get("/api/health", response_model=HealthResponse)
    def get_health() -> HealthResponse:
        checks: dict[str, HealthCheck] = {}
        try:
            service.catalog()
            checks["config"] = HealthCheck(
                ok=True,
                message="Dataset configuration loaded.",
            )
        except Exception:
            checks["config"] = HealthCheck(
                ok=False,
                message="Dataset configuration is unavailable or invalid.",
            )

        try:
            with service.snowflake_factory() as client:
                result = client.run_query("SELECT 1 AS HEALTH_CHECK")
            if result["rows"] != [(1,)]:
                raise RuntimeError("Unexpected health-check result.")
            checks["snowflake"] = HealthCheck(
                ok=True,
                message="Snowflake reader connection is available.",
            )
        except Exception as exc:
            if _is_timeout(exc):
                message = "Snowflake did not respond before the configured timeout."
            else:
                message = "Snowflake reader connection is unavailable."
            checks["snowflake"] = HealthCheck(ok=False, message=message)

        try:
            response = service.gemma_factory().generate(
                "Reply with the word OK.",
                max_tokens=8,
            )
            if not response.strip():
                raise RuntimeError("Gemma returned an empty response.")
            checks["gemma"] = HealthCheck(
                ok=True,
                message="Gemma backend is responding.",
            )
        except Exception as exc:
            if _is_timeout(exc):
                message = "Gemma did not respond before the configured timeout."
            else:
                message = "Gemma backend is unavailable."
            checks["gemma"] = HealthCheck(ok=False, message=message)

        outcomes = [check.ok for check in checks.values()]
        if all(outcomes):
            status: Literal["ok", "degraded", "down"] = "ok"
        elif (
            not checks["config"].ok
            or not checks["snowflake"].ok and not checks["gemma"].ok
        ):
            status = "down"
        else:
            status = "degraded"
        return HealthResponse(status=status, checks=checks)

    @application.get("/api/datasets", response_model=DatasetListResponse)
    def get_datasets() -> DatasetListResponse:
        try:
            entries = service.catalog()
        except Exception as exc:
            raise ApiFailure(
                HTTP_500_INTERNAL_SERVER_ERROR,
                "INTERNAL_ERROR",
                "Dataset information is temporarily unavailable.",
            ) from exc
        return DatasetListResponse(
            datasets=[entry[0] for entry in entries.values()]
        )

    @application.post("/api/ask", response_model=AskResponse)
    def post_ask(request_data: AskRequest) -> AskResponse:
        started = time.perf_counter()
        try:
            pipeline = service.pipeline_for(request_data.dataset)
            history = [
                message.model_dump()
                for message in request_data.history[-10:]
            ]
            result = pipeline.ask(request_data.question, history=history)
            elapsed_ms = max(0, int((time.perf_counter() - started) * 1000))
            response = _map_result(result, service.max_rows(), elapsed_ms)
            logger.info(
                "ask completed dataset=%s status=%s query_id=%s elapsed_ms=%d",
                request_data.dataset,
                response.status,
                response.query_id or "-",
                response.elapsed_ms,
            )
            return response
        except ApiFailure:
            raise
        except Exception as exc:
            elapsed_ms = max(0, int((time.perf_counter() - started) * 1000))
            if _is_timeout(exc):
                logger.warning(
                    "ask timed out dataset=%s elapsed_ms=%d",
                    request_data.dataset,
                    elapsed_ms,
                )
                raise ApiFailure(
                    HTTP_504_GATEWAY_TIMEOUT,
                    "UPSTREAM_TIMEOUT",
                    "A required data service did not respond in time. Please try again.",
                ) from exc
            logger.error(
                "ask failed dataset=%s error_type=%s elapsed_ms=%d",
                request_data.dataset,
                type(exc).__name__,
                elapsed_ms,
            )
            return _friendly_pipeline_error(elapsed_ms)

    if _DEFAULT_FRONTEND_DIST.is_dir():
        @application.get("/chat", include_in_schema=False)
        def serve_chat_page() -> FileResponse:
            """Serve the frontend entry point for its client-side chat route."""
            return FileResponse(_DEFAULT_FRONTEND_DIST / "index.html")

        application.mount(
            "/",
            StaticFiles(directory=str(_DEFAULT_FRONTEND_DIST), html=True),
            name="frontend",
        )

    return application


app = create_app()
