# DataMind

DataMind answers natural-language questions about configured Snowflake datasets.
The React frontend sends questions to a FastAPI backend. Gemma classifies each
question, proposes SQL, and explains returned rows; a SQL guard validates the
query, and Snowflake executes it with the read-only `DATAMIND_READER` role.
Answers include the SQL and Snowflake query ID as evidence.

## Features

- React + TypeScript chat interface with dataset selection, saved chats, service
  health, and expandable SQL/result evidence.
- Dataset-specific tables, columns, examples, and join keys in YAML.
- SQL validation, configured table/join scoping, and read-only Snowflake access.
- Dataset-neutral FastAPI API with a versioned contract and JSON fixtures.
- Local Ollama/Gemma or compatible hosted Gemma endpoint.
- Evaluation tools with independent pandas ground truth for Bank Marketing and
  hand-written SQL ground truth for TPC-H.
- Loader-role separation and an optional reversible change demo that edits a
  Snowflake copy, not the source table.

## Architecture

```text
React UI -> FastAPI -> Pipeline -> Gemma (classify / propose SQL)
                              -> SQL guard -> Snowflake reader role
                              <- rows + query ID <- Snowflake
                              -> Gemma (explain returned rows)
```

Gemma handles language only; Snowflake executes each question's SQL and is the
source of computed values. `DATAMIND_LOADER` is reserved for dataset loading
and the reversible demo. See [architecture](docs/architecture.md) and the
[API contract](docs/api_contract.md).

## Prerequisites

- Python 3.11 or newer.
- A supported Node.js LTS release (22 or newer) and npm. CI also checks Node
  20 for compatibility.
- Snowflake account (a trial account is sufficient if it provides the required
  sample data and role/warehouse privileges).
- Ollama with `gemma3:4b` pulled locally, or a compatible hosted Gemma API.
- Git and PowerShell on Windows for the documented launcher scripts.

Dataset source, licensing, and attribution are documented in
[docs/datasets.md](docs/datasets.md). **Attribution:** see the UCI Cite-button
reference in [docs/datasets.md](docs/datasets.md).

## Setup

Run commands from the repository root unless a step says otherwise.

### 1. Install dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements.txt
Push-Location frontend
npm ci
Pop-Location
```

### 2. Configure Snowflake roles

Make a local copy of the setup template, replace `<your_user>` with your
Snowflake username in that local copy, and run it in Snowsight as
`ACCOUNTADMIN`:

```powershell
Copy-Item scripts\setup.sql.example scripts\setup.sql
```

The script creates an XSMALL warehouse with auto-suspend, a SELECT-only
`DATAMIND_READER`, and a separate `DATAMIND_LOADER` for loading and the
disposable-copy demo. Keep `scripts\setup.sql` local; it is gitignored. See
[Snowflake and Gemma setup](docs/snowflake_and_gemma.md).

### 3. Configure credentials and Gemma

```powershell
Copy-Item .env.example .env
```

Fill in the Snowflake account, username, password, and loader role locally.
Keep `SNOWFLAKE_ROLE=DATAMIND_READER`. The defaults select Ollama and
`gemma3:4b`; install Ollama and pull the model if needed:

```powershell
ollama pull gemma3:4b
```

Never commit `.env`, `scripts\setup.sql`, credentials, account identifiers, or
usernames. For a hosted model, configure the API settings in `.env` as described
in [Snowflake and Gemma](docs/snowflake_and_gemma.md).

### 4. Download and load Bank Marketing

The source CSV is downloaded locally and is not committed. From the repository
root:

```powershell
New-Item -ItemType Directory -Force backend\data | Out-Null
Invoke-WebRequest `
  -Uri "https://archive.ics.uci.edu/static/public/222/bank+marketing.zip" `
  -OutFile "backend\data\bank-marketing.zip"
Expand-Archive "backend\data\bank-marketing.zip" `
  -DestinationPath "backend\data\bank-marketing" -Force
Push-Location backend
python -m scripts.load_data `
  "data\bank-marketing\bank+marketing\bank-full.csv" BANK_MARKETING
python -m scripts.count_rows BANK_MARKETING
Pop-Location
```

The CSV is semicolon-delimited; the loader verifies its final row count. If the
archive extracts to a different subdirectory, pass that extracted `bank-full.csv`
path to `load_data.py`.

### 5. Verify live services

Start Ollama (or the hosted endpoint), then run:

```powershell
Push-Location backend
python -m scripts.verify_live
Pop-Location
```

The live verifier checks configuration, the reader connection and expected
45,211-row count, reader write rejection, Gemma text/JSON output, three pipeline
questions, and live edge cases. It stops at the first failure and reports an
action. Live verification needs real Snowflake and Gemma configuration;
automated tests do not.

### 6. Start the app

For the API and Vite development servers:

```powershell
.\scripts\dev.ps1
```

Open `http://localhost:5173`. To build the React app and serve frontend plus API
from one port:

