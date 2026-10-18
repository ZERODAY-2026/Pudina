/**
 * src/components/HealthIndicator.tsx
 * Displays live service status for Snowflake, Gemma, and Config.
 */
import { HealthResponse } from "../types";

interface Props {
  health: HealthResponse | null;
  loading?: boolean;
}

export function HealthIndicator({ health, loading }: Props) {
  const checks = health?.checks;

  const services = [
    {
      key: "snowflake",
      name: "Snowflake",
      check: checks?.snowflake,
    },
    {
      key: "gemma",
      name: "Gemma",
      check: checks?.gemma,
    },
    {
      key: "config",
      name: "Config",
      check: checks?.config,
    },
  ];

  return (
    <div
      className="health-indicator"
      aria-label="System service health"
      role="region"
    >
      <div className="sidebar-label">Service Status</div>
      {services.map(({ key, name, check }) => {
        const isOk = check?.ok === true;
        const dotClass = loading && !check
          ? "status-dot"
          : isOk
            ? "status-dot status-dot--ok"
            : "status-dot status-dot--down";
        const message = check?.message || (loading ? "Checking…" : "Unknown");

        return (
          <div
            key={key}
            className="health-service"
            aria-label={`${name}: ${isOk ? "Operational" : "Unavailable"} (${message})`}
          >
            <span
              className={dotClass}
              role="img"
              aria-label={isOk ? "Operational" : "Error"}
            />
            <span className="health-service__name">{name}</span>
            <span className="health-service__msg" title={message}>
              {message}
            </span>
          </div>
        );
      })}
    </div>
  );
}
