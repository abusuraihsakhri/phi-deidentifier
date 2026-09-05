# Phi Deidentifier

> **Domain:** Clinical Decision Support & Biomedical Computing
> **Standard:** HIPAA Safe Harbor (45 CFR 164.514(b))

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)

</div>

---

## What It Does

PHI De-identifier is a rule-based clinical text redaction tool. It scans clinical
notes for HIPAA Safe Harbor identifier categories (names, dates, phone numbers,
MRNs, SSNs, addresses, and more) and redacts them, either as a single file or
in batch over a directory.

---

## Installation

```bash
pip install -e .
```

For development (includes pytest):

```bash
pip install -e ".[dev]"
```

---

## Usage

### Single File Mode

```bash
python deidentify.py examples/sample_note.txt
```

This produces:
- `examples/sample_note.deid.txt` — redacted text
- `examples/sample_note.audit.json` — audit log of every redaction

### Batch Directory Mode

```bash
python deidentify.py /path/to/notes/ -o /path/to/output/
```

Processes all `.txt` files, writing redacted text and per-file audit logs.

### Options

| Flag | Description |
|:-----|:------------|
| `-o, --output` | Output file (single mode) or directory (batch mode) |
| `--mode mask` | Replace PHI with `[CATEGORY]` tags (default) |
| `--mode pseudonym` | Replace with consistent surrogate tokens like `[NAME_1]` |
| `--audit` | Path for audit log file or directory |
| `--report` | Batch mode: path to CSV summary report |

### Examples

```bash
# Mask PHI in a single file
python deidentify.py note.txt

# Use pseudonym mode
python deidentify.py note.txt --mode pseudonym

# Custom output and audit paths
python deidentify.py note.txt -o redacted.txt --audit log.json

# Batch process with custom output directory
python deidentify.py ./notes/ -o ./redacted/ --mode pseudonym
```

---

## HIPAA Safe Harbor Categories

The tool detects and redacts 17 identifier categories:

| Category | Example |
|:---------|:--------|
| NAME | `John Smith` |
| DATE | `03/14/1958` |
| AGE | Ages 90 and over |
| PHONE | `(617) 555-0142` |
| FAX | `fax (617) 555-0199` |
| EMAIL | `john@example.com` |
| URL | `www.example.com` |
| IP | `10.0.0.5` |
| SSN | `044-56-7890` |
| MRN | `MRN: A1234567` |
| HEALTH_PLAN_ID | `Member ID: XYZ123` |
| ACCOUNT | `Account: 88213456` |
| LICENSE_CERT | `License: ABC123` |
| VEHICLE_ID | `VIN: 1HGCM82633A` |
| DEVICE_ID | `Serial: SN12345` |
| ZIP | `MA 02115` |
| ADDRESS | `452 Oak Street` |

---

## API Server

Launch the FastAPI REST server:

```bash
python cli.py serve --host 127.0.0.1 --port 8000
```

Endpoints:
- `GET /health` — health check
- `GET /metrics` — operational metrics
- `POST /api/audit` — submit a task for evaluation
- `POST /api/chat` — supervisory chat query
- `GET /api/audit/logs` — retrieve and verify HMAC audit trail

### Docker

```bash
docker-compose up
```

**Note:** Set `AUDIT_SECRET_KEY` in production. See Security section below.

---

## Testing

```bash
pytest -v
```

Test structure:
- `tests/test_deidentifier.py` — core de-identification engine tests
- `tests/test_phi_deidentifier.py` — API, workers, and audit trail tests
- `tests/test_enrichment.py` — enrichment suite tests
- `test_deidentify.py` — import smoke test

---

## Security

### Audit Secret Key

The HMAC-SHA256 audit trail requires a secret key. **Do not use the default
in production.**

Set via environment variable:

```bash
export AUDIT_SECRET_KEY="your-secure-random-key"
```

Or in docker-compose.yml, pass it at runtime:

```bash
AUDIT_SECRET_KEY=$(openssl rand -hex 32) docker-compose up
```

### PHI Guard

The outbound PHI guard intercepts responses containing unredacted identifiers
(SSNs, MRNs, phone numbers, etc.) before they leave the system.

### Path Handling

File paths are normalized and validated. The tool handles encoding errors
gracefully (falls back to latin-1 if UTF-8 decoding fails).

---

## Project Structure

```
phi-deidentifier/
├── deidentify.py          # CLI entry point for PHI de-identification
├── phi_deid/              # Core de-identification engine
│   ├── deidentifier.py    # Rule-based detection and redaction
│   ├── patterns.py        # Regex patterns for structured identifiers
│   ├── batch.py           # Batch file/directory processing
│   └── gazetteer.py       # Name dictionary for name detection
├── agents/                # API server and worker framework
│   ├── api.py             # FastAPI REST endpoints
│   ├── supervisor.py      # Task orchestration
│   ├── workers.py         # Specialized evaluation workers
│   ├── base.py            # Security guard and audit trail
│   └── models.py          # Pydantic data models
├── data/
│   └── names.csv          # Name gazetteer dictionary
├── tests/                 # Test suite
├── examples/
│   └── sample_note.txt    # Sample clinical note
├── web/
│   └── index.html         # Operations console UI
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

---

## License

MIT