```powershell
.\scripts\build_and_serve.ps1
```

Then open `http://localhost:8000`. The frontend uses the real API by default.
The Vite proxy and opt-in mock mode are described in
[frontend documentation](docs/frontend.md).

## Configuration

- Backend application: [`backend/src/`](backend/src/)
- Dataset schemas: [`backend/config/`](backend/config/)
- Backend utilities: [`backend/scripts/`](backend/scripts/)
- Evaluations: [`backend/eval/`](backend/eval/)
- Backend tests: [`backend/tests/`](backend/tests/)
- Frontend: [`frontend/`](frontend/)
- API contract and fixtures: [`docs/api_contract.md`](docs/api_contract.md)
  and [`docs/fixtures/`](docs/fixtures/)
- Environment template: [`.env.example`](.env.example)

Add a dataset by defining its tables, columns, example values, and allowed join
keys in a new YAML file under `backend/config/`. The API discovers configured
datasets automatically. Review [datasets](docs/datasets.md) and
[architecture](docs/architecture.md) before adding data sources.

## Troubleshooting

- **`ModuleNotFoundError: src`:** run backend Python modules with the backend
  directory as the working directory, for example `Push-Location backend` then
  `python -m scripts.verify_live`.
- **Snowflake authentication/privilege failures:** check the `.env` connection
  values, `DATAMIND_READER` grants, selected warehouse, and account-level
  access. Do not grant write privileges to the reader role.
- **Loader failures:** confirm `SNOWFLAKE_LOAD_ROLE=DATAMIND_LOADER`, loader
  schema privileges, the CSV path, and the semicolon-delimited file.
- **Gemma health/down or slow response:** ensure Ollama is running and the
  configured model is available, or check the hosted endpoint and timeout.
- **Frontend cannot reach API:** verify port 8000, the Vite proxy, and
  `CORS_ORIGINS` for custom origins. `scripts\dev.ps1` refuses occupied ports.
- **No TPC-H results:** `SNOWFLAKE_SAMPLE_DATA.TPCH_SF1` must be accessible to
  the reader role in the Snowflake account.
- **Demo clone remains after interruption:** follow the guarded cleanup steps
  in [the data-change demo guide](docs/demo_data_change.md); never write to the
  source Bank Marketing table.

## Evaluation and tests

Install dependencies as in Setup. Automated tests require no Snowflake or Gemma
credentials:

```powershell
Push-Location backend
python -m pytest -q
Pop-Location

Push-Location frontend
npm run lint
npm test
npm run build
Pop-Location
```

Live Bank Marketing evaluation needs the CSV plus live Snowflake/Gemma:

```powershell
Push-Location backend
python -m eval.compute_ground_truth --csv data\bank-marketing\bank+marketing\bank-full.csv
python -m eval.run_eval
python -m eval.run_eval --manifest eval\questions_unseen.yaml `
  --report eval\results_unseen.md
python -m eval.run_tpch_eval
Pop-Location
```

The recorded reports currently show Bank Marketing original **14/20 (70%)**
(held-out **4/5 (80%)**), unseen **15/20 (75%)**, and TPC-H **4/10 (40%)**.
These are historical live-run results, not promises of repeatability; the
TPC-H grouped-label grader has a documented correctness limitation. Read
[testing results and limitations](docs/testing.md) and the
[reproduction guide](docs/reproduce.md) before interpreting them.

## Screenshots and demo

Screenshot guidance and current evidence notes are in
[docs/frontend.md](docs/frontend.md) and
[docs/evidence/](docs/evidence/). See the timed
[demo script](docs/demo_script.md) for a five-minute walkthrough.

## Documentation

- [Architecture](docs/architecture.md)
- [API contract](docs/api_contract.md)
- [Datasets and attribution](docs/datasets.md)
- [Snowflake and Gemma](docs/snowflake_and_gemma.md)
- [Testing, evaluation, and limitations](docs/testing.md)
- [Reproduce locally](docs/reproduce.md)
- [Contribute (draft)](docs/contribution.md)
- [Frontend and screenshot notes](docs/frontend.md)
- [Reversible data-change demo](docs/demo_data_change.md)
- [Evidence template](docs/evidence/README.md)
- [Final submission checklist](docs/final_checklist.md)
