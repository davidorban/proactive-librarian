"""Tests for ingest pipeline helpers (sha1, paths, manifest, failures).

Full PDF→markdown extraction is exercised by the real CLI run, not by unit
tests — synthesising a PDF in-process would require a dev-only dependency
for marginal value. These tests cover the helpers where a regression would
silently corrupt the cache."""
from __future__ import annotations

import json
from pathlib import Path

from proactive_librarian.ingest import (
    IngestStats,
    compute_sha1,
    get_page_dir,
    load_manifest,
    save_failures,
    save_manifest,
)


class TestComputeSha1:
    def test_known_content(self, tmp_path):
        p = tmp_path / "hello.bin"
        p.write_bytes(b"hello world")
        assert compute_sha1(p) == "2aae6c35c94fcfb415dbe95f408b9ce91ee846ed"

    def test_empty_file(self, tmp_path):
        p = tmp_path / "empty.bin"
        p.write_bytes(b"")
        assert compute_sha1(p) == "da39a3ee5e6b4b0d3255bfef95601890afd80709"

    def test_large_file_streamed(self, tmp_path):
        """Streaming sha1 must match a one-shot read for files larger than chunk_size."""
        import hashlib
        p = tmp_path / "big.bin"
        data = b"x" * (3 * 1024 * 1024 + 17)  # > 1 MB chunk
        p.write_bytes(data)
        assert compute_sha1(p) == hashlib.sha1(data).hexdigest()


class TestGetPageDir:
    def test_simple_mapping(self, permissive_config, tmp_path):
        pdf = tmp_path / "Subj" / "Geo" / "foo.pdf"
        pdf.parent.mkdir(parents=True)
        pdf.touch()
        out = get_page_dir(pdf, permissive_config)
        assert out == permissive_config.derived_root / "Subj" / "Geo" / "foo"

    def test_custom_derived_dir(self, tmp_path):
        from proactive_librarian.config import Config
        cfg = Config(pdf_root=tmp_path, derived_dir=".cache")
        pdf = tmp_path / "Foo" / "x.pdf"
        pdf.parent.mkdir(parents=True)
        pdf.touch()
        out = get_page_dir(pdf, cfg)
        assert out == tmp_path / ".cache" / "Foo" / "x"


class TestManifest:
    def test_load_returns_empty_when_missing(self, permissive_config):
        assert load_manifest(permissive_config) == {}

    def test_save_and_load_roundtrip(self, permissive_config):
        payload = {"Subj/foo.pdf": {"sha1": "abc", "page_count": 12}}
        save_manifest(payload, permissive_config)
        assert load_manifest(permissive_config) == payload

    def test_save_is_atomic(self, permissive_config):
        save_manifest({"k": "v"}, permissive_config)
        manifest = permissive_config.manifest_path
        assert manifest.exists()
        assert not manifest.with_suffix(".json.tmp").exists()

    def test_load_returns_empty_on_corrupt(self, permissive_config):
        permissive_config.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        permissive_config.manifest_path.write_text("{not json", encoding="utf-8")
        assert load_manifest(permissive_config) == {}


class TestFailuresLog:
    def test_includes_metadata(self, permissive_config):
        stats = IngestStats()
        stats.failures.append({"pdf": "Subj/x.pdf", "reason": "encrypted"})
        save_failures(stats, permissive_config)
        data = json.loads(permissive_config.failures_path.read_text())
        assert data["total_failures"] == 1
        assert data["failures"][0]["reason"] == "encrypted"
        assert "generated_at" in data

    def test_record_failure_uses_relative_path(self, permissive_config, tmp_path):
        stats = IngestStats()
        stats.record_failure(
            tmp_path / "Subj" / "x.pdf", "boom", permissive_config.pdf_root
        )
        assert stats.errors == 1
        assert stats.failures[0]["pdf"] == "Subj/x.pdf"

    def test_record_failure_falls_back_to_str_outside_root(self, permissive_config):
        stats = IngestStats()
        stats.record_failure(
            Path("/elsewhere/x.pdf"), "boom", permissive_config.pdf_root
        )
        assert stats.failures[0]["pdf"] == "/elsewhere/x.pdf"
