"""
update_pubs.py - Automatically update _publications from Semantic Scholar / Crossref APIs.

NOTE: Google Scholar scraping is intentionally NOT used in this script.
      Only Semantic Scholar Graph API v1 and Crossref Works API are used.

Usage:
    python scripts/update_pubs.py

Environment variables (optional):
    SEMANTIC_SCHOLAR_KEY  - API key for Semantic Scholar (raises rate limit)
    CROSSREF_EMAIL        - Email for Crossref polite pool (improves rate limit)

Example log output:
    INFO:update_pubs:Fetching from Semantic Scholar for query: Yoshitaka Inoue
    INFO:update_pubs:Found 5 papers via Semantic Scholar
    INFO:update_pubs:[NEW] 2024-05-14-drGAT.md created
    INFO:update_pubs:Summary -> Added: 3, Updated: 1, Skipped: 1
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
import yaml

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
QUERIES = ["Yoshitaka Inoue", "DrugAgent"]

OUTPUT_DIR = Path("_publications")

SEMANTIC_SCHOLAR_SEARCH = "https://api.semanticscholar.org/graph/v1/paper/search"
CROSSREF_WORKS = "https://api.crossref.org/works"

RATE_LIMIT_DELAY = 1.0   # seconds between requests
MAX_RETRIES = 3
BACKOFF_BASE = 2.0       # exponential backoff base (seconds)

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s",
)
logger = logging.getLogger("update_pubs")


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def slugify(text: str, max_len: int = 40) -> str:
    """Convert *text* to a filesystem-safe ASCII slug.

    Args:
        text: Input string (e.g. paper title).
        max_len: Maximum length of the returned slug.

    Returns:
        Lower-case, hyphen-separated slug truncated to *max_len* characters.

    Example:
        >>> slugify("DrugAgent: Explainable Drug Repurposing")
        'drugagent-explainable-drug-repurposing'
    """
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s-]+", "-", text).strip("-")
    return text[:max_len].strip("-")


def make_filename(meta: dict) -> str:
    """Build the ``YYYY-MM-DD-slug.md`` filename from paper *meta*.

    Args:
        meta: Dictionary with at least ``year`` and ``title`` keys.
              An optional ``date`` key (``YYYY-MM-DD`` string) overrides the
              year-only date.

    Returns:
        Filename string such as ``2024-05-14-drugagent.md``.

    Example:
        >>> make_filename({"year": 2024, "title": "DrugAgent"})
        '2024-01-01-drugagent.md'
    """
    year = meta.get("year") or datetime.now(timezone.utc).year
    date_str = meta.get("date") or f"{year}-01-01"
    slug = slugify(meta.get("title", "untitled"))
    if not slug:
        slug = "untitled"
    return f"{date_str}-{slug}.md"


def title_hash(title: str) -> str:
    """Return the first 8 hex characters of the SHA-1 hash of *title*.

    Used as a fallback identifier when a paper has no DOI.

    Args:
        title: Paper title string.

    Returns:
        8-character hex string.
    """
    return hashlib.sha1(title.encode("utf-8")).hexdigest()[:8]


def escape_yaml_str(value: str) -> str:
    """Escape double-quotes inside *value* so it is safe in a YAML double-quoted scalar.

    Args:
        value: Raw string value.

    Returns:
        String with ``"`` replaced by ``\"``.
    """
    return value.replace('"', '\\"')


# ---------------------------------------------------------------------------
# API interaction
# ---------------------------------------------------------------------------

def _request_with_retry(
    url: str,
    params: dict,
    headers: Optional[dict] = None,
    retries: int = MAX_RETRIES,
) -> Optional[requests.Response]:
    """GET *url* with *params*, retrying on failure with exponential back-off.

    Handles HTTP 429 (Too Many Requests) and transient errors up to *retries*
    times before giving up.

    Args:
        url: Request URL.
        params: Query parameters.
        headers: Optional HTTP headers.
        retries: Maximum number of retry attempts.

    Returns:
        A :class:`requests.Response` on success, or ``None`` after all retries
        are exhausted.
    """
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, params=params, headers=headers or {}, timeout=30)
            if resp.status_code == 429:
                wait = BACKOFF_BASE ** attempt
                logger.warning("Rate limited (429). Waiting %.1fs before retry %d/%d.", wait, attempt + 1, retries)
                time.sleep(wait)
                continue
            if resp.status_code == 401:
                logger.error("Authentication failure (401) for %s. Check your API key.", url)
                return None
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            if attempt < retries:
                wait = BACKOFF_BASE ** attempt
                logger.warning("Request error: %s. Retrying in %.1fs (%d/%d).", exc, wait, attempt + 1, retries)
                time.sleep(wait)
            else:
                logger.error("Request failed after %d attempts: %s", retries + 1, exc)
                return None
    return None


def fetch_semantic_scholar(query: str, api_key: Optional[str] = None) -> list[dict]:
    """Fetch papers matching *query* from the Semantic Scholar Graph API v1.

    Args:
        query: Search query string.
        api_key: Optional Semantic Scholar API key (raises rate limit).

    Returns:
        List of normalised paper metadata dictionaries.
    """
    logger.info("Fetching from Semantic Scholar for query: %s", query)
    headers = {}
    if api_key:
        headers["x-api-key"] = api_key

    params = {
        "query": query,
        "fields": "title,authors,year,venue,doi,abstract,url",
        "limit": 50,
    }

    time.sleep(RATE_LIMIT_DELAY)
    resp = _request_with_retry(SEMANTIC_SCHOLAR_SEARCH, params, headers)
    if resp is None:
        return []

    data = resp.json()
    papers = []
    for item in data.get("data", []):
        authors_list = [
            f"{a.get('name', '')}" for a in item.get("authors", [])
        ]
        doi = (item.get("doi") or "").strip() or None
        url = item.get("url") or (f"https://doi.org/{doi}" if doi else "")
        papers.append(
            {
                "title": item.get("title", ""),
                "authors": ", ".join(authors_list),
                "year": item.get("year"),
                "venue": item.get("venue") or "",
                "doi": doi,
                "url": url,
                "abstract": item.get("abstract") or "",
                "source": "semantic_scholar",
            }
        )
    logger.info("Found %d papers via Semantic Scholar.", len(papers))
    return papers


def fetch_crossref(query: str, email: Optional[str] = None) -> list[dict]:
    """Fetch papers matching *query* from the Crossref Works API.

    Used as a fallback when Semantic Scholar returns no results.

    Args:
        query: Search query string.
        email: Optional email for Crossref's polite pool (better rate limits).

    Returns:
        List of normalised paper metadata dictionaries.
    """
    logger.info("Fetching from Crossref for query: %s", query)
    params: dict = {"query": query, "rows": 50}
    if email:
        params["mailto"] = email

    time.sleep(RATE_LIMIT_DELAY)
    resp = _request_with_retry(CROSSREF_WORKS, params)
    if resp is None:
        return []

    items = resp.json().get("message", {}).get("items", [])
    papers = []
    for item in items:
        title_list = item.get("title", [])
        title = title_list[0] if title_list else ""
        author_parts = []
        for a in item.get("author", []):
            given = a.get("given", "")
            family = a.get("family", "")
            name = f"{given} {family}".strip()
            if name:
                author_parts.append(name)
        doi = (item.get("DOI") or "").strip() or None
        url = item.get("URL") or (f"https://doi.org/{doi}" if doi else "")
        # Crossref date: prefer published-print, fall back to created
        date_parts = (
            item.get("published-print", {}).get("date-parts")
            or item.get("created", {}).get("date-parts")
            or [[None]]
        )
        year = date_parts[0][0] if date_parts[0] else None
        venue = item.get("container-title", [""])[0] if item.get("container-title") else ""
        abstract = item.get("abstract", "")
        papers.append(
            {
                "title": title,
                "authors": ", ".join(author_parts),
                "year": year,
                "venue": venue,
                "doi": doi,
                "url": url,
                "abstract": abstract,
                "source": "crossref",
            }
        )
    logger.info("Found %d papers via Crossref.", len(papers))
    return papers


def fetch_papers(query: str, api_key: Optional[str] = None, email: Optional[str] = None) -> list[dict]:
    """Fetch papers for *query*, falling back to Crossref if Semantic Scholar fails.

    Args:
        query: Search query string.
        api_key: Semantic Scholar API key (optional).
        email: Crossref polite-pool email (optional).

    Returns:
        List of normalised paper metadata dictionaries.
    """
    papers = fetch_semantic_scholar(query, api_key)
    if not papers:
        logger.info("Semantic Scholar returned nothing; falling back to Crossref.")
        papers = fetch_crossref(query, email)
    return papers


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------

def load_existing_dois(output_dir: Path) -> dict[str, Path]:
    """Scan *output_dir* for existing Markdown files and return a DOI→path map.

    Files without a ``doi`` frontmatter field are indexed by their filename stem
    instead (as a fallback).

    Args:
        output_dir: Path to the ``_publications`` directory.

    Returns:
        Dictionary mapping DOI strings (lower-cased) or filename stems to their
        :class:`~pathlib.Path`.
    """
    doi_map: dict[str, Path] = {}
    for md_file in output_dir.glob("*.md"):
        try:
            post = frontmatter.load(str(md_file))
            doi = post.get("doi")
            if doi:
                doi_map[str(doi).lower().strip()] = md_file
            else:
                doi_map[md_file.stem.lower()] = md_file
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not parse frontmatter in %s: %s", md_file, exc)
            doi_map[md_file.stem.lower()] = md_file
    return doi_map


def build_markdown(meta: dict) -> str:
    """Render a Markdown publication file from *meta*.

    Args:
        meta: Paper metadata dict with keys ``title``, ``authors``, ``year``,
              ``venue``, ``doi``, ``url``, ``abstract``.

    Returns:
        UTF-8 string ready to be written as a ``.md`` file.
    """
    title = escape_yaml_str(meta.get("title") or "")
    authors = escape_yaml_str(meta.get("authors") or "")
    year = meta.get("year") or ""
    venue = escape_yaml_str(meta.get("venue") or "")
    doi = meta.get("doi") or ""
    url = meta.get("url") or (f"https://doi.org/{doi}" if doi else "")
    abstract = (meta.get("abstract") or "").strip()

    # Build YAML frontmatter manually for full control over quoting
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
    body = abstract if abstract else ""
    return "\n".join(fm_lines) + "\n\n" + body + "\n"


def write_publication(meta: dict, output_dir: Path, existing: dict[str, Path]) -> str:
    """Write (or update) a single publication Markdown file.

    Determines whether to create a new file or overwrite an existing one by
    matching the paper's DOI (or title hash as fallback) against *existing*.

    Args:
        meta: Paper metadata dictionary.
        output_dir: Destination directory for ``.md`` files.
        existing: DOI→path mapping returned by :func:`load_existing_dois`.

    Returns:
        One of ``"added"``, ``"updated"``, or ``"skipped"``.
    """
    doi = (meta.get("doi") or "").lower().strip()
    # Determine if we have an existing file for this paper
    if doi and doi in existing:
        target = existing[doi]
        action = "updated"
    else:
        filename = make_filename(meta)
        target = output_dir / filename
        action = "added"

    content = build_markdown(meta)

    # Check if content has actually changed (skip if identical)
    if target.exists():
        existing_content = target.read_text(encoding="utf-8")
        if existing_content == content:
            logger.debug("No change for %s; skipping.", target.name)
            return "skipped"
        action = "updated"

    target.write_text(content, encoding="utf-8")
    logger.info("[%s] %s", action.upper(), target.name)
    # Update the index so subsequent writes in the same run are aware
    if doi:
        existing[doi] = target
    return action


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Run the publication update pipeline.

    Iterates over :data:`QUERIES`, fetches papers from Semantic Scholar
    (falling back to Crossref), then writes/updates Markdown files in
    :data:`OUTPUT_DIR`.  Prints a summary at the end.
    """
    api_key = os.environ.get("SEMANTIC_SCHOLAR_KEY")
    email = os.environ.get("CROSSREF_EMAIL")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    existing = load_existing_dois(OUTPUT_DIR)

    counts = {"added": 0, "updated": 0, "skipped": 0}

    for query in QUERIES:
        try:
            papers = fetch_papers(query, api_key=api_key, email=email)
        except Exception as exc:  # noqa: BLE001
            logger.error("Unexpected error while fetching query '%s': %s", query, exc)
            continue

        for paper in papers:
            if not paper.get("title"):
                logger.debug("Skipping paper with no title.")
                counts["skipped"] += 1
                continue
            try:
                result = write_publication(paper, OUTPUT_DIR, existing)
                counts[result] += 1
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to write paper '%s': %s", paper.get("title", "?"), exc)
                counts["skipped"] += 1

    logger.info(
        "Summary -> Added: %d, Updated: %d, Skipped: %d",
        counts["added"],
        counts["updated"],
        counts["skipped"],
    )


if __name__ == "__main__":
    main()
