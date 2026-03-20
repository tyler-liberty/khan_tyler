# khan_tyler

Math standards tooling for Khan Academy pacing workflows: an optional **CCSS.Math** snapshot CLI and a local **pacing-guide** web app that maps state pacing materials to KA content.

## Projects

| Folder | Purpose |
|--------|---------|
| [**pacing-guide-web**](pacing-guide-web/README.md) | FastAPI UI: upload pacing PDFs or spreadsheets, extract structure via OpenRouter (Claude), map standards using KA GraphQL or an offline CCSS CSV. |
| [**ka-standards-cache**](ka-standards-cache/README.md) | Python CLI to refresh `CCSS.Math` from Khan Academy into `data/` for airgap / pinned exports used by pacing-guide-web. |

## Setup

1. **ka-standards-cache** — Optional. See its README; run `sync_ccss_standards.py` if you need a fresh CSV. Committed `data/CCSS.Math/` is enough for many flows.
2. **pacing-guide-web** — `python3 -m venv .venv`, `pip install -r requirements.txt`, copy `.env.example` → `.env`, set `OPENROUTER_API_KEY` and `MAP_PACING_SKILL_BIN`, then run from that directory:

   ```bash
   cd pacing-guide-web
   source .venv/bin/activate
   uvicorn main:app --reload --port 8010
   ```

Open [http://127.0.0.1:8010](http://127.0.0.1:8010).

Secrets stay in `.env` (never commit). The **map-pacing-guide** Claude skill `bin/` must exist locally — see `pacing-guide-web/README.md`.
