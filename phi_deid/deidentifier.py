"""Core rule-based de-identification engine.

Implements a subset of the HIPAA Safe Harbor method (45 CFR 164.514(b)):
structured identifiers are found with regular expressions, and personal
names / geographic subdivisions are found with a name-dictionary gazetteer
combined with contextual cues (titles, "Patient:" labels, street suffixes),
in the spirit of the PhysioNet de-identification approach.

Every match is one of the 18 Safe Harbor identifier categories. Matches never
overlap: rules run in a fixed priority order (most specific / highest
confidence first) and a span already claimed by an earlier rule cannot be
claimed again by a later one.
"""

import re
from dataclasses import dataclass

from . import patterns as pat
from .gazetteer import load_name_gazetteer

CATEGORIES = [
    "NAME",
    "DATE",
    "AGE",
    "PHONE",
    "FAX",
    "EMAIL",
    "URL",
    "IP",
    "SSN",
    "MRN",
    "HEALTH_PLAN_ID",
    "ACCOUNT",
    "LICENSE_CERT",
    "VEHICLE_ID",
    "DEVICE_ID",
    "ZIP",
    "ADDRESS",
]

_TITLE_CUE_RE = re.compile(
    r"(?:Mr|Mrs|Ms|Miss|Mx|Dr|Prof|Patient|Pt|Attending|Nurse|Physician)\.?\s*:?\s*$",
    re.IGNORECASE,
)
_LABELED_NAME_RE = re.compile(
    r"\b(?:Patient(?:\s+Name)?|Name|Pt)\s*:\s*"
    r"(?P<value>[A-Z][a-zA-Z'\-]+(?:\s+[A-Z][a-zA-Z'\-]+){0,3})"
)
_NAME_CANDIDATE_RE = re.compile(
    r"\b(?:[A-Z][a-zA-Z'\-]+\.?\s+){1,3}[A-Z][a-zA-Z'\-]+\.?\b"
)
_PHONE_CONTEXT_RE = re.compile(r"fax", re.IGNORECASE)


@dataclass
class RedactionMatch:
    category: str
    rule: str
    start: int
    end: int
    text: str


