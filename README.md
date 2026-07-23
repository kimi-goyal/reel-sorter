# Recipe Box

**An AI-powered personal cookbook that turns saved Instagram cooking reels into a searchable, chapter-organized recipe collection — with an agentic assistant that can answer questions about what's in it.**

Saved cooking reels are unstructured and effectively unsearchable once they scroll past your feed. Recipe Box ingests a saved Instagram collection, extracts each recipe's real ingredients by transcribing the reel's audio and structuring it with an LLM, organizes everything into ingredient-based "chapters," and layers an AI agent on top that can answer natural-language questions ("what can I make with paneer?") by querying the data directly.

> **Status note:** ingestion currently registers new reels as `pending`; the extraction pipeline (`scripts/pipeline.py`) must be run afterward to actually populate real recipe/ingredient data for them. This is by design — ingestion and extraction are deliberately separate steps so a batch of newly saved reels can be reviewed/queued before the (rate-limited, slower) extraction step runs against them.

---

## Overview

The app has four working parts:

1. **Ingestion** (`ai_engine.py: ingest_user_instagram_collection`) — parses an exported Instagram `saved_collections.json`, deduplicates against existing reels by URL, and registers new ones as `pending`.
2. **Extraction pipeline** (`scripts/pipeline.py`) — for each pending reel: downloads the audio via `yt-dlp`, transcribes it with Groq-hosted Whisper-large-v3, then sends the transcript + caption to Llama 3.3 70B to extract a structured recipe (name, common ingredients, special/key ingredients), and marks the reel `processed`.
3. **Cookbook + Ask the Box + Grocery Planner** (`cookbook_app.py`) — a Streamlit interface with three tabs: chapter-organized recipe browsing (grouped by key ingredient), an agentic chat assistant, and a weekly grocery list built from selected recipes.
4. **Agent orchestration** (`ai_engine.py: orchestrate_agent_response`) — routes each chat question to either a structured SQL tool or a semantic vector search tool depending on what the question needs, then synthesizes a natural-language answer from the result.

---
```

## Architecture
┌───────────────────────┐
│ Instagram Export        │
│ (saved_collections.json)│
└───────────┬───────────┘
            │ upload via sidebar
            ▼
┌───────────────────────┐
│ Ingestion                │
│ (dedupe by URL,           │
│  status = 'pending')      │
└───────────┬───────────┘
            │  (run manually / on a schedule)
            ▼
┌───────────────────────┐
│ Extraction Pipeline      │
│ (scripts/pipeline.py)    │
│                            │
│ 1. yt-dlp → audio          │
│ 2. Whisper-large-v3        │
│    (Groq) → transcript     │
│ 3. Llama 3.3 70B → JSON    │
│    {recipe_name,            │
│     common[], special[]}   │
└───────────┬───────────┘
            │ status → 'processed'
            ▼
┌───────────────────────┐        ┌───────────────────────┐
│ SQLite                  │───────▶│ ChromaDB                │
│ (reels, recipes,         │  sync  │ (vector embeddings of   │
│ ingredients)             │        │ recipe transcripts,      │
└───────────┬───────────┘        │ all-MiniLM-L6-v2)        │
            │                       └───────────┬───────────┘
            │                                     │
            ▼                                     ▼
┌─────────────────────────────────────────────────────────┐
│               Agent Orchestrator (Groq, tool-calling)     │
│  routes each query to either:                              │
│   • tool_sql_query_executor        (exact counts/lookups)  │
│   • tool_semantic_vector_search    (fuzzy/conceptual)       │
└───────────────────────────┬───────────────────────────┘
                              ▼
                  ┌───────────────────────┐
                  │ Streamlit UI            │
                  │ (Cookbook / Ask the Box │
                  │ / Grocery Planner)      │
                  └───────────────────────┘
```
---

## Features

- Ingests a real Instagram data export (`saved_collections.json`), with URL-based deduplication so re-uploading the same collection never creates duplicate reels
- Automated recipe extraction: downloads reel audio, transcribes it (Whisper-large-v3), and extracts structured ingredients/recipe name via Llama 3.3 70B — no manual tagging
- Chapter-based cookbook view, grouped dynamically by each recipe's key ("special") ingredient
- Agentic chat assistant that decides per-question whether to run an exact SQL lookup or a semantic vector search, rather than using one fixed retrieval strategy
- Grocery planner that builds a shopping list from selected recipes, split into "buy" (special ingredients) vs. "check your pantry" (common staples)

---

## Tech Stack
-----------------------------------------------------------------------------------------------
| Layer            | Technology                                                               |
|------------------|--------------------------------------------------------------------------|
| Interface        | Streamlit                                                                |
| Audio extraction | yt-dlp                                                                   |
| Speech-to-text   | Groq-hosted Whisper-large-v3                                             |
| Storage          | SQLite                                                                   |
| Vector store     | ChromaDB (`all-MiniLM-L6-v2` embeddings via Sentence Transformers)       |
| LLM / Agent      | Groq API (Llama 3.3 70B — function/tool calling + structured extraction) |


