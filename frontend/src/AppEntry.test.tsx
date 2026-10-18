import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import AppEntry from "./AppEntry";

vi.mock("./landing/components/RippleGrid", () => ({
  default: () => <div data-testid="ripple-grid" />,
}));

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
    datasets: [
      {
        id: "bank-marketing",
        name: "UCI Bank Marketing",
        description: "Sample dataset",
        example_questions: [],
      },
    ],
  }),
  ask: vi.fn(),
}));

vi.stubGlobal(
  "IntersectionObserver",
  class {
    observe() {}
    unobserve() {}
    disconnect() {}
  },
);

afterEach(() => {
  cleanup();
  window.history.replaceState({}, "", "/");
  vi.unstubAllGlobals();
});

describe("AppEntry routes", () => {
  it("shows the landing page at the root path", () => {
    window.history.replaceState({}, "", "/");
    render(<AppEntry />);

    expect(
      screen.getByRole("heading", { name: "DataMind", level: 1 }),
    ).toBeTruthy();
    expect(screen.getByRole("link", { name: /launch datamind/i }).getAttribute("href")).toBe(
      "/chat",
    );
  });

  it("shows the live application at /chat", async () => {
    window.history.replaceState({}, "", "/chat");
    render(<AppEntry />);

    expect(screen.getByRole("banner")).toBeTruthy();
    fireEvent.change(await screen.findByLabelText("Select dataset"), {
      target: { value: "bank-marketing" },
    });
    await waitFor(() => {
      expect(screen.getByLabelText("Ask a question")).toBeTruthy();
    });
    const chatArea = document.querySelector(".chat-area");
    expect(chatArea).toBeTruthy();
    fireEvent.mouseMove(chatArea!, { clientX: 120, clientY: 80 });
    expect(chatArea).toHaveStyle({
      "--chat-pointer-x": "120px",
      "--chat-pointer-y": "80px",
    });
    fireEvent.mouseLeave(chatArea!);
    expect(chatArea).toHaveStyle({
      "--chat-pointer-x": "-1000px",
      "--chat-pointer-y": "-1000px",
    });
  });
});
