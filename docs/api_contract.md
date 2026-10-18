# DataMind API contract

This document defines the backend HTTP interface consumed by frontend clients.
Examples are in [`fixtures/`](./fixtures/). JSON object keys shown below are
required unless a field is explicitly nullable; response objects use the same
shape in every fixture.

## `GET /api/health`

Returns HTTP `200` with:

```json
{
  "status": "ok",
  "checks": {
    "config": { "ok": true, "message": "Dataset configuration loaded." },
    "snowflake": { "ok": true, "message": "Reader connection available." },
    "gemma": { "ok": true, "message": "Gemma backend available." }
  }
}
```

`status` is `ok`, `degraded`, or `down`. Each check is reported independently;
`message` is a concise, user-safe diagnostic and must not contain credentials.
See [`health_ok.json`](./fixtures/health_ok.json) and
[`health_degraded.json`](./fixtures/health_degraded.json).

## `GET /api/datasets`

Returns HTTP `200`:

```json
{
  "datasets": [
    {
      "id": "bank-marketing",
      "name": "UCI Bank Marketing",
      "description": "Bank campaign contacts and term-deposit outcomes.",
      "example_questions": ["How many clients are in the dataset?"]
    }
  ]
}
```

Each dataset has a stable `id`, display `name`, `description`, and
`example_questions` array of strings. The `dataset` field in an ask request
uses this ID, not the display name.

## `POST /api/ask`

### Request

```json
{
  "question": "How many clients subscribed to a term deposit?",
  "dataset": "bank-marketing",
  "history": [
    { "role": "user", "content": "How many clients are in the dataset?" },
    { "role": "assistant", "content": "There are 45,211 client contacts." }
  ]
}
```

- `question`: string containing 1–1000 characters.
- `dataset`: string dataset ID returned by `GET /api/datasets`.
- `history`: array of `{role, content}` messages; `role` is `user` or
  `assistant`, `content` is a string, and the array may contain at most 10
  entries (messages/turns).

### Response

Successful application responses use HTTP `200` and always include this shape:

```json
{
  "status": "answered",
  "answer": "5,289 clients subscribed to a term deposit.",
  "explanation": "Counted rows in BANK_MARKETING where y = 'yes'.",
  "assumptions": [],
  "sql": "SELECT COUNT(*) AS subscribed_clients FROM BANK_MARKETING WHERE \"y\" = 'yes'",
  "columns": ["SUBSCRIBED_CLIENTS"],
  "rows": [[5289]],
  "row_count": 1,
  "truncated": false,
  "query_id": "01c7cf01-0007-82d8-0002-106200026a2e",
  "clarifying_question": null,
  "elapsed_ms": 412
}
```

`rows` is an array of row arrays aligned positionally with `columns`; cell
values are JSON-compatible values. `row_count` is the number of rows included
in `rows`. `truncated` is true when matching rows were omitted because the
response row limit was reached. `elapsed_ms` is a non-negative integer.
Nullable fields use JSON `null`; arrays are present even when empty.

The exact keys for all statuses are `status`, `answer`, `explanation`,
`assumptions`, `sql`, `columns`, `rows`, `row_count`, `truncated`, `query_id`,
`clarifying_question`, and `elapsed_ms`.

### Status rules

- **`answered`**: `answer`, `explanation`, `sql`, and `query_id` are non-null;
  `columns` and `rows` contain the executed query result. This status always
  includes SQL, rows, columns, query ID, and an explanation.
- **`clarify`**: `clarifying_question` is non-null; `sql` and `query_id` are
  null. No query has been executed; `columns` and `rows` are empty.
- **`unsupported`**: `answer` is non-null and explains both the refusal and
  what the system can answer; `sql` and `query_id` are null. No query has been
  executed; `columns` and `rows` are empty.
- **`empty`**: `answer` says that no rows matched; `sql` and `query_id` are
  non-null; `rows` is empty and `row_count` is `0`. `columns` contains the
  result column names.
- **`error`**: `answer` is a friendly, user-facing message that the pipeline
  could not complete the request. `sql` and `query_id` may be null if execution
  did not reach Snowflake; partial result arrays must still follow the response
  shape.

See [`ask_answered.json`](./fixtures/ask_answered.json),
[`ask_answered_large.json`](./fixtures/ask_answered_large.json),
[`ask_clarify.json`](./fixtures/ask_clarify.json),
[`ask_unsupported.json`](./fixtures/ask_unsupported.json),
[`ask_empty.json`](./fixtures/ask_empty.json), and
[`ask_error.json`](./fixtures/ask_error.json).

## HTTP errors

Request-level and service-level errors use this shape:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "question must contain between 1 and 1000 characters."
  }
}
```

Supported codes are:

- `VALIDATION_ERROR` — malformed request or a field outside its constraints
  (HTTP `400`).
- `UNKNOWN_DATASET` — the requested dataset ID does not exist (HTTP `404`).
- `UPSTREAM_TIMEOUT` — Snowflake or Gemma did not respond before its timeout
  (HTTP `504`).
- `INTERNAL_ERROR` — an unexpected backend failure (HTTP `500`).

HTTP error objects are distinct from an HTTP `200` response whose application
status is `error`. Examples:
[`http_validation_error.json`](./fixtures/http_validation_error.json) and
[`http_timeout_error.json`](./fixtures/http_timeout_error.json).

## Versioning

Any change to request or response shapes must update this contract and its
fixtures in the same commit.
