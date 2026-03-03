"""
update_pubs.py - 特定の著者IDを使用してSemantic Scholarから論文を自動更新します。
"""

import hashlib
import logging
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import frontmatter
import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
# あなたの特定のSemantic Scholar Author ID
AUTHOR_ID = "2301432341"

OUTPUT_DIR = Path("_publications")

# エンドポイントを「著者ID指定」に変更
SEMANTIC_SCHOLAR_AUTHOR_PAPERS = f"https://api.semanticscholar.org/graph/v1/author/{AUTHOR_ID}/papers"

RATE_LIMIT_DELAY = 1.0
MAX_RETRIES = 3
BACKOFF_BASE = 2.0

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s",
)
logger = logging.getLogger("update_pubs")

# ---------------------------------------------------------------------------
# Helper utilities (既存のまま)
# ---------------------------------------------------------------------------

def slugify(text: str, max_len: int = 40) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text).strip("-")
    return text[:max_len].strip("-")

def make_filename(meta: dict) -> str:
    year = meta.get("year") or datetime.now(timezone.utc).year
    date_str = f"{year}-01-01"
    slug = slugify(meta.get("title", "untitled"))
    return f"{date_str}-{slug}.md"

def escape_yaml_str(value: str) -> str:
    return str(value).replace('"', '\\"')

# ---------------------------------------------------------------------------
# API interaction
# ---------------------------------------------------------------------------

def _request_with_retry(url: str, params: dict, headers: Optional[dict] = None) -> Optional[requests.Response]:
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.get(url, params=params, headers=headers or {}, timeout=30)
            if resp.status_code == 429:
                wait = BACKOFF_BASE ** attempt
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            if attempt < MAX_RETRIES:
                time.sleep(BACKOFF_BASE ** attempt)
            else:
                return None
    return None

def fetch_semantic_scholar_by_author(api_key: Optional[str] = None) -> list[dict]:
    """著者IDを使用して正確な論文リストを取得します。"""
    logger.info("Fetching papers for Author ID: %s", AUTHOR_ID)
    headers = {"x-api-key": api_key} if api_key else {}
    params = {
        "fields": "title,authors,year,venue,doi,abstract,url",
        "limit": 100,
    }

    resp = _request_with_retry(SEMANTIC_SCHOLAR_AUTHOR_PAPERS, params, headers)
    if resp is None:
        return []

    data = resp.json()
    papers = []
    # 著者IDエンドポイント用のデータ構造でパース
    for item in data.get("data", []):
        authors_list = [f"{a.get('name', '')}" for a in item.get("authors", [])]
        doi = (item.get("doi") or "").strip() or None
        url = item.get("url") or (f"https://doi.org/{doi}" if doi else "")
        papers.append({
            "title": item.get("title", ""),
            "authors": ", ".join(authors_list),
            "year": item.get("year"),
            "venue": item.get("venue") or "",
            "doi": doi,
            "url": url,
            "abstract": item.get("abstract") or "",
        })
    return papers

# ---------------------------------------------------------------------------
# File I/O (既存のロジックを最適化)
# ---------------------------------------------------------------------------

def load_existing_dois(output_dir: Path) -> dict[str, Path]:
    doi_map: dict[str, Path] = {}
    for md_file in output_dir.glob("*.md"):
        try:
            post = frontmatter.load(str(md_file))
            doi = post.get("doi")
            if doi:
                doi_map[str(doi).lower().strip()] = md_file
            else:
                doi_map[md_file.stem.lower()] = md_file
        except Exception:
            doi_map[md_file.stem.lower()] = md_file
    return doi_map

def build_markdown(meta: dict) -> str:
    title = escape_yaml_str(meta.get("title", ""))
    authors = escape_yaml_str(meta.get("authors", ""))
    year = meta.get("year") or ""
    venue = escape_yaml_str(meta.get("venue", ""))
    doi = meta.get("doi") or ""
    url = meta.get("url") or ""
    abstract = (meta.get("abstract") or "").strip()

    fm_lines = [
        "---",
        f'title: "{title}"',
        f'authors: "{authors}"',
        f"year: {year}",
        f'venue: "{venue}"',
        f'doi: "{doi}"',
        f'url: "{url}"',
        "collection: publications",
        "---",
    ]
    return "\n".join(fm_lines) + "\n\n" + abstract + "\n"

def write_publication(meta: dict, output_dir: Path, existing: dict[str, Path]) -> str:
    doi = (meta.get("doi") or "").lower().strip()
    if doi and doi in existing:
        target = existing[doi]
        action = "updated"
    else:
        filename = make_filename(meta)
        target = output_dir / filename
        action = "added"

    content = build_markdown(meta)
    if target.exists() and target.read_text(encoding="utf-8") == content:
        return "skipped"

    target.write_text(content, encoding="utf-8")
    logger.info("[%s] %s", action.upper(), target.name)
    return action

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    api_key = os.environ.get("SEMANTIC_SCHOLAR_KEY")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    existing = load_existing_dois(OUTPUT_DIR)

    counts = {"added": 0, "updated": 0, "skipped": 0}

    try:
        papers = fetch_semantic_scholar_by_author(api_key)
        for paper in papers:
            if not paper.get("title"): continue
            result = write_publication(paper, OUTPUT_DIR, existing)
            counts[result] += 1
    except Exception as exc:
        logger.error("Error: %s", exc)

    logger.info("Summary -> Added: %d, Updated: %d, Skipped: %d", 
                counts["added"], counts["updated"], counts["skipped"])

if __name__ == "__main__":
    main()
