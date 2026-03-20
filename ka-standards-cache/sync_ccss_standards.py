#!/usr/bin/env python3
"""
Fetch CCSS.Math from KA GetSetOfStandards (same endpoint as map-pacing-guide ka-standards-api).

Saves raw JSON + full mapping CSV + per-grade CSV slices under data/CCSS.Math/.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

SET_ID = "CCSS.Math"
GRAPHQL_URL = "https://www.khanacademy.org/api/internal/graphql/GetSetOfStandards"
BASE_URL = "https://www.khanacademy.org"
_DEFAULT_HASH = "2804988494"
_API_TIMEOUT = 60

_SCRIPT_DIR = Path(__file__).resolve().parent


def _skill_hash_cache() -> Path | None:
    p = Path.home() / ".claude/skills/map-pacing-guide/.ka-graphql-hash"
    return p if p.is_file() else None


def load_hash(explicit: str | None) -> str:
    if explicit:
        return explicit
    cache = _skill_hash_cache()
    if cache:
        try:
            t = cache.read_text(encoding="utf-8").strip()
            if t:
                return t
        except OSError:
            pass
    return _DEFAULT_HASH


def fetch_standards(set_id: str, graphql_hash: str) -> dict:
    variables = json.dumps({"setId": set_id, "region": "*"})
    params = urllib.parse.urlencode({"hash": graphql_hash, "variables": variables})
    url = f"{GRAPHQL_URL}?{params}"
    req = urllib.request.Request(
        url,
        headers={"x-ka-fkey": "1", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=_API_TIMEOUT) as resp:
        return json.loads(resp.read())


def iter_content_rows(standards: list, set_id: str, url_field_choice: str):
    """Mirror ka-standards-api.iter_content_rows."""
    for std in standards:
        mapped = std.get("mappedContent", [])
        if not mapped:
            continue
        std_code = std.get("standardId", "")
        std_desc = std.get("description", "")
        for item in mapped:
            kind = item.get("contentKind", "")
            title = item.get("title", "")
            if url_field_choice == "default":
                url_path = item.get("defaultUrlPath", "")
            else:
                url_path = item.get("urlWithinStandardSet", "")
                if not url_path:
                    url_path = item.get("defaultUrlPath", "")
            if url_path and not url_path.startswith("http"):
                full_url = BASE_URL + url_path
            else:
                full_url = url_path
            if full_url and "internal-courses" in full_url:
                continue
            yield [set_id, std_code, std_desc, kind, title, full_url]


def ccss_grade_bucket(standard_id: str) -> str:
    """Infer grade label from KA CCSS Standard ID for file split."""
    s = (standard_id or "").strip()
    if s.startswith("K."):
        return "K"
    m = re.match(r"^(\d+)\.", s)
    if m:
        return m.group(1)
    # High school: HSA.*, HSF.*, HSN.*, MP.*, etc. (leading digit is always K–12)
    return "HS"


CSV_HEADER = ["Set ID", "Standard ID", "Standard Description", "Content Kind", "Content Title", "Content URL"]


def main() -> None:
    ap = argparse.ArgumentParser(description=f"Download {SET_ID} and save JSON + CSV (+ by-grade slices).")
    ap.add_argument("--output-dir", type=Path, default=_SCRIPT_DIR / "data", help="Base output directory")
    ap.add_argument(
        "--url-field",
        choices=["state", "default"],
        default="state",
        help="Same as ka-standards-api: state vs default URL path",
    )
    ap.add_argument("--hash", help="Override GraphQL persisted-query hash")
    args = ap.parse_args()

    out_base = args.output_dir / SET_ID
    out_base.mkdir(parents=True, exist_ok=True)

    ghash = load_hash(args.hash)
    print(f"Fetching {SET_ID} (hash={ghash[:12]}…)", file=sys.stderr)
    try:
        data = fetch_standards(SET_ID, ghash)
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}. Try: ka-standards-api --discover-hash", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Network error: {e}", file=sys.stderr)
        sys.exit(1)

    if "errors" in data:
        msgs = "; ".join(e.get("message", str(e)) for e in data["errors"])
        print(f"GraphQL errors: {msgs}", file=sys.stderr)
        sys.exit(1)

    json_path = out_base / "graphql_response.json"
    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Wrote {json_path}", file=sys.stderr)

    standards_data = data.get("data", {}).get("setOfStandards")
    if not standards_data:
        print("Missing data.setOfStandards", file=sys.stderr)
        sys.exit(1)

    top_standards = standards_data.get("standards", [])
    if not top_standards:
        top_standards = standards_data if isinstance(standards_data, list) else []

    rows = list(iter_content_rows(top_standards, SET_ID, args.url_field))
    csv_path = out_base / f"{SET_ID}.full.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(CSV_HEADER)
        w.writerows(rows)
    print(f"Wrote {csv_path} ({len(rows)} content rows)", file=sys.stderr)

    by_grade: dict[str, list[list]] = defaultdict(list)
    for row in rows:
        sid = row[1] if len(row) > 1 else ""
        by_grade[ccss_grade_bucket(sid)].append(row)

    bg_dir = out_base / "by_grade"
    bg_dir.mkdir(parents=True, exist_ok=True)
    def _sort_key(g: str) -> tuple:
        if g == "K":
            return (-1, "")
        if g == "HS":
            return (200, g)
        if g.isdigit():
            return (0, int(g))
        return (100, g)

    for grade, grows in sorted(by_grade.items(), key=lambda x: _sort_key(x[0])):
        p = bg_dir / f"{grade}.csv"
        with p.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(CSV_HEADER)
            w.writerows(grows)
        print(f"Wrote {p} ({len(grows)} rows)", file=sys.stderr)

    manifest = {
        "set_id": SET_ID,
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
        "graphql_hash": ghash,
        "total_standards": len(top_standards),
        "standards_with_mapped_content": sum(1 for s in top_standards if s.get("mappedContent")),
        "total_content_rows": len(rows),
        "by_grade": {g: len(rs) for g, rs in sorted(by_grade.items())},
        "paths": {
            "directory": str(out_base),
            "graphql_json": json_path.name,
            "full_csv": csv_path.name,
            "by_grade": bg_dir.name,
        },
    }
    mp = out_base / "manifest.json"
    mp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote {mp}", file=sys.stderr)


if __name__ == "__main__":
    main()
