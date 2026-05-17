"""PDF → per-page markdown extraction pipeline.

Walk a PDF tree, extract text page-by-page via pypdf, write a deterministic
cache under `<pdf_root>/<derived_dir>/`. The cache is reproducible from the
PDFs; safe to delete and rebuild.

Page numbers come from the FILE PATH (`pNNNN.md`), never parsed from content.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError
    from tqdm import tqdm
except ImportError as e:
    print(
        f"Missing dependency: {e}\n"
        "Install with: pip install pypdf 'cryptography>=3.1' tqdm",
        file=sys.stderr,
    )
    raise

from proactive_librarian.config import Config
from proactive_librarian.taxonomy import derive_subject_geography, validate_subject_or_raise


DERIVED_VERSION = 2  # page-per-file format


@dataclass
class IngestStats:
    processed: int = 0
    skipped: int = 0
    errors: int = 0
    total_pages: int = 0
    failures: list[dict] = field(default_factory=list)

    def record_failure(self, pdf_path: Path, reason: str, pdf_root: Path) -> None:
        self.errors += 1
        try:
            rel = str(pdf_path.relative_to(pdf_root))
        except ValueError:
            rel = str(pdf_path)
        self.failures.append({"pdf": rel, "reason": reason})


def compute_sha1(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Streaming SHA-1 — handles arbitrarily large files."""
    h = hashlib.sha1()
    with path.open("rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def get_page_dir(pdf_path: Path, config: Config) -> Path:
    """Map `<pdf_root>/<sub>/<file>.pdf` → `<derived_root>/<sub>/<file>/`."""
    rel = pdf_path.resolve().relative_to(config.pdf_root)
    return config.derived_root / rel.with_suffix("")


def extract_page_text(page) -> str:
    """Robust page extraction with surrogate-character sanitisation.

    PDFs sometimes leak unpaired UTF-16 surrogates from emoji or 4-byte chars;
    these crash the subsequent UTF-8 write unless replaced.
    """
    try:
        text = page.extract_text() or ""
    except Exception as exc:
        text = f"[pypdf extraction failed: {exc}]"
    text = text.encode("utf-8", errors="replace").decode("utf-8")
    return text.strip()


def write_page_atomic(page_dir: Path, page_num: int, text: str, config: Config) -> None:
    path = page_dir / config.page_filename(page_num)
    tmp = path.with_suffix(".md.tmp")
    tmp.write_text(text + "\n", encoding="utf-8")
    tmp.replace(path)


def write_meta(
    page_dir: Path,
    source_pdf: Path,
    subject: str,
    geography: Optional[str],
    page_count: int,
    file_size: int,
    sha1: str,
    config: Config,
) -> None:
    meta = {
        "source_pdf": str(source_pdf.resolve().relative_to(config.pdf_root)),
        "subject": subject,
        "geography": geography or "General",
        "page_count": page_count,
        "file_size_bytes": file_size,
        "sha1": sha1,
        "ingested_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "derived_version": DERIVED_VERSION,
    }
    path = page_dir / "_meta.json"
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    tmp.replace(path)


def load_manifest(config: Config) -> dict[str, dict]:
    if not config.manifest_path.exists():
        return {}
    try:
        return json.loads(config.manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_manifest(manifest: dict[str, dict], config: Config) -> None:
    config.manifest_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = config.manifest_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(config.manifest_path)


def save_failures(stats: IngestStats, config: Config) -> None:
    config.failures_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total_failures": len(stats.failures),
        "failures": stats.failures,
    }
    tmp = config.failures_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(config.failures_path)


def ingest_one(
    pdf_path: Path,
    config: Config,
    manifest: dict[str, dict],
    force: bool,
    stats: IngestStats,
) -> str:
    """Process one PDF; return a short status string."""
    rel_key = str(pdf_path.resolve().relative_to(config.pdf_root))

    try:
        subject, geography = derive_subject_geography(pdf_path, config)
        validate_subject_or_raise(subject, config)
    except ValueError as ve:
        stats.record_failure(pdf_path, f"taxonomy: {str(ve).splitlines()[0]}", config.pdf_root)
        return "taxonomy-error"

    sha1 = compute_sha1(pdf_path)
    page_dir = get_page_dir(pdf_path, config)

    prior = manifest.get(rel_key)
    if not force and prior and prior.get("sha1") == sha1 and page_dir.exists():
        stats.skipped += 1
        return "sha1-match"

    if page_dir.exists():
        shutil.rmtree(page_dir)
    page_dir.mkdir(parents=True, exist_ok=True)

    try:
        reader = PdfReader(str(pdf_path))
        if reader.is_encrypted:
            try:
                if reader.decrypt("") == 0:
                    raise PdfReadError("PDF is encrypted with a non-empty password")
            except Exception as exc:
                stats.record_failure(pdf_path, f"encrypted: {exc}", config.pdf_root)
                shutil.rmtree(page_dir, ignore_errors=True)
                return "encrypted"
        page_count = len(reader.pages)
    except Exception as exc:
        stats.record_failure(pdf_path, f"pypdf open failed: {exc}", config.pdf_root)
        shutil.rmtree(page_dir, ignore_errors=True)
        return "open-error"

    try:
        for i, page in enumerate(reader.pages, start=1):
            text = extract_page_text(page)
            write_page_atomic(page_dir, i, text, config)
        write_meta(
            page_dir, pdf_path, subject, geography,
            page_count, pdf_path.stat().st_size, sha1, config,
        )
    except Exception as exc:
        stats.record_failure(pdf_path, f"page-write failed: {exc}", config.pdf_root)
        shutil.rmtree(page_dir, ignore_errors=True)
        return "write-error"

    manifest[rel_key] = {
        "sha1": sha1,
        "subject": subject,
        "geography": geography or "General",
        "page_count": page_count,
        "ingested_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    stats.processed += 1
    stats.total_pages += page_count
    return f"ingested {page_count}p"


def run_ingest(
    config: Config,
    *,
    full: bool = False,
    dry_run: bool = False,
    limit: int = 0,
    category: Optional[str] = None,
    clean: bool = False,
    verbose: bool = False,
) -> IngestStats:
    """Top-level ingest entry. Suitable for CLI or programmatic use."""
    if not config.pdf_root.exists():
        raise FileNotFoundError(f"pdf_root does not exist: {config.pdf_root}")

    if clean and config.derived_root.exists():
        print(f"--clean: removing {config.derived_root} ...")
        shutil.rmtree(config.derived_root)

    config.derived_root.mkdir(exist_ok=True, parents=True)

    print(f"Scanning for PDFs under {config.pdf_root} ...")
    derived_name = config.derived_dir
    all_pdfs = sorted(
        p for p in config.pdf_root.rglob("*.pdf") if derived_name not in p.parts
    )
    print(f"Found {len(all_pdfs)} PDF files.")

    if category:
        all_pdfs = [p for p in all_pdfs
                    if derive_subject_geography(p, config)[0] == category]
        print(f"Filtered to {len(all_pdfs)} under category {category!r}.")

    if limit > 0:
        all_pdfs = all_pdfs[:limit]
        print(f"Limited to first {len(all_pdfs)} PDFs.")

    if not all_pdfs:
        print("Nothing to do.")
        return IngestStats()

    print(f"Mode: {'FULL (force re-extract)' if full else 'INCREMENTAL (sha1 cache)'}")
    if dry_run:
        print("*** DRY RUN — no files will be written ***")

    manifest = load_manifest(config)
    stats = IngestStats()
    start = time.time()

    for pdf_path in tqdm(all_pdfs, desc="Ingesting", unit="pdf"):
        if dry_run:
            try:
                subject, _ = derive_subject_geography(pdf_path, config)
                validate_subject_or_raise(subject, config)
                stats.processed += 1
                if verbose:
                    tqdm.write(f"DRY ok: {pdf_path}")
            except ValueError as ve:
                stats.record_failure(pdf_path, str(ve).splitlines()[0], config.pdf_root)
            continue

        status = ingest_one(pdf_path, config, manifest, full, stats)
        if verbose:
            tqdm.write(f"{status}: {pdf_path}")

    elapsed = time.time() - start

    if not dry_run:
        save_manifest(manifest, config)
    save_failures(stats, config)

    print("\n" + "=" * 60)
    print("INGEST COMPLETE")
    print(f"  PDFs processed:        {stats.processed}")
    print(f"  PDFs skipped (sha1):   {stats.skipped}")
    print(f"  Failures:              {stats.errors}")
    print(f"  Total pages extracted: {stats.total_pages}")
    print(f"  Wall time:             {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print(f"  Derived cache:         {config.derived_root}")
    print(f"  Manifest:              {config.manifest_path}")
    print(f"  Failures log:          {config.failures_path}")
    print("=" * 60)

    if stats.errors > 0:
        print(f"\n{stats.errors} PDF(s) failed — inspect "
              f"{config.failures_path.name} for details.")

    return stats
