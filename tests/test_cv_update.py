"""Unit tests for scripts/update_cv.py."""

import sys
import os
import textwrap
from pathlib import Path
from unittest.mock import patch, MagicMock

# Allow importing the script from the sibling `scripts/` directory.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from update_cv import (  # noqa: E402
    truncate_at_jekyll_section,
    html_to_markdown,
    CV_HEADER,
    CV_FOOTER,
    JEKYLL_SECTION_HEADINGS,
)


# ---------------------------------------------------------------------------
# truncate_at_jekyll_section
# ---------------------------------------------------------------------------

def test_truncate_stops_at_atx_publications():
    """Content after '# Publications' heading should be removed."""
    md = textwrap.dedent("""\
        # Education
        Some content here.

        # Publications
        * Should be removed
    """)
    result = truncate_at_jekyll_section(md)
    assert "Education" in result
    assert "Publications" not in result
    assert "Should be removed" not in result


def test_truncate_stops_at_atx_talks():
    md = textwrap.dedent("""\
        # Education
        Some education.

        # Talks
        Talk content.
    """)
    result = truncate_at_jekyll_section(md)
    assert "Education" in result
    assert "Talks" not in result


def test_truncate_stops_at_setext_publications():
    """Setext-style '====' heading for Publications should also be removed."""
    md = textwrap.dedent("""\
        Education
        =========
        Some content.

        Publications
        ============
        * Should be removed
    """)
    result = truncate_at_jekyll_section(md)
    assert "Education" in result
    assert "Publications" not in result
    assert "Should be removed" not in result


def test_truncate_preserves_non_jekyll_sections():
    md = textwrap.dedent("""\
        # Education
        B.Sc. in Computer Science.

        # Work Experience
        Some company.

        # Skills
        Python, R.
    """)
    result = truncate_at_jekyll_section(md)
    assert "Education" in result
    assert "Work Experience" in result
    assert "Skills" in result


def test_truncate_empty_string():
    assert truncate_at_jekyll_section("") == "\n"


def test_truncate_no_jekyll_sections():
    md = "# Education\nContent only."
    result = truncate_at_jekyll_section(md)
    assert "Education" in result
    assert "Content only." in result


def test_truncate_case_insensitive():
    """Section matching should be case-insensitive."""
    md = "# PUBLICATIONS\nshould be gone"
    result = truncate_at_jekyll_section(md)
    assert "PUBLICATIONS" not in result
    assert "should be gone" not in result


# ---------------------------------------------------------------------------
# html_to_markdown
# ---------------------------------------------------------------------------

def test_html_to_markdown_basic():
    html = "<h1>Education</h1><p>University of Example.</p>"
    result = html_to_markdown(html)
    assert "Education" in result
    assert "University of Example" in result


def test_html_to_markdown_preserves_links():
    html = '<p>See <a href="https://example.com">here</a>.</p>'
    result = html_to_markdown(html)
    assert "https://example.com" in result


def test_html_to_markdown_ignores_images():
    html = '<img src="photo.jpg" alt="My Photo"><p>Text</p>'
    result = html_to_markdown(html)
    assert "photo.jpg" not in result
    assert "Text" in result


def test_html_to_markdown_bold():
    html = "<p><strong>Important</strong></p>"
    result = html_to_markdown(html)
    assert "Important" in result


# ---------------------------------------------------------------------------
# CV_HEADER / CV_FOOTER sanity checks
# ---------------------------------------------------------------------------

def test_cv_header_contains_frontmatter():
    assert CV_HEADER.startswith("---")
    assert "permalink: /cv/" in CV_HEADER
    assert "layout: archive" in CV_HEADER


def test_cv_footer_contains_jekyll_sections():
    assert "Publications" in CV_FOOTER
    assert "Talks" in CV_FOOTER
    assert "Teaching" in CV_FOOTER
    assert "site.publications" in CV_FOOTER
    assert "site.talks" in CV_FOOTER
    assert "site.teaching" in CV_FOOTER


def test_jekyll_section_headings_set():
    assert "publications" in JEKYLL_SECTION_HEADINGS
    assert "talks" in JEKYLL_SECTION_HEADINGS
    assert "teaching" in JEKYLL_SECTION_HEADINGS


# ---------------------------------------------------------------------------
# update_cv (with mocked network / filesystem)
# ---------------------------------------------------------------------------

def test_update_cv_returns_error_on_fetch_failure(tmp_path):
    from update_cv import update_cv

    with patch("update_cv.fetch_google_doc_html", return_value=""):
        result = update_cv(cv_path=tmp_path / "cv.md")
    assert result == "error"


def test_update_cv_writes_file(tmp_path):
    from update_cv import update_cv

    fake_html = "<h1>Education</h1><p>Test University</p>"
    cv_path = tmp_path / "cv.md"

    with patch("update_cv.fetch_google_doc_html", return_value=fake_html):
        result = update_cv(cv_path=cv_path)

    assert result == "updated"
    assert cv_path.exists()
    content = cv_path.read_text(encoding="utf-8")
    assert "Education" in content
    assert "Publications" in content  # from CV_FOOTER


def test_update_cv_skips_when_unchanged(tmp_path):
    from update_cv import update_cv, html_to_markdown, truncate_at_jekyll_section

    fake_html = "<h1>Education</h1><p>No change.</p>"
    cv_path = tmp_path / "cv.md"

    # First write
    with patch("update_cv.fetch_google_doc_html", return_value=fake_html):
        update_cv(cv_path=cv_path)

    # Second write should be skipped (same content)
    with patch("update_cv.fetch_google_doc_html", return_value=fake_html):
        result = update_cv(cv_path=cv_path)

    assert result == "skipped"


def test_update_cv_strips_jekyll_sections_from_doc(tmp_path):
    """Publications from the Google Doc should not appear in the output
    (they're replaced by the Jekyll Liquid template in CV_FOOTER)."""
    from update_cv import update_cv

    fake_html = (
        "<h1>Education</h1><p>Test University</p>"
        "<h1>Publications</h1><p>My paper list from the doc.</p>"
    )
    cv_path = tmp_path / "cv.md"

    with patch("update_cv.fetch_google_doc_html", return_value=fake_html):
        update_cv(cv_path=cv_path)

    content = cv_path.read_text(encoding="utf-8")
    # The manually-listed publications from the doc should be gone …
    assert "My paper list from the doc." not in content
    # … but the Jekyll liquid template should be present.
    assert "site.publications" in content
