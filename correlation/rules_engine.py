"""Deterministic rule-based forensic signal correlation and weighted indicator calculation (Tasks C & 5)."""

import re
from typing import List, Dict, Any, Tuple
from core.schemas import Signal, CrossModalFinding, OverallIndicator

# Base weights across all supported forensic modules
BASE_WEIGHTS = {
    # Image
    "img_ai_001": 0.30,         # AI Image Detector
    "txt_plaus_001": 0.30,      # Visual Plausibility
    "img_exif_001": 0.15,       # Metadata (EXIF)
    "img_ela_001": 0.15,        # Error Level Analysis (ELA)
    "txt_vis_match_001": 0.10,  # Caption-Image Mismatch
    "txt_heur_001": 0.08,       # Text linguistic markers
    # Video (Task 5 calibrated weights)
    "vid_ai_001": 0.35,         # AI detector across frames
    "vid_plaus_001": 0.30,      # Visual plausibility & physics
    "vid_temp_001": 0.15,       # Temporal consistency
    "vid_meta_001": 0.10,       # Video container metadata
    "vid_cap_001": 0.10,        # Video vs caption alignment
    "vid_ela_001": 0.05,        # Video ELA (low weight, unreliable on video)
    # Audio (Task B & Task C)
    "aud_meta_001": 0.05,       # Audio container & metadata
    "aud_spec_001": 0.25,       # High-frequency cutoff heuristic
    "aud_noise_001": 0.20,      # Noise floor & spectral flatness heuristic
    "aud_prosody_001": 0.25,    # Pitch variation & prosody heuristic
    "aud_silence_001": 0.15,    # Silence & breath regularity heuristic
    "aud_voice_001": 0.45,      # Audio synthetic voice classifier (disabled/None)
    "aud_trans_001": 0.15,      # Audio transcript alignment
}


