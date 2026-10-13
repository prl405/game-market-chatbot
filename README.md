# Game Market Chatbot

A personal chatbot for exploring Steam game-market data with natural-language questions. A Python agent queries a local SQLite-compatible database, OpenRouter supplies the language model, and a React frontend communicates with the agent through a FastAPI backend. The frontend renders charts returned by the agent.

## Prerequisites

- Python 3.14 or newer
- [uv](https://docs.astral.sh/uv/) for Python environments and dependencies
- Node.js and npm for the React frontend (use a current Node.js LTS release)
- Internet access to download the dataset and to use OpenRouter chat

## API keys and configuration

An `OPENROUTER_API_KEY` is required to use chat. Create a key through [OpenRouter](https://openrouter.ai/) and add it to a `.env` file in the repository root. The default model is `openrouter/free`; set `OPENROUTER_MODEL` to another OpenRouter model slug if desired.

```dotenv
OPENROUTER_API_KEY=your-openrouter-api-key
# OPENROUTER_MODEL=openrouter/free
```

The database is local by default at `./data/games.db`, so no database credentials are needed for local development. To use a remote Turso database instead, set `DB_PATH` to its `libsql://` URL and provide `TURSO_AUTH_TOKEN`. The local API's CORS settings already allow the standard Vite origins; set `API_CORS_ORIGINS` to a comma-separated list if you use a different frontend origin.

## Install and ingest local data

Run these commands from the repository root. `uv sync` creates the Python environment and installs the application and test dependencies.

```bash
uv sync
```

Initialize the local database schema, then download and ingest the Gamalytics Steam-game dataset:

```bash
uv run game-market-chatbot db init
uv run game-market-chatbot ingest gamalytics
```

Ingestion fetches the catalog in pages and upserts records into `data/games.db`. The full catalog is roughly 130,000 games and requires about 130 requests; availability and request limits depend on the data provider. Re-running ingestion updates existing records rather than duplicating them. You can set `DB_PATH` in `.env` to store the database elsewhere.

## Run the application

Add the OpenRouter key to `.env` before using chat. Start the API from the repository root:

```bash
uv run uvicorn game_market_chatbot.api.app:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal, install and start the frontend:

```bash
cd frontend
npm ci
npm run dev
```

Open the Vite URL printed in the terminal (normally `http://localhost:5173`). The API provides `GET /health` and `POST /api/chat` at `http://127.0.0.1:8000`.

## Tests

### Test layout

```text
tests/
  conftest.py       # fixtures shared across suites (seeded in-memory database)
  unit/             # isolated, mocked tests, organised by source module
    agent/ api/ db/ ingestion/ tools/
  integration/      # HTTP-boundary (FastAPI) and SQL-against-a-database tests
  eval/             # opt-in live LLM evaluations (not part of routine runs)
frontend/src/       # Vitest tests are co-located with the code they test
                    # (components/*.test.tsx, components/charts/*, services/*)
```

### Routine checks

These are deterministic: no network access, credentials, or populated database are needed.

```bash
# Backend, from the repository root (runs tests/unit and tests/integration)
uv run pytest
uv run pytest tests/unit/tools        # a single suite while iterating

# Frontend, from frontend/
npm test
npm run lint
npm run build
```

### Live LLM evaluation (opt-in)

The evaluation in `tests/eval` is excluded from `uv run pytest`. It makes real OpenRouter requests against the local database and is non-deterministic. **Warning: it runs 10 questions through the agent, needs network access, and can consume a high number of API tokens.** Only run it when you intend to incur that usage, and make sure the database has been ingested and `OPENROUTER_API_KEY` is configured:

```bash
RUN_LLM_EVAL=1 uv run pytest tests/eval/test_answer_quality.py -v
```

## Project structure

- `src/game_market_chatbot/agent`: OpenRouter chat agent and tool loop
- `src/game_market_chatbot/api`: FastAPI schemas, routes, and app configuration
- `src/game_market_chatbot/db`: SQLite/Turso client and schema
- `src/game_market_chatbot/ingestion`: Gamalytics data ingestion
- `src/game_market_chatbot/tools`: Market queries and chart-spec tools
- `frontend/`: React chat interface and chart rendering
- `tests/unit`, `tests/integration`: deterministic Python tests (shared fixtures in `tests/conftest.py`)
- `tests/eval`: opt-in live LLM evaluations, excluded from `uv run pytest`

## Data source and project use

The Steam game-market data used for this project was gathered from [Gamalytics](https://gamalytic.com/) through its free tier game-list API endpoint. This is an independent personal project, not affiliated with Gamalytics or Steam, and it is for personal and educational use only, not for making money. Please consult the data provider's current terms before using or redistributing the data.
