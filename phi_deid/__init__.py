"""PHI De-identifier: rule-based HIPAA Safe Harbor de-identification for clinical text."""

from .deidentifier import Deidentifier, RedactionMatch, CATEGORIES
from .gazetteer import load_name_gazetteer

__all__ = ["Deidentifier", "RedactionMatch", "CATEGORIES", "load_name_gazetteer"]

__version__ = "1.0.0"
