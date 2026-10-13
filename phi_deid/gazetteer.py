"""Loads the bundled name gazetteer (dictionary of first/last names) used for
dictionary-based name detection.
"""

import csv
import os
import warnings

_PACKAGE_PATH = os.path.join(os.path.dirname(__file__), "data", "names.csv")
_SOURCE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "names.csv"
)
DEFAULT_NAMES_PATH = _PACKAGE_PATH if os.path.isfile(_PACKAGE_PATH) else _SOURCE_PATH


def load_name_gazetteer(path=None):
    """Load the name gazetteer CSV (columns: name,type where type is 'first' or 'last').

    Returns a dict with keys 'first' and 'last', each a set of upper-cased names.
    If the file cannot be loaded, returns empty sets and emits a warning.
    """
    path = path or DEFAULT_NAMES_PATH
    first_names = set()
    last_names = set()

    try:
        with open(path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = (row.get("name") or "").strip().upper()
                kind = (row.get("type") or "").strip().lower()
                if not name:
                    continue
                if kind == "first":
                    first_names.add(name)
                elif kind == "last":
                    last_names.add(name)
    except (OSError, csv.Error) as e:
        warnings.warn(
            f"Could not load name gazetteer from {path}: {e}. "
            "Name detection will rely on context only.",
            RuntimeWarning,
            stacklevel=2,
        )

    return {"first": first_names, "last": last_names, "all": first_names | last_names}
