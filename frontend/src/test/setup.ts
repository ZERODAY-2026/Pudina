/**
 * src/test/setup.ts
 * Global Vitest setup: extends expect with jest-dom and jest-axe matchers.
 */
import "@testing-library/jest-dom";
import { configureAxe, toHaveNoViolations } from "jest-axe";
import { expect } from "vitest";

// Extend Vitest's expect with toHaveNoViolations.
expect.extend(toHaveNoViolations);

// Configure axe globally so tests can call axe(container) directly.
export const axe = configureAxe({
  rules: {
    // Disable rules that fire on incomplete jsdom environments.
    region: { enabled: false },
  },
});
