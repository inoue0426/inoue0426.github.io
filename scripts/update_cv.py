#!/usr/bin/env python3
"""
update_cv.py - Updates _pages/cv.md from a publicly shared Google Docs document.

The Google Doc is exported as HTML, converted to Markdown via html2text, and
then merged back into cv.md.  Sections managed by Jekyll Liquid templates
(Publications, Talks, Teaching) are stripped from the Google Doc content and
re-appended from the fixed CV_FOOTER template so they continue to be
auto-generated from site data.
"""
from __future__ import annotations

import logging
import os
import re
import sys
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("update_cv")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
# The Google Doc ID can be overridden via the GOOGLE_DOC_ID environment
# variable so the document can be changed without modifying source code.
GOOGLE_DOC_ID = (
    os.environ.get("GOOGLE_DOC_ID") or "1MhDXdLBmyeCmtZ9Nl2uiqMtoHrTNxi1p"
)
EXPORT_URL = (
    f"https://docs.google.com/document/d/{GOOGLE_DOC_ID}/export?format=html"
)
CV_PATH = Path("_pages/cv.md")

# Heading names (lower-case) whose sections — and everything that follows —
# are managed by Jekyll and should NOT be imported from the Google Doc.
JEKYLL_SECTION_HEADINGS = {"publications", "talks", "teaching"}

# ---------------------------------------------------------------------------
# Fixed template pieces
# ---------------------------------------------------------------------------
CV_HEADER = """\
---
layout: archive
title: "CV"
permalink: /cv/
author_profile: true
redirect_from:
  - /resume
---

You can see the latest version [here](https://docs.google.com/document/d/1MhDXdLBmyeCmtZ9Nl2uiqMtoHrTNxi1p/edit?usp=sharing&ouid=106112363458944521656&rtpof=true&sd=true)

{% include base_path %}

"""

CV_FOOTER = """\
Publications
======
{% assign pub_count = site.publications | size %}
{% assign years = site.publications | map: "year" | uniq | sort | reverse %}
* Auto-updated publication count: **{{ pub_count }}**
* Covered years: **{{ years | join: ", " }}**

  <ul>{% for post in site.publications reversed %}
    {% include archive-single-cv.html %}
  {% endfor %}</ul>

Talks
======
  <ul>{% for post in site.talks reversed %}
    {% include archive-single-talk-cv.html  %}
  {% endfor %}</ul>

Teaching
======
  <ul>{% for post in site.teaching reversed %}
    {% include archive-single-cv.html %}
  {% endfor %}</ul>
"""


# ---------------------------------------------------------------------------
# Fetching
# ---------------------------------------------------------------------------
def fetch_google_doc_html(url: str = EXPORT_URL) -> str:
    """Download the Google Doc as HTML.  Returns an empty string on failure."""
    logger.info("Fetching Google Doc from %s", url)
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as exc:
        logger.error("Failed to fetch Google Doc: %s", exc)
        return ""


# ---------------------------------------------------------------------------
# Conversion helpers
# ---------------------------------------------------------------------------
def html_to_markdown(html_content: str) -> str:
    """Convert HTML to Markdown using the html2text library."""
    import html2text  # imported here so the module can be tested without it

    converter = html2text.HTML2Text()
    converter.ignore_links = False
    converter.body_width = 0       # disable line-wrapping
    converter.ignore_images = True
    # keep links intact — disabling protection avoids spurious angle-bracket
    # wrapping, and disabling wrap_links keeps URLs on the same line as text.
    converter.protect_links = False
    converter.wrap_links = False
    return converter.handle(html_content)


def truncate_at_jekyll_section(markdown: str) -> str:
    """Return *markdown* with every line from the first Jekyll-managed section
    heading onward removed.

    Supports both ATX headings (``# Title``) and Setext headings
    (``Title\\n======``).
    """
    lines = markdown.splitlines()
    result: list[str] = []

    for line in lines:
        stripped = line.strip()

        # --- ATX heading: # Title / ## Title / …
        atx_match = re.match(r"^#{1,6}\s+(.+)$", stripped)
        if atx_match:
            heading_text = atx_match.group(1).strip().lower()
            if heading_text in JEKYLL_SECTION_HEADINGS:
                break

        # --- Setext h1: a line of '=' preceded by the heading text
        if result and re.match(r"^=+$", stripped):
            prev = result[-1].strip().lower()
            if prev in JEKYLL_SECTION_HEADINGS:
                result.pop()  # discard the heading-text line
                break

        # --- Setext h2: a line of '-' preceded by the heading text
        if result and re.match(r"^-+$", stripped):
            prev = result[-1].strip().lower()
            if prev in JEKYLL_SECTION_HEADINGS:
                result.pop()
                break

        result.append(line)

    return "\n".join(result).rstrip() + "\n"


# ---------------------------------------------------------------------------
# Main update logic
# ---------------------------------------------------------------------------
def update_cv(cv_path: Path = CV_PATH) -> str:
    """Fetch the Google Doc, convert to Markdown, and rewrite *cv_path*.

    Returns ``'updated'``, ``'skipped'``, or ``'error'``.
    """
    html_content = fetch_google_doc_html()
    if not html_content:
        logger.error("No content fetched from Google Doc; aborting.")
        return "error"

    markdown = html_to_markdown(html_content)
    body = truncate_at_jekyll_section(markdown)

    new_content = CV_HEADER + body + "\n" + CV_FOOTER

    # Skip writing if the file already has identical content.
    if cv_path.exists():
        try:
            existing = cv_path.read_text(encoding="utf-8")
            if existing == new_content:
                logger.info("[SKIPPED] %s (no change)", cv_path)
                return "skipped"
        except OSError:
            pass

    cv_path.write_text(new_content, encoding="utf-8")
    logger.info("[UPDATED] %s", cv_path)
    return "updated"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> None:
    result = update_cv()
    if result == "error":
        sys.exit(1)
    logger.info("CV update result: %s", result)


if __name__ == "__main__":
    main()
