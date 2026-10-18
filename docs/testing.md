# Backend testing and verification

## Automated tests

Run the backend test suite from the repository root:

```powershell
Push-Location backend
python -m pytest -q
Pop-Location
```

The final submission-pass backend run completed with **138 passed** and one
third-party Starlette/AnyIO deprecation warning. Coverage includes unit tests
for configuration loading, prompts, SQL validation, pipeline behavior,
Snowflake/Gemma adapters, the API, and evaluation utilities.

The API tests use FastAPI `TestClient` with mocked pipeline/services. Contract
tests load the JSON fixtures under [`fixtures/`](./fixtures/) and validate
response keys, types, and status invariants. They do not prove that the live
Snowflake or Gemma services are available.

The React frontend was installed from its lockfile with `npm ci`; `npm run lint`,
`npm test`, and `npm run build` passed on the submission-pass worktree.
Frontend tests: **89 passed** across 7 files, including runtime contract
validation for response fixtures. The app layout uses the full content width
when its fixed sidebar drawer is closed.

The local React app was exercised in a browser against the live API. Health
reported config, Snowflake, and Gemma as operational; the catalog exposed both
configured datasets. Asking “How many clients are in the dataset?” returned
**45,211** with SQL, one result row, and query ID
`01c7cf92-0007-82d8-0002-1062000274e6`; the evidence panel displayed all of
these fields. This successful question does not replace the full live verifier
below, which still has an observed average-age failure.

During integration, the committed dataset fixture contained only Bank
Marketing although the live catalog also returned TPC-H SF1, and its Bank
description did not match the config; the fixture was corrected, and a backend
regression test now compares it exactly with the discovered catalog. Health
fixtures were also generalized to match the API's dataset-independent
configuration message. The browser's Data Loader control previously called an
API route that does not exist and displayed a success-like fallback; it now
explains that loading is a backend administrative operation instead of
attempting a nonexistent upload.

The live count's generated explanation also appended a numeric-consistency
warning for the SQL `LIMIT 500` value even though the returned count was 45,211.
This is a false-positive warning in pipeline explanation checking; the SQL,
Snowflake rows, and query ID were present and agreed on the count.

## Latest TPC-H React UI verification

The latest UI queries were run after the backend was moved into `backend/` and
the join-path repairs were added:

| Question | Verified rows | Query ID |
|---|---|---|
| Which three nations have the most orders? | FRANCE 61,600; RUSSIA 61,495; INDONESIA 61,377 | `01c7cfd7-0007-82d8-0002-106200027dda` |
| How many suppliers belong to each region? | AMERICA 2,036; MIDDLE EAST 2,019; ASIA 2,003; EUROPE 1,987; AFRICA 1,955 | `01c7cfd6-0007-82d8-0002-106200027dc2` |

The first SQL followed `ORDERS -> CUSTOMER -> NATION`; the second followed
`SUPPLIER -> NATION -> REGION`. A separate reader-role query using
`COUNT(DISTINCT S_SUPPKEY)` matched all five supplier counts
(`01c7cfca-0007-82d8-0002-106200027c16`). Repeated live asks returned distinct
query IDs. This verifies those question paths only; it is not a rerun of the
complete TPC-H evaluation or the manual data-change demo. Detailed notes are in
[`evidence/i2-ui-validation.md`](evidence/i2-ui-validation.md).

## Live Bank Marketing verifier

Run:

```powershell
Push-Location backend
python -m scripts.verify_live
Pop-Location
```

Latest observed result:

| Check | Result |
|---|---|
| Required environment configuration | PASS |
| Reader connection and full Bank Marketing row count | PASS — 45,211 rows; query ID `01c7cf6e-0007-82d8-0002-1062000273d2` |
| Reader-role write rejection | PASS — a zero-row INSERT was denied |
| Gemma text and JSON generation | PASS |
| Three live pipeline questions | FAIL — average-age request produced a Snowflake compilation error: `invalid identifier 'AGE'` |

The verifier stops on that first failed step. Its ambiguous, empty-result,
unsupported, unsafe-SQL, and prompt-injection edge checks therefore did **not**
run in this invocation. The observed failure is consistent with SQL using
unquoted `AGE` when the configured Bank Marketing column is lowercase and
quoted; the SQL guard currently checks query shape and table scope, not column
existence or casing. Do not treat the earlier individual live checks as a
passing result for this run.

## Dataset A — original evaluation

The latest recorded 20-question Bank Marketing evaluation is
[`results.md`](../backend/eval/results.md): **14/20 (70.0%)**, with **4/5 (80.0%)**
held-out questions.

| Category | Passed | Total | Accuracy |
|---|---:|---:|---:|
| ambiguous | 2 | 2 | 100.0% |
| empty_result | 1 | 2 | 50.0% |
| filter | 3 | 5 | 60.0% |
| join | 0 | 2 | 0.0% |
| multi_step | 2 | 3 | 66.7% |
| simple_aggregate | 4 | 4 | 100.0% |
| unsupported | 2 | 2 | 100.0% |

