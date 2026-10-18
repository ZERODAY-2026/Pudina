/**
 * src/App.test.tsx
 * Smoke + accessibility test for the app shell and full page integration.
 */
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, waitFor, act, fireEvent } from "@testing-library/react";
import { axe } from "./test/setup";
import { ask } from "./api/client";
import App from "./App";

const { mockDatasets } = vi.hoisted(() => ({
  mockDatasets: [
    {
      id: "bank-marketing",
      name: "UCI Bank Marketing",
      description: "Portuguese bank campaign contacts and term-deposit subscription outcomes.",
      example_questions: [
        "How many clients are in the dataset?",
        "How many clients subscribed to a term deposit?",
      ],
    },
    {
      id: "tpc-h-sf1",
      name: "TPC-H SF1",
      description: "TPC-H sample records.",
      example_questions: ["How many customer records are in the sample?"],
    },
  ],
}));

// Stub the API client so tests never make real network requests.
vi.mock("./api/client", () => ({
  getHealth: vi.fn().mockResolvedValue({
    status: "ok",
    checks: {
      config: { ok: true, message: "ok" },
      snowflake: { ok: true, message: "ok" },
      gemma: { ok: true, message: "ok" },
    },
  }),
  getDatasets: vi.fn().mockResolvedValue({
    datasets: mockDatasets,
  }),
  ask: vi.fn().mockResolvedValue({
    status: "answered",
    answer: "There are 45,211 clients in the dataset.",
    explanation: "Counted rows in clients table.",
    assumptions: [],
    sql: "SELECT COUNT(*) FROM clients",
    columns: ["COUNT"],
    rows: [[45211]],
    row_count: 1,
    truncated: false,
    query_id: "q-123",
    clarifying_question: null,
    elapsed_ms: 320,
  }),
}));

beforeEach(() => localStorage.clear());
afterEach(() => vi.clearAllMocks());

/** Renders App and waits for the initial async fetches to settle. */
async function renderApp() {
  let result!: ReturnType<typeof render>;
  await act(async () => {
    result = render(<App />);
    await Promise.resolve();
  });
  return result;
}

describe("App shell", () => {
  it("renders header with DataMind title", async () => {
    await renderApp();
    expect(screen.getByRole("banner")).toBeTruthy();
    expect(screen.getByText("DataMind")).toBeTruthy();
  });

  it("renders sidebar landmark", async () => {
    await renderApp();
    expect(screen.getByRole("complementary")).toBeTruthy();
  });

  it("renders main landmark with heading", async () => {
    await renderApp();
    fireEvent.change(await screen.findByLabelText("Select dataset"), {
      target: { value: "bank-marketing" },
    });
    expect(screen.getByRole("main")).toBeTruthy();
    expect(
      screen.getByRole("heading", { name: /ask your data anything/i }),
    ).toBeTruthy();
  });

  it("transitions health status to ok after fetch resolves", async () => {
    await renderApp();
    await waitFor(() =>
      expect(
        screen.getByLabelText(/system status: all systems operational/i),
      ).toBeTruthy(),
    );
  });

  it("has no accessibility violations", async () => {
    const { container } = await renderApp();
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("keeps chats with their dataset and clears a selected example from the composer", async () => {
    localStorage.clear();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    await renderApp();

    const select = await screen.findByLabelText("Select dataset");
    fireEvent.change(select, { target: { value: "bank-marketing" } });
    const bankQuestion = screen
      .getAllByRole("button", { name: "How many clients are in the dataset?" })
      .at(-1);
    fireEvent.click(bankQuestion!);
    await screen.findByText("There are 45,211 clients in the dataset.");
    expect((screen.getByLabelText("Ask a question") as HTMLTextAreaElement).value).toBe("");
    await waitFor(() => {
      expect(
        screen.queryByRole("status", { name: "Generating answer" }),
      ).toBeNull();
    });

    fireEvent.change(select, { target: { value: "tpc-h-sf1" } });
    await screen.findByText("TPC-H sample records.");
    expect(
      screen.getByRole("button", {
        name: /How many clients are in the dataset\?.*UCI Bank Marketing/,
      }),
    ).toBeTruthy();

    const tpchQuestion = screen
      .getAllByRole("button", {
        name: "How many customer records are in the sample?",
      })
      .at(-1);
    fireEvent.click(tpchQuestion!);
    await waitFor(() => {
      expect(vi.mocked(ask).mock.calls).toHaveLength(2);
    });
    expect(vi.mocked(ask).mock.calls[1]?.[1]).toBe("tpc-h-sf1");
    await waitFor(() => {
      expect(
        screen.getAllByText("There are 45,211 clients in the dataset."),
      ).toHaveLength(1);
    });
    expect((screen.getByLabelText("Ask a question") as HTMLTextAreaElement).value).toBe("");
    expect(
      screen.getByRole("button", {
        name: /How many customer records are in the sampl.*TPC-H SF1/,
      }),
    ).toBeTruthy();
    confirmSpy.mockRestore();
  });
});
