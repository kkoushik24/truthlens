"""Evidence collection across visual media, video frames, transcripts, and metadata (Task 2)."""

import base64
import io
import json
import re
import subprocess
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

from PIL import Image, ExifTags
import imageio_ffmpeg

from core.config import settings


def prepare_image_for_groq_vision(
    image_input: Union[Path, str, Image.Image, Any],
    max_dim: int = 1024,
    quality: int = 85,
) -> str:
    """Resize in-memory copy of image/frame to max_dim on the longest side and encode as base64 JPEG.
    
    The original file on disk is left untouched.
    """
    img = None
    try:
        if isinstance(image_input, (str, Path)):
            img = Image.open(image_input)
        elif isinstance(image_input, Image.Image):
            img = image_input.copy()
        elif hasattr(image_input, "shape"):
            # Numpy ndarray (BGR or RGB)
            import numpy as np
            if len(image_input.shape) == 3 and image_input.shape[2] == 3:
                # Assume OpenCV BGR
                rgb_arr = image_input[:, :, ::-1]
                img = Image.fromarray(rgb_arr)
            else:
                img = Image.fromarray(image_input)
        else:
            raise ValueError(f"Unsupported image input type: {type(image_input)}")

        rgb_img = img.convert("RGB")
        if max(rgb_img.size) > max_dim:
            rgb_img.thumbnail((max_dim, max_dim), Image.Resampling.BILINEAR)

        buf = io.BytesIO()
        rgb_img.save(buf, format="JPEG", quality=quality, optimize=True)
        return base64.b64encode(buf.getvalue()).decode("utf-8")
    finally:
        if img is not None and isinstance(image_input, (str, Path)):
            try:
                img.close()
            except Exception:
                pass


def _clean_json_response(content: str) -> str:
    """Strip code fences, whitespace, and preamble from LLM response."""
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
    match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
    if match:
        return match.group(1).strip()
    return cleaned.strip()


def describe_visual_with_groq_vision(
    image_input: Union[Path, str, Image.Image, Any],
    groq_client: Optional[Any] = None,
) -> Dict[str, Any]:
    """Ask Groq Vision model for objective visible description only.
    
    Rules:
    - Only report what is visibly and literally present.
    - Do NOT guess dates, years, or geographical locations (cities, countries).
    - Never use the words 'natural' or 'authentic'.
    - Never judge whether the media is 'real' or 'fake'.
    - Returns JSON with objects, actions, setting, visible_text_or_signs,
      weather_or_time_of_day, people_count, uncertain_items.
    """
    if not settings.GROQ_API_KEY or len(settings.GROQ_API_KEY.strip()) < 5:
        return {
            "status": "FAILED: GROQ_API_KEY not configured in .env",
            "error": "GROQ_API_KEY not configured in .env",
            "data": None,
        }

    try:
        b64_image = prepare_image_for_groq_vision(image_input, max_dim=1024)
    except Exception as prep_err:
        return {
            "status": f"FAILED: Failed to prepare image for vision API: {str(prep_err)}",
            "error": str(prep_err),
            "data": None,
        }

    prompt = (
        "You are an objective visual evidence auditor for a multimodal forensics workstation.\n"
        "Examine this image and describe ONLY what is visibly and literally present.\n"
        "Strict constraints:\n"
        "1. Do NOT guess calendar dates, years, or specific geographic locations (do not guess a city or country unless written explicitly on a visible sign).\n"
        "2. Do NOT use the words 'natural' or 'authentic'. Do NOT judge if the image is real or fake.\n"
        "3. If an element is ambiguous or unclear, list it under 'uncertain_items'.\n\n"
        "Return a valid JSON object with EXACTLY these keys:\n"
        "{\n"
        '  "objects": ["list of visible physical objects/entities"],\n'
        '  "actions": ["visible actions, movements, or postures"],\n'
        '  "setting": "brief description of physical environment without guessing city/country",\n'
        '  "visible_text_or_signs": ["exact text strings visible on signs, clothes, screens, or empty list"],\n'
        '  "weather_or_time_of_day": "visible lighting or weather cues (e.g. daylight sunny, night, indoor lighting, N/A)",\n'
        '  "people_count": 0,\n'
        '  "uncertain_items": ["any items that are ambiguous or unclear, or empty list"]\n'
        "}"
    )

    try:
        if groq_client is not None:
            client = groq_client
        else:
            from groq import Groq
            client = Groq(api_key=settings.GROQ_API_KEY)
    except Exception as init_err:
        return {
            "status": f"FAILED: Failed to initialize Groq client: {str(init_err)}",
            "error": str(init_err),
            "data": None,
        }

    data_uri = f"data:image/jpeg;base64,{b64_image}"
    model_name = settings.GROQ_VISION_MODEL

    for attempt in range(2):
        try:
            resp = client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": data_uri}},
                        ],
                    }
                ],
                model=model_name,
                response_format={"type": "json_object"},
                temperature=0.1,
                timeout=25.0,
            )
            raw_content = resp.choices[0].message.content or ""
            cleaned = _clean_json_response(raw_content)
            parsed = json.loads(cleaned)

            # Sanitize and ensure expected keys exist
            data = {
                "objects": parsed.get("objects", []) if isinstance(parsed.get("objects"), list) else [],
                "actions": parsed.get("actions", []) if isinstance(parsed.get("actions"), list) else [],
                "setting": str(parsed.get("setting", "Unspecified setting")).strip(),
                "visible_text_or_signs": (
                    parsed.get("visible_text_or_signs", [])
                    if isinstance(parsed.get("visible_text_or_signs"), list)
                    else []
                ),
                "weather_or_time_of_day": str(
                    parsed.get("weather_or_time_of_day", "Unspecified lighting/weather")
                ).strip(),
                "people_count": parsed.get("people_count", 0),
                "uncertain_items": (
                    parsed.get("uncertain_items", [])
                    if isinstance(parsed.get("uncertain_items"), list)
                    else []
                ),
            }
            return {
                "status": "COMPLETED",
                "error": None,
                "data": data,
                "model": model_name,
            }
        except Exception as err:
            err_str = str(err).lower()
            if "not_found" in err_str or "deprecated" in err_str or "does not exist" in err_str:
                return {
                    "status": (
                        f"FAILED: Vision model '{model_name}' was rejected or not found by Groq. "
                        "Please update GROQ_VISION_MODEL in core/config.py or .env file."
                    ),
                    "error": str(err),
                    "data": None,
                }
            if attempt == 0:
                time.sleep(1.0)
                continue
            return {
                "status": f"FAILED: Groq Vision API error: {str(err)}",
                "error": str(err),
                "data": None,
            }

    return {
        "status": "FAILED: Vision analysis returned no output after retry.",
        "error": "No output after retry",
        "data": None,
    }


