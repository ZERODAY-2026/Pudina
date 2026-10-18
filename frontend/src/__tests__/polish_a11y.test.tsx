/**
 * src/__tests__/polish_a11y.test.tsx
 * Tests for Phase 4: Polish, Responsiveness, and Accessibility:
 * - Skip to main content link
 * - Screen reader live announcement region
 * - Mobile drawer open/close/backdrop/Escape key interactions
 * - Focus management and restoration
 * - Semantic landmarks
 * - Full page and card accessibility (jest-axe)
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { axe } from "../test/setup";
import App from "../App";

const { mockDataset, mockHealth, mockAnswer } = vi.hoisted(() => ({
  mockDataset: {
    id: "bank-marketing",
    name: "UCI Bank Marketing",
    description: "Portuguese bank campaign data",
    example_questions: [
      "How many clients are in the dataset?",
      "What is the average age?",
    ],
  },
  mockHealth: {
    status: "ok" as const,
    checks: {
      config: { ok: true, message: "Valid config" },
      snowflake: { ok: true, message: "Connected to warehouse" },
      gemma: { ok: true, message: "Model ready" },
    },
  },
  mockAnswer: {
    status: "answered" as const,
    answer: "There are 45,211 clients in the dataset.",
    explanation: "Counted rows in clients table.",
    assumptions: ["Assumes distinct contact records"],
    sql: "SELECT COUNT(*) FROM clients",
    columns: ["COUNT"],
    rows: [[45211]],
    row_count: 1,
    truncated: false,
    query_id: "q-123",
    clarifying_question: null,
    elapsed_ms: 120,
  },
}));

vi.mock("../api/client", () => ({
  getHealth: vi.fn().mockImplementation(() => Promise.resolve(mockHealth)),
  getDatasets: vi.fn().mockImplementation(() =>
    Promise.resolve({
      datasets: [mockDataset],
    }),
  ),
  ask: vi.fn().mockImplementation(() => Promise.resolve(mockAnswer)),
}));

/** Renders App and flushes async mount effects without act() warnings */
async function renderApp() {
  let result!: ReturnType<typeof render>;
  await act(async () => {
    result = render(<App />);
    await Promise.resolve();
  });
  return result;
}

describe("Accessibility and Landmarks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders skip-to-content link pointing to #main-content", async () => {
    await renderApp();
    const skipLink = screen.getByText("Skip to main content");
    expect(skipLink).toBeTruthy();
    expect(skipLink.getAttribute("href")).toBe("#main-content");
  });

  it("renders polite live region for screen reader announcements", async () => {
    const { container } = await renderApp();
    const liveRegion = container.querySelector(".sr-only[aria-live='polite']");
    expect(liveRegion).toBeTruthy();
    expect(liveRegion?.getAttribute("aria-atomic")).toBe("true");
  });

  it("renders required semantic landmarks", async () => {
    await renderApp();
    expect(screen.getByRole("banner")).toBeTruthy();
    expect(screen.getByRole("complementary")).toBeTruthy();
    expect(screen.getByRole("main")).toBeTruthy();
    expect(screen.getByRole("main").id).toBe("main-content");
  });
});

describe("Responsive Drawer and Focus Management", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("toggles mobile drawer with menu button and updates aria-expanded", async () => {
    await renderApp();

    const menuBtn = screen.getByRole("button", { name: /open sidebar menu/i });
    expect(menuBtn.getAttribute("aria-expanded")).toBe("false");

    // Click to open drawer
    await act(async () => {
      fireEvent.click(menuBtn);
    });
    expect(menuBtn.getAttribute("aria-expanded")).toBe("true");

    // Sidebar panel has open class
    const sidebar = screen.getByRole("complementary");
    expect(sidebar.className).toContain("app-sidebar--open");

    // Backdrop is present
    const backdrop = document.querySelector(".sidebar-backdrop");
    expect(backdrop).toBeTruthy();

    // Click backdrop to close
    if (backdrop) {
      await act(async () => {
        fireEvent.click(backdrop);
      });
    }
    expect(menuBtn.getAttribute("aria-expanded")).toBe("false");
    expect(sidebar.className).not.toContain("app-sidebar--open");
  });

  it("closes drawer on Escape key and returns focus to menu button", async () => {
    await renderApp();

    const menuBtn = screen.getByRole("button", { name: /open sidebar menu/i });
    await act(async () => {
      fireEvent.click(menuBtn);
    });
    expect(menuBtn.getAttribute("aria-expanded")).toBe("true");

    // Press Escape
    await act(async () => {
      fireEvent.keyDown(window, { key: "Escape" });
    });

    // Drawer is closed
    expect(menuBtn.getAttribute("aria-expanded")).toBe("false");
    // Menu button regains focus
    expect(document.activeElement).toBe(menuBtn);
  });

  it("closes drawer when close button inside drawer is clicked", async () => {
    await renderApp();

    const menuBtn = screen.getByRole("button", { name: /open sidebar menu/i });
    await act(async () => {
      fireEvent.click(menuBtn);
    });

    const closeBtn = screen.getByRole("button", { name: /close sidebar panel/i });
    await act(async () => {
      fireEvent.click(closeBtn);
    });

    expect(menuBtn.getAttribute("aria-expanded")).toBe("false");
  });
});

describe("Full Page and Component Accessibility (jest-axe)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("full application page has no accessibility violations with chat active", async () => {
    const { container } = await renderApp();

    await waitFor(() => {
      expect(screen.getByLabelText("Select dataset")).toBeTruthy();
    });

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it("full application page has no accessibility violations when drawer is open", async () => {
    const { container } = await renderApp();

    const menuBtn = screen.getByRole("button", { name: /open sidebar menu/i });
    await act(async () => {
      fireEvent.click(menuBtn);
    });

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
