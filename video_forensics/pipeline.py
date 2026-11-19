"""Video forensics pipeline orchestration for TruthLens (Tasks 2, 3, 4)."""

import json
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

from core.schemas import Signal, FrameLocation, create_fallback_signal
from core.case_manager import CaseManager
from image_forensics.ela_analyzer import perform_ela

from .frame_sampler import sample_video_frames
from .video_metadata import analyze_video_metadata
from .temporal_consistency import check_temporal_consistency
from .keyframe_ai_detector import analyze_video_frames_ai, generate_per_frame_score_chart
from .visual_plausibility import check_video_visual_plausibility, check_video_caption_alignment
from .audio_extractor import extract_audio_from_video


def analyze_video_pipeline(
    video_path: Path,
    caption: Optional[str] = None,
    case_manager: Optional[CaseManager] = None,
) -> Tuple[List[Signal], Optional[Path]]:
    """Execute all video forensic modules and return aggregated signals and extracted audio track."""
    signals: List[Signal] = []
    extracted_audio_path: Optional[Path] = None
    filename = video_path.name

    try:
        # 1. Container & Codec Metadata Audit (Task 4: max score 0.35, recompression caveat)
        meta_signal = analyze_video_metadata(video_path)
        signals.append(meta_signal)
        if case_manager:
            case_manager.log_action(
                f"Video container metadata audit completed for {filename} (score: {meta_signal.score})."
            )

        # 2. Sample Up to 12 Uniform Frames (Task 2: hard cap 15, includes first/last, skip blank, trim 60s)
        frames_dir = None
        if case_manager:
            frames_dir = case_manager.artifacts_dir / f"frames_{video_path.stem}"
        else:
            frames_dir = video_path.parent / f"_temp_frames_{video_path.stem}"

        video_info, sampled_frames = sample_video_frames(
            video_path=video_path,
            output_dir=frames_dir,
            max_frames=12,
        )

        if not sampled_frames:
            err_reason = video_info.get("error") or "No readable frames could be extracted from video container."
            fallback = create_fallback_signal(
                signal_id="vid_sample_001",
                modality="video",
                name="Video Frame Sampling",
                source_file=filename,
                reason=f"FAILED: {err_reason}",
                limitation="Videos under 2 seconds or with unreadable containers cannot be evaluated.",
            )
            signals.append(fallback)
            return signals, None

        if case_manager:
            trim_msg = f" ({video_info['trim_note']})" if video_info.get("is_trimmed") else ""
            case_manager.log_action(
                f"Extracted {len(sampled_frames)} evenly spaced keyframes across {video_info.get('duration_seconds', 0)}s{trim_msg}."
            )

        # 3. Temporal Consistency (Task 4: score 0 to 1, limitation on smooth modern AI frames)
        temp_signal = check_temporal_consistency(sampled_frames, source_file=filename)
        signals.append(temp_signal)
        if case_manager:
            case_manager.log_action(
                f"Video temporal consistency evaluated (score: {temp_signal.score})."
            )

        # 4. Per-Frame AI Detection (Task 3: all frames evaluated, face crop check, higher of top-3 mean vs max)
        vid_ai_sig, per_frame_records = analyze_video_frames_ai(
            sampled_frames=sampled_frames,
            source_file=filename,
        )
        signals.append(vid_ai_sig)
        if case_manager:
            case_manager.log_action(
                f"Per-frame AI detector completed across {len(sampled_frames)} frames (score: {vid_ai_sig.score})."
            )
            # Save per-frame records as JSON artifact and render chart
            chart_path = case_manager.get_artifact_path(f"frame_scores_{video_path.stem}.png")
            generate_per_frame_score_chart(per_frame_records, chart_path)

            data_path = case_manager.get_artifact_path(f"frame_scores_{video_path.stem}.json")
            try:
                data_path.write_text(json.dumps(per_frame_records, indent=2), encoding="utf-8")
            except Exception:
                pass

        # 5. ELA on Video Keyframes (Task 4: weight 0.05, clear recompression limitation, never top reason)
        highest_ela_score = -1.0
        peak_frame_item = sampled_frames[0]
        peak_ela_signal = None

        for frame_item in sampled_frames:
            frame_path = frame_item.get("path")
            if frame_path and Path(frame_path).is_file():
                ela_sig, _ = perform_ela(frame_path)
                curr_score = ela_sig.score if ela_sig.score is not None else 0.0
                if curr_score > highest_ela_score:
                    highest_ela_score = curr_score
                    peak_frame_item = frame_item
                    peak_ela_signal = ela_sig

        peak_idx = int(peak_frame_item["index"])
        peak_ts = float(peak_frame_item["timestamp"])

        if peak_ela_signal and peak_ela_signal.score is not None:
            vid_ela_sig = Signal(
                signal_id="vid_ela_001",
                modality="video",
                name="Video Keyframe Error Level Analysis",
                score=peak_ela_signal.score,
                evidence=(
                    f"Sampled keyframe #{peak_idx} at timestamp {peak_ts:.2f}s analyzed for compression divergence. "
                    f"Divergence score: {peak_ela_signal.score:.2f}."
                ),
                location=FrameLocation(index=peak_idx),
                limitation="Error Level Analysis is highly unreliable on compressed video containers and re-encoded streaming formats. Treat this as weak secondary evidence.",
                source_file=filename,
            )
            signals.append(vid_ela_sig)

        # 6. Visual Plausibility & Physics Audit (Task 4: 5 candidate frames to Groq Vision)
        plaus_sig = check_video_visual_plausibility(
            sampled_frames=sampled_frames,
            per_frame_ai_records=per_frame_records,
            source_file=filename,
        )
        signals.append(plaus_sig)
        if case_manager:
            case_manager.log_action(
                f"Visual plausibility audit completed (score: {plaus_sig.score})."
            )

        # 7. Video Caption Alignment (Task 4: Groq Vision cross-check if caption provided)
        cap_sig = check_video_caption_alignment(
            sampled_frames=sampled_frames,
            caption=caption,
            source_file=filename,
        )
        signals.append(cap_sig)
        if case_manager:
            case_manager.log_action(
                f"Video caption alignment check completed (score: {cap_sig.score})."
            )

        # 8. Extract Audio Track (Task 4: extract with ffmpeg, return audio path or SKIPPED signal)
        if case_manager:
            audio_target = case_manager.get_artifact_path(f"{video_path.stem}_audio.wav")
            extracted_audio_path = extract_audio_from_video(video_path, audio_target)
            if extracted_audio_path:
                case_manager.log_action(
                    f"Extracted audio stream from video to {extracted_audio_path.name}."
                )
            else:
                signals.append(
                    Signal(
                        signal_id="vid_aud_001",
                        modality="video",
                        name="Video Audio Track Inspection",
                        score=None,
                        evidence="SKIPPED: Video file has no audio stream.",
                        location=None,
                        limitation="Silent videos cannot be evaluated for acoustic or synthetic speech anomalies.",
                        source_file=filename,
                    )
                )

        return signals, extracted_audio_path

    except Exception as e:
        fallback = create_fallback_signal(
            signal_id="vid_pipe_001",
            modality="video",
            name="Video Forensics Pipeline",
            source_file=filename,
            reason=f"Pipeline error: {str(e)}",
            limitation="Video decoding or frame sampling encountered an unhandled exception.",
        )
        signals.append(fallback)
        return signals, None