def extract_image_metadata(image_path: Path) -> Dict[str, Any]:
    """Extract EXIF metadata: timestamp, GPS, make/model, and editing software tags.
    
    Marks missing fields explicitly (e.g. 'missing').
    """
    meta: Dict[str, Any] = {
        "has_exif": False,
        "datetime": None,
        "datetime_original": None,
        "gps": None,
        "make": None,
        "model": None,
        "software": None,
        "notes": [],
    }

    if not image_path.is_file():
        meta["notes"].append("Image file does not exist on disk.")
        return meta

    try:
        with Image.open(image_path) as img:
            exif = img.getexif()
            if not exif:
                meta["notes"].append("No EXIF metadata block found (stripped or absent).")
                return meta

            meta["has_exif"] = True
            decoded: Dict[str, Any] = {}
            for tag_id, val in exif.items():
                name = ExifTags.TAGS.get(tag_id, str(tag_id))
                decoded[name] = val

            meta["datetime"] = decoded.get("DateTime")
            meta["datetime_original"] = decoded.get("DateTimeOriginal") or decoded.get("DateTimeDigitized")
            meta["make"] = decoded.get("Make")
            meta["model"] = decoded.get("Model")
            meta["software"] = decoded.get("Software") or decoded.get("ProcessingSoftware")

            # Try to read GPS IFD
            if hasattr(exif, "get_ifd"):
                try:
                    gps_ifd = exif.get_ifd(0x8825)
                    if gps_ifd:
                        gps_decoded = {}
                        for k, v in gps_ifd.items():
                            gname = ExifTags.GPSTAGS.get(k, str(k))
                            gps_decoded[gname] = v
                        if "GPSLatitude" in gps_decoded and "GPSLongitude" in gps_decoded:
                            meta["gps"] = f"Lat: {gps_decoded['GPSLatitude']}, Lon: {gps_decoded['GPSLongitude']}"
                except Exception:
                    pass
    except Exception as e:
        meta["notes"].append(f"Error parsing image EXIF: {str(e)}")

    return meta


