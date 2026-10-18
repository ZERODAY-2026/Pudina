import { describe, expect, it, vi, afterEach } from "vitest";
import {
  ApiContractError,
  parseApiErrorBody,
  parseAskResponse,
  parseDatasetsResponse,
  parseHealthResponse,
} from "../contract";
import { getHealth } from "../client";
import askAnswered from "../fixtures/ask_answered.json";
import askAnsweredLarge from "../fixtures/ask_answered_large.json";
import askClarify from "../fixtures/ask_clarify.json";
import askEmpty from "../fixtures/ask_empty.json";
import askError from "../fixtures/ask_error.json";
import askUnsupported from "../fixtures/ask_unsupported.json";
import datasets from "../fixtures/datasets.json";
import healthDegraded from "../fixtures/health_degraded.json";
import healthOk from "../fixtures/health_ok.json";
import httpTimeoutError from "../fixtures/http_timeout_error.json";
import httpValidationError from "../fixtures/http_validation_error.json";

afterEach(() => vi.unstubAllGlobals());

describe("frontend API contract validators", () => {
  it.each([
    ["answered", askAnswered],
    ["large answered", askAnsweredLarge],
    ["clarify", askClarify],
    ["unsupported", askUnsupported],
    ["empty", askEmpty],
    ["error", askError],
  ])("accepts the %s ask fixture", (_name, fixture) => {
    expect(parseAskResponse(fixture)).toEqual(fixture);
  });

  it.each([
    ["healthy", healthOk],
    ["degraded", healthDegraded],
  ])("accepts the %s health fixture", (_name, fixture) => {
    expect(parseHealthResponse(fixture)).toEqual(fixture);
  });

  it("accepts the datasets fixture", () => {
    expect(parseDatasetsResponse(datasets)).toEqual(datasets);
  });

  it.each([httpValidationError, httpTimeoutError])(
    "accepts HTTP error fixture %j",
    (fixture) => {
      expect(parseApiErrorBody(fixture)).toEqual(fixture);
    },
  );

  it("rejects missing or unexpected ask response keys", () => {
    expect(() =>
      parseAskResponse({ ...askAnswered, unexpected: true }),
    ).toThrow(ApiContractError);
    const missingQueryId = { ...askAnswered, query_id: null };
    expect(() => parseAskResponse(missingQueryId)).toThrow(ApiContractError);
  });

  it("rejects row shapes that do not align with columns and row_count", () => {
    const invalidRows = { ...askAnswered, rows: [[1, 2]] };
    expect(() => parseAskResponse(invalidRows)).toThrow(ApiContractError);
    const invalidCount = { ...askAnswered, row_count: 2 };
    expect(() => parseAskResponse(invalidCount)).toThrow(ApiContractError);
  });

  it("rejects malformed error envelopes rather than inventing a fallback", () => {
    expect(() => parseApiErrorBody({ error: { message: "bad" } })).toThrow(
      ApiContractError,
    );
  });
});

describe("default API mode", () => {
  it("calls the real health endpoint unless mock mode is explicitly enabled", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(healthOk), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(getHealth()).resolves.toEqual(healthOk);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/health",
      expect.objectContaining({ method: "GET", signal: expect.any(AbortSignal) }),
    );
  });
});
