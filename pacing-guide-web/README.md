# pacing-guide-web

Local **FastAPI** app with a small static UI for the **map-pacing-guide** Claude skill pipeline (local `bin/` scripts): upload state pacing materials, extract structured pacing via **OpenRouter → Claude**, fetch Khan Academy standard→content data (**GetSetOfStandards** or an optional offline **CCSS.Math** CSV), and produce a **mapped `.xlsx`**.

## Prerequisites

- **Python 3** — use this project’s **`.venv`** after `pip install -r requirements.txt`. The app runs skill subprocesses with **`sys.executable`** so scripts see the same packages (**`openpyxl`**, etc.).
- **map-pacing-guide `bin/`** — `ka-init`, `ka-parse-pacing-guide`, `ka-map-pipeline`, etc. Point **`MAP_PACING_SKILL_BIN`** at that directory.
- **`playwright-cli`** on `PATH` when the skill needs browser/hash discovery (`ka-browse`, hash discovery). If `ka-init` only complains about Playwright, follow the skill’s `references/setup.md` or run **`bin/setup`** in the skill repo.

## Setup

```bash
cd pacing-guide-web
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit **`.env`**: at minimum **`OPENROUTER_API_KEY`** and **`MAP_PACING_SKILL_BIN`**.  
`.env` is loaded from **this directory** (`main.py` uses `ROOT / ".env"`), even if you start the shell elsewhere—as long as Python imports `main` correctly.

## Run

**Start the server from the `pacing-guide-web` directory** (this folder as the process working directory). The app serves `static/` relative to that path; running uvicorn from a parent folder can break static files and reload behavior.

```bash
cd pacing-guide-web
source .venv/bin/activate
uvicorn main:app --reload --port 8010
```

Open **http://127.0.0.1:8010** (or `http://localhost:8010`).

**Stop / free the port** (macOS/Linux):

```bash
lsof -ti :8010 | xargs kill -9
```

### Check readiness

**`GET /health`** — no secrets returned; useful fields:

| Field | Meaning |
|--------|---------|
| `openrouter_configured` | `OPENROUTER_API_KEY` is set |
| `skill_bin` / `skill_bin_ready` | Path to skill `bin` and whether `ka-init` exists there |
| `env_file_present` | `.env` exists beside `main.py` |
| `ka_offline_ccss_usable` | `KA_CCSS_MATH_CSV` points at an existing file |
| `ka_graphql_hash_configured` | `KA_GRAPHQL_HASH` set or skill’s `.ka-graphql-hash` file exists |

## UI workflow

1. **Extract (step 1)** — upload **`.pdf`**, **`.docx`**, **`.csv`**, or **`.xlsx`**. PDF uses **pypdf** → Claude; other types use **`ka-parse-pacing-guide --emit-llm-text-to`** → same JSON schema. Optional **state** / **grade** form overrides merge into the result.
2. **Map (step 2)** — edit the standards lines if needed, then run mapping. The server builds KA standard data (GraphQL or offline CCSS file), runs **`ka-map-pipeline`**, and returns a **`job_id`**.
3. **Preview / download** — table preview from the spreadsheet; download is **`.xlsx` only**.

Legacy one-shot: **`POST /api/run`** runs extract + map in a single call.

**Chat:** **`POST /chat`** — same OpenRouter client shape as `openrouter-webapp`; API key stays on the server.

## HTTP API (summary)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/` | Static UI (`static/index.html`) |
| `GET` | `/health` | Config / skill readiness |
| `POST` | `/api/step1/extract` | Multipart: `file`, optional `state`, `grade` → `pacing_json`, `standards_text`, `extraction_summary` |
| `POST` | `/api/step2/map` | JSON: `pacing_base`, `standards_text` → `job_id`, log, summary |
| `POST` | `/api/run` | Multipart: full pipeline in one request |
| `GET` | `/api/jobs/{job_id}/preview` | Query `limit` — parsed rows from mapping xlsx for the UI |
| `GET` | `/api/jobs/{job_id}/download` | Latest **`.xlsx`** for that job |
| `POST` | `/chat` | LLM proxy (optional streaming) |

Mapping jobs write under **`.tmp/jobs/<job_id>/`** (gitignored). Step 1 cleans up its temp dir after the response; step 2 leaves artifacts until you delete them.

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENROUTER_API_KEY` | Yes (extract + chat) | OpenRouter API key |
| `MAP_PACING_SKILL_BIN` | Yes | Absolute path to **map-pacing-guide `bin/`** |
| `OPENROUTER_BASE_URL` | No | Default `https://openrouter.ai/api/v1` |
| `OPENROUTER_DEFAULT_MODEL` | No | Default model id (e.g. `anthropic/claude-sonnet-4.6`) |
| `KA_CCSS_MATH_CSV` | No | If set and file exists, **CCSS.Math** uses this CSV instead of GraphQL |
| `KA_GRAPHQL_URL` | No | Default KA persisted query URL for GetSetOfStandards |
| `KA_GRAPHQL_HASH` | No | Override hash if the bundled default is stale (`ka-standards-api --discover-hash`) |
| `KA_STANDARDS_URL_FIELD` | No | `state` (default) or `default` — URL column, matches **`ka-standards-api --url-field`** |

There is no separate “sync CSV to disk” feature in this app: mappings use **live GraphQL** (or your optional **CCSS.Math** file). The pipeline still materializes a temp tabular file per job; that file is not the user-facing download.

## Troubleshooting

- **`RuntimeError: Directory 'static' does not exist`** — You started uvicorn with the wrong working directory. **`cd pacing-guide-web`** and run again.
- **502 on extract** — Model returned no `records`; try a cleaner PDF export or simplify spreadsheet layout.
- **GraphQL / standards errors** — Refresh **`KA_GRAPHQL_HASH`** or use **`KA_CCSS_MATH_CSV`** for CCSS-only offline runs. Optional full CCSS export: repo **`ka-standards-cache`** (`sync_ccss_standards.py`).
- **Port already in use** — Kill the process on **8010** (see Run section) or pick another `--port`.

## Stack

**FastAPI**, **uvicorn**, **httpx**, **OpenAI-compatible client** (OpenRouter), **pypdf**, **openpyxl**, **python-dotenv**.
