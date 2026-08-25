#!/usr/bin/env python
"""PHI De-identifier command-line interface.

Scans clinical note text for the 18 HIPAA Safe Harbor identifier categories
and redacts them, either as a single file or in batch over a directory.
"""

import argparse
import json
import os
import sys

from phi_deid.batch import process_directory, process_file, write_report_csv
from phi_deid.deidentifier import CATEGORIES, Deidentifier


def build_parser():
    parser = argparse.ArgumentParser(
        prog="deidentify.py",
        description=(
            "Redact HIPAA Safe Harbor PHI identifiers (names, dates, phone "
            "numbers, MRNs, addresses, and more) from clinical text."
        ),
    )
    parser.add_argument(
        "input", help="Path to a clinical note text file, or a directory of .txt files"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file (single-file mode) or output directory (batch mode). "
             "Defaults to '<input>.deid.txt' or '<input_dir>_deidentified/'.",
    )
    parser.add_argument(
        "--mode", choices=["mask", "pseudonym"], default="mask",
        help="Redaction style: 'mask' replaces PHI with a category tag like "
             "[NAME]; 'pseudonym' replaces it with a consistent surrogate "
             "token like [NAME_1], the same token every time that value "
             "recurs in the document. Default: mask.",
    )
    parser.add_argument(
        "--audit",
        help="Path to write the audit log. Single-file mode: a JSON file "
             "(default '<input>.audit.json'). Batch mode: a directory of "
             "per-file JSON audit logs (default '<output>/audit/').",
    )
    parser.add_argument(
        "--report",
        help="Batch mode only: path to the CSV summary report "
             "(default '<output>/deid_report.csv').",
    )
    return parser


def run_single_file(args):
    deid = Deidentifier(mode=args.mode)
    output_path = args.output or _default_single_output(args.input)
    audit_path = args.audit or _default_single_audit(args.input)

    redacted_text, audit_log, counts = process_file(deid, args.input)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(redacted_text)
    with open(audit_path, "w", encoding="utf-8") as f:
        json.dump(audit_log, f, indent=2)

    print(f"De-identified: {args.input} -> {output_path}")
    print(f"Audit log: {audit_path}")
    print(f"Total redactions: {len(audit_log)}")
    for cat in CATEGORIES:
        if counts[cat]:
            print(f"  {cat}: {counts[cat]}")
    return 0


def run_batch(args):
    output_dir = args.output or _default_batch_output(args.input)
    audit_dir = args.audit or os.path.join(output_dir, "audit")
    report_path = args.report or os.path.join(output_dir, "deid_report.csv")

    report = process_directory(args.input, output_dir, audit_dir, mode=args.mode)
    write_report_csv(report, report_path)

    print(f"Processed {report['total_files']} file(s) from {args.input}")
    print(f"Redacted text written to: {output_dir}")
    print(f"Per-file audit logs written to: {audit_dir}")
    print(f"Summary report: {report_path}")
    print(f"Total redactions: {report['total_redactions']}")
    for cat in CATEGORIES:
        if report["totals"][cat]:
            print(f"  {cat}: {report['totals'][cat]}")
    return 0


def _default_single_output(input_path):
    base, _ext = os.path.splitext(input_path)
    return f"{base}.deid.txt"


def _default_single_audit(input_path):
    base, _ext = os.path.splitext(input_path)
    return f"{base}.audit.json"


def _default_batch_output(input_dir):
    input_dir = input_dir.rstrip("/\\")
    return f"{input_dir}_deidentified"


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    if not os.path.exists(args.input):
        parser.error(f"input path does not exist: {args.input}")

    if os.path.isdir(args.input):
        return run_batch(args)
    return run_single_file(args)


if __name__ == "__main__":
    sys.exit(main())