class Deidentifier:
    """Detects and redacts the 18 HIPAA Safe Harbor identifier categories."""

    def __init__(self, mode="mask", name_gazetteer=None):
        if mode not in ("mask", "pseudonym"):
            raise ValueError("mode must be 'mask' or 'pseudonym'")
        self.mode = mode
        self.gazetteer = name_gazetteer or load_name_gazetteer()
        self._surrogate_map = {}
        self._surrogate_counters = {}

    # -- public API ---------------------------------------------------

    def redact(self, text):
        """Redact PHI in `text`.

        Returns (redacted_text, audit_log) where audit_log is a list of dicts
        with keys: category, rule, start, end, replacement. Raw PHI is excluded.
        """
        self._surrogate_map = {}
        self._surrogate_counters = {}

        matches = self._find_all_matches(text)
        redacted_text = self._apply_redactions(text, matches)

        audit_log = [
            {
                "category": m.category,
                "rule": m.rule,
                "start": m.start,
                "end": m.end,
                "replacement": self._peek_replacement(m.category, m.text),
            }
            for m in matches
        ]
        return redacted_text, audit_log

    # -- match discovery ------------------------------------------------

    def _find_all_matches(self, text):
        taken = []  # sorted list of (start, end) already claimed
        results = []

        def add_candidates(cands):
            for category, rule, start, end in cands:
                if start >= end:
                    continue
                if self._overlaps(taken, start, end):
                    continue
                taken.append((start, end))
                taken.sort()
                results.append(RedactionMatch(category, rule, start, end, text[start:end]))

        # 1. Highly specific structured identifiers first.
        add_candidates(
            (("EMAIL", "email", m.start(), m.end()) for m in pat.EMAIL_RE.finditer(text))
        )
        add_candidates(
            (("URL", "url", m.start(), m.end()) for m in pat.URL_RE.finditer(text))
        )
        add_candidates(
            (("IP", "ip_address", m.start(), m.end()) for m in pat.IP_RE.finditer(text))
        )
        add_candidates(
            (("SSN", "ssn", m.start(), m.end()) for m in pat.SSN_RE.finditer(text))
        )

        # 2. Labeled numeric/alphanumeric identifiers (value only).
        add_candidates(self._labeled_matches(text, pat.MRN_RE, "MRN", "mrn_label"))
        add_candidates(
            self._labeled_matches(text, pat.HEALTH_PLAN_RE, "HEALTH_PLAN_ID", "health_plan_label")
        )
        add_candidates(self._labeled_matches(text, pat.ACCOUNT_RE, "ACCOUNT", "account_label"))
        add_candidates(
            self._labeled_matches(text, pat.LICENSE_CERT_RE, "LICENSE_CERT", "license_label")
        )
        add_candidates(
            self._labeled_matches(text, pat.VEHICLE_ID_RE, "VEHICLE_ID", "vehicle_id_label")
        )
        add_candidates(
            self._labeled_matches(text, pat.DEVICE_ID_RE, "DEVICE_ID", "device_id_label")
        )

        # 3. Phone / fax numbers (same shape, split by nearby context).
        add_candidates(self._phone_fax_matches(text))

        # 4. Dates.
        add_candidates(
            (("DATE", "date_numeric", m.start(), m.end()) for m in pat.DATE_NUMERIC_RE.finditer(text))
        )
        add_candidates(
            (("DATE", "date_textual", m.start(), m.end()) for m in pat.DATE_TEXTUAL_RE.finditer(text))
        )

        # 5. Ages over 89.
        add_candidates(self._age_matches(text))

        # 6. ZIP codes (context-supported only).
        add_candidates(self._labeled_matches(text, pat.ZIP_LABELED_RE, "ZIP", "zip_label"))
        add_candidates(
            self._labeled_matches(text, pat.ZIP_AFTER_STATE_RE, "ZIP", "zip_after_state")
        )

        # 7. Street addresses.
        add_candidates(
            (("ADDRESS", "street_address", m.start(), m.end()) for m in pat.ADDRESS_RE.finditer(text))
        )

        # 8. Names: explicit "Patient:"/"Name:" labels, then title-cued
        #    spans, then bare dictionary hits.
        add_candidates(self._labeled_name_matches(text))
        add_candidates(self._title_cued_name_matches(text))
        add_candidates(self._gazetteer_name_matches(text))

        results.sort(key=lambda m: m.start)
        return results

    @staticmethod
    def _overlaps(taken, start, end):
        for t_start, t_end in taken:
            if start < t_end and end > t_start:
                return True
        return False

    @staticmethod
    def _labeled_matches(text, regex, category, rule):
        for m in regex.finditer(text):
            yield (category, rule, m.start("value"), m.end("value"))

    def _phone_fax_matches(self, text):
        for m in pat.PHONE_RE.finditer(text):
            context = text[max(0, m.start() - 20) : m.start()]
            if _PHONE_CONTEXT_RE.search(context):
                yield ("FAX", "fax_context", m.start(), m.end())
            else:
                yield ("PHONE", "phone_number", m.start(), m.end())

    def _age_matches(self, text):
        for m in pat.AGE_RE.finditer(text):
            if m.group("age1") is not None:
                value, start, end = m.group("age1"), m.start("age1"), m.end("age1")
            else:
                value, start, end = m.group("age2"), m.start("age2"), m.end("age2")
            if int(value) >= 90:
                yield ("AGE", "age_over_89", start, end)

    def _labeled_name_matches(self, text):
        for m in _LABELED_NAME_RE.finditer(text):
            yield ("NAME", "name_label_context", m.start("value"), m.end("value"))

    def _title_cued_name_matches(self, text):
        for m in _NAME_CANDIDATE_RE.finditer(text):
            context = text[max(0, m.start() - 20) : m.start()]
            if _TITLE_CUE_RE.search(context):
                yield ("NAME", "name_title_context", m.start(), m.end())

    def _gazetteer_name_matches(self, text):
        names = self.gazetteer["all"]
        for m in _NAME_CANDIDATE_RE.finditer(text):
            tokens = m.group(0).split()
            if any(tok.strip(".").upper() in names for tok in tokens):
                yield ("NAME", "name_gazetteer", m.start(), m.end())

    # -- redaction application ------------------------------------------

    def _apply_redactions(self, text, matches):
        pieces = []
        cursor = 0
        for m in matches:
            pieces.append(text[cursor : m.start])
            pieces.append(self._replacement_for(m.category, m.text))
            cursor = m.end
        pieces.append(text[cursor:])
        return "".join(pieces)

    def _replacement_for(self, category, original_text):
        if self.mode == "mask":
            return f"[{category}]"

        key = (category, original_text.strip().upper())
        if key not in self._surrogate_map:
            n = self._surrogate_counters.get(category, 0) + 1
            self._surrogate_counters[category] = n
            self._surrogate_map[key] = f"[{category}_{n}]"
        return self._surrogate_map[key]

    def _peek_replacement(self, category, original_text):
        """Compute what token was/will be used, without mutating counters
        (assumes redact() already ran _apply_redactions, so pseudonym mode
        lookups here just read the map that redact() already built)."""
        if self.mode == "mask":
            return f"[{category}]"
        key = (category, original_text.strip().upper())
        return self._surrogate_map.get(key, f"[{category}]")
