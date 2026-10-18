/**
 * src/__tests__/f5_features.test.tsx
 * Comprehensive unit and integration tests for F5 UI/UX Overhaul:
 * - Persistent Hamburger navigation drawer
 * - Multi-chat session management (+ New Chat, switching, auto-titling, deleting)
 * - Dataset access and backend loading guidance
 * - Unified "All Details" evidence container in AnswerCard
 * - Full jest-axe accessibility on the new layout & components
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { axe } from "../test/setup";
import App from "../App";
import { AnswerCard } from "../components/AnswerCard";
import { DataLoader } from "../components/DataLoader";
import { ChatSessionsList } from "../components/ChatSessionsList";
import { AssistantMessage, ChatSession } from "../types";

import askAnsweredFixture from "../api/fixtures/ask_answered.json";

const { mockDataset, mockSecondDataset } = vi.hoisted(() => ({
  mockDataset: {
    id: "bank-marketing",
    name: "UCI Bank Marketing",
    description: "Portuguese bank campaign data",
    example_questions: [
      "How many clients are in the dataset?",
      "What is the average age?",
    ],
  },
  mockSecondDataset: {
    id: "ecommerce-sales",
    name: "E-Commerce Sales",
    description: "Retail transactions and revenue",
    example_questions: ["What is the top item?"],
  },
}));

vi.mock("../api/client", () => ({
  getHealth: vi.fn().mockResolvedValue({
    status: "ok",
    checks: {
      config: { ok: true, message: "Valid config" },
      snowflake: { ok: true, message: "Connected to warehouse" },
      gemma: { ok: true, message: "Model ready" },
    },
  }),
  getDatasets: vi.fn().mockResolvedValue({
    datasets: [mockDataset, mockSecondDataset],
  }),
  ask: vi.fn().mockResolvedValue({
    status: "answered",
    answer: "There are 45,211 clients in the dataset.",
    explanation: "Counted rows in clients table.",
    assumptions: ["Counted active contacts only"],
    sql: "SELECT COUNT(*) FROM clients",
    columns: ["JOB", "COUNT"],
    rows: [
      ["admin.", 10422],
      ["blue-collar", 9732],
      ["technician", 7597],
    ],
    row_count: 3,
    truncated: false,
    query_id: "q-snowflake-555",
    clarifying_question: null,
    elapsed_ms: 280,
  }),
}));

describe("F5: Hamburger Menu & Drawer Navigation", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
  });

  it("toggles the sidebar drawer when Hamburger button is clicked", async () => {
    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole("banner")).toBeTruthy();
    });

    const menuBtn = screen.getByRole("button", { name: /open sidebar menu/i });
    expect(menuBtn.getAttribute("aria-expanded")).toBe("false");

    // Click Hamburger to open drawer
    fireEvent.click(menuBtn);
    expect(menuBtn.getAttribute("aria-expanded")).toBe("true");

    // Drawer should have open class and close button
    const closeBtn = screen.getByRole("button", { name: /close sidebar panel/i });
    expect(closeBtn).toBeTruthy();

    // Click close button
    fireEvent.click(closeBtn);
    expect(menuBtn.getAttribute("aria-expanded")).toBe("false");
  });

  it("closes drawer on Escape key press", async () => {
    render(<App />);

    const menuBtn = await screen.findByRole("button", { name: /open sidebar menu/i });
    fireEvent.click(menuBtn);
    expect(menuBtn.getAttribute("aria-expanded")).toBe("true");

    fireEvent.keyDown(window, { key: "Escape" });
    expect(menuBtn.getAttribute("aria-expanded")).toBe("false");
  });
});

describe("F5: Multi-Chat History Sessions", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("allows creating new chat sessions and switching between them", () => {
    const onSelect = vi.fn();
    const onDelete = vi.fn();
    const onNew = vi.fn();

    const sampleSessions: ChatSession[] = [
      {
        id: "session-1",
        title: "How many total deposits?",
        datasetId: "bank-marketing",
        datasetName: "UCI Bank Marketing",
        createdAt: Date.now() - 60000,
        updatedAt: Date.now() - 60000,
        messages: [],
      },
      {
        id: "session-2",
        title: "Top revenue items",
        datasetId: "ecommerce-sales",
        datasetName: "E-Commerce Sales",
        createdAt: Date.now(),
        updatedAt: Date.now(),
        messages: [],
      },
    ];

    render(
      <ChatSessionsList
        sessions={sampleSessions}
        activeSessionId="session-1"
        onSelectSession={onSelect}
        onDeleteSession={onDelete}
        onNewChat={onNew}
      />,
    );

    // Shows session titles
    expect(screen.getByText("How many total deposits?")).toBeTruthy();
    expect(screen.getByText("Top revenue items")).toBeTruthy();

    // Click second session to switch
    fireEvent.click(screen.getByText("Top revenue items"));
    expect(onSelect).toHaveBeenCalledWith("session-2");

    // Click delete on first session
    const deleteBtns = screen.getAllByRole("button", { name: /delete chat/i });
    fireEvent.click(deleteBtns[0]);
    expect(onDelete).toHaveBeenCalledWith("session-1");

    // Click "+ New Chat" button
    const newChatBtn = screen.getByRole("button", { name: /start a new chat|\+ new chat/i });
    fireEvent.click(newChatBtn);
    expect(onNew).toHaveBeenCalled();
  });
});

describe("F5: Data & Snowflake Loader Flow", () => {
  it("explains live Snowflake reads without reporting a fake browser upload", async () => {
    const { container } = render(
      <DataLoader
        selectedDataset={mockDataset}
      />,
    );

    expect(screen.getByText(/TABLE: BANK-MARKETING/i)).toBeTruthy();
    expect(screen.getByText(/Questions run against the selected Snowflake dataset in real time/i)).toBeTruthy();
    expect(screen.getByText(/Configure datasets with their schema in/i)).toBeTruthy();
    expect(screen.queryByRole("button", { name: /load \/ sync/i })).toBeNull();
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe("F5: Unified All Details in AnswerCard", () => {
  it("shows only status badge and answer initially, and expands all evidence on single click", async () => {
    const msg: AssistantMessage = {
      id: "msg-unified-test",
      role: "assistant",
      timestamp: Date.now(),
      response: {
        ...askAnsweredFixture,
        explanation: "Aggregated sum and count over database cluster.",
        assumptions: ["Filter excludes deleted accounts"],
        sql: "SELECT category, count(*) FROM data GROUP BY 1",
        columns: ["CATEGORY", "COUNT"],
        rows: [
          ["Alpha", 120],
          ["Beta", 240],
        ],
        row_count: 2,
        query_id: "q-unified-987",
      } as unknown as AssistantMessage["response"],
    };

    const { container } = render(
      <AnswerCard
        message={msg}
        exampleQuestions={["Example 1?"]}
      />,
    );

    // 1. Initial State: Answer text visible
    expect(screen.getByText(/5,289 clients subscribed to a term deposit/i)).toBeTruthy();

    // Evidence components are hidden
    expect(screen.queryByText(/aggregated sum and count/i)).toBeNull();
    expect(screen.queryByText("SELECT")).toBeNull();
    expect(screen.queryByText("q-unified-987")).toBeNull();

    // 2. Click "All Details" button
    const detailsToggle = screen.getByRole("button", { name: /all details/i });
    expect(detailsToggle.getAttribute("aria-expanded")).toBe("false");

    fireEvent.click(detailsToggle);
    expect(detailsToggle.getAttribute("aria-expanded")).toBe("true");

    // 3. All evidence sections revealed simultaneously
    expect(screen.getByText(/aggregated sum and count/i)).toBeTruthy();
    expect(screen.getByText("Filter excludes deleted accounts")).toBeTruthy();
    expect(screen.getByText("SELECT")).toBeTruthy();
    expect(screen.getByText("category")).toBeTruthy();
    expect(screen.getByText("Alpha")).toBeTruthy();
    expect(screen.getByText("q-unified-987")).toBeTruthy();

    // Check accessibility of the entire expanded AnswerCard
    expect(await axe(container)).toHaveNoViolations();
  });
});
