# Evidence collection template

Save only redacted, non-sensitive evidence. Do not include credentials, a
Snowflake username/account identifier, personal data, or downloaded source rows.
Keep the original evidence files local unless they have been reviewed for
secrets and data-license requirements.

## Snowflake query IDs

| Date (UTC) | Dataset | Purpose/question | Role | Query ID | Result summary |
|---|---|---|---|---|---|
| YYYY-MM-DD |  |  | DATAMIND_READER |  |  |
| YYYY-MM-DD |  |  | DATAMIND_READER |  |  |

## Snowsight screenshots

| Screenshot file | What it demonstrates | Redaction checked |
|---|---|---|
| `screenshots/<name>.png` | Query result / active role / table copy | Yes / No |

Before sharing a screenshot, redact account names, usernames, worksheet tabs
containing identifiers, connection details, and unrelated rows.

## Evaluation outputs

| Report file | Manifest | Run date | Passed / total | Query IDs retained |
|---|---|---|---:|---|
| `../../backend/eval/results.md` | `../../backend/eval/questions.yaml` | YYYY-MM-DD |  | Yes / No |
| `../../backend/eval/results_unseen.md` | `../../backend/eval/questions_unseen.yaml` | YYYY-MM-DD |  | Yes / No |
| `../../backend/eval/results_tpch.md` | `../../backend/eval/questions_tpch.yaml` | YYYY-MM-DD |  | Yes / No |

Record the executed command and any category-level failures here:

```text
Command:
Outcome:
Known failure or limitation:
```

See [`i2-ui-validation.md`](./i2-ui-validation.md) for the recorded live
TPC-H UI query IDs, verified join paths, and pending manual demo actions.

## Reversible data-change demo

```text
Command:
Confirmation entered:
BEFORE answer / query ID:
AFTER answer / query ID:
REVERTED answer / query ID:
Direct SQL verification:
Disposable clone dropped:
```

Keep evidence that confirms the source table was not modified and the clone was
removed. Do not submit screenshots or logs that expose Snowflake identifiers.
