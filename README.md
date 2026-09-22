# Game Market Chatbot

A conversational chatbot for exploring Steam video game market data. It uses
Gamalytics data stored in SQLite/Turso, an OpenRouter LLM with query tools, and
a Streamlit interface with optional Plotly charts.

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
```

`DB_PATH` defaults to `./data/games.db`. For Turso Cloud, set it to a
`libsql://` URL and provide `TURSO_AUTH_TOKEN`.

## Run locally

Initialise the database and load Gamalytics data:

```bash
uv run game-market-chatbot db init
uv run game-market-chatbot ingest gamalytics
```

Start the Streamlit app:

```bash
uv run game-market-chatbot app
```

Then open the local URL shown by Streamlit and ask questions about game sales,
genres, prices, publishers, or review scores.

## Tests

```bash
uv run pytest
```

## Project structure

- `src/game_market_chatbot/agent`: OpenRouter chat agent and tool loop
- `src/game_market_chatbot/db`: SQLite/Turso client and schema
- `src/game_market_chatbot/ingestion`: Gamalytics data ingestion
- `src/game_market_chatbot/tools`: Reusable market query tools
- `src/game_market_chatbot/ui`: Plotly chart rendering
- `src/game_market_chatbot/app.py`: Streamlit chat UI
