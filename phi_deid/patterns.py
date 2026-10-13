"""Regex patterns for the structured HIPAA Safe Harbor identifier categories.

Each entry in STRUCTURED_RULES is a tuple of (category, rule_name, compiled_regex).
For rules where the whole match should be redacted, the regex has no named
'value' group. For "labeled identifier" rules (MRN, account numbers, etc.)
the regex captures the identifier itself in a group named 'value' so that only
the value -- not the label -- gets redacted.
"""

import re

# ---------------------------------------------------------------------------
# Contact / network identifiers
# ---------------------------------------------------------------------------

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

URL_RE = re.compile(
    r"\b(?:https?://[^\s,;)>\]\"']+|www\.[^\s,;)>\]\"']+\.[A-Za-z]{2,}[^\s,;)>\]\"']*)"
)

IP_RE = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b"
)

# ---------------------------------------------------------------------------
# National / government identifiers
# ---------------------------------------------------------------------------

SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")

# ---------------------------------------------------------------------------
# Telephone / fax numbers (matched together, split by context in deidentifier.py)
# ---------------------------------------------------------------------------

PHONE_RE = re.compile(
    r"(?<!\w)(?:\+?1[-.\s]?)?(?:\(\d{3}\)|\d{3})[-.\s]?\d{3}[-.\s]?\d{4}(?!\w)"
)

# ---------------------------------------------------------------------------
# Labeled identifiers: "Label: VALUE" style structured IDs.
# The label text stays in the redacted output; only the value is replaced.
# ---------------------------------------------------------------------------

def _labeled(label_pattern, value_pattern=r"[A-Za-z0-9][A-Za-z0-9-]{2,14}"):
    return re.compile(
        r"\b(?:" + label_pattern + r")\s*[:#]?\s*(?P<value>" + value_pattern + r")\b",
        re.IGNORECASE,
    )


MRN_RE = _labeled(r"MRN|Medical\s+Record\s+(?:No\.?|Number|#)?|Record\s*#")
HEALTH_PLAN_RE = _labeled(
    r"Health\s+Plan(?:\s+(?:ID|Number|No\.?|Beneficiary\s+(?:ID|Number)))?|"
    r"Beneficiary\s+(?:ID|Number)|Member\s+ID"
)
ACCOUNT_RE = _labeled(r"Acct(?:\.|ount)?\s*(?:No\.?|Number|#)?|Account\s*#")
LICENSE_CERT_RE = _labeled(
    r"License\s*(?:No\.?|Number|#)?|Lic\.?\s*#|Certificate\s*(?:No\.?|Number|#)?"
)
VEHICLE_ID_RE = _labeled(
    r"VIN|License\s+Plate|Plate\s*(?:No\.?|Number|#)?",
    value_pattern=r"[A-Za-z0-9][A-Za-z0-9-]{4,17}",
)
DEVICE_ID_RE = _labeled(
    r"Device\s*(?:ID|Serial|S/N)|Serial\s*(?:No\.?|Number|#)?"
)

# ---------------------------------------------------------------------------
# Dates -- every common numeric / textual clinical note format.
# ---------------------------------------------------------------------------

_MONTHS = (
    r"Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
    r"Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?"
)

DATE_NUMERIC_RE = re.compile(
    r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{1,2}-\d{1,2})\b"
)

DATE_TEXTUAL_RE = re.compile(
    r"\b(?:(?:" + _MONTHS + r")\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}"
    r"|\d{1,2}(?:st|nd|rd|th)?\s+(?:" + _MONTHS + r")\.?,?\s+\d{4})\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Ages over 89 (Safe Harbor requires redacting ages 90+)
# ---------------------------------------------------------------------------

AGE_RE = re.compile(
    r"\b(?:[Aa]ge[d]?[:\s]+(?P<age1>\d{1,3})\b"
    r"|(?P<age2>\d{1,3})[- ](?:years?[- ]old|y\.?o\.?|year-old))",
)

# ---------------------------------------------------------------------------
# ZIP codes -- only matched with contextual support (state abbreviation or
# explicit "ZIP" label) to avoid treating arbitrary 5-digit numbers as ZIPs.
# ---------------------------------------------------------------------------

_STATE_ABBRS = (
    "AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|ME|MD|MA|MI|MN|MS|MO|"
    "MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|TN|TX|UT|VT|VA|WA|WV|WI|WY|DC"
)

ZIP_AFTER_STATE_RE = re.compile(
    r"\b(?:" + _STATE_ABBRS + r")\s+(?P<value>\d{5}(?:-\d{4})?)\b"
)
ZIP_LABELED_RE = _labeled(r"ZIP(?:\s*Code)?", value_pattern=r"\d{5}(?:-\d{4})?")

# ---------------------------------------------------------------------------
# Street addresses (geographic subdivision smaller than state)
# ---------------------------------------------------------------------------

_STREET_SUFFIX = (
    r"Street|St\.?|Avenue|Ave\.?|Boulevard|Blvd\.?|Road|Rd\.?|Lane|Ln\.?|Drive|Dr\.?|"
    r"Court|Ct\.?|Place|Pl\.?|Way|Circle|Cir\.?|Terrace|Ter\.?|Highway|Hwy\.?|"
    r"Parkway|Pkwy\.?|Square|Sq\.?"
)

ADDRESS_RE = re.compile(
    r"\b\d{1,6}\s+(?:[A-Z][a-zA-Z']*\s+){1,4}(?:" + _STREET_SUFFIX + r")\b"
    r"(?:,?\s*(?:Apt|Suite|Ste|Unit|#)\.?\s*[A-Za-z0-9-]+)?"
)
