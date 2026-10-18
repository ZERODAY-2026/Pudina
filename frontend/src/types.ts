/**
 * src/types.ts
 * TypeScript types that mirror docs/api_contract.md exactly.
 * Do not change shapes here without updating the contract and fixtures first.
 */

// ---------------------------------------------------------------------------
// GET /api/health
// ---------------------------------------------------------------------------

export interface HealthCheck {
  ok: boolean;
  message: string;
}

export interface HealthChecks {
  config: HealthCheck;
  snowflake: HealthCheck;
  gemma: HealthCheck;
}

/** "ok" | "degraded" | "down" */
export type HealthStatus = "ok" | "degraded" | "down";

export interface HealthResponse {
  status: HealthStatus;
  checks: HealthChecks;
}

// ---------------------------------------------------------------------------
// GET /api/datasets
// ---------------------------------------------------------------------------

export interface Dataset {
  id: string;
  name: string;
  description: string;
  example_questions: string[];
}

export interface DatasetsResponse {
  datasets: Dataset[];
}

// ---------------------------------------------------------------------------
// POST /api/ask
// ---------------------------------------------------------------------------

export type MessageRole = "user" | "assistant";

export interface HistoryMessage {
  role: MessageRole;
  content: string;
}

export interface AskRequest {
  question: string;
  dataset: string;
  history: HistoryMessage[];
}

/** Application-level status returned inside HTTP 200 responses. */
export type AskStatus =
  | "answered"
  | "clarify"
  | "unsupported"
  | "empty"
  | "error";

/** Row values are JSON-compatible primitives. */
export type RowCell = string | number | boolean | null;

export interface AskResponse {
  status: AskStatus;
  answer: string | null;
  explanation: string | null;
  assumptions: string[];
  sql: string | null;
  columns: string[];
  rows: RowCell[][];
  row_count: number;
  truncated: boolean;
  query_id: string | null;
  clarifying_question: string | null;
  elapsed_ms: number;
}

// ---------------------------------------------------------------------------
// HTTP-level errors  (distinct from AskResponse with status "error")
// ---------------------------------------------------------------------------

export type ApiErrorCode =
  | "VALIDATION_ERROR"
  | "UNKNOWN_DATASET"
  | "UPSTREAM_TIMEOUT"
  | "INTERNAL_ERROR";

export interface ApiErrorBody {
  error: {
    code: ApiErrorCode;
    message: string;
  };
}

/** Thrown by the API client on non-2xx responses. */
export class ApiError extends Error {
  constructor(
    public readonly code: ApiErrorCode,
    message: string,
    public readonly httpStatus: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

// ---------------------------------------------------------------------------
// Chat UI types (not part of the API contract)
// ---------------------------------------------------------------------------

export interface UserMessage {
  id: string;
  role: "user";
  question: string;
  timestamp: number;
}

export interface AssistantMessage {
  id: string;
  role: "assistant";
  response: AskResponse;
  timestamp: number;
}

/** Discriminated union of chat message variants. */
export type ChatMessage = UserMessage | AssistantMessage;

/** Error recorded when a send/retry attempt fails (distinct from AskResponse status "error"). */
export interface ChatError {
  /** User-facing message. */
  message: string;
  /** API error code, if the error came from the backend. */
  code?: ApiErrorCode;
  /** Whether the user can meaningfully retry the request. */
  canRetry: boolean;
  /** The original question that triggered the error, for retry. */
  lastQuestion: string;
  /** The dataset ID used when the error occurred, for retry. */
  lastDatasetId: string;
}

/** Stored multi-chat session */
export interface ChatSession {
  id: string;
  title: string;
  datasetId: string;
  datasetName: string;
  createdAt: number;
  updatedAt: number;
  messages: ChatMessage[];
}
