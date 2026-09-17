# Game Market Chatbot — Implementation Plan

## Problem Statement

Build a conversational AI chatbot that answers video game market questions, backed by Gamalytics Steam data ingested into Turso (SQLite), with an LLM via OpenRouter and a Streamlit UI that renders both text and charts.

---

## Requirements

- Python/uv project targeting Turso (SQLite-compatible, local dev + Turso Cloud)
- CLI ingestion scripts that paginate through Gamalytics (`/steam-games/list`, ~130 pages × 1,000 records), handle duplicates via upsert on `steamId`, and normalize array fields
- Extensible ingestion architecture for additional API sources
- OpenRouter LLM integration with a hybrid tool-use approach: predefined query functions for common patterns + text-to-SQL fallback for open-ended questions
- Streamlit chat UI: the model decides when to display a chart alongside text responses
- Charts rendered in Streamlit using Plotly

---

## Background

- **API**: `api.gamalytic.com/steam-games/list` returns `{pages: 130, total: ~130k, result: [...], next: {limit: 1000, page: N}}`
- **Pagination**: query params `page` (0-indexed) and `limit` (default 1000); iterate until `page >= pages`
- **Unique key**: `steamId` (integer) — used for upsert/deduplication
- **Schema considerations**: `genres`, `developers`, `publishers` are arrays — stored as JSON text columns for simplicity given SQLite; query tools must account for this (see note in Task 4)
- **OpenRouter**: OpenAI-compatible API with model selection; supports function/tool calling
- **Turso**: libsql-compatible SQLite; `pyturso` already in `pyproject.toml`; works locally and in Turso Cloud with the same client
- **Streamlit**: session state holds chat history; `st.plotly_chart` renders charts inline

---

## Architecture

A three-layer architecture:

```
┌─────────────────────────────────────────┐
│              Streamlit UI               │
│  (chat input → messages → text+charts) │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│            Chat Agent Layer             │
│  LLM (OpenRouter) + Tool Dispatch       │
│  - Predefined query tools               │
│  - SQL fallback tool                    │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│            Data Layer                   │
│  Turso/SQLite DB  ←  Ingestion Scripts  │
│  (steam_games table)     (CLI)          │
└─────────────────────────────────────────┘
```

---

## Task Breakdown

### Task 1: Project Setup & Database Schema

**Objective:** Configure dependencies and define the database schema.

**Implementation:**
- Add dependencies to `pyproject.toml`: `streamlit`, `openai` (OpenRouter is OpenAI-compatible), `httpx`, `plotly`, `python-dotenv`
- Create `.env.example` with `TURSO_URL`, `TURSO_AUTH_TOKEN`, `OPENROUTER_API_KEY`, `GAMALYTICS_API_KEY`
- Create `src/game_market_chatbot/db/schema.sql` with a `steam_games` table using `steam_id` as primary key; columns for all scalar fields; `genres`, `developers`, `publishers` as `TEXT` (JSON-encoded)
- Create `src/game_market_chatbot/db/client.py` — a thin wrapper around `pyturso` that reads env vars and returns a connection
- Write a `uv run game-market-chatbot db init` CLI entry point that runs the schema

**Test:** `db init` runs without error; inspection confirms the table exists with correct columns.

---

### Task 2: Gamalytics Ingestion Script (Paginated, Deduplicated)

**Objective:** Fetch all games from Gamalytics and upsert into the database.

**Implementation:**
- Create `src/game_market_chatbot/ingestion/gamalytics.py`
- Use `httpx` to GET `https://api.gamalytic.com/steam-games/list?page={n}&limit=1000`
- Iterate pages 0 to `response["pages"] - 1`
- For each record, serialize `genres`, `developers`, `publishers` to JSON strings
- Use `INSERT OR REPLACE INTO steam_games (...)` (SQLite upsert on primary key) to handle duplicates
- Batch inserts per page for efficiency
- Print progress: `Page {n}/{total} — {count} games upserted`
- Register a `uv run game-market-chatbot ingest gamalytics` CLI entry point

**Test:** Run twice; confirm row count stabilizes (no duplicates added); check a known game's data.

---

### Task 3: Extensible Ingestion Architecture

**Objective:** Make the ingestion system pluggable for future API sources.

**Implementation:**
- Create `src/game_market_chatbot/ingestion/base.py` with an abstract `BaseIngester` class defining `ingest()` and `source_name` interface
- Refactor `gamalytics.py` to extend `BaseIngester`
- Create `src/game_market_chatbot/ingestion/__init__.py` that registers ingesters by name (e.g., `{"gamalytics": GamalyticsIngester}`)
- Update the CLI to dispatch `ingest <source>` dynamically from the registry

**Test:** Add a stub `MockIngester` in tests and confirm it can be registered and called.

---

### Task 4: Predefined Query Tools (Data Access Layer)

**Objective:** Implement typed query functions the LLM can call for common analyses.

**Implementation:**
- Create `src/game_market_chatbot/tools/queries.py` with functions including:
  - `get_top_games_by_copies_sold(limit, genre_filter)` → list of dicts
  - `get_genre_market_share()` → aggregated genre data
  - `get_publisher_class_breakdown()` → AAA/AA/Indie/Hobbyist counts
  - `get_games_by_price_range(min_price, max_price)` → list
  - `get_review_score_distribution()` → histogram buckets
