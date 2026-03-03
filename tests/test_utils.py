"""Unit tests for utility functions in scripts/update_pubs.py."""

import sys
import os

# Allow importing the script from the sibling `scripts/` directory.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from update_pubs import make_filename, slugify, title_hash, build_markdown  # noqa: E402


def test_slugify_basic():
    assert slugify("DrugAgent: Explainable Drug Repurposing") == "drugagent-explainable-drug-repurposing"


def test_slugify_special_chars():
    assert slugify('Title with "quotes" & symbols!') == "title-with-quotes-symbols"


def test_slugify_max_len():
    long_title = "a" * 100
    result = slugify(long_title, max_len=40)
    assert len(result) <= 40


def test_make_filename_with_year():
    meta = {"year": 2024, "title": "DrugAgent"}
    filename = make_filename(meta)
    assert filename == "2024-01-01-drugagent.md"


def test_make_filename_with_date():
    meta = {"year": 2024, "date": "2024-05-14", "title": "drGAT"}
    filename = make_filename(meta)
    assert filename == "2024-05-14-drgat.md"


def test_make_filename_no_year():
    meta = {"title": "Some Paper"}
    filename = make_filename(meta)
    # Should still produce a valid filename ending in .md
    assert filename.endswith(".md")
    assert "some-paper" in filename


def test_make_filename_empty_title():
    meta = {"year": 2023, "title": ""}
    filename = make_filename(meta)
    assert filename.endswith(".md")
    assert "2023" in filename


def test_title_hash_length():
    h = title_hash("Some Paper Title")
    assert len(h) == 8
    assert all(c in "0123456789abcdef" for c in h)


def test_title_hash_deterministic():
    assert title_hash("DrugAgent") == title_hash("DrugAgent")


def test_build_markdown_contains_frontmatter():
    meta = {
        "title": "Test Paper",
        "authors": "John Doe",
        "year": 2024,
        "venue": "Nature",
        "doi": "10.1234/test",
        "url": "https://doi.org/10.1234/test",
        "abstract": "This is the abstract.",
    }
    content = build_markdown(meta)
    assert content.startswith("---")
    assert 'title: "Test Paper"' in content
    assert 'doi: "10.1234/test"' in content
    assert "This is the abstract." in content


def test_build_markdown_escapes_quotes():
    meta = {
        "title": 'He said "hello"',
        "authors": "Jane Doe",
        "year": 2023,
        "venue": "",
        "doi": "",
        "url": "",
        "abstract": "",
    }
    content = build_markdown(meta)
    assert '\\"hello\\"' in content
