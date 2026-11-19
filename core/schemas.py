"""Pydantic V2 Schemas for TruthLens Signals, Findings, and Forensic Reports."""

from typing import List, Optional, Literal, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator


# Location sub-schemas for spatial, temporal, or frame-based evidence
class RegionLocation(BaseModel):
    type: Literal["region"] = "region"
    bbox: List[int] = Field(
        ...,
        description="Bounding box coordinates [x1, y1, x2, y2]",
        min_length=4,
        max_length=4,
    )


class TimeLocation(BaseModel):
    type: Literal["time"] = "time"
    start: float = Field(..., ge=0.0, description="Start timestamp in seconds")
    end: float = Field(..., ge=0.0, description="End timestamp in seconds")


class FrameLocation(BaseModel):
    type: Literal["frame"] = "frame"
    index: int = Field(..., ge=0, description="Frame index in video sequence")


Location = Union[RegionLocation, TimeLocation, FrameLocation, Dict[str, Any]]


class Signal(BaseModel):
    """Atomic forensic indicator returned by every analysis module."""

    signal_id: str = Field(
        ...,
        description="Unique identifier for this forensic signal (e.g. ela_001)",
    )
    modality: Literal["image", "video", "audio", "text"] = Field(
        ...,
        description="Media modality inspected",
    )
    name: str = Field(
        ...,
        description="Human-readable name of the forensic test",
    )
    score: Optional[float] = Field(
        default=None,
        description="Normalized suspicion score [0.0 - 1.0], or None if inconclusive/failed",
    )
    evidence: str = Field(
        ...,
        description="Plain-English description of observed forensic evidence",
    )
    location: Optional[Location] = Field(
        default=None,
        description="Spatial (bbox), temporal (seconds), or frame-based anomaly location",
    )
    limitation: str = Field(
        ...,
        min_length=1,
        description="REQUIRED: Forensic caveats explaining why this indicator could be misleading or inaccurate",
    )
    source_file: str = Field(
        ...,
        description="Filename of the analyzed source asset",
    )

    @field_validator("score")
    @classmethod
    def validate_score_bounds(cls, v: Optional[float]) -> Optional[float]:
        if v is not None:
            if not (0.0 <= v <= 1.0):
                raise ValueError(f"Score must be between 0.0 and 1.0 or null; received {v}")
            return round(v, 4)
        return None


class CrossModalFinding(BaseModel):
    """Correlated observation connecting evidence across two or more modalities."""

    finding: str = Field(
        ...,
        description="Explanation of how signals across modalities interact",
    )
    supporting_signals: List[str] = Field(
        default_factory=list,
        description="List of signal_id values supporting this finding",
    )
    effect: Literal["strengthens", "weakens"] = Field(
        ...,
        description="Whether this correlation strengthens or weakens suspicion of manipulation",
    )


class OverallIndicator(BaseModel):
    """Aggregate forensic indicator. Strictly an indicator, never a verdict."""

    level: Literal["low", "moderate", "elevated"] = Field(
        ...,
        description="Suspicion tier based on correlated indicators",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score [0.0 - 1.0] in the indicator assessment",
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Forensic warnings or missing signal limitations",
    )
    primary_drivers: List[str] = Field(
        default_factory=list,
        description="Key signal IDs driving the overall assessment",
    )

    @field_validator("confidence")
    @classmethod
    def round_confidence(cls, v: float) -> float:
        return round(v, 4)


class HistoryItem(BaseModel):
    """Audit log entry for forensics pipeline operations."""

    time: str = Field(..., description="ISO 8601 timestamp")
    action: str = Field(..., description="Description of the operation performed")


class ForensicReport(BaseModel):
    """Final comprehensive forensic evaluation report."""

    case_id: str = Field(..., description="Unique case identifier")
    inputs: List[str] = Field(
        default_factory=list,
        description="List of filenames submitted for forensic analysis",
    )
    input_hashes: Dict[str, str] = Field(
        default_factory=dict,
        description="Cryptographic SHA-256 hashes of original uploaded media",
    )
    signals: List[Signal] = Field(
        default_factory=list,
        description="List of all forensic signals gathered across modules",
    )
    cross_modal_findings: List[CrossModalFinding] = Field(
        default_factory=list,
        description="Correlated findings across multimodal signals",
    )
    overall_indicator: OverallIndicator = Field(
        ...,
        description="Summary indicator level and confidence",
    )
    limitations: List[str] = Field(
        default_factory=list,
        description="System-wide limitations and technical caveats",
    )
    recommended_human_checks: List[str] = Field(
        default_factory=list,
        description="Recommended forensic steps for human investigators",
    )
    history: List[HistoryItem] = Field(
        default_factory=list,
        description="Chronological audit log of case processing actions",
    )


def create_fallback_signal(
    signal_id: str,
    modality: Literal["image", "video", "audio", "text"],
    name: str,
    source_file: str,
    reason: str,
    limitation: Optional[str] = None,
) -> Signal:
    """Helper to safely build a null-score signal when an analysis step fails or is inconclusive."""
    default_limitation = (
        limitation
        or f"Analysis step '{name}' encountered an error or missing prerequisite: {reason}. Score set to null to avoid false positive."
    )
    return Signal(
        signal_id=signal_id,
        modality=modality,
        name=name,
        score=None,
        evidence=f"Analysis could not be completed: {reason}",
        location=None,
        limitation=default_limitation,
        source_file=source_file,
    )
