#!/usr/bin/env python3
"""
update_pubs_fixed.py - Semantic Scholar の特定著者IDから論文を取得して
_markdown_ ファイル群を更新するスクリプト（改良版）
"""
from __future__ import annotations

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
AUTHOR_ID = "2301432341"
OUTPUT_DIR = Path("_publications")
SEMANTIC_SCHOLAR_AUTHOR_PAPERS = f"https://api.semanticscholar.org/graph/v1/author/{AUTHOR_ID}/papers"
RATE_LIMIT_DELAY = 0.1
MAX_RETRIES = 3
BACKOFF_BASE = 2.0
PAGE_LIMIT = 100  # 一度に取る件数（100 が妥当）

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("update_pubs_fixed")


def load_env_file(env_path: Path = Path(".env")) -> None:
    if not env_path.exists():
        return
    try:
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
    except Exception as exc:
        logger.warning("Failed to load .env file: %s", exc)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def slugify(text: str, max_len: int = 40) -> str:
    text = (text or "").lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text).strip("-")
    return text[:max_len].strip("-") or "untitled"

def title_hash(title: str) -> str:
    """Return an 8-character hex hash of the given title string."""
    return hashlib.sha1(title.encode("utf-8")).hexdigest()[:8]

def make_filename(meta: dict) -> str:
    """Return a filename string (not a Path) for the given paper metadata.

    Uses ``meta["date"]`` if present, otherwise falls back to ``meta["year"]``
    to build a ``YYYY-MM-DD-<slug>.md`` filename.
    """
    date_str = meta.get("date") or ""
    if not date_str:
        year = meta.get("year") or datetime.now(timezone.utc).year
        date_str = f"{year}-01-01"
    slug = slugify(meta.get("title", "untitled"))
    return f"{date_str}-{slug}.md"

def _resolve_filepath(meta: dict, output_dir: Path) -> Path:
    """Resolve the full output Path for a paper, avoiding collisions."""
    base = make_filename(meta)
    target = output_dir / base
    # 衝突回避：既に存在するなら短ハッシュを付与
    if target.exists():
        h = title_hash(meta.get("title", "") + str(meta.get("doi", "")))
        stem = base.removesuffix(".md")
        target = output_dir / f"{stem}-{h}.md"
    return target

def escape_yaml_str(value: Optional[str]) -> str:
    if value is None:
        return ""
    # 参考: YAML 内でのダブルクォートエスケープ
    return str(value).replace('"', '\\"')

# ---------------------------------------------------------------------------
# HTTP / API
# ---------------------------------------------------------------------------
# --- 差し替え用: _request_with_retry （失敗時に resp.text をログ出力するよう改善）
def _request_with_retry(url: str, params: dict, headers: Optional[dict] = None) -> Optional[requests.Response]:
    headers = headers or {}
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=30)
            if resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After")
                wait = int(retry_after) if retry_after and retry_after.isdigit() else BACKOFF_BASE ** attempt
                logger.warning("Rate limited (429). waiting %s s (attempt %d)", wait, attempt)
                time.sleep(wait)
                continue
            # <--- 400 系で戻ってきた場合に resp.text をログに出す（原因診断用）
            if resp.status_code >= 400:
                logger.error("HTTP %d from API: %s", resp.status_code, resp.text)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            if attempt < MAX_RETRIES:
                wait = BACKOFF_BASE ** attempt
                logger.warning("Request failed (attempt %d/%d): %s — retrying in %s s", attempt, MAX_RETRIES, exc, wait)
                time.sleep(wait)
            else:
                logger.error("Request failed final attempt: %s", exc)
                return None
    return None

# ---------------------------------------------------------------------------
# Link resolution helper: best URL を決める
# ---------------------------------------------------------------------------
def _get_paper_details(paper_id: str, api_key: Optional[str]) -> dict:
    """
    /paper/{paperId}?fields=... で openAccessPdf, externalIds, url を取得する。
    失敗したら空 dict を返す（呼び出し側でフォールバック処理）。
    """
    if not paper_id:
        return {}
    url = f"https://api.semanticscholar.org/graph/v1/paper/{paper_id}"
    headers = {"x-api-key": api_key} if api_key else {}
    params = {"fields": "openAccessPdf,externalIds,url,externalIds"}
    resp = _request_with_retry(url, params, headers)
    if resp is None:
        return {}
    try:
        return resp.json()
    except Exception:
        return {}

