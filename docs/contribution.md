# Contribution guide — draft

_Draft for the project maintainer to review and edit before publishing._

## Before opening a change

- Confirm the change is in backend scope. Do not modify frontend code as part
  of a backend-only contribution.
- Keep credentials, personal Snowflake identifiers, downloaded datasets, query
  exports, and screenshots containing account details out of Git.
- Prefer configuration-driven behavior over dataset-name or table-name
  branches. Add dataset descriptions, column semantics, sample values, join
  keys, and user examples to a new `backend/config/*.yaml`.
- Keep Gemma responsible for language tasks and Snowflake responsible for
  computing results. Do not answer data questions from local files or
  hard-coded expected values.
- Preserve read-only query enforcement and keep `DATAMIND_READER` separate
  from `DATAMIND_LOADER`. Application query code must never use the loader
  role.

## Tests and evaluation

Before submitting, run the relevant focused tests and then:

```powershell
Push-Location backend
python -m pytest -q
Pop-Location
```

For API behavior changes, update `docs/api_contract.md` and its JSON fixtures
in the same change. Keep evaluation targets independent of the natural-language
pipeline: use a separate source calculation or explicit SQL, and retain query
IDs for live evidence. Do not use held-out questions to tune prompts or
implement question-specific branches.

Live checks need configured Snowflake and Gemma services. Report the command
run, pass/fail outcome, query IDs, and limitations; do not replace missing live
results with mock output.

## Pull-request checklist

- [ ] Change is limited to its stated backend/documentation scope.
- [ ] No local data, credentials, usernames, account identifiers, or unredacted
      evidence files are committed.
- [ ] Schema/config and examples accurately describe the selected dataset.
- [ ] SQL remains read-only, table-scoped, and tested, including fully qualified
      table names when relevant.
- [ ] Focused tests and the full test suite are reported.
- [ ] Live results and known failures are described accurately.
- [ ] API contract and fixtures are updated together if a response shape changes.
- [ ] Documentation links and reproduction commands were checked.
