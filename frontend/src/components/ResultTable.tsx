/**
 * src/components/ResultTable.tsx
 * Renders query result table with sticky header, numeric alignment,
 * distinct NULL display, CSV download, row capping for large datasets, and optional SVG chart.
 */
import { useMemo, useState } from "react";
import { RowCell } from "../types";
import { downloadCsv, exportRowsToCsv } from "../utils/csv";
import { getChartEligibility } from "../utils/chart";
import { BarChart } from "./BarChart";

interface Props {
  columns: string[];
  rows: RowCell[][];
  rowCount: number;
  truncated: boolean;
  queryId?: string | null;
}

const MAX_DISPLAY_ROWS = 200;

export function ResultTable({
  columns,
  rows,
  rowCount,
  truncated,
}: Props) {
  const [showChart, setShowChart] = useState(false);

  // Cap displayed rows for performance (e.g. ask_answered_large)
  const isCapped = rows.length > MAX_DISPLAY_ROWS;
  const displayedRows = useMemo(
    () => (isCapped ? rows.slice(0, MAX_DISPLAY_ROWS) : rows),
    [rows, isCapped],
  );

  // Detect which columns are numeric for right-alignment
  const numericColumns = useMemo(() => {
    return columns.map((_, colIdx) => {
      const nonNulls = rows
        .map((r) => r[colIdx])
        .filter((val) => val !== null && val !== undefined);
      return (
        nonNulls.length > 0 &&
        nonNulls.every((val) => typeof val === "number" && !Number.isNaN(val))
      );
    });
  }, [columns, rows]);

  // Check chart eligibility
  const chartEligibility = useMemo(
    () => getChartEligibility(columns, rows),
    [columns, rows],
  );

  const handleDownloadCsv = () => {
    const csv = exportRowsToCsv(columns, displayedRows);
    downloadCsv("query_results.csv", csv);
  };

  const totalCount = rowCount || rows.length;

  return (
    <div className="result-table-container">
      {/* Controls & Meta info bar */}
      <div className="result-table__meta">
        <span className="result-table__count" aria-live="polite">
          Showing {displayedRows.length} of {totalCount}
          {truncated ? " (truncated by server)" : ""} rows
          {isCapped ? " • Display capped at 200 rows for performance" : ""}
        </span>

        <div className="result-table__actions">
          {chartEligibility.eligible && (
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              aria-label="Chart of the rows above"
              onClick={() => setShowChart(!showChart)}
            >
              {showChart ? "Hide chart" : "Show chart"}
            </button>
          )}

          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={handleDownloadCsv}
            aria-label="Download CSV"
          >
            Download CSV
          </button>
        </div>
      </div>

      {/* Optional Chart */}
      {showChart && chartEligibility.eligible && chartEligibility.data && (
        <BarChart
          data={chartEligibility.data}
          categoryTitle={chartEligibility.categoryColName}
          numericTitle={chartEligibility.numericColName}
        />
      )}

      {/* Table view */}
      <div className="table-scroll" tabIndex={0} role="region" aria-label="Query results data table">
        <table className="data-table">
          <thead>
            <tr>
              <th className="table-index-header" aria-label="Row number">
                #
              </th>
              {columns.map((col, idx) => (
                <th
                  key={idx}
                  className={numericColumns[idx] ? "cell--numeric" : "cell--text"}
                  scope="col"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {displayedRows.map((row, rowIdx) => (
              <tr key={rowIdx}>
                <td className="table-index-cell">{rowIdx + 1}</td>
                {row.map((cell, cellIdx) => {
                  const isNumeric = numericColumns[cellIdx];
                  const isNull = cell === null || cell === undefined;

                  return (
                    <td
                      key={cellIdx}
                      className={isNumeric ? "cell--numeric" : "cell--text"}
                    >
                      {isNull ? (
                        <span className="cell-null" aria-label="Null value">
                          NULL
                        </span>
                      ) : isNumeric ? (
                        Number(cell).toLocaleString()
                      ) : (
                        String(cell)
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