def choose_best_link(paper_meta: dict, api_key: Optional[str] = None) -> str:
    """
    手持ちの meta (paperId, doi, url, etc.) を見て最適なリンクを返す。
    - まず /paper/{paperId} を叩いて openAccessPdf を確認
    - 次に externalIds (DOI, ArXiv) を確認
    - 次に既にある paper_meta['url']
    - 最後に semanticscholar の論文ページ
    """
    # 1) try detailed paper endpoint (openAccessPdf)
    paper_id = paper_meta.get("paperId") or ""
    details = _get_paper_details(paper_id, api_key) if paper_id else {}

    # openAccessPdf があるか
    oap = details.get("openAccessPdf") or {}
    if isinstance(oap, dict):
        pdf_url = oap.get("url") or oap.get("URL")
        if pdf_url:
            return pdf_url

    # 2) externalIds -> DOI or ArXiv
    ext = details.get("externalIds") or paper_meta.get("externalIds") or {}
    if isinstance(ext, dict):
        doi = (ext.get("DOI") or ext.get("doi") or "").strip()
        if doi:
            return f"https://doi.org/{doi}"
        # arXiv may be in different keys, try common forms
        arxiv = (ext.get("ArXiv") or ext.get("arXiv") or ext.get("ARXIV") or "").strip()
        if arxiv:
            # arXiv id may contain version suffix, keep it
            return f"https://arxiv.org/abs/{arxiv}"

    # 3) details.url or meta.url
    details_url = details.get("url") or paper_meta.get("url") or ""
    if details_url:
        return details_url

    # 4) if meta has doi field (fallback)
    doi_meta = (paper_meta.get("doi") or "").strip()
    if doi_meta:
        return f"https://doi.org/{doi_meta}"

    # 5) fallback: semantic scholar paper page (if we have paperId)
    if paper_id:
        return f"https://www.semanticscholar.org/paper/{paper_id}"

    # 6) nothing found
    return ""

# --- 差し替え用: fetch_semantic_scholar_by_author （fields から abstract を外した最小実装）
def fetch_semantic_scholar_by_author(api_key: Optional[str] = None) -> list[dict]:
    """
    AUTHOR_ID の著者情報を author/{id} エンドポイントで取得し、
    ネストされた papers 配列をパースして論文リストを返す実装。
    - externalIds から DOI を抽出する（もしあれば）。
    """
    author_url = f"https://api.semanticscholar.org/graph/v1/author/{AUTHOR_ID}"
    headers = {"x-api-key": api_key} if api_key else {}
    # papers.* というネスト指定で必要な情報をリクエストする。
    fields = ",".join([
        "papers.paperId",
        "papers.title",
        "papers.authors",
        "papers.year",
        "papers.venue",
        "papers.externalIds",
        "papers.url",
    ])
    params = {"fields": fields}
    logger.info("Fetching author summary from %s with fields=%s", author_url, fields)

    resp = _request_with_retry(author_url, params, headers)
    if resp is None:
        logger.error("Failed to fetch author record.")
        return []

    try:
        payload = resp.json()
    except ValueError:
        logger.error("JSON decode error: %s", resp.text[:1000])
        return []

    # payload から papers 配列を取り出す（存在しないなら空）
    papers_raw = []
    if isinstance(payload, dict):
        papers_raw = payload.get("papers") or []
    elif isinstance(payload, list):
        papers_raw = payload
    else:
        logger.warning("Unexpected payload type: %s", type(payload))
        papers_raw = []

    papers = []
    for item in papers_raw:
        # item は既に paper オブジェクトになっているはず
        if not isinstance(item, dict):
            continue
        # authors の取り出し（author オブジェクトか文字列のどちらにも対応）
        authors_list = []
        for a in item.get("authors") or []:
            if isinstance(a, dict):
                authors_list.append(a.get("name", ""))
            else:
                authors_list.append(str(a))

        # externalIds は dict 形式で来ることが多い: {"DOI":"10.xxx", "PMID":"..."}
        doi = ""
        ext = item.get("externalIds") or {}
        if isinstance(ext, dict):
            doi = (ext.get("DOI") or ext.get("doi") or "").strip()

        # fallback: item.get("url") が DOI URL を含むこともあるが必ずしも安定しない
        url = item.get("url") or (f"https://doi.org/{doi}" if doi else "")

        papers.append({
            "title": item.get("title") or "",
            "authors": ", ".join([x for x in authors_list if x]),
            "year": item.get("year"),
            "venue": item.get("venue") or "",
            "doi": doi or "",
            "url": url or "",
            "abstract": "",  # author/{id}?fields=papers.abstract を追加すれば得られるが容量に注意
            "paperId": item.get("paperId") or "",
        })

