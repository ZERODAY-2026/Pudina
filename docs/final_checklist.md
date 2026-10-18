# Final submission checklist

This checklist points reviewers to repository evidence and marks actions that
cannot be completed or proven by repository inspection alone. Criterion text for
P1–P3 and S1–S10 was not included in the repository; those rows therefore map
to the closest implementation evidence without claiming rubric compliance.

## Gates

| Gate | Evidence | Status / remaining action |
|---|---|---|
| G1 — License | [`LICENSE`](../LICENSE) | MIT license file is present; reviewer should confirm it matches the submission requirements. |
| G2 — Reproducible demo | [`README.md`](../README.md), [`reproduce.md`](reproduce.md), [`demo_script.md`](demo_script.md), [`setup.sql.example`](../scripts/setup.sql.example) | A sanitized working-tree snapshot passed dependency install, frontend build, backend/frontend tests, and local app smoke checks. This was not a literal Git clone; repeat from a fresh clone after committing. Snowflake provisioning and live evaluation remain owner actions. |
| G3 — Real system | [`architecture.md`](architecture.md), [`api_contract.md`](api_contract.md), [`backend/src/`](../backend/src/), [`docs/evidence/i2-ui-validation.md`](evidence/i2-ui-validation.md) | Real React/API queries and evidence panels were observed for TPC-H. Bank full verifier has historically failed after earlier checks; inspect [`testing.md`](testing.md) for the recorded failure. |
| G4 — Dataset disclosure | [`datasets.md`](datasets.md), [`backend/config/`](../backend/config/) | Bank source/license/attribution and in-account TPC-H disclosure documented. |
| G5 — No secrets | [`.env.example`](../.env.example), [`.gitignore`](../.gitignore), [evidence notes](evidence/README.md), [`testing.md`](testing.md) | Eight reachable commits had no detected credential/account or generic secret-pattern matches and no tracked data files. The local ignored setup SQL contains the configured username; see the scan details in `testing.md`. |

## Project and system evidence

| ID | Evidence pointer | Review note |
|---|---|---|
| P1 | [`README.md`](../README.md), [`architecture.md`](architecture.md) | Overview and architecture documentation; exact rubric wording is external. |
| P2 | [`frontend/`](../frontend/), [`docs/frontend.md`](frontend.md), [`backend/src/api.py`](../backend/src/api.py) | Frontend/API implementation and usage documentation; compare with external criterion. |
| P3 | [`backend/tests/`](../backend/tests/), [`frontend/src/`](../frontend/src/) | Automated tests and frontend implementation; compare with external criterion. |
| S1 | [`api_contract.md`](api_contract.md), [`docs/fixtures/`](fixtures/) | API schema and shared fixtures. |
| S2 | [`backend/src/api.py`](../backend/src/api.py), [`backend/tests/test_api.py`](../backend/tests/test_api.py) | FastAPI routes, status mapping, validation, and API tests. |
| S3 | [`backend/src/pipeline.py`](../backend/src/pipeline.py), [`backend/src/prompts.py`](../backend/src/prompts.py) | Classification, SQL proposal, and row-grounded explanation path. |
| S4 | [`backend/src/sql_guard.py`](../backend/src/sql_guard.py), [`backend/tests/test_sql_guard.py`](../backend/tests/test_sql_guard.py) | Read-only SQL, table/join scope, and result-limit validation. |
| S5 | [`backend/src/snowflake_client.py`](../backend/src/snowflake_client.py), [`snowflake_and_gemma.md`](snowflake_and_gemma.md) | Snowflake reader role and service separation. |
| S6 | [`backend/config/`](../backend/config/), [`datasets.md`](datasets.md) | Dataset-specific schema, descriptions, and join metadata. |
| S7 | [`backend/eval/`](../backend/eval/), [`testing.md`](testing.md) | Evaluation manifests, results, and known grading limitations. |
| S8 | [`frontend/src/`](../frontend/src/), [`frontend/package.json`](../frontend/package.json) | React UI, contract validators, scripts, and tests. |
| S9 | [`docs/evidence/`](evidence/), [`demo_script.md`](demo_script.md) | Redacted live query evidence and presentation outline; manual captures remain owner work. |
| S10 | [`README.md`](../README.md), [`reproduce.md`](reproduce.md), [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) | Setup/reproduction instructions and credential-free CI; verify CI status on the hosted repository. |

## PS1 extras

| Deliverable | Evidence | Status / remaining action |
|---|---|---|
| Grounding evidence | [`docs/evidence/i2-ui-validation.md`](evidence/i2-ui-validation.md), [`api_contract.md`](api_contract.md) | Two TPC-H UI query IDs and returned rows recorded. Capture and review screenshots before sharing. |
| Reversible data-change demo | [`demo_data_change.md`](demo_data_change.md), [`backend/scripts/demo_data_change.py`](../backend/scripts/demo_data_change.py) | Script and manual process documented. Owner must perform the manual Snowsight clone/insert/revert/drop sequence if demonstrating data mutation. |
| Snowflake/Gemma roles | [`snowflake_and_gemma.md`](snowflake_and_gemma.md), [`scripts/setup.sql.example`](../scripts/setup.sql.example) | Role separation and setup template documented; owner must configure their Snowflake account. |
| Evaluation set | [`backend/eval/questions.yaml`](../backend/eval/questions.yaml), [`backend/eval/questions_unseen.yaml`](../backend/eval/questions_unseen.yaml), [`backend/eval/questions_tpch.yaml`](../backend/eval/questions_tpch.yaml), [`testing.md`](testing.md) | Manifests and historical results are present. Live runs need the dataset, Snowflake, and Gemma. |
| Setup script | [`scripts/setup.sql.example`](../scripts/setup.sql.example) | Template is committed. Owner must create a local copy, replace `<your_user>`, and run it as `ACCOUNTADMIN`; never commit the local copy. |

## Owner actions before submission

- After committing, clone the final branch to a clean directory and complete
  the README workflow there, including frontend install/build and
  backend/frontend tests. The current sanitized snapshot was not a Git clone.
- Configure Snowflake and Gemma privately, run `backend/scripts/verify_live.py`
  through its documented module command, and retain redacted query-ID evidence.
- If the manual data-change segment will be shown, use only the disposable
  clone, verify before/after/reverted values directly, drop the clone, and
  remove any temporary dataset config.
- Capture and redact screenshots; do not disclose usernames, account IDs,
  credentials, or unrelated data.
- Confirm hosted CI is green and provide the authoritative P1–P3/S1–S10 rubric
  descriptions for a criterion-by-criterion sign-off.
