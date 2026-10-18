# Snowflake and Gemma operations

## Snowflake roles and query path

The backend reads through `DATAMIND_READER`, configured by
`SNOWFLAKE_ROLE`. The Snowflake client rejects another application role and
disables secondary roles for the session. Question SQL passes the SQL guard
before the client executes it. The live verifier also checks that a zero-row
INSERT is denied to the reader role.

`DATAMIND_LOADER`, configured by `SNOWFLAKE_LOAD_ROLE`, is reserved for
`backend/scripts/load_data.py` and the reversible data-change demo. It is not used by
the API for query execution. The demo uses it to create and modify a disposable
clone; loader SELECT access on the source is needed to make that clone.

The checked-in Snowflake setup template provisions `DATAMIND_WH` as `XSMALL`,
with auto-resume enabled and auto-suspend after 60 seconds. This is a small
on-demand warehouse configuration; Snowflake charges still depend on actual
warehouse use and the account's pricing.

## Gemma runtime and responsibilities

The example environment selects `GEMMA_BACKEND=ollama` and
`GEMMA_MODEL=gemma3:4b`. In that setup, Ollama serves Gemma locally at
`http://localhost:11434`; the model is used for classification, SQL proposal,
and result explanation. Snowflake, not Gemma, computes counts, filters,
aggregates, and joins. Gemma 3 4B is the configured local default so the
prototype can run language inference without requiring a hosted-model account
or sending prompts to a hosted provider. This is a deployment choice, not a
claim that it is the most accurate or fastest model; the evaluation reports
document the observed limitations.

An OpenAI-compatible hosted chat-completions backend can be selected instead
with `GEMMA_BACKEND=api`, `GEMMA_MODEL`, `GEMMA_API_BASE_URL`, and
`GEMMA_API_KEY`. Credentials belong in the local ignored `.env`, never in
tracked files or screenshots.

The local Ollama option permits inference without a hosted API key or hosted
model request by default. Choosing a hosted endpoint can incur that provider's
charges and sends prompts to the configured provider; make that choice
explicitly.

## Credit and resource controls

- The `XSMALL` warehouse and 60-second auto-suspend reduce idle warehouse time;
  auto-resume starts it when a query needs it.
- The default Snowflake connection timeout is 15 seconds. Failed or slow
  requests do not cause an intentional retry loop in the query path.
- `SQL_GUARD_MAX_LIMIT` defaults to 500 and caps returned SQL rows.
  `API_MAX_ROWS` defaults to 200 and limits rows returned to the UI. These are
  result-size controls, not guarantees that a large aggregate or join scans
  less source data.
- Use the reader role for evaluations and UI questions. The loader role is
  needed only when loading the Bank Marketing data or running the explicitly
  confirmed copy-edit-revert demo.
- Stop local evaluation and development servers when not in use. Local Ollama
  avoids hosted inference charges but still consumes local compute and power.
