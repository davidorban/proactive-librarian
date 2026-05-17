"""Tests for the configuration loader."""
from __future__ import annotations

from pathlib import Path

import pytest

from proactive_librarian.config import Config, load_config


class TestLoadConfig:
    def test_missing_pdf_root_raises(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("LIBRARIAN_PDF_ROOT", raising=False)
        with pytest.raises(ValueError, match="pdf_root is required"):
            load_config()

    def test_loads_from_yaml(self, tmp_path, monkeypatch):
        pdf_dir = tmp_path / "pdfs"
        pdf_dir.mkdir()
        (tmp_path / "proactive-librarian.yaml").write_text(
            f"pdf_root: {pdf_dir}\ncollection_name: my_corpus\n",
            encoding="utf-8",
        )
        monkeypatch.chdir(tmp_path)
        cfg = load_config()
        assert cfg.pdf_root == pdf_dir.resolve()
        assert cfg.collection_name == "my_corpus"

    def test_cli_overrides_win(self, tmp_path, monkeypatch):
        pdf_dir = tmp_path / "pdfs"
        pdf_dir.mkdir()
        (tmp_path / "proactive-librarian.yaml").write_text(
            f"pdf_root: {pdf_dir}\ncollection_name: from_file\n",
            encoding="utf-8",
        )
        monkeypatch.chdir(tmp_path)
        cfg = load_config(cli_overrides={"collection_name": "from_cli"})
        assert cfg.collection_name == "from_cli"

    def test_environment_fallback(self, tmp_path, monkeypatch):
        pdf_dir = tmp_path / "pdfs"
        pdf_dir.mkdir()
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("LIBRARIAN_PDF_ROOT", str(pdf_dir))
        cfg = load_config()
        assert cfg.pdf_root == pdf_dir.resolve()

    def test_explicit_config_path_must_exist(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_config(explicit_path=tmp_path / "does-not-exist.yaml")

    def test_invalid_yaml_raises_value_error(self, tmp_path, monkeypatch):
        bad = tmp_path / "proactive-librarian.yaml"
        bad.write_text("pdf_root: /tmp\n  bad-indent: nope", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        with pytest.raises(ValueError, match="Invalid YAML"):
            load_config()


class TestConfigDerivedPaths:
    def test_derived_root(self, tmp_path):
        cfg = Config(pdf_root=tmp_path, derived_dir=".cache")
        assert cfg.derived_root == tmp_path / ".cache"

    def test_manifest_and_failures_paths(self, tmp_path):
        cfg = Config(pdf_root=tmp_path)
        assert cfg.manifest_path == tmp_path / ".derived" / "_manifest.json"
        assert cfg.failures_path == tmp_path / ".derived" / "_failures.json"

    def test_page_filename_padding(self, tmp_path):
        cfg = Config(pdf_root=tmp_path, page_filename_padding=4)
        assert cfg.page_filename(1) == "p0001.md"
        assert cfg.page_filename(42) == "p0042.md"
        assert cfg.page_filename(9999) == "p9999.md"

    def test_page_filename_padding_custom(self, tmp_path):
        cfg = Config(pdf_root=tmp_path, page_filename_padding=3)
        assert cfg.page_filename(7) == "p007.md"
