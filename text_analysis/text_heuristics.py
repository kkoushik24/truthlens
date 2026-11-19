"""Heuristic linguistic and chronological analysis for captions and claims."""

import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from core.schemas import Signal, create_fallback_signal


SENSATIONALIST_MARKERS = [
    "100% real", "100% authentic", "undeniable proof", "undeniable evidence",
    "proof they are lying", "unquestionably authentic", "caught red-handed",
    "they don't want you to see", "shocking leaked", "banned footage",
    "mainstream media won't show", "secret footage", "exposed",
    "government coverup", "completely unedited"
]


def analyze_caption_heuristics(
    caption: str,
    source_file: str = "caption.txt",
    metadata: Optional[Dict[str, Any]] = None,
) -> Signal:
    """Analyze caption text for manipulative framing, extreme certainty claims, and temporal inconsistencies."""
    try:
        clean_caption = caption.strip()
        if not clean_caption:
            return Signal(
                signal_id="txt_heur_001",
                modality="text",
                name="Caption Linguistic Integrity",
                score=None,
                evidence="SKIPPED: no caption provided",
                location=None,
                limitation="A written caption or contextual claim is required to evaluate linguistic framing.",
                source_file=source_file,
            )

        caption_lower = clean_caption.lower()
        evidence_points: List[str] = []
        suspicion_score = 0.15

        # 1. Check for sensationalist certainty markers
        matched_markers = [m for m in SENSATIONALIST_MARKERS if m in caption_lower]
        if matched_markers:
            suspicion_score = max(suspicion_score, 0.70)
            evidence_points.append(
                f"Caption utilizes sensationalist certainty markers designed to bypass critical scrutiny: [{', '.join(matched_markers)}]."
            )

        # 2. Extract potential years claimed in caption
        years_found = [int(y) for y in re.findall(r"\b(19\d\d|20\d\d)\b", caption)]
        current_year = datetime.now().year

        for y in years_found:
            if y > current_year + 1:
                suspicion_score = max(suspicion_score, 0.85)
                evidence_points.append(f"Caption claims an impossible future event date (Year: {y}).")

        # 3. Check for conflict with metadata if provided
        if metadata and years_found:
            meta_date_str = str(
                metadata.get("DateTime") or metadata.get("DateTimeOriginal") or ""
            )
            meta_years = [int(y) for y in re.findall(r"\b(19\d\d|20\d\d)\b", meta_date_str)]
            if meta_years:
                meta_year = meta_years[0]
                if meta_year not in years_found:
                    diff = abs(meta_year - years_found[0])
                    if diff >= 2:
                        suspicion_score = max(suspicion_score, 0.80)
                        evidence_points.append(
                            f"Significant chronological conflict: Caption claims year {years_found[0]}, "
                            f"but media EXIF metadata records capture in year {meta_year} (divergence: {diff} years)."
                        )

        if not evidence_points:
            evidence_points.append(
                "Caption phrasing uses neutral descriptive language without manipulative absolute markers."
            )

        final_evidence = " ".join(evidence_points)

        return Signal(
            signal_id="txt_heur_001",
            modality="text",
            name="Caption Linguistic Integrity",
            score=round(suspicion_score, 2),
            evidence=final_evidence,
            location=None,
            limitation=(
                "Heuristic linguistic checks detect sensationalism and chronological anomalies, but cannot "
                "verify whether a factually true story was simply reported with hyperbolic phrasing."
            ),
            source_file=source_file,
        )

    except Exception as e:
        return create_fallback_signal(
            signal_id="txt_heur_001",
            modality="text",
            name="Caption Linguistic Integrity",
            source_file=source_file,
            reason=f"Caption heuristic evaluation failed: {str(e)}",
            limitation="Text encoding or parsing error interrupted linguistic analysis.",
        )
