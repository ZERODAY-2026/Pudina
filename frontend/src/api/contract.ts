import type {
  ApiErrorBody,
  AskResponse,
  DatasetsResponse,
  HealthResponse,
  RowCell,
} from "../types";

export class ApiContractError extends Error {
  constructor() {
    super("The API returned a response that does not match the documented contract.");
    this.name = "ApiContractError";
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasExactKeys(value: Record<string, unknown>, keys: string[]): boolean {
  return (
    Object.keys(value).length === keys.length &&
    keys.every((key) => Object.prototype.hasOwnProperty.call(value, key))
  );
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

function isHealthResponse(value: unknown): value is HealthResponse {
  const checks = isRecord(value) ? value.checks : null;
  if (
    !isRecord(value) ||
    !hasExactKeys(value, ["status", "checks"]) ||
    typeof value.status !== "string" ||
    !["ok", "degraded", "down"].includes(value.status) ||
    !isRecord(checks) ||
    !hasExactKeys(checks, ["config", "snowflake", "gemma"])
  ) {
    return false;
  }
  return ["config", "snowflake", "gemma"].every((name) => {
    const check = checks[name];
    return (
      isRecord(check) &&
      hasExactKeys(check, ["ok", "message"]) &&
      typeof check.ok === "boolean" &&
      typeof check.message === "string"
    );
  });
}

export function parseHealthResponse(value: unknown): HealthResponse {
  if (!isHealthResponse(value)) {
    throw new ApiContractError();
  }
  return value;
}

function isDatasetsResponse(value: unknown): value is DatasetsResponse {
  if (
    !isRecord(value) ||
    !hasExactKeys(value, ["datasets"]) ||
    !Array.isArray(value.datasets) ||
    !value.datasets.every(
      (dataset) =>
        isRecord(dataset) &&
        hasExactKeys(dataset, ["id", "name", "description", "example_questions"]) &&
        typeof dataset.id === "string" &&
        dataset.id.length > 0 &&
        typeof dataset.name === "string" &&
        dataset.name.length > 0 &&
        typeof dataset.description === "string" &&
        isStringArray(dataset.example_questions),
    )
  ) {
    return false;
  }
  return true;
}

export function parseDatasetsResponse(value: unknown): DatasetsResponse {
  if (!isDatasetsResponse(value)) {
    throw new ApiContractError();
  }
  return value;
}

function isRowCell(value: unknown): value is RowCell {
  return (
    value === null ||
    typeof value === "string" ||
    typeof value === "boolean" ||
    (typeof value === "number" && Number.isFinite(value))
  );
}

function isRows(value: unknown, columns: unknown): value is RowCell[][] {
  return (
    isStringArray(columns) &&
    Array.isArray(value) &&
    value.every(
      (row) =>
        Array.isArray(row) &&
        row.length === columns.length &&
        row.every(isRowCell),
    )
  );
}

function isAskResponse(value: unknown): value is AskResponse {
  if (
    !isRecord(value) ||
    !hasExactKeys(value, [
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
    ]) ||
    !["answered", "clarify", "unsupported", "empty", "error"].includes(
      String(value.status),
    ) ||
    !(value.answer === null || typeof value.answer === "string") ||
    !(value.explanation === null || typeof value.explanation === "string") ||
    !isStringArray(value.assumptions) ||
    !(value.sql === null || typeof value.sql === "string") ||
    !isStringArray(value.columns) ||
    !isRows(value.rows, value.columns) ||
    !Number.isSafeInteger(value.row_count) ||
    typeof value.row_count !== "number" ||
    value.row_count < 0 ||
    value.row_count !== value.rows.length ||
    typeof value.truncated !== "boolean" ||
    !(value.query_id === null || typeof value.query_id === "string") ||
    !(
      value.clarifying_question === null ||
      typeof value.clarifying_question === "string"
    ) ||
    !Number.isSafeInteger(value.elapsed_ms) ||
    typeof value.elapsed_ms !== "number" ||
    value.elapsed_ms < 0
  ) {
    return false;
  }

  const status = value.status;
  if (
    (status === "answered" &&
      (!value.answer ||
        !value.explanation ||
        !value.sql ||
        !value.query_id)) ||
    (status === "clarify" &&
      (!value.clarifying_question ||
        value.sql !== null ||
        value.query_id !== null ||
        value.columns.length !== 0 ||
        value.rows.length !== 0)) ||
    (status === "unsupported" &&
      (!value.answer || value.sql !== null || value.query_id !== null)) ||
    (status === "empty" &&
      (!value.answer?.toLowerCase().includes("no rows") ||
        !value.sql ||
        !value.query_id ||
        value.rows.length !== 0 ||
        value.row_count !== 0)) ||
    (status === "error" && !value.answer)
  ) {
    return false;
  }
  return true;
}

export function parseAskResponse(value: unknown): AskResponse {
  if (!isAskResponse(value)) {
    throw new ApiContractError();
  }
  return value;
}

function isApiErrorBody(value: unknown): value is ApiErrorBody {
  if (
    !isRecord(value) ||
    !hasExactKeys(value, ["error"]) ||
    !isRecord(value.error) ||
    !hasExactKeys(value.error, ["code", "message"]) ||
    ![
      "VALIDATION_ERROR",
      "UNKNOWN_DATASET",
      "UPSTREAM_TIMEOUT",
      "INTERNAL_ERROR",
    ].includes(String(value.error.code)) ||
    typeof value.error.message !== "string"
  ) {
    return false;
  }
  return true;
}

export function parseApiErrorBody(value: unknown): ApiErrorBody {
  if (!isApiErrorBody(value)) {
    throw new ApiContractError();
  }
  return value;
}
