/**
 * src/utils/chart.ts
 * Logic to check chart eligibility and extract chart data series.
 * Eligible when:
 * - Exactly two columns: one categorical and one numeric
 * - Between 2 and 15 rows inclusive
 */
import { RowCell } from "../types";

export interface ChartDataPoint {
  label: string;
  value: number;
}

export interface ChartEligibility {
  eligible: boolean;
  categoryColName?: string;
  numericColName?: string;
  data?: ChartDataPoint[];
}

export function getChartEligibility(
  columns: string[],
  rows: RowCell[][],
): ChartEligibility {
  if (
    !columns ||
    columns.length !== 2 ||
    !rows ||
    rows.length < 2 ||
    rows.length > 15
  ) {
    return { eligible: false };
  }

  const isColNumeric = (colIdx: number) => {
    const nonNulls = rows
      .map((r) => r[colIdx])
      .filter((v) => v !== null && v !== undefined);
    return (
      nonNulls.length > 0 &&
      nonNulls.every((v) => typeof v === "number" && !Number.isNaN(v))
    );
  };

  const isColCategorical = (colIdx: number) => {
    const nonNulls = rows
      .map((r) => r[colIdx])
      .filter((v) => v !== null && v !== undefined);
    return (
      nonNulls.length > 0 &&
      nonNulls.every(
        (v) => typeof v === "string" || typeof v === "boolean",
      )
    );
  };

  let catIdx = -1;
  let numIdx = -1;

  if (isColCategorical(0) && isColNumeric(1)) {
    catIdx = 0;
    numIdx = 1;
  } else if (isColNumeric(0) && isColCategorical(1)) {
    catIdx = 1;
    numIdx = 0;
  } else {
    return { eligible: false };
  }

  const data: ChartDataPoint[] = rows.map((r) => {
    const label = r[catIdx] === null || r[catIdx] === undefined ? "NULL" : String(r[catIdx]);
    const val = typeof r[numIdx] === "number" ? (r[numIdx] as number) : 0;
    return { label, value: val };
  });

  return {
    eligible: true,
    categoryColName: columns[catIdx],
    numericColName: columns[numIdx],
    data,
  };
}
