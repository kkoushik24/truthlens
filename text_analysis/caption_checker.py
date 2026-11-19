"""Visual-textual alignment checking and 'Possible out-of-context use' signal generation (Task 4)."""

import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List

from core.schemas import Signal, create_fallback_signal
from core.config import settings
from .claim_extractor import extract_atomic_claims
from .evidence_collector import collect_evidence_bundle
from .claim_comparator import compare_claims_to_evidence
from .llm_provider import get_llm_provider, LLMProvider

LIMITATION_TEXT = (
    "A vision model can misread an image. A mismatch here means the caption deserves checking, "
    "not that the media is manipulated."
)

# In-memory result cache: (media_sha256, caption_text) -> (Signal, full_analysis_dict)
_CAPTION_ANALYSIS_CACHE: Dict[Tuple[str, str], Tuple[Signal, Dict[str, Any]]] = {}


def get_media_sha256(media_path: Path) -> str:
    """Compute SHA256 of media asset for deterministic cache indexing."""
    try:
        h = hashlib.sha256()
        with open(media_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return str(media_path)


def clear_caption_cache() -> None:
    """Clear the in-memory caption analysis cache (called on reset/new upload)."""
    _CAPTION_ANALYSIS_CACHE.clear()


def compute_caption_signal(
    comparison_res: Dict[str, Any],
    source_file: str,
) -> Signal:
    """Calculate 'Caption vs Media' forensic signal from claim comparison results (Task 4).
    
    Rules:
    - Signal ID: txt_vis_match_001
    - Name: 'Possible out-of-context use'
    - Score = weighted share of checkable claims that are contradicted (cannot_verify counts as 0.1 each).
    - Consistency check: If any claim is contradicted, score is >= 0.35 (MODERATE tier).
      If 0 contradictions, score is <= 0.25 (LOW tier).
    - If fully supported: score = 0.0, evidence = 'The caption matches what is visible. This does not show the media is unedited.'
    - Limitation: 'A vision model can misread an image. A mismatch here means the caption deserves checking, not that the media is manipulated.'
    """
    filename = source_file

    if comparison_res.get("status") == "SKIPPED: no caption provided":
        return Signal(
            signal_id="txt_vis_match_001",
            modality="text",
            name="Possible out-of-context use",
            score=None,
            evidence="SKIPPED: no caption provided",
            location=None,
            limitation=LIMITATION_TEXT,
            source_file=filename,
        )

    if comparison_res.get("status", "").startswith("FAILED:"):
        return Signal(
            signal_id="txt_vis_match_001",
            modality="text",
            name="Possible out-of-context use",
            score=None,
            evidence=comparison_res["status"],
            location=None,
            limitation=LIMITATION_TEXT,
            source_file=filename,
        )

    comparisons = comparison_res.get("comparisons", [])
    checkable = [c for c in comparisons if c.get("checkable_from_media", True)]

    if not checkable:
        return Signal(
            signal_id="txt_vis_match_001",
            modality="text",
            name="Possible out-of-context use",
            score=0.0,
            evidence="The caption contains no checkable claims against media.",
            location=None,
            limitation=LIMITATION_TEXT,
            source_file=filename,
        )

    total_checkable = len(checkable)
    contradicted_claims = [c for c in checkable if c["status"] == "contradicted"]
    unverified_claims = [c for c in checkable if c["status"] == "cannot_verify"]
    supported_claims = [c for c in checkable if c["status"] == "supported"]

    c_count = len(contradicted_claims)
    u_count = len(unverified_claims)
    s_count = len(supported_claims)

    # Weighted share: clear contradictions weigh 1.0; cannot_verify counts as 0.1 each.
    raw_points = 1.0 * c_count + 0.1 * u_count
    raw_score = raw_points / float(total_checkable)

    # Consistency check:
    # If there is at least one clear contradiction, score must be >= 0.35 (MODERATE tier)
    if c_count > 0:
        score = round(max(0.35, min(1.0, raw_score)), 2)
        names = [f"'{c['claim_text']}'" for c in contradicted_claims]
        evidence = (
            f"Possible out-of-context use: {c_count} checkable claim(s) directly conflict with what is shown in the media "
            f"({', '.join(names[:3])})."
        )
    elif u_count > 0:
        score = round(min(0.25, raw_score), 2)
        evidence = (
            f"Contextual claims cannot be verified from the media alone ({u_count} unverified claim(s)). "
            "No direct visual contradictions detected."
        )
    else:
        score = 0.0
        evidence = "The caption matches what is visible. This does not show the media is unedited."

    return Signal(
        signal_id="txt_vis_match_001",
        modality="text",
        name="Possible out-of-context use",
        score=score,
        evidence=evidence,
        location=None,
        limitation=LIMITATION_TEXT,
        source_file=filename,
    )


def check_caption_vs_media(
    media_path: Path,
    caption: str,
    media_type: Optional[str] = None,
    sampled_frames: Optional[List[Dict[str, Any]]] = None,
    per_frame_records: Optional[List[Dict[str, Any]]] = None,
    transcript: Optional[str] = None,
    groq_client: Optional[Any] = None,
    llm_provider: Optional[LLMProvider] = None,
) -> Tuple[Signal, Dict[str, Any]]:
    """Execute end-to-end caption verification (Tasks 1, 2, 3) and produce 'Possible out-of-context use' signal (Task 4)."""
    filename = media_path.name
    clean_caption = (caption or "").strip()

    # 1. Skip if no caption provided
    if not clean_caption:
        empty_res = {
            "status": "SKIPPED: no caption provided",
            "is_trimmed": False,
            "original_caption": "",
            "english_translation": "",
            "detected_language": "none",
            "translation_note": None,
            "claims": [],
            "evidence_bundle": {"evidence_items": [], "evidence_map": {}},
            "comparisons": [],
            "context_notes": [],
            "counts": {"total": 0, "supported": 0, "contradicted": 0, "cannot_verify": 0},
            "summary_text": "SKIPPED: no caption provided",
            "unverifiable_claims": [],
            "error": None,
        }
        sig = compute_caption_signal(empty_res, filename)
        return sig, empty_res

    # Check cache for identical media and caption (Task 6)
    media_hash = get_media_sha256(media_path)
    cache_key = (media_hash, clean_caption)
    if llm_provider is None and groq_client is None:
        if cache_key in _CAPTION_ANALYSIS_CACHE:
            return _CAPTION_ANALYSIS_CACHE[cache_key]

    # Fallback to local heuristic provider if explicitly passed (for offline unit tests)
    if llm_provider is not None:
        try:
            res = llm_provider.analyze_image_caption_alignment(media_path, clean_caption)
            suspicion_score = float(res.get("suspicion_score", 0.2))
            mismatches = res.get("mismatches", [])
            visual_desc = res.get("visual_description", "")
            if mismatches:
                elem_str = ", ".join(mismatches)
                evidence = (
                    f"The text claims '{clean_caption}', but the image shows {visual_desc}. "
                    f"Contradictions were detected in: {elem_str}. "
                    f"Strong indicator of false context or misattribution."
                )
            else:
                evidence = (
                    f"The visual scene ({visual_desc}) aligns with the provided caption. "
                    "The caption matches what is visible. This does not show the media is unedited."
                )
            sig = Signal(
                signal_id="txt_vis_match_001",
                modality="text",
                name="Possible out-of-context use",
                score=round(suspicion_score, 2),
                evidence=evidence,
                location=None,
                limitation=LIMITATION_TEXT,
                source_file=filename,
            )
            return sig, {"status": "COMPLETED", "comparisons": []}
        except Exception as e:
            sig = Signal(
                signal_id="txt_vis_match_001",
                modality="text",
                name="Possible out-of-context use",
                score=None,
                evidence=f"FAILED: Caption comparison failed: {str(e)}",
                location=None,
                limitation=LIMITATION_TEXT,
                source_file=filename,
            )
            return sig, {"status": f"FAILED: {str(e)}", "comparisons": []}

    # 2. Task 1: Atomic Claim Extraction
    claims_res = extract_atomic_claims(clean_caption, groq_client=groq_client)
    if claims_res["status"].startswith("FAILED:"):
        sig = compute_caption_signal(claims_res, filename)
        fail_dict = {
            "status": claims_res["status"],
            "is_trimmed": claims_res.get("is_trimmed", False),
            "original_caption": clean_caption,
            "english_translation": clean_caption,
            "detected_language": "unknown",
            "translation_note": None,
            "claims": [],
            "evidence_bundle": {"evidence_items": [], "evidence_map": {}},
            "comparisons": [],
            "context_notes": [],
            "counts": {"total": 0, "supported": 0, "contradicted": 0, "cannot_verify": 0},
            "summary_text": claims_res["status"],
            "unverifiable_claims": [],
            "signal": sig,
            "error": claims_res.get("error"),
        }
        return sig, fail_dict

    # 3. Task 2: Evidence Collection
    evidence_bundle = collect_evidence_bundle(
        media_path=media_path,
        media_type=media_type,
        sampled_frames=sampled_frames,
        per_frame_records=per_frame_records,
        transcript=transcript,
        groq_client=groq_client,
    )
    if evidence_bundle["status"].startswith("FAILED:"):
        # Log evidence failure but continue comparison against available metadata if possible
        pass

    # 4. Task 3: Claim-by-Claim Comparison
    comp_res = compare_claims_to_evidence(
        claims=claims_res.get("claims", []),
        evidence_bundle=evidence_bundle,
        caption=claims_res.get("english_translation") or clean_caption,
        groq_client=groq_client,
    )

    # 5. Task 4: Signal Generation
    sig = compute_caption_signal(comp_res, filename)

    # Full analysis bundle for the Text & Context Tab UI (Task 5)
    full_analysis = {
        "status": comp_res.get("status", "COMPLETED"),
        "is_trimmed": claims_res.get("is_trimmed", False),
        "original_caption": claims_res.get("original_caption", clean_caption),
        "english_translation": claims_res.get("english_translation", clean_caption),
        "detected_language": claims_res.get("detected_language", "English"),
        "translation_note": claims_res.get("translation_note"),
        "claims": claims_res.get("claims", []),
        "evidence_bundle": evidence_bundle,
        "comparisons": comp_res.get("comparisons", []),
        "context_notes": comp_res.get("context_notes", []),
        "counts": comp_res.get("counts", {}),
        "summary_text": comp_res.get("summary_text", ""),
        "unverifiable_claims": comp_res.get("unverifiable_claims", []),
        "signal": sig,
        "error": comp_res.get("error"),
    }

    if llm_provider is None and groq_client is None:
        _CAPTION_ANALYSIS_CACHE[cache_key] = (sig, full_analysis)

    return sig, full_analysis


def check_caption_vs_image(
    image_path: Path,
    caption: str,
    llm_provider: Optional[LLMProvider] = None,
    groq_client: Optional[Any] = None,
) -> Signal:
    """Backwards-compatible wrapper returning Signal directly."""
    sig, _ = check_caption_vs_media(
        media_path=image_path,
        caption=caption,
        media_type="image",
        llm_provider=llm_provider,
        groq_client=groq_client,
    )
    return sig