- Each function runs parameterized SQL against the Turso client and returns serializable data
- Create `src/game_market_chatbot/tools/registry.py` that exposes an OpenAI-format `tools` list (JSON schema definitions) for each function

> **Implementation note — JSON array columns:** `genres`, `developers`, and `publishers` are stored as JSON-encoded text strings (e.g., `'["Simulation","Casual"]'`). Any predefined query that filters on these fields must use `LIKE '%value%'` rather than equality checks. For example, `get_top_games_by_copies_sold(genre_filter="Simulation")` must generate `WHERE genres LIKE '%Simulation%'`, not `WHERE genres = 'Simulation'`. The same applies to the text-to-SQL fallback — the system prompt should explicitly inform the LLM of this storage format so generated SQL handles it correctly.

**Test:** Call each function directly with sample params; assert results are non-empty dicts/lists with correct keys. Include a test that verifies genre filtering uses `LIKE` and returns correct results for a multi-genre game.

---

### Task 5: Text-to-SQL Fallback Tool

**Objective:** Allow the LLM to write raw SQL for open-ended questions not covered by predefined tools.

**Implementation:**
- Add a `run_sql_query(sql: str)` tool in `tools/queries.py`
- The function validates the SQL is read-only (starts with `SELECT`, no destructive keywords) and executes it via the Turso client
- Returns up to 500 rows as a list of dicts
- Add its schema definition to `tools/registry.py`
- Include a `get_schema_info()` tool that returns the table schema as a string, explicitly documenting that `genres`, `developers`, and `publishers` are JSON-encoded text arrays requiring `LIKE` for filtering

**Test:** Valid SELECT runs correctly; INSERT/DROP raises a `ValueError`.

---

### Task 6: Chat Agent with OpenRouter Integration

**Objective:** Wire the LLM to the tools so it can answer questions and decide when to chart.

**Implementation:**
- Create `src/game_market_chatbot/agent/chat.py`
- Initialize the `openai.OpenAI` client pointed at `https://openrouter.ai/api/v1` with the API key
- System prompt includes: role description, the DB schema (from `get_schema_info()`), instructions to call predefined tools first, fall back to `run_sql_query` for complex questions, and emit a `render_chart` tool call when a visualization would be valuable
- Add a `render_chart(chart_type, data, x_field, y_field, title)` tool definition in the registry (execution is handled by the UI layer, not the agent layer)
- Implement a `chat(messages: list) -> AgentResponse` function that runs the tool loop: call LLM → execute tool calls → append results → re-call LLM → return final text + optional chart spec
- `AgentResponse` is a dataclass with `text: str`, `chart_spec: dict | None`

**Test:** Mock the OpenRouter API; assert that a question like "what are the top 5 genres?" calls `get_genre_market_share` and returns a response with text.

---

### Task 7: Streamlit Chat UI

**Objective:** Build the conversational front-end that renders text and charts.

**Implementation:**
- Create `src/game_market_chatbot/app.py`
- Use `st.session_state` to persist `messages: list` (role/content pairs) and `chart_specs: list`
- Render chat history with `st.chat_message`; for each assistant message, check if an associated chart spec exists and render it with `st.plotly_chart` below the message
- `st.chat_input` sends user messages → calls `agent.chat()` → appends result to session state
- Show a spinner during LLM calls
- Add a sidebar with a "Data Info" panel showing row count and last ingestion timestamp from the DB
- Register `uv run game-market-chatbot app` as a CLI entry point that runs `streamlit run app.py`

**Test:** Load the app in a browser; send "show top 5 games by review score" and verify a text response appears.

---

### Task 8: Chart Rendering Integration

**Objective:** Fully implement chart rendering from LLM-generated chart specs.

**Implementation:**
- Create `src/game_market_chatbot/ui/charts.py` with a `render_chart(spec: dict)` function
- Support chart types: `bar`, `line`, `scatter`, `pie` using Plotly Express
- Map `spec["chart_type"]`, `spec["data"]`, `spec["x_field"]`, `spec["y_field"]`, `spec["title"]` to the appropriate `px.*` call
- Integrate into `app.py`: when `AgentResponse.chart_spec` is not None, call `render_chart` and pass the figure to `st.plotly_chart`
- Add graceful error handling if chart rendering fails (show a warning, still display the text response)

**Test:** Pass a mock bar chart spec to `render_chart` and assert it returns a valid Plotly figure.

---

## Project Structure

```
game-market-chatbot/
├── .env.example
├── pyproject.toml
├── PLAN.md
└── src/
    └── game_market_chatbot/
        ├── __init__.py          # CLI entry points
        ├── app.py               # Streamlit UI
        ├── agent/
        │   └── chat.py          # LLM + tool loop
        ├── db/
        │   ├── client.py        # Turso connection wrapper
        │   └── schema.sql       # Table definitions
        ├── ingestion/
        │   ├── __init__.py      # Ingester registry
        │   ├── base.py          # Abstract BaseIngester
        │   └── gamalytics.py   # Gamalytics implementation
        ├── tools/
        │   ├── queries.py       # Predefined + SQL fallback tools
        │   └── registry.py     # OpenAI-format tool definitions
        └── ui/
            └── charts.py        # Plotly chart renderer
```
