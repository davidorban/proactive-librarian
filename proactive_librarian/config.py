"""Configuration loader for proactive-librarian.

Everything that was hardcoded in the original personal-vault implementation
lives here as overridable settings. The intent is "config file in repo root,
sensible defaults everywhere else."
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


DEFAULT_CONFIG_FILENAMES = ("proactive-librarian.yaml", "proactive-librarian.yml")


@dataclass(frozen=True)
class TaxonomyConfig:
    """Optional subject-category enforcement."""
    enabled: bool = False
    allowed_subjects: tuple[str, ...] = ()
    guide_reference: Optional[str] = None  # human-readable pointer to a docs file


@dataclass(frozen=True)
class BackendConfig:
    """Retrieval backend settings. Only QMD is implemented today."""
    type: str = "qmd"
    binary: str = "qmd"
    timeout_seconds: int = 30


@dataclass(frozen=True)
class Config:
    """All settings for a single proactive-librarian instance.

    Construct via `load_config(...)`. The dataclass is frozen so callers can
    safely share it across threads / passes.
    """
    pdf_root: Path
    derived_dir: str = ".derived"
    collection_name: str = "research"
    page_filename_padding: int = 4
    taxonomy: TaxonomyConfig = field(default_factory=TaxonomyConfig)
    backend: BackendConfig = field(default_factory=BackendConfig)

    @property
    def derived_root(self) -> Path:
        return self.pdf_root / self.derived_dir

    @property
    def manifest_path(self) -> Path:
        return self.derived_root / "_manifest.json"

    @property
    def failures_path(self) -> Path:
        return self.derived_root / "_failures.json"

    def page_filename(self, n: int) -> str:
        return f"p{n:0{self.page_filename_padding}d}.md"


def _find_default_config(start: Path) -> Optional[Path]:
    """Look for a config file in `start` (typically cwd). No upward search —
    explicit beats implicit."""
    for name in DEFAULT_CONFIG_FILENAMES:
        candidate = start / name
        if candidate.exists():
            return candidate
    return None


def load_config(
    explicit_path: Optional[Path] = None,
    cli_overrides: Optional[dict] = None,
) -> Config:
    """Resolve config from (in priority order): CLI overrides > config file > defaults.

    Args:
        explicit_path: an absolute path passed via `--config`. Required to exist if given.
        cli_overrides: a dict like `{"pdf_root": "/x/y"}` from argparse. Wins over file values.

    Returns:
        Frozen `Config`.

    Raises:
        FileNotFoundError if `explicit_path` was passed but doesn't exist.
        ValueError if `pdf_root` cannot be resolved from any source.
    """
    cli_overrides = cli_overrides or {}

    file_data: dict = {}
    config_path: Optional[Path] = None

    if explicit_path is not None:
        if not explicit_path.exists():
            raise FileNotFoundError(f"Config file not found: {explicit_path}")
        config_path = explicit_path
    else:
        config_path = _find_default_config(Path.cwd())

    if config_path is not None:
        try:
            file_data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {config_path}: {e}") from e

    # Layer: defaults < file < CLI
    merged: dict = {**file_data, **cli_overrides}

    pdf_root_str = merged.get("pdf_root") or os.environ.get("LIBRARIAN_PDF_ROOT")
    if not pdf_root_str:
        raise ValueError(
            "pdf_root is required. Set it in proactive-librarian.yaml, "
            "via --pdf-root, or via $LIBRARIAN_PDF_ROOT."
        )
    pdf_root = Path(pdf_root_str).expanduser().resolve()

    taxonomy_data = merged.get("taxonomy") or {}
    taxonomy = TaxonomyConfig(
        enabled=bool(taxonomy_data.get("enabled", False)),
        allowed_subjects=tuple(taxonomy_data.get("allowed_subjects", []) or []),
        guide_reference=taxonomy_data.get("guide_reference"),
    )

    backend_data = merged.get("backend") or {}
    backend = BackendConfig(
        type=backend_data.get("type", "qmd"),
        binary=backend_data.get("binary", "qmd"),
        timeout_seconds=int(backend_data.get("timeout_seconds", 30)),
    )

    return Config(
        pdf_root=pdf_root,
        derived_dir=merged.get("derived_dir", ".derived"),
        collection_name=merged.get("collection_name", "research"),
        page_filename_padding=int(merged.get("page_filename_padding", 4)),
        taxonomy=taxonomy,
        backend=backend,
    )
