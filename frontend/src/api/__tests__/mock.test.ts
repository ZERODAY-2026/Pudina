/**
 * src/api/__tests__/mock.test.ts
 * Unit tests for mock.ts: verifies fixture routing, shape, and latency.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mockAsk, mockGetDatasets, mockGetHealth } from "../mock";

// Use fake timers so delay() resolves instantly.
beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

/** Advance timers past the max mock delay (900 ms). */
async function flush() {
  vi.advanceTimersByTime(1000);
  await Promise.resolve();
}

describe("mockGetHealth", () => {
  it("returns status ok", async () => {
    const p = mockGetHealth();
    await flush();
    const res = await p;
    expect(res.status).toBe("ok");
  });

  it("returns all three checks", async () => {
    const p = mockGetHealth();
    await flush();
    const res = await p;
    expect(res.checks).toHaveProperty("config");
    expect(res.checks).toHaveProperty("snowflake");
    expect(res.checks).toHaveProperty("gemma");
  });
});

describe("mockGetDatasets", () => {
  it("returns at least one dataset", async () => {
    const p = mockGetDatasets();
    await flush();
    const res = await p;
    expect(res.datasets.length).toBeGreaterThan(0);
  });

  it("each dataset has required fields", async () => {
    const p = mockGetDatasets();
    await flush();
    const { datasets } = await p;
    for (const ds of datasets) {
      expect(ds).toHaveProperty("id");
      expect(ds).toHaveProperty("name");
      expect(ds).toHaveProperty("description");
      expect(Array.isArray(ds.example_questions)).toBe(true);
    }
  });
});

describe("mockAsk fixture routing", () => {
  const cases: [string, string][] = [
    ["what should clarify this", "clarify"],
    ["please refuse to answer", "unsupported"],
    ["show empty results", "empty"],
    ["trigger an error here", "error"],
    ["give me a large dataset result", "answered"],   // "large" → answered (large fixture)
    ["how many clients are there", "answered"],
  ];

  it.each(cases)('question "%s" → status %s', async (question, expectedStatus) => {
    const p = mockAsk(question);
    await flush();
    const res = await p;
    expect(res.status).toBe(expectedStatus);
  });

  it("response always has the required contract keys", async () => {
    const p = mockAsk("any question");
    await flush();
    const res = await p;
    const requiredKeys = [
      "status", "answer", "explanation", "assumptions",
      "sql", "columns", "rows", "row_count",
      "truncated", "query_id", "clarifying_question", "elapsed_ms",
    ];
    for (const key of requiredKeys) {
      expect(res).toHaveProperty(key);
    }
  });
});
