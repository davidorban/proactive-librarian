"""Shared pytest fixtures."""
from __future__ import annotations

from pathlib import Path

import pytest

from proactive_librarian.config import (
    BackendConfig,
    Config,
    TaxonomyConfig,
)


@pytest.fixture
def permissive_config(tmp_path: Path) -> Config:
    """A config rooted at tmp_path with no taxonomy enforcement."""
    return Config(
        pdf_root=tmp_path,
        derived_dir=".derived",
        collection_name="test",
        taxonomy=TaxonomyConfig(enabled=False),
        backend=BackendConfig(),
    )


@pytest.fixture
def strict_config(tmp_path: Path) -> Config:
    """A config with taxonomy enforcement and a known subject list."""
    return Config(
        pdf_root=tmp_path,
        derived_dir=".derived",
        collection_name="test",
        taxonomy=TaxonomyConfig(
            enabled=True,
            allowed_subjects=("Alpha", "Beta", "Gamma"),
            guide_reference="docs/taxonomy.md",
        ),
        backend=BackendConfig(),
    )
