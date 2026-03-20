# KA standards cache (Common Core)

Fetches **one** Khan Academy GraphQL payload for **`CCSS.Math`** (includes K–8 + high school in a single set), saves:

- **Raw API JSON** — full `GetSetOfStandards` response for debugging / re-processing
- **Full CSV** — same shape as `ka-standards-api` (exercises/videos/articles with URLs)
- **`by_grade/`** — same CSV header, rows split by inferred grade (`K`, `1`–`8`, `HS`, `other`)

## Requirements

- Python 3.10+
- Network access to `www.khanacademy.org`
- GraphQL hash: uses the map-pacing-guide skill cache if present:

  `~/.claude/skills/map-pacing-guide/.ka-graphql-hash`

  If the fetch fails with HTTP errors, run:

  `"$HOME/.claude/skills/map-pacing-guide/bin/ka-standards-api" --discover-hash`

## Run

```bash
cd ka-standards-cache
python3 sync_ccss_standards.py
```

Optional:

```bash
python3 sync_ccss_standards.py --output-dir ./data --url-field default
python3 sync_ccss_standards.py --hash 2804988494
```

Output layout:

```
data/CCSS.Math/
  manifest.json
  graphql_response.json
  CCSS.Math.full.csv
  by_grade/K.csv
  by_grade/1.csv
  ...
  by_grade/8.csv
  by_grade/HS.csv
  by_grade/other.csv   # rare IDs that don’t match heuristics
```

This is **not** a separate GraphQL call per grade — KA’s `CCSS.Math` set is already all grades. The split is **local** only.

**`pacing-guide-web`** loads Common Core mappings via KA **GetSetOfStandards** in the server by default. Optionally set **`KA_CCSS_MATH_CSV`** there if you want a fixed local file instead.
