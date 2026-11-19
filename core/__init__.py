"""TruthLens Core Forensic Infrastructure."""

from .schemas import (
    Signal,
    Location,
    RegionLocation,
    TimeLocation,
    FrameLocation,
    CrossModalFinding,
    OverallIndicator,
    HistoryItem,
    ForensicReport,
    create_fallback_signal,
)
from .hashing import calculate_sha256, calculate_bytes_sha256
from .case_manager import CaseManager
from .config import settings

__all__ = [
    "Signal",
    "Location",
    "RegionLocation",
    "TimeLocation",
    "FrameLocation",
    "CrossModalFinding",
    "OverallIndicator",
    "HistoryItem",
    "ForensicReport",
    "create_fallback_signal",
    "calculate_sha256",
    "calculate_bytes_sha256",
    "CaseManager",
    "settings",
]
