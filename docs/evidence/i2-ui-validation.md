# I2 React/Snowflake validation notes

Validated against the React UI served by the current FastAPI source at
`http://localhost:8001/`. `/api/health` reported `ok` for config, Snowflake, and
Gemma. The selected dataset was TPC-H SF1. No Snowflake data was changed.

## Live UI queries

| Question | UI result | Query ID |
|---|---|---|
| Which three nations have the most orders? | FRANCE (61,600), RUSSIA (61,495), INDONESIA (61,377) | `01c7cfd7-0007-82d8-0002-106200027dda` |
| How many suppliers belong to each region? | AMERICA (2,036), MIDDLE EAST (2,019), ASIA (2,003), EUROPE (1,987), AFRICA (1,955) | `01c7cfd6-0007-82d8-0002-106200027dc2` |

The nation query's SQL joined `ORDERS` to `NATION` through `CUSTOMER`, using
`O_CUSTKEY = C_CUSTKEY` and `C_NATIONKEY = N_NATIONKEY`. The supplier query
joined `SUPPLIER` to `REGION` through `NATION`, using
`S_NATIONKEY = N_NATIONKEY` and `N_REGIONKEY = R_REGIONKEY`. Both evidence
panels displayed SQL, all result rows, and the Snowflake query ID.

An independent reader-role check used `COUNT(DISTINCT S_SUPPKEY)` grouped by
region and matched all five supplier counts above. Its query ID was
`01c7cfca-0007-82d8-0002-106200027c16`.

The supplier question was executed more than once without changing data. The
earlier execution ID `01c7cfd3-0007-82d8-0002-106200027d7a` and the later ID in
the table are distinct, confirming that each question reached Snowflake rather
than returning a cached result. A data-change-specific stale-result check is
still pending the manual clone/insert/revert below.

## Issues fixed during I2

- Gemma sometimes joined tables using guessed or invalid keys. SQL generation
  now prioritizes the shortest configured path for named entities, repairs a
  guessed direct join only when the configuration supplies a path, and rejects
  remaining joins that are not configured relationships.
- Gemma generated `R_REGIONNAME` for the configured `REGION.R_NAME` field. A
  unique schema-derived column suffix is now corrected before validation.
- In one same-chat attempt, the answer model reused nation names from the
  previous response when explaining supplier counts. Complete standalone
  questions now omit unrelated prior turns; explicitly phrased follow-ups
  retain recent context. Repeating the supplier question after this change
  returned the correct region names and counts.
- The Load Data panel showed dataset-neutral guidance: this browser app does
  not upload files or modify Snowflake tables.

## Screenshots to capture

- TPC-H SF1 selected, showing its configured examples.
- Nation ranking evidence panel with the `ORDERS -> CUSTOMER -> NATION` SQL,
  all three rows, and the query ID.
- Supplier-by-region evidence panel with the `SUPPLIER -> NATION -> REGION`
  SQL, all five rows, and the query ID.
- Service health showing config, Snowflake, and Gemma operational.
- Dataset-neutral Load Data instructions.
- For the manual demo only: Snowsight clone and tagged row, the matching React
  answer before and after the change, the reverted answer with its new query
  ID, direct SQL verification, and the dropped clone.

Redact usernames, account identifiers, connection details, and unrelated
worksheet or data content before sharing screenshots.

## Manual data-change variant: not yet performed

I did not use Snowsight or the loader role to create, modify, or drop a table.
To finish the data-change-specific demonstration, follow the manual clone,
tagged-row insert, reader verification, delete/revert, and drop steps in
[`../demo_data_change.md`](../demo_data_change.md). Use only the disposable
`BANK_MARKETING_DEMO_CHANGE` clone, never the source table. Record the
before/after/reverted answers and distinct query IDs in the evidence template
after completing those steps.
