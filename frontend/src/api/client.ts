/**
 * src/api/client.ts
 * Typed HTTP client for the DataMind API.
 *
 * In MOCK MODE (VITE_USE_MOCK=true) all calls are routed through mock.ts.
 * Otherwise requests go to /api/* (proxied to VITE_API_BASE or http://localhost:8000).
 *
 * No API URLs are hard-coded in components; everything goes through this module.
 */

import {
  ApiError,
  type AskRequest,
  type AskResponse,
  type DatasetsResponse,
  type HealthResponse,
  type HistoryMessage,
} from "../types";
import {
  ApiContractError,
  parseApiErrorBody,
  parseAskResponse,
  parseDatasetsResponse,
  parseHealthResponse,
} from "./contract";
import { mockAsk, mockGetDatasets, mockGetHealth } from "./mock";

const USE_MOCK = import.meta.env.VITE_USE_MOCK === "true";

/** Default per-request timeout (ms). */
const DEFAULT_TIMEOUT_MS = 30_000;

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/**
 * Combines the caller's AbortSignal with an optional timeout signal so every
 * request respects both the caller's cancellation and a hard deadline.
 */
function makeSignal(
  callerSignal?: AbortSignal,
  timeoutMs = DEFAULT_TIMEOUT_MS,
): { signal: AbortSignal; clearTimeout: () => void } {
  const ac = new AbortController();

  const timer = setTimeout(() => ac.abort(new DOMException("Request timed out", "TimeoutError")), timeoutMs);

  if (callerSignal) {
    if (callerSignal.aborted) {
      ac.abort(callerSignal.reason);
    } else {
      callerSignal.addEventListener("abort", () => ac.abort(callerSignal.reason), {
        once: true,
      });
    }
  }

  return { signal: ac.signal, clearTimeout: () => clearTimeout(timer) };
}

async function parseErrorBody(res: Response): Promise<ApiError> {
  try {
    const body = parseApiErrorBody(await res.json());
    return new ApiError(body.error.code, body.error.message, res.status);
  } catch {
    throw new ApiContractError();
  }
}

async function fetchJson(
  path: string,
  init: RequestInit,
  timeoutMs?: number,
): Promise<unknown> {
  const { signal, clearTimeout } = makeSignal(
    init.signal as AbortSignal | undefined,
    timeoutMs,
  );

  try {
    const res = await fetch(path, { ...init, signal });
    if (!res.ok) throw await parseErrorBody(res);
    return await res.json();
  } finally {
    clearTimeout();
  }
}

// ---------------------------------------------------------------------------
// Public API functions
// ---------------------------------------------------------------------------

/**
 * GET /api/health
 * Returns the overall system health status and per-service checks.
 */
export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  if (USE_MOCK) return parseHealthResponse(await mockGetHealth());
  return parseHealthResponse(
    await fetchJson("/api/health", { method: "GET", signal }),
  );
}

/**
 * GET /api/datasets
 * Returns the list of available datasets with example questions.
 */
export async function getDatasets(
  signal?: AbortSignal,
): Promise<DatasetsResponse> {
  if (USE_MOCK) return parseDatasetsResponse(await mockGetDatasets());
  return parseDatasetsResponse(
    await fetchJson("/api/datasets", { method: "GET", signal }),
  );
}

/**
 * POST /api/ask
 * Submits a natural-language question and returns a structured answer.
 *
 * @param question  The user's question (1–1000 characters).
 * @param dataset   Dataset ID from GET /api/datasets.
 * @param history   Prior conversation turns (at most 10 entries).
 * @param signal    Optional AbortSignal for cancellation.
 */
export async function ask(
  question: string,
  dataset: string,
  history: HistoryMessage[] = [],
  signal?: AbortSignal,
): Promise<AskResponse> {
  if (USE_MOCK) return parseAskResponse(await mockAsk(question));

  const body: AskRequest = { question, dataset, history };
  return parseAskResponse(await fetchJson(
    "/api/ask",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      signal,
    },
  ));
}
