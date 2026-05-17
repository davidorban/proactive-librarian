"""Tests for the retrieval / citation-formatting logic.

The actual backend subprocess call is mocked — we test only the pure logic
(path parsing, snippet trimming, citation formatting)."""
from __future__ import annotations

from proactive_librarian.query import format_citation, parse_result_path


class TestParseResultPath:
    def test_v2_path_with_uri_prefix(self):
        r = {"file": "qmd://research/Subj/Geo/foo/p0042.md"}
        pdf, page = parse_result_path(r)
        assert pdf == "Subj/Geo/foo.pdf"
        assert page == 42

    def test_v2_path_without_prefix(self):
        r = {"file": "Subj/foo/p0001.md"}
        pdf, page = parse_result_path(r)
        assert pdf == "Subj/foo.pdf"
        assert page == 1

    def test_non_v2_path_returns_none(self):
        """Stale v1-format leftover entries (no page subdirectory)."""
        r = {"file": "qmd://research/Subj/foo.md"}
        pdf, page = parse_result_path(r)
        assert pdf is None
        assert page is None

    def test_empty_file_field(self):
        assert parse_result_path({}) == (None, None)
        assert parse_result_path({"file": ""}) == (None, None)

    def test_path_field_fallback(self):
        r = {"path": "qmd://research/Subj/foo/p0010.md"}
        pdf, page = parse_result_path(r)
        assert page == 10


class TestFormatCitation:
    def test_well_formed_result(self):
        r = {
            "file": "qmd://research/Subj/foo/p0042.md",
            "snippet": "Some matching text about the topic.",
            "score": 0.87,
        }
        out = format_citation(r)
        assert out is not None
        assert "**foo.pdf**:p.42" in out
        assert "score 0.87" in out
        assert "Some matching text about the topic." in out

    def test_returns_none_for_invalid_layout(self):
        r = {"file": "qmd://research/wrong.md", "snippet": "x", "score": 0.5}
        assert format_citation(r) is None

    def test_snippet_truncation(self):
        long_snippet = "x" * 400
        r = {
            "file": "Subj/foo/p0001.md",
            "snippet": long_snippet,
            "score": 0.5,
        }
        out = format_citation(r)
        assert "..." in out
        # 317 + ellipsis = 320, plus newlines
        assert len(out) < 400

    def test_whitespace_collapse(self):
        r = {
            "file": "Subj/foo/p0001.md",
            "snippet": "line one\n\nline   two\tline three",
            "score": 0.5,
        }
        out = format_citation(r)
        assert "line one line two line three" in out