Failure analysis in the report includes wrong filters/count semantics, questions
that describe joins to tables absent from the configured Bank Marketing schema,
and an empty-result request mapped to the wrong category value. The
not-previously-contacted manifest case also uses the obsolete `pdays = 999`
sentinel: the configured data notes and UCI data use `-1`. That case is a
ground-truth/manifest defect, not evidence that the query returning 36,954 is
wrong.

## Dataset A — unseen evaluation

The separate 20-question report is
[`results_unseen.md`](../backend/eval/results_unseen.md): **15/20 (75.0%)**. It has no
held-out split.

| Category | Passed | Total | Accuracy |
|---|---:|---:|---:|
| ambiguous | 3 | 3 | 100.0% |
| empty_result | 2 | 2 | 100.0% |
| filter | 1 | 1 | 100.0% |
| multi_step | 2 | 6 | 33.3% |
| prompt_injection | 0 | 1 | 0.0% |
| simple_aggregate | 4 | 4 | 100.0% |
| unsupported | 3 | 3 | 100.0% |

The main measured weakness is follow-up interpretation: a later question can
lose an earlier measure or filter, or retain an incorrect population.
The mixed prompt-injection/data question was also refused rather than answered.

## Dataset B — TPC-H SF1 evaluation

[`results_tpch.md`](../backend/eval/results_tpch.md) was produced by the live
`eval.run_tpch_eval` run. Expected answers came from the hand-written,
independent Snowflake SQL in
[`compute_tpch_ground_truth.py`](../backend/eval/compute_tpch_ground_truth.py); the
questions were sent through `POST /api/ask` using FastAPI `TestClient`.
The latest recorded result is **4/10 (40.0%)**, with no held-out questions.

| Category | Passed | Total | Accuracy |
|---|---:|---:|---:|
| ambiguous | 1 | 1 | 100.0% |
| filter | 0 | 1 | 0.0% |
| join | 1 | 3 | 33.3% |
| simple_aggregate | 1 | 4 | 25.0% |
| unsupported | 1 | 1 | 100.0% |

This is not a successful multi-table validation. The API returned friendly
errors for six requests. One reported join pass is a **false positive for
numeric correctness**: the supplier-by-region response listed every expected
region, but the generated SQL joined `REGION.R_REGIONKEY` to
`SUPPLIER.S_NATIONKEY` instead of following `SUPPLIER` → `NATION` → `REGION`.
It returned counts such as 420 for AFRICA, while the independent SQL returned
1,955. The current `string_list` grader checks that expected labels occur in
the answer/rows; it does not verify their paired counts or ranking. The
three-nation question passed in the first recorded run but failed in the latest
run, which further shows that join generation is not yet reliable.

The aggregate and join failures, plus the mismatch above, mean the B5
acceptance condition that dataset B answer join questions correctly via the
API is **not demonstrated** by these results. Re-run the evaluator after
improving schema grounding and grading grouped values together.

## Known limits

- The latest recorded live verifier failed at the average-age pipeline question
  with an identifier/casing error. Checks after that stage remain unverified;
  this later TPC-H UI run does not constitute a successful verifier run.
- SQL validation restricts statements and configured tables/join relationships.
  The pipeline applies schema-grounded repairs for uniquely identifiable
  column-name suffix errors, but does not fully type-check every SQL expression.
- The TPC-H live evaluation is small and does not prove general join accuracy;
  the current grouped string-list comparison can pass incorrect metrics.
- Gemma output is nondeterministic enough that successive TPC-H runs differed.
  Retain each report and its Snowflake query IDs; do not present one run as a
  guarantee of repeatability.
- Snowflake Connector **3.18.1** is pinned because it publishes a Windows
  CPython 3.13 wheel; the previous 3.14.0 pin attempted a source build and
  required unavailable MSVC in the clean Python 3.13 install. Clean dependency
  installs and backend tests are checked on Python 3.12 and 3.13 locally; CI
  includes Python 3.11, 3.12, and 3.13.
- The TPC-H and Bank Marketing reports require live services; mocked tests do
  not regenerate those result files.

## Repository hygiene scan

The final scan compared local Snowflake/Gemma values in memory against project
text and scanned all **8 reachable commits**. No exact credential/account
matches or generic key/private-key patterns were found in Git history. No data
files are tracked in the current index or present in reachable history.

The working-tree scan found one expected identity match in the ignored local
`scripts/setup.sql`: the configured Snowflake username. The ignored root `.env`
contains the local Snowflake connection values and was used only as the
comparison source; values were not printed. No account-identifier or
credential-value match, nor any generic key/private-key pattern, was found in
other scanned project files. The committed `.env.example` contains empty
credential fields. The local ignored `data/` directory contains one file; its
contents were not inspected.

No history was rewritten. The clean, sanitized working-tree snapshot install
and test passed, but it was not a literal Git clone of this uncommitted state;
repeat the README workflow from a fresh clone after the changes are committed.