def extract_video_metadata(video_path: Path) -> Dict[str, Any]:
    """Extract video container metadata: creation time, GPS, encoder, duration."""
    meta: Dict[str, Any] = {
        "creation_time": None,
        "gps": None,
        "encoder": None,
        "duration": None,
        "notes": [],
    }

    if not video_path.is_file():
        meta["notes"].append("Video file does not exist on disk.")
        return meta

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        cmd = [ffmpeg_exe, "-i", str(video_path)]
        proc = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10.0
        )
        out = proc.stderr or proc.stdout or ""

        cr_match = re.search(r"creation_time\s*:\s*([^\r\n]+)", out, re.IGNORECASE)
        if cr_match:
            meta["creation_time"] = cr_match.group(1).strip()

        loc_match = re.search(r"(?:location|location-eng)\s*:\s*([^\r\n]+)", out, re.IGNORECASE)
        if loc_match:
            meta["gps"] = loc_match.group(1).strip()

        enc_match = re.search(r"encoder\s*:\s*([^\r\n]+)", out, re.IGNORECASE)
        if enc_match:
            meta["encoder"] = enc_match.group(1).strip()

        dur_match = re.search(r"Duration:\s*(\d+:\d+:\d+\.\d+)", out)
        if dur_match:
            meta["duration"] = dur_match.group(1).strip()
    except Exception as e:
        meta["notes"].append(f"Error extracting video metadata: {str(e)}")

    return meta


def extract_audio_metadata(audio_path: Path) -> Dict[str, Any]:
    """Extract audio container metadata: creation date, duration, sample rate."""
    meta: Dict[str, Any] = {
        "creation_time": None,
        "gps": None,
        "duration": None,
        "encoder": None,
        "notes": [],
    }

    if not audio_path.is_file():
        meta["notes"].append("Audio file does not exist on disk.")
        return meta

    try:
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        cmd = [ffmpeg_exe, "-i", str(audio_path)]
        proc = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10.0
        )
        out = proc.stderr or proc.stdout or ""

        date_match = re.search(r"(?:date|creation_time)\s*:\s*([^\r\n]+)", out, re.IGNORECASE)
        if date_match:
            meta["creation_time"] = date_match.group(1).strip()

        dur_match = re.search(r"Duration:\s*(\d+:\d+:\d+\.\d+)", out)
        if dur_match:
            meta["duration"] = dur_match.group(1).strip()
    except Exception as e:
        meta["notes"].append(f"Error extracting audio metadata: {str(e)}")

    return meta