def evaluate_rule_based_correlation(
    signals: List[Signal],
) -> Tuple[OverallIndicator, List[CrossModalFinding]]:
    """Deterministically aggregate multimodal signals using calibrated weights (Tasks C & 5).

    Returns:
        (OverallIndicator, List[CrossModalFinding])
    """
    valid_signals = [s for s in signals if s.score is not None]
    signals_by_id = {s.signal_id: s for s in signals}
    warnings: List[str] = []

    has_image = any(s.modality == "image" for s in signals)
    has_video = any(s.modality == "video" for s in signals)
    has_audio = any(s.modality == "audio" for s in signals)

    # 1. Missing or skipped major model checks
    if has_image and not has_video:
        ai_sig = signals_by_id.get("img_ai_001")
        plaus_sig = signals_by_id.get("txt_plaus_001")
        if (ai_sig and ai_sig.score is None) or (ai_sig is None and len(signals) >= 4):
            warnings.append("Result based on limited signals: AI Image Generator Detection did not run.")
        if (plaus_sig and plaus_sig.score is None) or (plaus_sig is None and len(signals) >= 4):
            warnings.append("Result based on limited signals: Visual Plausibility & Physics Audit did not run.")

    # Audio classifier disabled check (Task A & Task C)
    voice_sig = signals_by_id.get("aud_voice_001")
    if has_audio and not has_video:
        if voice_sig is None or voice_sig.score is None or "sanity check" in str(voice_sig.evidence):
            warnings.append("Result based on limited signals: the synthetic-voice classifier is disabled.")

    if not valid_signals:
        indicator = OverallIndicator(
            level="low",
            confidence=0.20,
            primary_drivers=[],
            warnings=warnings,
        )
        finding = CrossModalFinding(
            finding="No conclusive forensic signals could be computed. Insufficient valid data to evaluate.",
            supporting_signals=[s.signal_id for s in signals],
            effect="weakens",
        )
        return indicator, [finding]

    # 2. Compute weighted combination re-normalized for skipped signals
    active_weights: Dict[str, float] = {}
    for s in valid_signals:
        w = BASE_WEIGHTS.get(s.signal_id, 0.10)
        # Task 4 rule: Lossless PNG gets 0.5x weight on ELA
        if s.signal_id == "img_ela_001":
            if s.source_file.lower().endswith((".png", ".bmp", ".tiff", ".webp")):
                w *= 0.5
        active_weights[s.signal_id] = w

    total_weight = sum(active_weights.values())
    if total_weight > 0:
        normalized_weights = {sid: w / total_weight for sid, w in active_weights.items()}
        composite_score = sum(normalized_weights[s.signal_id] * s.score for s in valid_signals)
    else:
        composite_score = 0.20

    # 3. Determine Initial Risk Level from composite score
    # below 0.35 = low, 0.35 to 0.60 = moderate, above 0.60 = elevated
    if composite_score > 0.60:
        level = "elevated"
    elif composite_score >= 0.35:
        level = "moderate"
    else:
        level = "low"

    # Task 4 rule: Caption mismatch indicates possible out-of-context use, which is different from tampering.
    # It must never push the overall level above MODERATE by itself.
    txt_match_sig = signals_by_id.get("txt_vis_match_001")
    if txt_match_sig and txt_match_sig.score is not None and txt_match_sig.score >= 0.35:
        if level == "low":
            level = "moderate"
            warnings.append("Possible out-of-context use: caption conflicts with media; overall level set to at least MODERATE.")

    if level == "elevated":
        independent_tampering_sigs = [
            s for s in valid_signals
            if s.signal_id not in ["txt_vis_match_001", "txt_heur_001"] and s.score is not None and s.score >= 0.60
        ]
        if not independent_tampering_sigs and txt_match_sig and txt_match_sig.score is not None:
            level = "moderate"
            warnings.append(
                "Level capped at MODERATE: caption mismatch indicates possible out-of-context use, "
                "which does not establish media tampering by itself."
            )

    # Task 4 rule: A caption that is fully supported must NEVER lower the overall level
    # and must not be used as evidence that the media is genuine.
    if txt_match_sig and txt_match_sig.score is not None and txt_match_sig.score <= 0.10:
        warnings.append("The caption matches what is visible. This does not show the media is unedited.")
        other_tampering_sigs = [
            s for s in valid_signals
            if s.signal_id not in ["txt_vis_match_001", "txt_heur_001"] and s.score is not None and s.score >= 0.50
        ]
        if other_tampering_sigs and level == "low":
            level = "moderate"
            warnings.append(
                "Positive evidence rule: Media tampering signals take precedence over caption match."
            )

    # 4. Image Vision Plausibility Rule
    if has_image and not has_video:
        plaus_sig = signals_by_id.get("txt_plaus_001")
        has_impossible_elements = (
            plaus_sig
            and plaus_sig.score is not None
            and (
                plaus_sig.score >= 0.65
                or (
                    ("impossible" in plaus_sig.evidence.lower() or "surreal" in plaus_sig.evidence.lower())
                    and "no impossible" not in plaus_sig.evidence.lower()
                    and "contains no" not in plaus_sig.evidence.lower()
                    and "not an impossible" not in plaus_sig.evidence.lower()
                )
            )
        )
        other_above_half = any(
            s.signal_id != "txt_plaus_001" and s.score is not None and s.score >= 0.50
            for s in valid_signals
        )
        if has_impossible_elements and other_above_half:
            level = "elevated"

        # Image Floor Rule: If two or more independent signals have score >= 0.60
        # and at least one is a media tampering signal -> ELEVATED
        independent_high_image_sigs = [
            s for s in valid_signals
            if s.score is not None and s.score >= 0.60
        ]
        if len(independent_high_image_sigs) >= 2:
            has_media_tampering = any(
                s.signal_id not in ["txt_vis_match_001", "txt_heur_001"]
                for s in independent_high_image_sigs
            )
            if has_media_tampering:
                level = "elevated"
                warnings.append(
                    f"Floor rule enforced: Multiple independent signals ({', '.join(s.signal_id for s in independent_high_image_sigs)}) "
                    "scored >= 0.60; level set to ELEVATED."
                )

    # 5. Audio Hard Cap Rule (Tasks A & C)
    if has_audio and not has_video and not has_image:
        is_classifier_active = (
            voice_sig is not None
            and voice_sig.score is not None
            and voice_sig.score >= 0.50
        )
        if not is_classifier_active:
            if level == "elevated":
                level = "moderate"
                rule_cap_msg = (
                    "Level capped at MODERATE: synthetic-voice classifier is disabled; "
                    "heuristics alone can never exceed MODERATE."
                )
                print(f"[Rule Enforced] {rule_cap_msg}")
                warnings.append(rule_cap_msg)

    # 6. VIDEO COMBINER & FLOOR RULES (Task 5)
    if has_video:
        vid_ai_sig = signals_by_id.get("vid_ai_001")
        vid_plaus_sig = signals_by_id.get("vid_plaus_001")

        # Positive evidence rule: any signal >= 0.60 is positive evidence and cannot be pulled down to low
        has_positive_evidence = any(s.score >= 0.60 for s in valid_signals)

        # Floor Rule 1: If AI detector flags ANY sampled frame with score >= 0.50 -> at least MODERATE
        if vid_ai_sig and vid_ai_sig.score is not None and vid_ai_sig.score >= 0.50:
            if level == "low":
                level = "moderate"
                warnings.append(
                    f"Floor rule enforced: Keyframe AI detector flagged frame with score {vid_ai_sig.score:.0%}; "
                    "level set to at least MODERATE."
                )

        # Floor Rule 2: If visual plausibility reports impossible elements -> at least MODERATE
        if vid_plaus_sig and vid_plaus_sig.score is not None:
            impossible_in_ev = (
                vid_plaus_sig.score >= 0.65
                or (
                    ("impossible" in str(vid_plaus_sig.evidence).lower() or "surreal" in str(vid_plaus_sig.evidence).lower())
                    and "no impossible" not in str(vid_plaus_sig.evidence).lower()
                    and "contains no" not in str(vid_plaus_sig.evidence).lower()
                )
            )
            if impossible_in_ev and level == "low":
                level = "moderate"
                warnings.append(
                    "Floor rule enforced: Visual plausibility audit reported impossible elements; "
                    "level set to at least MODERATE."
                )

        # Floor Rule 3: If two independent signals are both >= 0.60 -> at least ELEVATED
        independent_high_sigs = [s for s in valid_signals if s.score >= 0.60]
        if len(independent_high_sigs) >= 2:
            level = "elevated"
            warnings.append(
                f"Floor rule enforced: Multiple independent signals ({', '.join(s.signal_id for s in independent_high_sigs)}) "
                "scored >= 0.60; level set to ELEVATED."
            )
        elif has_positive_evidence and level == "low":
            level = "moderate"
            warnings.append("Positive evidence rule: Signal >= 0.60 cannot be pulled down to LOW by weak non-findings.")

        # CONSISTENCY CHECK: level must agree with evidence text (Task 5)
        if level == "low" and any(s.score >= 0.50 for s in valid_signals):
            high_names = [f"{s.name} ({s.score:.0%})" for s in valid_signals if s.score >= 0.50]
            level = "moderate"
            warnings.append(
                f"Consistency check: Level adjusted to MODERATE to reflect positive indicators: {', '.join(high_names)}."
            )

    # 7. Confidence Calculation
    is_audio_only = has_audio and not has_image and not has_video

    if is_audio_only:
        conf = 0.50
        spec_sig = signals_by_id.get("aud_spec_001")
        meta_sig = signals_by_id.get("aud_meta_001")

        is_low_quality = False
        if spec_sig and spec_sig.evidence and "Low sample rate / low bitrate" in spec_sig.evidence:
            is_low_quality = True
        elif meta_sig and meta_sig.evidence:
            sr_match = re.search(r"Sample rate:\s*(\d+)\s*Hz", meta_sig.evidence)
            if sr_match and int(sr_match.group(1)) <= 16000:
                is_low_quality = True

        if is_low_quality:
            conf -= 0.10
            warnings.append(
                "Confidence reduced by 10%: audio sample rate is low (<= 16 kHz) or heavily compressed (< 64 kbps)."
            )

        is_under_3s = False
        if meta_sig and meta_sig.evidence:
            dur_match = re.search(r"duration:\s*([\d\.]+)\s*s", meta_sig.evidence)
            if dur_match and float(dur_match.group(1)) < 3.0:
                is_under_3s = True

        if is_under_3s:
            conf -= 0.10
            warnings.append(
                "Confidence reduced by 10%: audio duration is under 3 seconds, limiting acoustic frames."
            )

        confidence = max(0.30, min(0.50, round(conf, 2)))

    elif has_video and not has_image:
        # Video confidence formula (Task 5)
        # Start at 0.85
        conf = 0.85

        vid_ai_sig = signals_by_id.get("vid_ai_001")
        if vid_ai_sig is None or vid_ai_sig.score is None:
            conf -= 0.15
            warnings.append("Confidence reduced by 15%: Keyframe AI detector did not run.")

        vid_plaus_sig = signals_by_id.get("vid_plaus_001")
        if vid_plaus_sig is None or vid_plaus_sig.score is None:
            conf -= 0.15
            warnings.append("Confidence reduced by 15%: Visual plausibility audit did not run.")

        # Subtract 0.15 if signals disagree (one >= 0.6 and another <= 0.2)
        has_high_score = any(s.score >= 0.60 for s in valid_signals)
        has_low_score = any(s.score <= 0.20 for s in valid_signals)
        if has_high_score and has_low_score:
            conf -= 0.15
            warnings.append(
                "Confidence reduced by 15%: Forensic signals show divergence between positive indicators and smooth continuity."
            )

        # Subtract 0.10 if the video is heavily compressed (low bitrate or small file, e.g. a messaging-app re-encode)
        source_name = signals[0].source_file.lower() if signals else ""
        vid_meta_sig = signals_by_id.get("vid_meta_001")
        is_heavily_compressed = False

        if any(app in source_name for app in ["whatsapp", "telegram", "wechat", "signal"]):
            is_heavily_compressed = True
        elif vid_meta_sig and vid_meta_sig.evidence:
            ev_str = vid_meta_sig.evidence.lower()
            bitrate_m = re.search(r"bitrate:\s*(\d+)", ev_str)
            if bitrate_m and int(bitrate_m.group(1)) < 1500:
                is_heavily_compressed = True
            elif "re-encoding" in ev_str or "stripped" in ev_str:
                is_heavily_compressed = True

        if is_heavily_compressed:
            conf -= 0.10
            warnings.append(
                "Confidence reduced by 10%: Video exhibits heavy messaging-app compression or low bitrate."
            )
            warnings.append("Compression may hide AI artifacts. A low result here is not reliable.")

        # If any "Model not downloaded" warning is active, confidence must never exceed 60%
        has_model_missing = any("model not downloaded" in str(s.evidence).lower() for s in signals)
        if has_model_missing:
            conf = min(0.60, conf)
            warnings.append("Confidence capped at 60%: One or more models were not downloaded.")

        confidence = max(0.30, min(0.95, round(conf, 2)))

    else:
        # Multimodal image / general confidence formula
        num_tests = len(valid_signals)
        coverage_weight = min(0.50, num_tests * 0.10)
        avg_score = sum(s.score for s in valid_signals) / float(num_tests)
        if level == "elevated":
            consensus_weight = min(0.45, avg_score * 0.50)
        elif level == "low":
            consensus_weight = min(0.45, (1.0 - avg_score) * 0.50)
        else:
            consensus_weight = 0.30

        base_confidence = min(0.95, max(0.35, coverage_weight + consensus_weight + 0.15))
        confidence = base_confidence

        has_model_missing = any("model not downloaded" in str(s.evidence).lower() for s in signals)
        if has_model_missing:
            confidence = min(0.60, confidence)
            warnings.append("Confidence capped at 60%: One or more models were not downloaded.")

        if warnings:
            confidence = max(0.25, confidence - 0.12 * len([w for w in warnings if "limited signals" in w]))
        confidence = round(confidence, 2)

    # 8. Extract Primary Drivers (Top Reasons)
    # Task 4 & 5 Rule: ELA on video frames is low weight (0.05) and must NEVER be listed as a top reason.
    # Non-findings (< 0.35) must never be listed as primary drivers / top reasons.
    candidate_drivers = [
        sid for sid in active_weights.keys()
        if not (has_video and sid == "vid_ela_001")
        and (signals_by_id[sid].score is not None and signals_by_id[sid].score >= 0.35)
    ]
    # Rank by score descending, then weight
    sorted_drivers = sorted(
        candidate_drivers,
        key=lambda sid: (signals_by_id[sid].score or 0.0),
        reverse=True,
    )

    # Floor rule requirement: If AI detector flagged frame >= 0.5, ensure vid_ai_001 is prioritized
    vid_ai = signals_by_id.get("vid_ai_001")
    if vid_ai and vid_ai.score is not None and vid_ai.score >= 0.50:
        if "vid_ai_001" in sorted_drivers:
            sorted_drivers.remove("vid_ai_001")
            sorted_drivers.insert(0, "vid_ai_001")

    primary_drivers = sorted_drivers[:3]

    # 9. Consistency Check on Findings (Tasks C & 5)
    findings: List[CrossModalFinding] = []
    elevated_sigs = [s for s in valid_signals if s.score >= 0.65]
    moderate_sigs = [s for s in valid_signals if 0.35 <= s.score < 0.65]
    low_sigs = [s for s in valid_signals if s.score < 0.35]

    if has_video:
        if level in ["moderate", "elevated"]:
            high_vids = [s.signal_id for s in valid_signals if s.score >= 0.50]
            display_vids = high_vids or (primary_drivers[:1] if primary_drivers else ["vid_ai_001"])
            findings.append(
                CrossModalFinding(
                    finding=(
                        f"Video forensic checks ({', '.join(display_vids)}) "
                        "detected generative synthesis characteristics across keyframes."
                    ),
                    supporting_signals=display_vids,
                    effect="strengthens",
                )
            )
        else:
            findings.append(
                CrossModalFinding(
                    finding=(
                        "No indicators found by these checks: sampled keyframes and temporal continuity "
                        "exhibit standard camera recording characteristics."
                    ),
                    supporting_signals=[s.signal_id for s in low_sigs[:3]],
                    effect="weakens",
                )
            )

    elif is_audio_only:
        if level == "low":
            sup_ids = [s.signal_id for s in low_sigs]
            findings.append(
                CrossModalFinding(
                    finding=(
                        f"Acoustic indicators ({', '.join(sup_ids)}) show consistent characteristics "
                        "with no indicators of tampering found by these checks."
                    ),
                    supporting_signals=sup_ids,
                    effect="weakens",
                )
            )
        else:
            mod_ids = [s.signal_id for s in (moderate_sigs or valid_signals)]
            findings.append(
                CrossModalFinding(
                    finding=(
                        f"Limited unusual acoustic characteristics were detected ({', '.join(mod_ids)}). "
                        "Level is strictly capped at MODERATE as heuristics are unvalidated on real speech."
                    ),
                    supporting_signals=mod_ids,
                    effect="strengthens",
                )
            )
    else:
        img_sigs = [s.signal_id for s in valid_signals if s.modality == "image" and s.score >= 0.50]
        txt_sigs = [s.signal_id for s in valid_signals if s.modality == "text" and s.score >= 0.50]

        if img_sigs and txt_sigs:
            findings.append(
                CrossModalFinding(
                    finding=(
                        f"Visual indicators ({', '.join(img_sigs)}) and textual context ({', '.join(txt_sigs)}) "
                        f"both point toward manipulation, reinforcing each other."
                    ),
                    supporting_signals=img_sigs + txt_sigs,
                    effect="strengthens",
                )
            )
        elif elevated_sigs:
            sup_ids = [s.signal_id for s in elevated_sigs]
            findings.append(
                CrossModalFinding(
                    finding=(
                        f"Multiple indicators ({', '.join(sup_ids)}) show anomalies inconsistent with standard capture."
                    ),
                    supporting_signals=sup_ids,
                    effect="strengthens",
                )
            )
        else:
            sup_ids = [s.signal_id for s in low_sigs[:4]]
            findings.append(
                CrossModalFinding(
                    finding=(
                        f"Indicators ({', '.join(sup_ids)}) show consistent characteristics without evidence of tampering."
                    ),
                    supporting_signals=sup_ids,
                    effect="weakens",
                )
            )

    # Task 4 rule: Caption mismatch together with another independent signal at 0.6 or higher strengthens finding, citing both signal IDs
    if txt_match_sig and txt_match_sig.score is not None and txt_match_sig.score >= 0.35:
        other_high = [
            s for s in valid_signals
            if s.signal_id not in ["txt_vis_match_001", "txt_heur_001"] and s.score is not None and s.score >= 0.60
        ]
        if other_high:
            cited_other = other_high[0]
            # Avoid duplicate findings
            already_cited = any(
                "txt_vis_match_001" in f.supporting_signals and cited_other.signal_id in f.supporting_signals
                for f in findings
            )
            if not already_cited:
                findings.append(
                    CrossModalFinding(
                        finding=(
                            f"Possible out-of-context use ({txt_match_sig.signal_id}) strengthens the "
                            f"tampering finding from {cited_other.signal_id} ({cited_other.name})."
                        ),
                        supporting_signals=[txt_match_sig.signal_id, cited_other.signal_id],
                        effect="strengthens",
                    )
                )

    indicator = OverallIndicator(
        level=level,
        confidence=confidence,
        primary_drivers=primary_drivers,
        warnings=warnings,
    )

    return indicator, findings
