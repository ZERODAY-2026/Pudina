/**
 * src/components/BarChart.tsx
 * Accessible hand-rolled SVG horizontal bar chart for categorical vs numeric data.
 * Zero external dependencies.
 */
import { ChartDataPoint } from "../utils/chart";

interface Props {
  data: ChartDataPoint[];
  categoryTitle?: string;
  numericTitle?: string;
}

export function BarChart({ data, categoryTitle, numericTitle }: Props) {
  if (!data || data.length === 0) return null;

  const maxVal = Math.max(...data.map((d) => d.value), 1);
  const rowHeight = 34;
  const paddingLeft = 140;
  const paddingRight = 60;
  const paddingTop = 24;
  const paddingBottom = 24;

  const width = 560;
  const chartWidth = width - paddingLeft - paddingRight;
  const height = paddingTop + data.length * rowHeight + paddingBottom;

  return (
    <div className="chart-wrapper" role="region" aria-label="Data chart">
      <div className="chart-header">
        <span className="chart-title">
          {categoryTitle && numericTitle
            ? `${numericTitle} by ${categoryTitle}`
            : "Chart of the rows above"}
        </span>
      </div>

      <svg
        className="chart-svg"
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label="Chart of the rows above"
      >
        <title>Chart of the rows above</title>
        <desc>
          Bar chart comparing {categoryTitle ?? "category"} with {numericTitle ?? "value"}.
        </desc>

        <defs>
          <linearGradient id="dm-bar-gradient" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="hsl(218, 100%, 62%)" />
            <stop offset="100%" stopColor="hsl(248, 80%, 65%)" />
          </linearGradient>
        </defs>

        {data.map((point, index) => {
          const y = paddingTop + index * rowHeight;
          const barWidth = Math.max(2, (point.value / maxVal) * chartWidth);
          const barY = y + 4;
          const barHeight = rowHeight - 12;

          return (
            <g key={index} className="chart-row">
              {/* Category label */}
              <text
                x={paddingLeft - 12}
                y={y + rowHeight / 2}
                textAnchor="end"
                dominantBaseline="central"
                className="chart-label"
              >
                {point.label.length > 18
                  ? `${point.label.slice(0, 16)}…`
                  : point.label}
              </text>

              {/* Background track */}
              <rect
                x={paddingLeft}
                y={barY}
                width={chartWidth}
                height={barHeight}
                rx={4}
                className="chart-bar-bg"
              />

              {/* Filled bar */}
              <rect
                x={paddingLeft}
                y={barY}
                width={barWidth}
                height={barHeight}
                rx={4}
                fill="url(#dm-bar-gradient)"
                className="chart-bar-fill"
              />

              {/* Value label */}
              <text
                x={paddingLeft + barWidth + 8}
                y={y + rowHeight / 2}
                dominantBaseline="central"
                className="chart-value"
              >
                {point.value.toLocaleString()}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