def select_video_frames_for_evidence(
    sampled_frames: List[Dict[str, Any]],
    per_frame_records: Optional[List[Dict[str, Any]]] = None,
    min_frames: int = 3,
    max_frames: int = 5,
) -> List[Dict[str, Any]]:
    """Select 3 to 5 sampled frames: first, middle, last, plus highest-scoring frames.
    
    Ensures frames are unique and sorted chronologically.
    """
    if not sampled_frames:
        return []

    if len(sampled_frames) <= min_frames:
        return sampled_frames

    selected_indices = set()
    # 1. First frame
    selected_indices.add(0)
    # 2. Middle frame
    selected_indices.add(len(sampled_frames) // 2)
    # 3. Last frame
    selected_indices.add(len(sampled_frames) - 1)

    # 4. Highest-scoring frames from per_frame_records if available
    if per_frame_records:
        scored = []
        for r in per_frame_records:
            score = float(r.get("score") or 0.0)
            scored.append((score, r.get("frame_index", 0)))
        scored.sort(reverse=True)

        # Map frame_index to position in sampled_frames
        idx_to_pos = {f.get("index"): pos for pos, f in enumerate(sampled_frames)}
        for _, f_idx in scored:
            if len(selected_indices) >= max_frames:
                break
            pos = idx_to_pos.get(f_idx)
            if pos is not None and pos not in selected_indices:
                selected_indices.add(pos)

    # Sort chosen frames chronologically
    sorted_positions = sorted(list(selected_indices))
    return [sampled_frames[p] for p in sorted_positions]


def collect_evidence_bundle(
    media_path: Path,
    media_type: Optional[str] = None,
    sampled_frames: Optional[List[Dict[str, Any]]] = None,
    per_frame_records: Optional[List[Dict[str, Any]]] = None,
    transcript: Optional[str] = None,
    groq_client: Optional[Any] = None,
) -> Dict[str, Any]:
    """Build a comprehensive forensic evidence bundle from media, frames, transcript, and metadata (Task 2).
    
    Each evidence item has:
    - id: 'e1', 'e2', ...
    - source: 'image' | 'frame_N' | 'transcript' | 'metadata'
    - text: plain English description of what is evidenced.
    """
    # Infer media_type if not given
    if not media_type:
        suf = media_path.suffix.lower()
        if suf in [".mp4", ".mov", ".avi", ".mkv", ".webm"]:
            media_type = "video"
        elif suf in [".wav", ".mp3", ".flac", ".ogg", ".m4a"]:
            media_type = "audio"
        else:
            media_type = "image"

    evidence_items: List[Dict[str, str]] = []
    evidence_counter = 1

    def _add_evidence(source: str, text: str):
        nonlocal evidence_counter
        evidence_items.append({
            "id": f"e{evidence_counter}",
            "source": source,
            "text": text.strip(),
        })
        evidence_counter += 1

    status = "COMPLETED"
    raw_vision_data: Dict[str, Any] = {}
    metadata_bundle: Dict[str, Any] = {}

    # --- 1. MEDIA VISUAL EVIDENCE ---
    if media_type == "image":
        vision_res = describe_visual_with_groq_vision(media_path, groq_client=groq_client)
        raw_vision_data["image"] = vision_res
        if vision_res["status"] != "COMPLETED":
            status = vision_res["status"]
            _add_evidence("image", f"Visual observation unavailable: {vision_res['status']}")
        else:
            vdata = vision_res["data"]
            # Objects
            objs = ", ".join(vdata["objects"]) if vdata["objects"] else "none detected"
            _add_evidence("image", f"Visible objects: {objs}")

            # Actions
            acts = ", ".join(vdata["actions"]) if vdata["actions"] else "none detected"
            _add_evidence("image", f"Visible actions and postures: {acts}")

            # Setting
            _add_evidence("image", f"Setting and environment: {vdata['setting']}")

            # Text / Signs
            txts = ", ".join(f"'{t}'" for t in vdata["visible_text_or_signs"]) if vdata["visible_text_or_signs"] else "none"
            _add_evidence("image", f"Visible text or signage: {txts}")

            # Weather / Lighting
            _add_evidence("image", f"Weather or time of day cues: {vdata['weather_or_time_of_day']}")

            # People count
            _add_evidence("image", f"People count: {vdata['people_count']} visible")

            # Uncertain items
            unc = ", ".join(vdata["uncertain_items"]) if vdata["uncertain_items"] else "none"
            _add_evidence("image", f"Ambiguous or uncertain items: {unc}")

    elif media_type == "video":
        # Video: sample 3 to 5 frames
        frames_to_audit = []
        if sampled_frames:
            frames_to_audit = select_video_frames_for_evidence(
                sampled_frames, per_frame_records=per_frame_records, min_frames=3, max_frames=5
            )
        elif media_path.is_file():
            # If sampled_frames not provided, sample directly
            try:
                from video_forensics.frame_sampler import sample_video_frames
                _, sampled = sample_video_frames(media_path, max_frames=12)
                frames_to_audit = select_video_frames_for_evidence(
                    sampled, per_frame_records=per_frame_records, min_frames=3, max_frames=5
                )
            except Exception as e:
                _add_evidence("frame_0", f"Frame extraction error: {str(e)}")

        if not frames_to_audit:
            _add_evidence("frame_0", "No video frames could be extracted for visual inspection.")
        else:
            for f_item in frames_to_audit:
                f_idx = f_item.get("index", 0)
                f_ts = float(f_item.get("timestamp", 0.0))
                f_src = f"frame_{f_idx}"

                # Prefer path, fallback to bgr array
                f_input = f_item.get("path") or f_item.get("bgr")
                if f_input is None:
                    continue

                f_vision = describe_visual_with_groq_vision(f_input, groq_client=groq_client)
                raw_vision_data[f_src] = f_vision

                if f_vision["status"] != "COMPLETED":
                    _add_evidence(f_src, f"Frame #{f_idx} ({f_ts:.2f}s) visual inspection unavailable: {f_vision['status']}")
                else:
                    fv = f_vision["data"]
                    objs = ", ".join(fv["objects"]) if fv["objects"] else "none"
                    acts = ", ".join(fv["actions"]) if fv["actions"] else "none"
                    txts = ", ".join(f"'{t}'" for t in fv["visible_text_or_signs"]) if fv["visible_text_or_signs"] else "none"
                    _add_evidence(
                        f_src,
                        f"Frame #{f_idx} ({f_ts:.2f}s) - Visible objects: {objs}; Actions: {acts}; "
                        f"Setting: {fv['setting']}; Text: {txts}; Lighting: {fv['weather_or_time_of_day']}; People: {fv['people_count']}"
                    )

    # --- 2. TRANSCRIPT EVIDENCE ---
    # Audio uses transcript only; video uses frames plus transcript if present
    if media_type in ["audio", "video"]:
        # If transcript not provided, try to extract if audio exists
        if transcript is None and media_type == "audio" and media_path.is_file():
            try:
                from audio_forensics.transcriber import transcribe_audio
                transcript = transcribe_audio(media_path)
            except Exception:
                transcript = None

        if transcript and transcript.strip():
            _add_evidence("transcript", f"Spoken dialogue transcript: \"{transcript.strip()}\"")
        else:
            _add_evidence("transcript", "Spoken dialogue transcript: none (no speech detected or audio track absent)")

    # --- 3. METADATA EVIDENCE ---
    # Include EXIF or video creation time and GPS if present, and mark when they are missing.
    if media_type == "image":
        img_meta = extract_image_metadata(media_path)
        metadata_bundle = img_meta

        # DateTime check
        dt_val = img_meta.get("datetime_original") or img_meta.get("datetime")
        if dt_val:
            _add_evidence("metadata", f"EXIF Timestamp: {dt_val}")
        else:
            _add_evidence("metadata", "EXIF Timestamp: missing (no date/time tag recorded in file)")

        # GPS check
        gps_val = img_meta.get("gps")
        if gps_val:
            _add_evidence("metadata", f"EXIF GPS Coordinates: {gps_val}")
        else:
            _add_evidence("metadata", "EXIF GPS Coordinates: missing (no location data recorded in file)")

        # Hardware & Software clues
        make_val = img_meta.get("make")
        mod_val = img_meta.get("model")
        if make_val or mod_val:
            _add_evidence("metadata", f"Camera Hardware tag: {make_val or ''} {mod_val or ''}".strip())

        soft_val = img_meta.get("software")
        if soft_val:
            _add_evidence("metadata", f"Editing Software tag: {soft_val}")

    elif media_type == "video":
        vid_meta = extract_video_metadata(media_path)
        metadata_bundle = vid_meta

        # Creation time
        cr_time = vid_meta.get("creation_time")
        if cr_time:
            _add_evidence("metadata", f"Video Container Creation Time: {cr_time}")
        else:
            _add_evidence("metadata", "Video Container Creation Time: missing (no creation timestamp in container)")

        # GPS
        v_gps = vid_meta.get("gps")
        if v_gps:
            _add_evidence("metadata", f"Video Container GPS: {v_gps}")
        else:
            _add_evidence("metadata", "Video Container GPS: missing (no geolocation metadata in container)")

        # Encoder
        v_enc = vid_meta.get("encoder")
        if v_enc:
            _add_evidence("metadata", f"Video Encoder tag: {v_enc}")

        # Duration
        v_dur = vid_meta.get("duration")
        if v_dur:
            _add_evidence("metadata", f"Video Duration: {v_dur}")

    elif media_type == "audio":
        aud_meta = extract_audio_metadata(media_path)
        metadata_bundle = aud_meta

        # Creation date
        aud_cr = aud_meta.get("creation_time")
        if aud_cr:
            _add_evidence("metadata", f"Audio Creation Date: {aud_cr}")
        else:
            _add_evidence("metadata", "Audio Creation Date: missing (no timestamp tag in container)")

        # GPS
        _add_evidence("metadata", "Audio GPS Coordinates: missing (audio container does not record geolocation)")

        # Duration
        aud_dur = aud_meta.get("duration")
        if aud_dur:
            _add_evidence("metadata", f"Audio Duration: {aud_dur}")

    # Build quick lookup map by ID
    evidence_map = {item["id"]: item for item in evidence_items}

    return {
        "status": status,
        "media_type": media_type,
        "evidence_items": evidence_items,
        "evidence_map": evidence_map,
        "raw_vision_data": raw_vision_data,
        "metadata": metadata_bundle,
        "transcript": transcript,
        "error": None if status == "COMPLETED" else status,
    }
