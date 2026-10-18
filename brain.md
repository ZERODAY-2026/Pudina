PROJECT: DataMind, a natural-language-to-data agent for the ZeroDay OSS Hacktoberfest 2026 (PS1).
Users ask questions in plain English; the system computes answers from real data in Snowflake, using Google Gemma for language tasks.

HARD RULES
- Snowflake must actually run every query at question time (no answering from local files or mocks).
- Gemma does language tasks only: classify the question, write SQL, explain results. Snowflake/SQL does all computation. Keep these two layers separate in code.
- Every answer returns: answer, plain-language explanation, assumptions, executed SQL, result rows, Snowflake query ID.
- Read-only: SELECT statements only, enforced by a SQL validator AND a read-only Snowflake role.
- Dataset-agnostic: all dataset specifics live in config/*.yaml. Switching datasets must need no code changes.
- No secrets in the repo. Credentials come from .env (provide .env.example). 
- Open source (MIT license), pinned dependencies, clear README.

STACK: Python 3.11+, snowflake-connector-python, sqlglot, pydantic, pyyaml, pytest, Streamlit UI.
Gemma is accessed through a single wrapper in src/llm.py so the backend can be swapped (Ollama or hosted API).
PROJECT: DataMind (Hacktoberfest PS1): React frontend + FastAPI backend over an existing Python pipeline (Gemma for language tasks, Snowflake for all computation).
The single source of truth between frontend and backend is docs/api_contract.md and docs/fixtures/*.json. Neither side may change response shapes without updating the contract and fixtures first.
Hard rules: no secrets, real usernames or data files in the repo; Snowflake runs every query; read-only role for the app; dataset-agnostic via config/*.yaml; Windows/PowerShell is the primary dev environment (no bash-only scripts); held-out eval questions are never used for tuning.
ROLE: BACKEND. Only modify src/, scripts/, config/, eval/, tests/, docs/ (except docs/frontend.md), requirements.txt, .env.example. Never touch frontend/.
REPO LAYOUT
datamind/
  config/ (one YAML per dataset)
  src/ (llm.py, snowflake_client.py, config_loader.py, sql_guard.py, pipeline.py, app.py)
  eval/ (questions.yaml, run_eval.py)
  scripts/ (setup.sql, load_data.py)
  docs/  tests/

WORKING STYLE: Work phase by phase. Keep code modular and typed, add docstrings and tests for each module, and tell me what to run to verify each step. Don't build ahead of the current phase.