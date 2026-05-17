"""Tests for the optional subject taxonomy enforcement."""
from __future__ import annotations

from pathlib import Path

import pytest

from proactive_librarian.taxonomy import (
    derive_subject_geography,
    validate_subject,
    validate_subject_or_raise,
)


class TestDeriveSubjectGeography:
    def test_subject_and_geography(self, permissive_config, tmp_path):
        pdf = tmp_path / "Alpha" / "Region1" / "report.pdf"
        pdf.parent.mkdir(parents=True)
        pdf.touch()
        subj, geo = derive_subject_geography(pdf, permissive_config)
        assert subj == "Alpha"
        assert geo == "Region1"

    def test_subject_only_when_pdf_at_subject_root(self, permissive_config, tmp_path):
        pdf = tmp_path / "Alpha" / "report.pdf"
        pdf.parent.mkdir(parents=True)
        pdf.touch()
        subj, geo = derive_subject_geography(pdf, permissive_config)
        assert subj == "Alpha"
        assert geo is None

    def test_strips_leading_whitespace(self, permissive_config, tmp_path):
        # Cloud-sync exports sometimes produce folders with leading spaces
        pdf = tmp_path / " Alpha " / "file.pdf"
        pdf.parent.mkdir(parents=True)
        pdf.touch()
        subj, _ = derive_subject_geography(pdf, permissive_config)
        assert subj == "Alpha"


class TestValidateSubjectPermissive:
    def test_anything_passes_when_disabled(self, permissive_config):
        ok, err = validate_subject("Anything", permissive_config)
        assert ok is True
        assert err == ""


class TestValidateSubjectStrict:
    @pytest.mark.parametrize("subject", ["Alpha", "Beta", "Gamma"])
    def test_allowed_subjects_pass(self, strict_config, subject):
        ok, err = validate_subject(subject, strict_config)
        assert ok is True
        assert err == ""

    def test_unknown_subject_returns_actionable_error(self, strict_config):
        ok, err = validate_subject("Delta", strict_config)
        assert ok is False
        assert "Delta" in err
        assert "Alpha" in err  # lists allowed subjects
        assert "config" in err  # tells user how to fix

    def test_guide_reference_surfaced_in_error(self, strict_config):
        _, err = validate_subject("Delta", strict_config)
        assert "docs/taxonomy.md" in err

    def test_or_raise_silent_on_valid(self, strict_config):
        validate_subject_or_raise("Alpha", strict_config)  # must not raise

    def test_or_raise_raises_on_invalid(self, strict_config):
        with pytest.raises(ValueError, match="Unknown subject"):
            validate_subject_or_raise("Delta", strict_config)
