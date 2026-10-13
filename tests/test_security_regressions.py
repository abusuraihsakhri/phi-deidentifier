"""Privacy, integrity and CLI reliability regression tests."""
import json

from agents.base import AuditTrail
from deidentify import main
from phi_deid import Deidentifier
from phi_deid.gazetteer import load_name_gazetteer


def test_redaction_audit_excludes_original_phi():
    source = "Patient: John Smith\nSSN: 044-56-7890\nPhone: (617) 555-0142"
    redacted, audit = Deidentifier().redact(source)
    assert "044-56-7890" not in redacted
    assert "John Smith" not in redacted
    assert "(617) 555-0142" not in redacted
    assert all("original" not in item for item in audit)
    serialized = json.dumps(audit)
    assert "John Smith" not in serialized
    assert "044-56-7890" not in serialized
    assert "(617) 555-0142" not in serialized


def test_international_and_parenthesized_phone_match():
    for value in ["(617) 555-0142", "+1 (617) 555-0142", "617-555-0142"]:
        redacted, _ = Deidentifier().redact("Phone: " + value)
        assert value not in redacted
        assert "[PHONE]" in redacted


def test_audit_trail_verifies_signatures_and_defends_its_contents():
    audit = AuditTrail(secret_key="test-secret")
    audit.log("operator", "reviewer", "TEST", {"status": "SUCCESS"})
    assert audit.verify_integrity()
    copy = audit.get_trail()
    copy[0]["payload_hash"] = "forged"
    assert audit.verify_integrity()
    audit.logs[0]["payload_hash"] = "forged"
    assert not audit.verify_integrity()


def test_cli_prevents_overwriting_source_and_audit(tmp_path):
    note = tmp_path / "note.txt"
    note.write_text("SSN: 044-56-7890", encoding="utf-8")
    assert main([str(note), "-o", str(note)]) == 1
    assert note.read_text(encoding="utf-8") == "SSN: 044-56-7890"
    assert main([str(note), "--audit", str(note)]) == 1
    assert main([str(note), "-o", str(tmp_path / "x"), "--audit", str(tmp_path / "x")]) == 1


def test_cli_creates_output_parents(tmp_path):
    note = tmp_path / "note.txt"
    note.write_text("SSN: 044-56-7890", encoding="utf-8")
    output = tmp_path / "nested" / "output.txt"
    audit = tmp_path / "logs" / "audit.json"
    assert main([str(note), "-o", str(output), "--audit", str(audit)]) == 0
    assert "[SSN]" in output.read_text(encoding="utf-8")
    assert "044-56-7890" not in audit.read_text(encoding="utf-8")


def test_packaged_gazetteer_has_names():
    assert "JOHN" in load_name_gazetteer()["all"]