---

## API Overview

**FastAPI backend (`backend/main.py`)** — built, but not currently called by the Streamlit app, which reads SQLite directly. Kept as a starting point for a future decoupled frontend.
----------------------------------------------------------------------------------------------------------------------------------------
| Method | Endpoint                          | Description                                                                             |
|--------|-----------------------------------|-----------------------------------------------------------------------------------------|
| `GET`  | `/api/recipes`                    | Returns non-skipped recipes with reel details and ingredients split into common/special |
| `POST` | `/api/recipes/{recipe_id}/status` | Marks a recipe approved (1) or skipped (0)                                              |


**Agent tools (internal, not HTTP endpoints — used by `orchestrate_agent_response`)**

| Tool | Purpose |
|---|---|
| `tool_sql_query_executor` | Runs a read-only SQL query the LLM generates itself, for exact counts/lookups over recipes, reels, ingredients |
| `tool_semantic_vector_search` | Fuzzy/conceptual search over recipe transcripts via ChromaDB |

---

## Database Schema Summary

**reels** — `id`, `url` (unique), `caption`, `hashtags`, `creator_name`, `creator_username`, `collection_name`, `status` (`pending` / `processed` / `failed`), `created_at`

**recipes** — `id`, `reel_id` (FK → reels), `recipe_name`, `transcript`, `approved` (`NULL` = unreviewed, `1` = approved, `0` = skipped), `tried_at`

**ingredients** — `id`, `recipe_id` (FK → recipes), `name`, `category` (`special` = key/buy ingredient, `common` = pantry staple)

---

## Local Setup

```bash
git clone https://github.com/kimi-goyal/recipe-box.git
cd recipe-box

python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env

python scripts/init_db.py       # creates the SQLite schema

streamlit run cookbook_app.py
```

Then, in the app sidebar: enter your collection name and upload your Instagram `saved_collections.json` export — this registers new reels as `pending`.

Run the extraction pipeline to turn pending reels into real recipes:

```bash
python scripts/pipeline.py
```

**System dependencies:** `yt-dlp` and `ffmpeg` must be installed and available on your `PATH` (`pip install yt-dlp` covers the Python side; install `ffmpeg` separately via your OS package manager, e.g. `brew install ffmpeg` or `apt install ffmpeg`).

---

## Environment Variables

```env
GROQ_API_KEY=your_groq_api_key
```

---

## Screenshots

- `screenshots/cookbook-view.png` — Chapter-organized recipe cards
  <img width="958" height="437" alt="image" src="https://github.com/user-attachments/assets/0be3af91-3a2a-477f-a74c-c748648890cd" />

- `screenshots/ask-the-box.png` — Agent chat answering an ingredient-based question
- <img width="692" height="397" alt="image" src="https://github.com/user-attachments/assets/8b1ba26d-0f63-41e5-bc55-fce50d2dd8b4" />

- `screenshots/grocery-planner.png` — Shopping list split into buy vs. pantry
- <img width="951" height="434" alt="image" src="https://github.com/user-attachments/assets/6ac4b634-1e3d-4447-a6b3-e69459aed66d" />


---

## Deployment

Live demo: https://create-cookbook-hro9qghatignxtmltodpds.streamlit.app/

---

## Future Improvements

- Auto-trigger `pipeline.py` after a successful upload instead of requiring a manual/separate run
- Replace the hardcoded `COMMON_INGREDIENTS` set in `pipeline.py` with an LLM judgment call so categorization generalizes beyond the current fixed list
- Clear the Chroma vector collection in `reset_pipeline.py`, not just SQLite, to avoid stale embeddings after a reset
- Centralize `DB_PATH`/`CHROMA_PATH` into a single config module instead of separate definitions per file
- Wire the FastAPI backend into the Streamlit frontend, or drop it if the direct-SQLite approach stays permanent
- Add authentication if this ever moves beyond a single-user local tool
- Support direct Instagram API ingestion instead of manual export upload

---

## Why This Project Is Technically Interesting

The core pipeline chains three distinct AI capabilities on unstructured, real-world input: **audio extraction** from a social video URL (`yt-dlp`), **speech-to-text** on that audio (Whisper-large-v3), and **structured extraction** from the resulting transcript plus caption (Llama 3.3 70B, prompted to return strict JSON with ingredient categorization). Each stage has its own failure modes — downloads fail, transcription can come back empty, the LLM can return malformed JSON — and the pipeline is built to fail gracefully per-reel (marking status accordingly) rather than crashing the whole batch.

On top of that, the **agent's routing decision** in "Ask the Box" is the second interesting piece: given a natural-language question, it dynamically decides whether it needs an exact structured answer (SQL) or a fuzzy conceptual one (vector search) rather than committing to one retrieval strategy up front. Together, this is a compact but genuine example of a multi-stage AI pipeline feeding a tool-using agent over a hybrid structured/unstructured data store — the same pattern behind much larger production RAG and agentic systems.
