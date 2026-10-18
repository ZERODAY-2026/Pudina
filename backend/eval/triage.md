# First live evaluation triage

Baseline: 14/20 overall (70.0%); held-out 4/5 (80.0%). This table records the
first live run before any prompt or backend behavior changes.

| ID | Category | Question | Expected | Actual | Generated SQL | Root cause |
|---|---|---|---|---|---|---|
| `filter_campaign` | filter (held-out) | How many clients were contacted at least three times in this campaign? | `numeric=15162` (CSV ground truth 15162) | `48`; exact generated SQL returned 48 in Snowflake. Counting rows where campaign >= 3 returned 15162 in Snowflake. | `SELECT COUNT(DISTINCT "campaign") FROM BANK_MARKETING WHERE "campaign" > 0 LIMIT 500` | WRONG_SQL |
| `filter_not_previously_contacted` | filter | How many clients had not been contacted in a previous campaign? | Manifest expects numeric 0; corrected CSV ground truth is 36954 because the script counts `pdays = 999` instead of `-1`. | Generated SQL returned 36954. Snowflake count for `pdays = -1` was 36954; count for `pdays = 999` was 0. The dataset config defines `-1` as the not-previously-contacted sentinel. | `SELECT COUNT(*) AS num_clients FROM BANK_MARKETING WHERE "pdays" = -1 LIMIT 500` | WRONG_EXPECTED |
| `join_account_details` | join | Join each marketing contact to the client's account profile details. | `status=unsupported`, answer contains `read-only questions` | `status=ambiguous`; asked for hypothetical join fields and target table. | — |
| `join_product_details` | join | Join the campaign contacts to product purchase details. | `status=unsupported`, answer contains `BANK_MARKETING` | `status=ambiguous`; asked which product details or join conditions. | — |
| `multi_senior_subscribers` | multi_step | How many clients over age 40 subscribed to a term deposit? | `numeric=2332` (CSV ground truth 2332) | `20494`; exact generated SQL returned 20494 in Snowflake. Counting rows with both `age > 40` and `y = 'yes'` returned 2332 in Snowflake. | `SELECT COUNT(CASE WHEN "age" > 40 THEN "y" ELSE NULL END) AS subscribed_over_40 FROM BANK_MARKETING LIMIT 500` | WRONG_SQL |
| `empty_unknown_job` | empty_result | Show clients whose job category is astronaut. | `status=answerable`, no rows | `status=answerable`; answer listed five clients with job `unknown`. Generated SQL returned five rows. | `SELECT * FROM BANK_MARKETING WHERE "job" = 'unknown' LIMIT 5` | WRONG_SQL |

## Numeric verification evidence

All comparison SQL ran against Snowflake using `DATAMIND_READER`; values were
also compared with the local CSV ground-truth calculation.

| Check | Snowflake result | CSV ground truth |
|---|---:|---:|
| Generated campaign SQL: `COUNT(DISTINCT campaign)` where campaign > 0 | 48 | — |
| Correct campaign row count: campaign >= 3 | 15162 | 15162 |
| Generated previous-contact filter: pdays = -1 | 36954 | 36954 |
| Manifest's previous-contact sentinel: pdays = 999 | 0 | 0 |
| Generated senior-subscriber expression | 20494 | — |
| Correct senior-subscriber count: age > 40 and y = 'yes' | 2332 | 2332 |

The previous-contact manifest expectation is wrong for the configured dataset:
the local 45211-row CSV and Snowflake both have 36954 rows with `pdays = -1`
and none with `pdays = 999`. The active schema says `-1` means not previously
contacted, while `compute_ground_truth.py` still counts `999`.
