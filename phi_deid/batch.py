"""Batch processing over a directory of clinical note text files."""

import csv
import json
import os

from .deidentifier import CATEGORIES, Deidentifier


def process_file(deid, input_path):
    """Redact a single file. Returns (redacted_text, audit_log, counts)."""
    try:
        with open(input_path, "r", encoding="utf-8") as f:
            text = f.read()
    except UnicodeDecodeError:
        # Retry with latin-1 as fallback for non-UTF-8 files
        with open(input_path, "r", encoding="latin-1") as f:
            text = f.read()

    redacted_text, audit_log = deid.redact(text)

    counts = {cat: 0 for cat in CATEGORIES}
    for entry in audit_log:
        counts[entry["category"]] = counts.get(entry["category"], 0) + 1

    return redacted_text, audit_log, counts


def process_directory(input_dir, output_dir, audit_dir, mode="mask", pattern="*.txt"):
    """De-identify every .txt file in `input_dir`.

    Writes redacted text to `output_dir`, a per-file audit log (JSON) to
    `audit_dir`, and returns a summary report: a list of per-file stats plus
    the totals across the whole batch.
    """
    if os.path.realpath(input_dir) == os.path.realpath(output_dir):
        raise ValueError("Output directory must differ from input directory")
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(audit_dir, exist_ok=True)

    filenames = sorted(
        fn for fn in os.listdir(input_dir)
        if fn.lower().endswith(".txt") and os.path.isfile(os.path.join(input_dir, fn))
    )

    per_file_rows = []
    totals = {cat: 0 for cat in CATEGORIES}

    for fn in filenames:
        # Each document gets a fresh surrogate map so pseudonyms are
        # consistent *within* a document but not linkable *across* documents.
        deid = Deidentifier(mode=mode)
        input_path = os.path.join(input_dir, fn)
        redacted_text, audit_log, counts = process_file(deid, input_path)

        stem = os.path.splitext(fn)[0]
        out_path = os.path.join(output_dir, f"{stem}.deid.txt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(redacted_text)

        audit_path = os.path.join(audit_dir, f"{stem}.audit.json")
        with open(audit_path, "w", encoding="utf-8") as f:
            json.dump(audit_log, f, indent=2)

        row = {"file": fn, "total_redactions": len(audit_log)}
        row.update(counts)
        per_file_rows.append(row)

        for cat, n in counts.items():
            totals[cat] += n

    return {
        "files": per_file_rows,
        "totals": totals,
        "total_files": len(filenames),
        "total_redactions": sum(totals.values()),
    }


def write_report_csv(report, report_path):
    os.makedirs(os.path.dirname(os.path.abspath(report_path)), exist_ok=True)
    fieldnames = ["file", "total_redactions"] + CATEGORIES
    with open(report_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in report["files"]:
            writer.writerow(row)
        totals_row = {"file": "TOTAL", "total_redactions": report["total_redactions"]}
        totals_row.update(report["totals"])
        writer.writerow(totals_row)
