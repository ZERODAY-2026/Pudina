/**
 * src/utils/csv.ts
 * Utility to export table rows and columns to RFC 4180 compliant CSV format.
 * Correctly escapes quotes, commas, and newlines.
 */
import { RowCell } from "../types";

export function escapeCsvCell(cell: RowCell): string {
  if (cell === null || cell === undefined) {
    return "";
  }
  const str = String(cell);
  // If the cell contains quotes, commas, or newlines, wrap in quotes and escape internal quotes
  if (/[",\r\n]/.test(str)) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
}

export function exportRowsToCsv(columns: string[], rows: RowCell[][]): string {
  const headerLine = columns.map(escapeCsvCell).join(",");
  const rowLines = rows.map((row) => row.map(escapeCsvCell).join(","));
  return [headerLine, ...rowLines].join("\r\n");
}

export function downloadCsv(filename: string, csvContent: string): void {
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.setAttribute("href", url);
  link.setAttribute("download", filename);
  link.style.visibility = "hidden";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
