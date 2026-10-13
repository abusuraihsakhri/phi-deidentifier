# PHI De-identifier

Rule-based redaction of common identifiers in free-text clinical notes. Includes a local Python CLI, batch processing, an experimental browser interface, and a separate authenticated operations API.

> **Safety boundary:** This tool is not validated for HIPAA Safe Harbor compliance. The U.S. Safe Harbor method covers 18 classes of identifiers and requires addressing actual knowledge of re-identification risk; these patterns do not reliably detect all names, locations, dates, or institution-specific IDs. Independently review output before using it in research, sharing it, or considering it de-identified. Do not enter real patient information in the public browser demo.

## Browser demonstration

The static interface in `web/index.html` executes the **same Python detection engine** via Pyodide 0.29.5. It accepts pasted synthetic text or a local text file, supports category masking and within-document pseudonym tokens, and allows copying or downloading the result. It has a 1 MB limit. The browser loads Pyodide code from a third-party CDN, so **do not process identifiable records in this public demonstration**. The application does not intentionally transmit the clinical text to a backend or store it in browser storage.

A GitHub Pages Actions workflow packages the browser interface with the Python source and name gazetteer. A public application URL will be listed here only after deployment and functionality have been verified.

## Install

Python 3.10–3.12 is exercised in CI.

```bash
python -m pip install -e .
# For development:
python -m pip install -e ".[dev]"
```

The distribution includes the name gazetteer and installs the `phi-deid` command.

## CLI

```bash
# Process one local note
phi-deid examples/sample_note.txt

# Replace each identifier with a document-local consistent token
phi-deid examples/sample_note.txt --mode pseudonym

# Process each .txt in a directory
phi-deid ./notes -o ./output --report ./output/summary.csv
```

A single file produces `<stem>.deid.txt` and `<stem>.audit.json` by default. Batch mode also emits a CSV count summary. The CLI prevents using identical source, output, and audit paths.

**Privacy:** JSON redaction audits contain the category, rule, character offsets, and replacement token, but **not the original matched text**. The original source files are not intentionally uploaded. Audit metadata and filenames can still reveal contextual information; store them using your institution's required controls. The application does not securely erase source text or automatically verify completeness.

## Detection coverage

The engine contains 17 rule labels: `NAME`, `DATE`, `AGE` (90 and older), `PHONE`, `FAX`, `EMAIL`, `URL`, `IP`, `SSN`, `MRN`, `HEALTH_PLAN_ID`, `ACCOUNT`, `LICENSE_CERT`, `VEHICLE_ID`, `DEVICE_ID`, `ZIP`, and `ADDRESS`. These are **heuristic pattern categories, not a claim that all 18 Safe Harbor identifier classes are completely implemented**. Name detection uses a small bundled dictionary and labels; it will miss unfamiliar names and can redact non-PHI words. Pseudonyms are consistent only within an individual note, not across documents.

## Authenticated operations API

The FastAPI service implements a separate numeric-metric evaluation workflow (it does **not** provide an HTTP endpoint for free-text de-identification). It includes `GET /health`, `GET /metrics`, `POST /api/audit`, `POST /api/chat`, and `GET /api/audit/logs`.

```bash
export PHI_DEID_API_KEY="replace-with-a-strong-random-secret"
export AUDIT_SECRET_KEY="replace-with-an-independent-random-secret"
python cli.py serve --host 127.0.0.1 --port 8000
```

All operational endpoints except `/health` require the HTTP header `Authorization: Bearer <PHI_DEID_API_KEY>`. Without a configured API key, they return HTTP 503. The in-memory audit chain recomputes HMAC-SHA256 signatures; for persistent, consistently keyed auditing set `AUDIT_SECRET_KEY`. Without it, an ephemeral random key is generated for that process. The audit is **in memory only**, not durable, and is not an immutable compliance record.

Docker deployment:

```bash
PHI_DEID_API_KEY="$(openssl rand -hex 32)" AUDIT_SECRET_KEY="$(openssl rand -hex 32)" docker compose up --build
```

By default Docker publishes the port **only on 127.0.0.1**. If exposing the service to other hosts, use TLS, network access controls, and operational security review. Avoid passing identifiable records to the metric and chat endpoints.

## Development and testing

```bash
pytest -v
python -m compileall -q phi_deid agents deidentify.py cli.py
```

CI tests the Python 3.10, 3.11 and 3.12 matrices, checks browser JavaScript syntax, and verifies the installed wheel's CLI entry point and name gazetteer. The codebase uses the Python standard library for the redaction engine, FastAPI/Pydantic for the operations API, Pyodide in the browser, and GitHub Actions for testing and Pages deployment.

The browser interface needs a modern browser with WebAssembly and an initial internet connection for its Pyodide runtime. It cannot be opened directly from `file://`; serve it from an HTTP server or use the Pages deployment.

## License

[MIT](LICENSE).
