# Reproduce DataMind locally

Use PowerShell from the repository root. The Python application, configs,
scripts, tests, and evaluations are under `backend/`; React remains under
`frontend/`.

## Prerequisites and setup

Install Python 3.11+, a supported Node.js LTS release (22 or newer), Git, and
PowerShell. CI also checks Node 20 compatibility. Live use needs
a Snowflake account and either Ollama with `gemma3:4b` or a compatible hosted
Gemma API.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
Push-Location frontend
npm ci
Pop-Location
```

Copy `.env.example` to `.env` and set your Snowflake values locally. Keep
`SNOWFLAKE_ROLE=DATAMIND_READER`; the loader role is separate.

Copy `scripts/setup.sql.example` to `scripts/setup.sql`, replace the
`<your_user>` placeholders in that local copy, and run it in Snowsight as
`ACCOUNTADMIN`. Never commit the generated SQL file. Start Ollama and pull
`gemma3:4b` when using the local model:

```powershell
ollama pull gemma3:4b
```

## Load Dataset A

Download and extract the semicolon-separated Bank Marketing CSV locally:

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
python -m scripts.verify_live
Pop-Location
```

The loaded bank table should contain 45,211 rows. Source and attribution
details are documented in [`datasets.md`](./datasets.md). The downloaded data
and Snowflake credentials are not repository files.

## Start the application

From the repository root, use `.\scripts\dev.ps1` to start FastAPI on port 8000
and Vite on port 5173, then open `http://localhost:5173`. To build and serve
the frontend and API from one port, use `.\scripts\build_and_serve.ps1` and
open `http://localhost:8000`.

For a direct API development server, run from the backend directory:

```powershell
Push-Location backend
python -m uvicorn src.api:app --reload --port 8000
Pop-Location
```

The endpoints and exact request/response shape are in
[`api_contract.md`](./api_contract.md). The reader role must have access to
`SNOWFLAKE_SAMPLE_DATA.TPCH_SF1` to query Dataset B.

## Evaluation and automated tests

Live evaluations use real Snowflake and Gemma. Bank ground truth is calculated
independently with pandas from the local CSV. TPC-H ground truth is obtained
with the hand-written SQL in the evaluation tools; it is not generated through
the natural-language pipeline.

```powershell
Push-Location backend
python -m eval.compute_ground_truth --csv data\bank-marketing\bank+marketing\bank-full.csv
python -m eval.run_eval
python -m eval.run_eval --manifest eval\questions_unseen.yaml `
  --report eval\results_unseen.md
python -m eval.run_tpch_eval
python -m pytest -q
Pop-Location

Push-Location frontend
npm run lint
npm test
npm run build
Pop-Location
```

The account owner should preserve resulting reports and query IDs after
reviewing them for sensitive data. The checked-in evaluation reports record
prior runs, not a guarantee of future model output. See
[`testing.md`](./testing.md) for accuracy and limitations.

## Reversible demo

First run the no-write preview, then follow the prompt and confirm before any
loader write:

```powershell
Push-Location backend
python -m scripts.demo_data_change --dry-run
python -m scripts.demo_data_change
Pop-Location
```

The demo uses a disposable Snowflake clone and removes its tagged row; it never
updates the source table. The manual Snowsight/React variant and cleanup
instructions are in [`demo_data_change.md`](./demo_data_change.md).
