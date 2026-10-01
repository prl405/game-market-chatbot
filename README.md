# Game Market Chatbot

A conversational chatbot for exploring Steam video game market data. It uses
Gamalytics data stored in SQLite/Turso, an OpenRouter LLM with query tools, and
the React frontend in `frontend/`, connected to the Python agent through FastAPI.

## Setup

Requires Python 3.14+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
touch .env
```

Set `OPENROUTER_API_KEY` in `.env` to enable chat. Optional settings include:

```dotenv
OPENROUTER_MODEL=openrouter/free
GAMALYTICS_API_KEY=your-api-key
DB_PATH=./data/games.db
API_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

`DB_PATH` defaults to `./data/games.db`. For Turso Cloud, set it to a
`libsql://` URL and provide `TURSO_AUTH_TOKEN`.

## Run locally

Initialise the database and load Gamalytics data if it is not already present:

```bash
uv run game-market-chatbot db init
uv run game-market-chatbot ingest gamalytics
```

Start the API from the repository root:

```bash
uv run uvicorn game_market_chatbot.api.app:app --reload --host 127.0.0.1 --port 8000
```

In another terminal, start the React frontend:

```bash
cd frontend
npm ci
npm run dev
```

Open the Vite URL (normally `http://localhost:5173`). Set
`API_CORS_ORIGINS` to a comma-separated list if the frontend uses a different
origin. The API exposes `GET /health` and `POST /api/chat`.

Assistant replies include an ordered `blocks` array. Markdown blocks contain
prose or GFM tables; chart blocks contain a validated chart specification.
This allows prose, tables, and multiple charts to appear in the intended
sequence. The legacy `text` and `chart_spec` fields remain in the response for
older clients; `chart_spec` contains only the first chart.

## Tests

```bash
uv run pytest
```

## Project structure

- `src/game_market_chatbot/agent`: OpenRouter chat agent and tool loop
- `src/game_market_chatbot/api`: FastAPI schemas, routes, and app configuration
- `src/game_market_chatbot/db`: SQLite/Turso client and schema
- `src/game_market_chatbot/ingestion`: Gamalytics data ingestion
- `src/game_market_chatbot/tools`: Reusable market query and chart-spec tools
- `frontend/`: React chat interface and chart rendering
