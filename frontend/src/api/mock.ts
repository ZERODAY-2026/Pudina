/**
 * src/api/mock.ts
 * Mock implementations of the DataMind API client functions.
 *
 * Activated when VITE_USE_MOCK=true.  Fixtures are imported directly from
 * docs/fixtures/ so they can never drift from the API contract.
 *
 * Fixture routing for mockAsk (matched in order, case-insensitive):
 *   "clarify"  → ask_clarify
 *   "refuse"   → ask_unsupported
 *   "empty"    → ask_empty
 *   "error"    → ask_error
 *   "large"    → ask_answered_large
 *   (default)  → ask_answered
 */

import type { AskResponse, DatasetsResponse, HealthResponse } from "../types";

// Fixtures are copied from docs/fixtures/ into this directory by
// scripts/sync-fixtures.js (run automatically via predev/prebuild hooks).
// They are the single source of truth and cannot drift from the contract
// without a rebuild triggering the sync.
import fixtureHealthOk from "./fixtures/health_ok.json";
import fixtureDatasets from "./fixtures/datasets.json";
import fixtureAskAnswered from "./fixtures/ask_answered.json";
import fixtureAskAnsweredLarge from "./fixtures/ask_answered_large.json";
import fixtureAskClarify from "./fixtures/ask_clarify.json";
import fixtureAskEmpty from "./fixtures/ask_empty.json";
import fixtureAskError from "./fixtures/ask_error.json";
import fixtureAskUnsupported from "./fixtures/ask_unsupported.json";

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/** Returns a promise that resolves after a random delay between min and max ms. */
function delay(minMs = 400, maxMs = 900): Promise<void> {
  const ms = minMs + Math.random() * (maxMs - minMs);
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Selects the appropriate ask fixture based on the question text.
 * Matching is case-insensitive and first-match wins.
 */
function selectAskFixture(question: string): AskResponse {
  const q = question.toLowerCase();
  if (q.includes("clarify")) return fixtureAskClarify as AskResponse;
  if (q.includes("refuse")) return fixtureAskUnsupported as AskResponse;
  if (q.includes("empty")) return fixtureAskEmpty as AskResponse;
  if (q.includes("error")) return fixtureAskError as AskResponse;
  if (q.includes("large")) return fixtureAskAnsweredLarge as AskResponse;
  return fixtureAskAnswered as AskResponse;
}

// ---------------------------------------------------------------------------
// Mock API functions (mirror signatures in client.ts)
// ---------------------------------------------------------------------------

/** Mock for GET /api/health */
export async function mockGetHealth(): Promise<HealthResponse> {
  await delay();
  return fixtureHealthOk as HealthResponse;
}

/** Mock for GET /api/datasets */
export async function mockGetDatasets(): Promise<DatasetsResponse> {
  await delay();
  return fixtureDatasets as DatasetsResponse;
}

/** Mock for POST /api/ask */
export async function mockAsk(question: string): Promise<AskResponse> {
  await delay();
  return selectAskFixture(question);
}
