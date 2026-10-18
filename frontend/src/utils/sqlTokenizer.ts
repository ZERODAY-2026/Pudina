/**
 * src/utils/sqlTokenizer.ts
 * Tokenizer for SQL queries with keyword/string/identifier/number recognition.
 */
const KEYWORDS = new Set([
  "SELECT",
  "FROM",
  "WHERE",
  "GROUP",
  "BY",
  "ORDER",
  "LIMIT",
  "OFFSET",
  "JOIN",
  "INNER",
  "LEFT",
  "RIGHT",
  "FULL",
  "OUTER",
  "ON",
  "AND",
  "OR",
  "NOT",
  "IN",
  "IS",
  "NULL",
  "AS",
  "COUNT",
  "SUM",
  "AVG",
  "MIN",
  "MAX",
  "CASE",
  "WHEN",
  "THEN",
  "ELSE",
  "END",
  "HAVING",
  "UNION",
  "ALL",
  "DISTINCT",
  "BETWEEN",
  "LIKE",
  "ILIKE",
  "ASC",
  "DESC",
  "WITH",
  "OVER",
  "PARTITION",
]);

export interface SqlToken {
  type: "keyword" | "string" | "identifier" | "number" | "text";
  value: string;
}

export function tokenizeSql(sql: string): SqlToken[] {
  const tokens: SqlToken[] = [];
  let i = 0;
  const len = sql.length;

  while (i < len) {
    const char = sql[i];

    // Single-quoted string literal
    if (char === "'") {
      let j = i + 1;
      while (j < len && sql[j] !== "'") {
        if (sql[j] === "\\" && j + 1 < len) {
          j += 2;
        } else {
          j++;
        }
      }
      tokens.push({ type: "string", value: sql.slice(i, j + 1) });
      i = j + 1;
      continue;
    }

    // Double-quoted identifier
    if (char === '"') {
      let j = i + 1;
      while (j < len && sql[j] !== '"') {
        j++;
      }
      tokens.push({ type: "identifier", value: sql.slice(i, j + 1) });
      i = j + 1;
      continue;
    }

    // Number literal
    if (/\d/.test(char)) {
      let j = i;
      while (j < len && /[\d.]/.test(sql[j])) {
        j++;
      }
      tokens.push({ type: "number", value: sql.slice(i, j) });
      i = j;
      continue;
    }

    // Word (keyword or plain word)
    if (/[a-zA-Z_]/.test(char)) {
      let j = i;
      while (j < len && /[a-zA-Z0-9_]/.test(sql[j])) {
        j++;
      }
      const word = sql.slice(i, j);
      if (KEYWORDS.has(word.toUpperCase())) {
        tokens.push({ type: "keyword", value: word });
      } else {
        tokens.push({ type: "text", value: word });
      }
      i = j;
      continue;
    }

    // Whitespace or punctuation
    tokens.push({ type: "text", value: char });
    i++;
  }

  return tokens;
}
