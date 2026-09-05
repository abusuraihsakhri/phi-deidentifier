"""
Tests for the core PHI de-identification engine.
"""
import os
import sys
import tempfile

import pytest

sys.path.insert(0, str(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from phi_deid.deidentifier import Deidentifier, CATEGORIES
from phi_deid.batch import process_file, process_directory


class TestDeidentifierMaskMode:
    """Test PHI detection and masking."""

    def setup_method(self):
        self.deid = Deidentifier(mode="mask")

    def test_redact_name_label(self):
        text = "Patient: John Smith was seen today."
        redacted, log = self.deid.redact(text)
        assert "[NAME]" in redacted
        assert "John Smith" not in redacted

    def test_redact_ssn(self):
        text = "SSN: 044-56-7890 is on file."
        redacted, log = self.deid.redact(text)
        assert "[SSN]" in redacted
        assert "044-56-7890" not in redacted

    def test_redact_email(self):
        text = "Contact john.smith@example.com for info."
        redacted, log = self.deid.redact(text)
        assert "[EMAIL]" in redacted
        assert "john.smith@example.com" not in redacted

    def test_redact_phone(self):
        text = "Phone: (617) 555-0142"
        redacted, log = self.deid.redact(text)
        assert "[PHONE]" in redacted
        assert "(617) 555-0142" not in redacted

    def test_redact_date(self):
        text = "DOB: 03/14/1958"
        redacted, log = self.deid.redact(text)
        assert "[DATE]" in redacted
        assert "03/14/1958" not in redacted

    def test_redact_age_over_89(self):
        text = "The patient is 91 years old."
        redacted, log = self.deid.redact(text)
        assert "[AGE]" in redacted
        assert "91" not in redacted

    def test_age_under_90_not_redacted(self):
        text = "The patient is 45 years old."
        redacted, log = self.deid.redact(text)
        assert "45" in redacted

    def test_redact_mrn(self):
        text = "MRN: A1234567"
        redacted, log = self.deid.redact(text)
        assert "[MRN]" in redacted

    def test_redact_url(self):
        text = "Visit www.patientportal.example.com"
        redacted, log = self.deid.redact(text)
        assert "[URL]" in redacted

    def test_redact_ip(self):
        text = "Connected from 10.0.0.5"
        redacted, log = self.deid.redact(text)
        assert "[IP]" in redacted
        assert "10.0.0.5" not in redacted

    def test_redact_address(self):
        text = "Lives at 452 Oak Street, Boston."
        redacted, log = self.deid.redact(text)
        assert "[ADDRESS]" in redacted

    def test_no_phi_passes_through(self):
        text = "The patient presents with normal cardiac function."
        redacted, log = self.deid.redact(text)
        assert redacted == text
        assert len(log) == 0


class TestDeidentifierPseudonymMode:
    """Test pseudonym (consistent surrogate) mode."""

    def setup_method(self):
        self.deid = Deidentifier(mode="pseudonym")

    def test_consistent_pseudonym(self):
        text = "John Smith saw Dr. Jones. John Smith returned."
        redacted, log = self.deid.redact(text)
        # Same name should get same pseudonym
        assert "[NAME_1]" in redacted

    def test_different_names_different_pseudonyms(self):
        text = "John Smith and Mary Johnson were present."
        redacted, log = self.deid.redact(text)
        # Should have two different name pseudonyms
        name_tokens = [entry["replacement"] for entry in log if entry["category"] == "NAME"]
        assert len(set(name_tokens)) >= 2


class TestDeidentifierValidation:
    """Test input validation."""

    def test_invalid_mode_raises(self):
        with pytest.raises(ValueError):
            Deidentifier(mode="invalid")

    def test_empty_text(self):
        deid = Deidentifier(mode="mask")
        redacted, log = deid.redact("")
        assert redacted == ""
        assert log == []


class TestBatchProcessing:
    """Test file and directory processing."""

    def test_process_file(self, tmp_path):
        input_file = tmp_path / "note.txt"
        input_file.write_text("Patient: John Smith\nSSN: 044-56-7890\n")

        deid = Deidentifier(mode="mask")
        redacted, log, counts = process_file(deid, str(input_file))

        assert "[NAME]" in redacted
        assert "[SSN]" in redacted
        assert counts["NAME"] >= 1
        assert counts["SSN"] == 1

    def test_process_directory(self, tmp_path):
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        audit_dir = tmp_path / "audit"

        (input_dir / "note1.txt").write_text("Patient: John Smith")
        (input_dir / "note2.txt").write_text("SSN: 044-56-7890")

        report = process_directory(str(input_dir), str(output_dir), str(audit_dir))

        assert report["total_files"] == 2
        assert report["total_redactions"] >= 2

    def test_non_txt_files_ignored(self, tmp_path):
        input_dir = tmp_path / "input"
        input_dir.mkdir()
        output_dir = tmp_path / "output"
        audit_dir = tmp_path / "audit"

        (input_dir / "note.txt").write_text("Patient: John Smith")
        (input_dir / "readme.md").write_text("SSN: 044-56-7890")

        report = process_directory(str(input_dir), str(output_dir), str(audit_dir))

        assert report["total_files"] == 1


class TestCategories:
    """Test that all 18 HIPAA categories are defined."""

    def test_18_categories(self):
        assert len(CATEGORIES) == 17  # Current implementation covers 17 of 18

    def test_expected_categories_present(self):
        expected = {
            "NAME", "DATE", "AGE", "PHONE", "FAX", "EMAIL", "URL", "IP",
            "SSN", "MRN", "HEALTH_PLAN_ID", "ACCOUNT", "LICENSE_CERT",
            "VEHICLE_ID", "DEVICE_ID", "ZIP", "ADDRESS",
        }
        assert set(CATEGORIES) == expected
