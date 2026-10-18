/**
 * src/components/AppHeader.tsx
 * Top application header with logo, branding, live health status,
 * and responsive mobile drawer menu toggle button.
 */
import { HealthStatus } from "../types";

interface Props {
  healthStatus: HealthStatus | "loading" | "unknown";
  isSidebarOpen?: boolean;
  onToggleSidebar?: () => void;
  menuButtonRef?: React.RefObject<HTMLButtonElement>;
}

const STATUS_LABELS: Record<string, string> = {
  ok: "All systems operational",
  degraded: "Degraded – some services unavailable",
  down: "System unavailable",
  loading: "Checking…",
  unknown: "Status unknown",
};

export function AppHeader({
  healthStatus,
  isSidebarOpen = false,
  onToggleSidebar,
  menuButtonRef,
}: Props) {
  const dotClass =
    healthStatus === "ok"
      ? "status-dot status-dot--ok"
      : healthStatus === "degraded"
        ? "status-dot status-dot--degraded"
        : healthStatus === "down"
          ? "status-dot status-dot--down"
          : "status-dot";

  return (
    <header className="app-header" role="banner">
      {/* Mobile drawer toggle */}
      {onToggleSidebar && (
        <button
          ref={menuButtonRef}
          type="button"
          className="menu-toggle-btn"
          onClick={onToggleSidebar}
          aria-label={isSidebarOpen ? "Close sidebar menu" : "Open sidebar menu"}
          aria-expanded={isSidebarOpen}
          aria-controls="app-sidebar-panel"
        >
          <span className="menu-toggle-icon" aria-hidden="true">
            {isSidebarOpen ? "✕" : "☰"}
          </span>
        </button>
      )}

      <a href="/" className="app-header__logo" aria-label="DataMind home">
        <div className="app-header__logo-mark" aria-hidden="true">
          DM
        </div>
        <span className="app-header__title">DataMind</span>
      </a>

      <span className="app-header__badge" aria-label="Hacktoberfest 2026 project">
        Hacktoberfest 2026
      </span>

      <div className="app-header__spacer" />

      <div
        className="app-header__status"
        aria-live="polite"
        aria-label={`System status: ${STATUS_LABELS[healthStatus] ?? "unknown"}`}
      >
        <span className={dotClass} role="img" aria-hidden="true" />
        <span className="app-header__status-text">{STATUS_LABELS[healthStatus] ?? "unknown"}</span>
      </div>
    </header>
  );
}
