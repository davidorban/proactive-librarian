"""Optional subject/geography taxonomy enforcement.

When `taxonomy.enabled: true` in config, the first path component under
`pdf_root` is treated as a "subject" and validated against the configured
allowed list. Any PDF in an unknown subject folder fails ingest loudly,
with an actionable error message.

When `taxonomy.enabled: false` (default), all subjects are accepted and
geography is captured permissively for sidecar metadata.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from proactive_librarian.config import Config


def derive_subject_geography(
    pdf_path: Path, config: Config
) -> tuple[str, Optional[str]]:
    """Map a PDF path to its (subject, geography).

    The PDF path may be absolute or relative to `config.pdf_root`. The
    "subject" is the first path component under `pdf_root`. The "geography"
    is the second component when it exists and isn't a file.

    Returns ("Unknown", None) for paths outside pdf_root.
    """
    try:
        rel = pdf_path.resolve().relative_to(config.pdf_root)
    except ValueError:
        # Path is not under pdf_root — try interpreting parts directly
        rel = pdf_path

    parts = rel.parts
    if not parts:
        return "Unknown", None

    # Leading whitespace can sneak in from cloud-sync exports
    subject = parts[0].strip()

    geography: Optional[str] = None
    if len(parts) >= 2 and not parts[1].lower().endswith(
        (".pdf", ".docx", ".xlsx", ".pptx")
    ):
        geography = parts[1].strip()

    return subject, geography


def validate_subject(subject: str, config: Config) -> tuple[bool, str]:
    """Return (is_valid, error_message_if_invalid)."""
    if not config.taxonomy.enabled:
        return True, ""

    if subject in config.taxonomy.allowed_subjects:
        return True, ""

    allowed_str = "\n".join(f"  - {s}" for s in sorted(config.taxonomy.allowed_subjects))
    guide = (
        f"  Reference: {config.taxonomy.guide_reference}\n"
        if config.taxonomy.guide_reference
        else ""
    )
    err = (
        f"Unknown subject category: {subject!r}\n\n"
        "Taxonomy enforcement is enabled in your config. Allowed subjects:\n"
        f"{allowed_str}\n\n"
        f"{guide}"
        "How to fix:\n"
        "  1. Move the PDF into one of the folders above, OR\n"
        "  2. Add the exact folder name to taxonomy.allowed_subjects in your config, OR\n"
        "  3. Disable enforcement: set taxonomy.enabled to false\n"
    )
    return False, err


def validate_subject_or_raise(subject: str, config: Config) -> None:
    ok, msg = validate_subject(subject, config)
    if not ok:
        raise ValueError(msg)