# 既に papers を取得した直後に best-link を解決して埋める
    for p in papers:
        try:
            best = choose_best_link(p, api_key)
            if best:
                p["url"] = best
            # 軽いスリープを入れてレート負荷を分散
            time.sleep(RATE_LIMIT_DELAY)
        except Exception as e:
            logger.warning("Failed to resolve link for paper '%s': %s", p.get("title"), e)

    logger.info("Parsed %d papers from author payload", len(papers))
    return papers

# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------
def load_existing_dois(output_dir: Path) -> dict[str, Path]:
    """
    既存の md ファイルを走査して DOI / slug / stem をキーに path を返す辞書を作る。
    """
    doi_map: dict[str, Path] = {}
    for md_file in output_dir.glob("*.md"):
        try:
            post = frontmatter.load(str(md_file))
            doi_raw = post.get("doi") or ""
            title_raw = post.get("title") or ""
            if doi_raw:
                doi_map[str(doi_raw).lower().strip()] = md_file
            # スラッグ（ファイル名の stem から日付を取り除いて slug 部分を取得）
            stem = md_file.stem
            # try to extract slug after date prefix like YYYY-01-01-slug...
            slug_part = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", stem).lower()
            if slug_part:
                doi_map[slug_part] = md_file
            # さらにメタデータの title から slug も作成
            if title_raw:
                doi_map[slugify(title_raw)] = md_file
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
    """
    既存ファイルがあれば更新、なければ追加。内容が同じならスキップ。
    返り値: "added" / "updated" / "skipped"
    """
    doi_key = (meta.get("doi") or "").lower().strip()
    title_slug = slugify(meta.get("title", ""))
    target = None
    action = "added"

    # マッチ順序: DOI -> title_slug -> fallback 新規ファイル
    if doi_key and doi_key in existing:
        target = existing[doi_key]
        action = "updated"
    elif title_slug and title_slug in existing:
        target = existing[title_slug]
        action = "updated"
    else:
        target = _resolve_filepath(meta, output_dir)
        action = "added"

    content = build_markdown(meta)
    # if exists and identical, skip
    if target.exists():
        try:
            existing_text = target.read_text(encoding="utf-8")
            if existing_text == content:
                return "skipped"
        except Exception:
            pass

    target.write_text(content, encoding="utf-8")
    logger.info("[%s] %s", action.upper(), target.name)
    return action

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    load_env_file()
    api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY") or os.environ.get("SEMANTIC_SCHOLAR_KEY")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    existing = load_existing_dois(OUTPUT_DIR)

    counts = {"added": 0, "updated": 0, "skipped": 0}

    papers = fetch_semantic_scholar_by_author(api_key)
    logger.info("Total papers fetched: %d", len(papers))
    for paper in papers:
        if not paper.get("title"):
            continue
        result = write_publication(paper, OUTPUT_DIR, existing)
        if result in counts:
            counts[result] += 1
        else:
            logger.warning("Unknown result: %s", result)

    logger.info("Summary -> Added: %d, Updated: %d, Skipped: %d", counts["added"], counts["updated"], counts["skipped"])

if __name__ == "__main__":
    main()
