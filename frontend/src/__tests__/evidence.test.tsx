/**
 * src/__tests__/evidence.test.tsx
 * Tests for Phase 3 Evidence Panels:
 * - CSV export & escaping
 * - Chart eligibility & SVG rendering
 * - SQL highlighting & copy button
 * - Query ID & copy button
 * - Result table sticky header, NULL display, row capping
 * - Status rendering with real contract fixtures (answered, clarify, unsupported, empty, error, large)
 * - Accessibility (jest-axe)
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { axe } from "../test/setup";
import { escapeCsvCell, exportRowsToCsv } from "../utils/csv";
import { getChartEligibility } from "../utils/chart";
import { tokenizeSql } from "../utils/sqlTokenizer";
import { AnswerCard } from "../components/AnswerCard";
import { ResultTable } from "../components/ResultTable";
import { SqlPanel } from "../components/SqlPanel";
import { QueryIdBadge } from "../components/QueryIdBadge";
import { BarChart } from "../components/BarChart";
import { AssistantMessage } from "../types";

// Import fixtures
import askAnsweredFixture from "../api/fixtures/ask_answered.json";
import askClarifyFixture from "../api/fixtures/ask_clarify.json";
import askUnsupportedFixture from "../api/fixtures/ask_unsupported.json";
import askEmptyFixture from "../api/fixtures/ask_empty.json";
import askErrorFixture from "../api/fixtures/ask_error.json";
import askAnsweredLargeFixture from "../api/fixtures/ask_answered_large.json";

describe("CSV Export and Escaping (RFC 4180)", () => {
  it("escapes cells containing commas, double quotes, and newlines", () => {
    expect(escapeCsvCell('Hello, "World"')).toBe('"Hello, ""World"""');
    expect(escapeCsvCell("Line 1\nLine 2")).toBe('"Line 1\nLine 2"');
    expect(escapeCsvCell('Row with "quote"')).toBe('"Row with ""quote"""');
  });

  it("handles null, undefined, booleans, and numbers correctly", () => {
    expect(escapeCsvCell(null)).toBe("");
    expect(escapeCsvCell(undefined as unknown as null)).toBe("");
    expect(escapeCsvCell(42)).toBe("42");
    expect(escapeCsvCell(true)).toBe("true");
  });

  it("exports table rows to CSV with proper headers and escaping", () => {
    const columns = ["Name", "Description", "Count"];
    const rows = [
      ['Alice, "CEO"', "Line1\nLine2", 10],
      ["Bob", "Standard user", null],
    ];

    const csv = exportRowsToCsv(columns, rows);
    const expected =
      'Name,Description,Count\r\n"Alice, ""CEO""","Line1\nLine2",10\r\nBob,Standard user,';
    expect(csv).toBe(expected);
  });
});

describe("Chart Eligibility Logic", () => {
  it("is eligible when exactly 1 categorical and 1 numeric column with 2 to 15 rows", () => {
    const columns = ["Category", "Total"];
    const rows = [
      ["Admin", 120],
      ["Technician", 350],
      ["Services", 80],
    ];

    const result = getChartEligibility(columns, rows);
    expect(result.eligible).toBe(true);
    expect(result.categoryColName).toBe("Category");
    expect(result.numericColName).toBe("Total");
    expect(result.data).toHaveLength(3);
    expect(result.data?.[0]).toEqual({ label: "Admin", value: 120 });
  });

  it("is eligible when numeric column is first and categorical is second", () => {
    const columns = ["Count", "Job"];
    const rows = [
      [50, "blue-collar"],
      [75, "management"],
    ];

    const result = getChartEligibility(columns, rows);
    expect(result.eligible).toBe(true);
    expect(result.categoryColName).toBe("Job");
    expect(result.numericColName).toBe("Count");
  });

  it("is not eligible if row count is less than 2 or greater than 15", () => {
    const columns = ["Cat", "Num"];
    expect(getChartEligibility(columns, [["A", 1]]).eligible).toBe(false);

    const sixteenRows = Array.from({ length: 16 }, (_, i) => [`Cat ${i}`, i]);
    expect(getChartEligibility(columns, sixteenRows).eligible).toBe(false);
  });

  it("is not eligible if more than 2 columns or both numeric/categorical", () => {
    expect(
      getChartEligibility(["A", "B", "C"], [["a", 1, 2], ["b", 3, 4]]).eligible,
    ).toBe(false);
    expect(
      getChartEligibility(["A", "B"], [[1, 2], [3, 4]]).eligible,
    ).toBe(false);
    expect(
      getChartEligibility(["A", "B"], [["a", "b"], ["c", "d"]]).eligible,
    ).toBe(false);
  });
});

describe("SQL Tokenizer & Highlighter", () => {
  it("tokenizes SQL keywords, strings, identifiers, and numbers", () => {
    const sql = 'SELECT "age", COUNT(*) FROM BANK WHERE "y" = \'yes\' LIMIT 10';
    const tokens = tokenizeSql(sql);

    const keywords = tokens.filter((t) => t.type === "keyword").map((t) => t.value.toUpperCase());
    expect(keywords).toContain("SELECT");
    expect(keywords).toContain("COUNT");
    expect(keywords).toContain("FROM");
    expect(keywords).toContain("WHERE");
    expect(keywords).toContain("LIMIT");

    const strings = tokens.filter((t) => t.type === "string");
    expect(strings[0].value).toBe("'yes'");

    const identifiers = tokens.filter((t) => t.type === "identifier");
    expect(identifiers.map((i) => i.value)).toContain('"age"');
    expect(identifiers.map((i) => i.value)).toContain('"y"');
  });
});

describe("Copy Buttons (Clipboard integration)", () => {
  beforeEach(() => {
    // Mock navigator.clipboard
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockResolvedValue(undefined),
      },
    });
  });

  it("SqlPanel copies SQL and updates button text", async () => {
    render(<SqlPanel sql="SELECT * FROM table" />);
    const copyBtn = screen.getByRole("button", { name: /copy sql/i });
    fireEvent.click(copyBtn);

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith("SELECT * FROM table");
    await waitFor(() => {
      expect(screen.getByText("Copied!")).toBeTruthy();
    });
  });

  it("QueryIdBadge copies query ID and updates button text", async () => {
    render(<QueryIdBadge queryId="snowflake-query-001" />);
    const copyBtn = screen.getByRole("button", { name: /copy/i });
    fireEvent.click(copyBtn);

    expect(navigator.clipboard.writeText).toHaveBeenCalledWith("snowflake-query-001");
    await waitFor(() => {
      expect(screen.getByText("Copied!")).toBeTruthy();
    });
  });
});

describe("ResultTable Component", () => {
  it("renders sticky header, rows, distinct NULL representation, and numeric alignment", () => {
    const columns = ["User", "Balance", "Active"];
    const rows = [
      ["Alice", 1500, true],
      ["Bob", null, false],
    ];

    render(
      <ResultTable
        columns={columns}
        rows={rows}
        rowCount={2}
        truncated={false}
      />,
    );

    // Verify row count indicator
    expect(screen.getByText(/showing 2 of 2 rows/i)).toBeTruthy();

    // Verify NULL representation
    expect(screen.getByText("NULL")).toBeTruthy();

    // Verify numeric cell formatting
    expect(screen.getByText("1,500")).toBeTruthy();

    // Verify Download CSV button is present
    expect(screen.getByRole("button", { name: /download csv/i })).toBeTruthy();
  });

  it("caps large results at 200 rows and notes performance capping", () => {
    const columns = ["ID", "Score"];
    const rows = Array.from({ length: 250 }, (_, i) => [i, i * 10]);

    render(
      <ResultTable
        columns={columns}
        rows={rows}
        rowCount={250}
        truncated={true}
      />,
    );

    expect(screen.getByText(/display capped at 200 rows for performance/i)).toBeTruthy();
    expect(screen.getByText(/truncated by server/i)).toBeTruthy();
  });

  it("toggles SVG chart on chart-eligible datasets", () => {
    const columns = ["Category", "Count"];
    const rows = [
      ["Small", 10],
      ["Medium", 20],
      ["Large", 30],
    ];

    render(
      <ResultTable
        columns={columns}
        rows={rows}
        rowCount={3}
        truncated={false}
      />,
    );

    const toggleBtn = screen.getByRole("button", { name: /chart of the rows above/i });
    expect(toggleBtn).toBeTruthy();

    // Click to show chart
    fireEvent.click(toggleBtn);
    expect(screen.getByRole("img", { name: /chart of the rows above/i })).toBeTruthy();

    // Click to hide chart
    fireEvent.click(toggleBtn);
    expect(screen.queryByRole("img", { name: /chart of the rows above/i })).toBeNull();
  });
});

describe("BarChart SVG Component", () => {
  it("renders accessible horizontal bar chart with labels and gradient", async () => {
    const data = [
      { label: "Admin", value: 100 },
      { label: "Services", value: 50 },
    ];

    const { container } = render(
      <BarChart data={data} categoryTitle="Job" numericTitle="Count" />,
    );

    expect(screen.getByRole("img", { name: /chart of the rows above/i })).toBeTruthy();
    expect(screen.getByText("Admin")).toBeTruthy();
    expect(screen.getByText("100")).toBeTruthy();

    expect(await axe(container)).toHaveNoViolations();
  });
});

describe("Contract Fixture Renders and Accessibility", () => {
  const exampleQuestions = [
    "How many clients are in the dataset?",
    "What is the average age?",
  ];

  it("renders ask_answered.json fixture and reveals evidence when All Details is clicked", async () => {
    const msg: AssistantMessage = {
      id: "msg-answered",
      role: "assistant",
      response: askAnsweredFixture as unknown as AssistantMessage["response"],
      timestamp: Date.now(),
    };

    const { container } = render(
      <AnswerCard message={msg} exampleQuestions={exampleQuestions} />,
    );

    // Answer text & status
    expect(screen.getByText(/5,289 clients subscribed to a term deposit/i)).toBeTruthy();
    expect(screen.getByText("Answered")).toBeTruthy();

    // By default, evidence details are hidden
    expect(screen.queryByText(/counted rows in bank_marketing/i)).toBeNull();

    // Toggle All Details
    const detailsToggle = screen.getByRole("button", { name: /all details/i });
    expect(detailsToggle.getAttribute("aria-expanded")).toBe("false");
    fireEvent.click(detailsToggle);
    expect(detailsToggle.getAttribute("aria-expanded")).toBe("true");

    // All evidence sections are revealed
    expect(screen.getByText(/counted rows in bank_marketing/i)).toBeTruthy();
    expect(screen.getByText("01c7cf01-0007-82d8-0002-106200026a2e")).toBeTruthy();
    expect(screen.getByText(/SELECT/)).toBeTruthy();

    expect(await axe(container)).toHaveNoViolations();
  });

  it("renders ask_clarify.json fixture quoting original question and triggers focus", async () => {
    const onFocusComposer = vi.fn();
    const msg: AssistantMessage = {
      id: "msg-clarify",
      role: "assistant",
      response: askClarifyFixture as unknown as AssistantMessage["response"],
      timestamp: Date.now(),
    };

    const { container } = render(
      <AnswerCard
        message={msg}
        userQuestion="Which is the best job?"
        exampleQuestions={exampleQuestions}
        onFocusComposer={onFocusComposer}
      />,
    );

    // Quoted original question
    expect(screen.getByText(/“Which is the best job\?”/i)).toBeTruthy();

    // Prominent clarifying question
    expect(screen.getByText(/which metric should define the best job/i)).toBeTruthy();

    // Focus composer was invoked
    expect(onFocusComposer).toHaveBeenCalled();

    expect(await axe(container)).toHaveNoViolations();
  });

  it("renders ask_unsupported.json fixture with explanation and suggestion chips", async () => {
    const onSelectQuestion = vi.fn();
    const msg: AssistantMessage = {
      id: "msg-unsupported",
      role: "assistant",
      response: askUnsupportedFixture as unknown as AssistantMessage["response"],
      timestamp: Date.now(),
    };

    const { container } = render(
      <AnswerCard
        message={msg}
        exampleQuestions={exampleQuestions}
        onSelectQuestion={onSelectQuestion}
      />,
    );

    expect(screen.getByText("Not supported")).toBeTruthy();
    expect(screen.getByText(/i can't predict future subscriptions/i)).toBeTruthy();

    // Suggestions rendered
    expect(screen.getByText("Questions I can answer:")).toBeTruthy();
    const suggestionBtn = screen.getByRole("button", { name: exampleQuestions[0] });
    fireEvent.click(suggestionBtn);
    expect(onSelectQuestion).toHaveBeenCalledWith(exampleQuestions[0]);

    expect(await axe(container)).toHaveNoViolations();
  });

  it("renders ask_empty.json fixture with SQL, query ID, and suggestion chips", async () => {
    const msg: AssistantMessage = {
      id: "msg-empty",
      role: "assistant",
      response: askEmptyFixture as unknown as AssistantMessage["response"],
      timestamp: Date.now(),
    };

    const { container } = render(
      <AnswerCard message={msg} exampleQuestions={exampleQuestions} />,
    );

    expect(screen.getByText("No results")).toBeTruthy();
    expect(screen.getByText(/no rows matched the requested criteria/i)).toBeTruthy();

    // Toggle All Details to inspect query ID and SQL
    const detailsToggle = screen.getByRole("button", { name: /all details/i });
    fireEvent.click(detailsToggle);

    expect(screen.getByText("01c7cf03-0007-82d8-0002-106200026b14")).toBeTruthy();
    expect(screen.getByText("Questions I can answer:")).toBeTruthy();

    expect(await axe(container)).toHaveNoViolations();
  });

  it("renders ask_error.json fixture with explanation and suggestion chips", async () => {
    const msg: AssistantMessage = {
      id: "msg-error",
      role: "assistant",
      response: askErrorFixture as unknown as AssistantMessage["response"],
      timestamp: Date.now(),
    };

    const { container } = render(
      <AnswerCard message={msg} exampleQuestions={exampleQuestions} />,
    );

    expect(screen.getByText("Error")).toBeTruthy();
    expect(screen.getByText(/i couldn't complete that query right now/i)).toBeTruthy();
    expect(screen.getByText("Questions I can answer:")).toBeTruthy();

    expect(await axe(container)).toHaveNoViolations();
  });

  it("renders ask_answered_large.json fixture with capped rows and download CSV", async () => {
    const msg: AssistantMessage = {
      id: "msg-large",
      role: "assistant",
      response: askAnsweredLargeFixture as unknown as AssistantMessage["response"],
      timestamp: Date.now(),
    };

    const { container } = render(
      <AnswerCard message={msg} exampleQuestions={exampleQuestions} />,
    );

    // Check answer text
    expect(screen.getByText(/showing 200 matching bank marketing contacts/i)).toBeTruthy();

    // Expand All Details panel
    const detailsToggle = screen.getByRole("button", { name: /all details/i });
    fireEvent.click(detailsToggle);

    // Verify rows table and download button
    expect(screen.getByRole("button", { name: /download csv/i })).toBeTruthy();
    expect(screen.getByText(/showing 200 of 200/i)).toBeTruthy();

    expect(await axe(container)).toHaveNoViolations();
  });

  it("reveals How I got this, SQL, Result Rows, Chart, and Query ID all at once on All Details click", async () => {
    // Eligible dataset for chart (1 categorical, 1 numeric, 3 rows)
    const chartEligibleResponse = {
      ...askAnsweredFixture,
      columns: ["JOB", "COUNT"],
      rows: [
        ["admin.", 10422],
        ["blue-collar", 9732],
        ["technician", 7597],
      ],
      row_count: 3,
      assumptions: ["Counted active contacts only"],
    };

    const msg: AssistantMessage = {
      id: "msg-chart-eligible",
      role: "assistant",
      response: chartEligibleResponse as unknown as AssistantMessage["response"],
      timestamp: Date.now(),
    };

    const { container } = render(
      <AnswerCard message={msg} exampleQuestions={exampleQuestions} />,
    );

    const toggle = screen.getByRole("button", { name: /all details/i });
    expect(toggle.getAttribute("aria-expanded")).toBe("false");

    fireEvent.click(toggle);
    expect(toggle.getAttribute("aria-expanded")).toBe("true");

    // 1. How I got this & Assumptions
    expect(screen.getByText(/counted rows in bank_marketing/i)).toBeTruthy();
    expect(screen.getByText("Counted active contacts only")).toBeTruthy();

    // 2. SQL executed
    expect(screen.getByText(/SELECT/)).toBeTruthy();

    // 3. Result rows table
    expect(screen.getByText("admin.")).toBeTruthy();
    expect(screen.getByRole("button", { name: /download csv/i })).toBeTruthy();

    // 4. Chart toggle & SVG visualization
    expect(screen.getByRole("button", { name: /chart of the rows above/i })).toBeTruthy();

    // 5. Snowflake Query ID
    expect(screen.getByText("01c7cf01-0007-82d8-0002-106200026a2e")).toBeTruthy();

    expect(await axe(container)).toHaveNoViolations();
  });
});
