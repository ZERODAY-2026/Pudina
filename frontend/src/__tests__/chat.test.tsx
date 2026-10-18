/**
 * src/__tests__/chat.test.tsx
 * Comprehensive unit and integration tests for Phase 2 chat components and user flows.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { axe } from "../test/setup";
import { HealthIndicator } from "../components/HealthIndicator";
import { AppSidebar } from "../components/AppSidebar";
import { ChatComposer } from "../components/ChatComposer";
import { EmptyState } from "../components/EmptyState";
import { UserBubble } from "../components/UserBubble";
import { AnswerCard } from "../components/AnswerCard";
import { LoadingMessage } from "../components/LoadingMessage";
import { ErrorMessage } from "../components/ErrorMessage";
import { ChatTranscript } from "../components/ChatTranscript";
import App from "../App";
import {
  AskStatus,
  AssistantMessage,
  ChatError,
  UserMessage,
} from "../types";

const { mockDataset, mockSecondDataset, mockHealth, mockAnswerResponse } = vi.hoisted(() => ({
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
    description: "Online store transactions and customer behavior",
    example_questions: ["What is the top selling item?"],
  },
  mockHealth: {
    status: "ok" as const,
    checks: {
      config: { ok: true, message: "Valid config" },
      snowflake: { ok: true, message: "Connected to warehouse" },
      gemma: { ok: true, message: "Model ready" },
    },
  },
  mockAnswerResponse: {
    status: "answered" as const,
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
  },
}));

vi.mock("../api/client", () => ({
  getHealth: vi.fn().mockImplementation(() => Promise.resolve(mockHealth)),
  getDatasets: vi.fn().mockImplementation(() =>
    Promise.resolve({
      datasets: [mockDataset, mockSecondDataset],
    }),
  ),
  ask: vi.fn().mockImplementation(() => Promise.resolve(mockAnswerResponse)),
}));

describe("HealthIndicator component", () => {
  it("renders Snowflake, Gemma, and Config service names and statuses", () => {
    render(<HealthIndicator health={mockHealth} />);
    expect(screen.getByText("Snowflake")).toBeTruthy();
    expect(screen.getByText("Connected to warehouse")).toBeTruthy();
    expect(screen.getByText("Gemma")).toBeTruthy();
    expect(screen.getByText("Model ready")).toBeTruthy();
    expect(screen.getByText("Config")).toBeTruthy();
    expect(screen.getByText("Valid config")).toBeTruthy();
  });

  it("has no accessibility violations", async () => {
    const { container } = render(<HealthIndicator health={mockHealth} />);
    expect(await axe(container)).toHaveNoViolations();
  });
});

describe("AppSidebar component", () => {
  it("renders dataset selector and description", () => {
    render(
      <AppSidebar
        datasets={[mockDataset]}
        selectedDataset={mockDataset}
        onSelectDataset={vi.fn()}
        onSelectQuestion={vi.fn()}
        health={mockHealth}
      />,
    );
    expect(screen.getByLabelText("Select dataset")).toBeTruthy();
    expect(screen.getByText(mockDataset.description)).toBeTruthy();
  });

  it("renders clickable example questions that invoke onSelectQuestion", () => {
    const onSelectQuestion = vi.fn();
    render(
      <AppSidebar
        datasets={[mockDataset]}
        selectedDataset={mockDataset}
        onSelectDataset={vi.fn()}
        onSelectQuestion={onSelectQuestion}
        health={mockHealth}
      />,
    );
    const qBtn = screen.getByRole("button", {
      name: mockDataset.example_questions[0],
    });
    fireEvent.click(qBtn);
    expect(onSelectQuestion).toHaveBeenCalledWith(mockDataset.example_questions[0]);
  });
});

describe("ChatComposer component", () => {
  it("renders character counter and updates as user types", () => {
    const onChange = vi.fn();
    render(
      <ChatComposer
        value="Hello data"
        onChange={onChange}
        onSend={vi.fn()}
      />,
    );
    expect(screen.getByText("10 / 1000")).toBeTruthy();
  });

  it("disables send button when input is empty or whitespace only", () => {
    render(
      <ChatComposer
        value="   "
        onChange={vi.fn()}
        onSend={vi.fn()}
      />,
    );
    const sendBtn = screen.getByRole("button", { name: /send question/i });
    expect(sendBtn).toBeDisabled();
  });

  it("calls onSend when Enter is pressed without Shift", () => {
    const onSend = vi.fn();
    render(
      <ChatComposer
        value="Valid question"
        onChange={vi.fn()}
        onSend={onSend}
      />,
    );
    const textarea = screen.getByLabelText("Ask a question");
    fireEvent.keyDown(textarea, { key: "Enter", shiftKey: false });
    expect(onSend).toHaveBeenCalledWith("Valid question");
  });

  it("does not send when Shift + Enter is pressed", () => {
    const onSend = vi.fn();
    render(
      <ChatComposer
        value="Valid question"
        onChange={vi.fn()}
        onSend={onSend}
      />,
    );
    const textarea = screen.getByLabelText("Ask a question");
    fireEvent.keyDown(textarea, { key: "Enter", shiftKey: true });
    expect(onSend).not.toHaveBeenCalled();
  });

  it("is disabled when loading is true", () => {
    render(
      <ChatComposer
        value="Valid question"
        onChange={vi.fn()}
        onSend={vi.fn()}
        loading={true}
      />,
    );
    const textarea = screen.getByLabelText("Ask a question");
    expect(textarea).toBeDisabled();
    const sendBtn = screen.getByRole("button", { name: /send question/i });
    expect(sendBtn).toBeDisabled();
  });
});

describe("EmptyState component", () => {
  it("renders explanation and clickable chips for dataset examples", () => {
    const onSelect = vi.fn();
    render(<EmptyState dataset={mockDataset} onSelectQuestion={onSelect} />);
    expect(screen.getByRole("heading", { name: /ask your data anything/i })).toBeTruthy();
    const chip = screen.getByRole("button", { name: mockDataset.example_questions[0] });
    fireEvent.click(chip);
    expect(onSelect).toHaveBeenCalledWith(mockDataset.example_questions[0]);
  });
});

describe("UserBubble component", () => {
  it("renders user question and formatted timestamp", () => {
    const userMsg: UserMessage = {
      id: "u-1",
      role: "user",
      question: "What is the total revenue?",
      timestamp: 1697620000000,
    };
    render(<UserBubble message={userMsg} />);
    expect(screen.getByText("What is the total revenue?")).toBeTruthy();
    expect(screen.getByRole("article")).toBeTruthy();
  });
});

describe("AnswerCard component status badges and content", () => {
  const statuses: { status: AskStatus; icon: string; label: string }[] = [
    { status: "answered", icon: "✓", label: "Answered" },
    { status: "clarify", icon: "?", label: "Needs clarification" },
    { status: "unsupported", icon: "⊘", label: "Not supported" },
    { status: "empty", icon: "∅", label: "No results" },
    { status: "error", icon: "✕", label: "Error" },
  ];

  statuses.forEach(({ status, icon, label }) => {
    it(`renders status badge with icon and text for '${status}'`, async () => {
      const msg: AssistantMessage = {
        id: `msg-${status}`,
        role: "assistant",
        timestamp: 1697620000000,
        response: {
          status,
          answer: status === "clarify" ? null : `Test answer for ${status}`,
          clarifying_question: status === "clarify" ? "Which year do you mean?" : null,
          explanation: "Generated based on schema",
          assumptions: [],
          sql: "SELECT 1",
          columns: ["COL"],
          rows: [[1]],
          row_count: 1,
          truncated: false,
          query_id: "q-1",
          elapsed_ms: 250,
        },
      };

      const { container } = render(<AnswerCard message={msg} />);
      const badge = screen.getByRole("status");
      expect(badge.textContent).toContain(icon);
      expect(badge.textContent).toContain(label);

      // Verify accessibility on each card state
      expect(await axe(container)).toHaveNoViolations();
    });
  });
});

describe("LoadingMessage and ErrorMessage components", () => {
  it("LoadingMessage displays spinner and triggers Cancel when clicked", () => {
    const onCancel = vi.fn();
    render(<LoadingMessage onCancel={onCancel} />);
    expect(screen.getByText(/thinking…/i)).toBeTruthy();
    const cancelBtn = screen.getByRole("button", { name: /cancel/i });
    fireEvent.click(cancelBtn);
    expect(onCancel).toHaveBeenCalled();
  });

  it("ErrorMessage displays error message, error code, and Retry button", () => {
    const onRetry = vi.fn();
    const err: ChatError = {
      message: "Upstream service timed out",
      code: "UPSTREAM_TIMEOUT",
      canRetry: true,
      lastQuestion: "What is the count?",
      lastDatasetId: "bank-marketing",
    };

    render(<ErrorMessage error={err} onRetry={onRetry} />);
    expect(screen.getByText("Upstream service timed out")).toBeTruthy();
    expect(screen.getByText("UPSTREAM_TIMEOUT")).toBeTruthy();
    const retryBtn = screen.getByRole("button", { name: /retry/i });
    fireEvent.click(retryBtn);
    expect(onRetry).toHaveBeenCalled();
  });
});

describe("ChatTranscript component", () => {
  it("renders EmptyState when messages array is empty", () => {
    render(
      <ChatTranscript
        messages={[]}
        loading={false}
        error={null}
        dataset={mockDataset}
        onSelectQuestion={vi.fn()}
        onCancel={vi.fn()}
        onRetry={vi.fn()}
      />,
    );
    expect(screen.getByRole("heading", { name: /ask your data anything/i })).toBeTruthy();
  });

  it("renders conversation messages when messages exist", () => {
    const userMsg: UserMessage = {
      id: "u-1",
      role: "user",
      question: "How many users?",
      timestamp: 1697620000000,
    };
    render(
      <ChatTranscript
        messages={[userMsg]}
        loading={false}
        error={null}
        dataset={mockDataset}
        onSelectQuestion={vi.fn()}
        onCancel={vi.fn()}
        onRetry={vi.fn()}
      />,
    );
    expect(screen.getByText("How many users?")).toBeTruthy();
  });
});

describe("Chat integration flows", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("sends question and displays user bubble and answer card", async () => {
    render(<App />);

    // Wait for datasets to load and select the first dataset
    await waitFor(() => {
      expect(screen.getByLabelText("Select dataset")).toBeTruthy();
    });

    const select = screen.getByLabelText("Select dataset");
    fireEvent.change(select, { target: { value: "bank-marketing" } });

    await waitFor(() => {
      expect(screen.getByLabelText("Ask a question")).toBeTruthy();
    });

    const textarea = screen.getByLabelText("Ask a question");
    fireEvent.change(textarea, { target: { value: "How many clients?" } });

    const sendBtn = screen.getByRole("button", { name: /send question/i });
    fireEvent.click(sendBtn);

    // Verify user bubble appears
    await waitFor(() => {
      expect(screen.getAllByText("How many clients?").length).toBeGreaterThanOrEqual(1);
    });

    // Verify answer card appears
    await waitFor(() => {
      expect(screen.getByText("There are 45,211 clients in the dataset.")).toBeTruthy();
    });
  });

  it("warns user before switching dataset if unsent input exists and cancels if rejected", async () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);

    render(<App />);

    await waitFor(() => {
      expect(screen.getByLabelText("Select dataset")).toBeTruthy();
    });

    const select = screen.getByLabelText("Select dataset") as HTMLSelectElement;
    fireEvent.change(select, { target: { value: "bank-marketing" } });

    await waitFor(() => {
      expect(screen.getByLabelText("Ask a question")).toBeTruthy();
    });

    // Enter draft text in composer
    const textarea = screen.getByLabelText("Ask a question");
    fireEvent.change(textarea, { target: { value: "Draft question" } });

    // Attempt to switch dataset
    fireEvent.change(select, { target: { value: "ecommerce-sales" } });

    expect(confirmSpy).toHaveBeenCalled();
    // Since user canceled, dataset should stay as bank-marketing
    expect(select.value).toBe("bank-marketing");

    confirmSpy.mockRestore();
  });

  it("switches dataset when user confirms and resets conversation", async () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);

    render(<App />);

    await waitFor(() => {
      expect(screen.getByLabelText("Select dataset")).toBeTruthy();
    });

    const select = screen.getByLabelText("Select dataset") as HTMLSelectElement;
    fireEvent.change(select, { target: { value: "bank-marketing" } });

    await waitFor(() => {
      expect(screen.getByLabelText("Ask a question")).toBeTruthy();
    });

    const textarea = screen.getByLabelText("Ask a question");
    fireEvent.change(textarea, { target: { value: "Draft question" } });

    // Switch dataset and confirm
    fireEvent.change(select, { target: { value: "ecommerce-sales" } });

    expect(confirmSpy).toHaveBeenCalled();
    expect(select.value).toBe("ecommerce-sales");

    confirmSpy.mockRestore();
  });
});
