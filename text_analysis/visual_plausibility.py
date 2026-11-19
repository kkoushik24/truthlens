"""Visual Plausibility & Physics Audit using Groq Vision Model."""

import json
import re
from pathlib import Path
from typing import Optional, Dict, Any

from core.schemas import Signal, create_fallback_signal
from core.config import settings
from .llm_provider import _prepare_image_for_vision_api


def _clean_json_response(content: str) -> str:
    """Strip markdown code blocks and whitespace from LLM response."""
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
    return cleaned.strip()


def check_visual_plausibility(image_path: Path) -> Signal:
    """Analyze visual plausibility and synthetic characteristics using Groq Vision."""
    filename = image_path.name

    if not settings.GROQ_API_KEY or len(settings.GROQ_API_KEY.strip()) < 5:
        return Signal(
            signal_id="txt_plaus_001",
            modality="text",
            name="Visual Plausibility & Physics Audit",
            score=None,
            evidence="FAILED: GROQ_API_KEY is not configured in .env",
            location=None,
            limitation="Groq Vision API key is required to perform visual plausibility reasoning.",
            source_file=filename,
        )

    prompt = (
        "You are an expert digital forensics examiner for TruthLens. "
        "Examine this image carefully for physical plausibility and synthetic AI generation traits.\n"
        "Look for:\n"
        "1. Anatomical, biological, or surreal impossibilities (e.g. food with human limbs, fruit wearing shoes, floating objects, impossible anatomy, illogical shadows/reflections).\n"
        "2. AI generator rendering signatures (oversaturated cartoonish gloss, smooth plastic skin, diffusion blending glitches).\n\n"
        "Respond ONLY with a valid JSON object matching this schema:\n"
        "{\n"
        '  "physically_plausible": true or false,\n'
        '  "impossible_elements": ["List of surreal or impossible items observed, e.g. fruit with human legs"],\n'
        '  "ai_generated_look": 0.0 to 1.0 (0.0 = completely real photo, 1.0 = obvious AI render),\n'
        '  "reason": "One plain-English sentence summarizing the finding without jargon"\n'
        "}"
    )

    try:
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)
        b64_image = _prepare_image_for_vision_api(image_path)
        data_uri = f"data:image/jpeg;base64,{b64_image}"

        # Helper for a single completion call
        def _call_groq():
            return client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": data_uri}},
                        ],
                    }
                ],
                model=settings.GROQ_VISION_MODEL,
                response_format={"type": "json_object"},
                temperature=0.1,
                timeout=15.0,
            )

        # Attempt 1 with retry on JSON parse failure
        content = ""
        parsed = None
        for attempt in range(2):
            try:
                chat_completion = _call_groq()
                content = chat_completion.choices[0].message.content
                cleaned_json = _clean_json_response(content)
                parsed = json.loads(cleaned_json)
                break
            except Exception as parse_err:
                if attempt == 1:
                    return Signal(
                        signal_id="txt_plaus_001",
                        modality="text",
                        name="Visual Plausibility & Physics Audit",
                        score=None,
                        evidence=f"FAILED: Invalid JSON from Groq Vision model: {str(parse_err)}",
                        location=None,
                        limitation="Model response was not valid JSON after retry.",
                        source_file=filename,
                    )

        if not parsed:
            return Signal(
                signal_id="txt_plaus_001",
                modality="text",
                name="Visual Plausibility & Physics Audit",
                score=None,
                evidence="FAILED: Empty response from Groq Vision",
                location=None,
                limitation="Visual plausibility check received no response from Groq.",
                source_file=filename,
            )

        physically_plausible = bool(parsed.get("physically_plausible", True))
        impossible_elements = [str(x) for x in parsed.get("impossible_elements", []) if str(x).strip()]
        ai_look = float(parsed.get("ai_generated_look", 0.2))
        reason = str(parsed.get("reason", "")).strip()

        # Score calculation: high score when impossible elements or AI look found
        if not physically_plausible or len(impossible_elements) > 0:
            score = max(0.85, ai_look)
            elem_str = ", ".join(impossible_elements) if impossible_elements else "biologically impossible features"
            evidence = (
                f"The image shows physically impossible or surreal elements ({elem_str}). "
                f"Normal cameras do not capture impossible physical events. "
                f"Strong evidence of AI generation."
            )
        elif ai_look >= 0.60:
            score = ai_look
            evidence = (
                f"The image shows rendering textures typical of generative AI ({reason}). "
                f"This visual pattern indicates synthetic generation rather than a camera photo. "
                f"Moderate to strong indicator."
            )
        else:
            score = max(0.10, ai_look)
            evidence = (
                f"Lighting, physics, and scene geometry look natural ({reason or 'no anomalies found'}). "
                f"No impossible or surreal elements were observed. "
                f"Consistent with genuine photography."
            )

        return Signal(
            signal_id="txt_plaus_001",
            modality="text",
            name="Visual Plausibility & Physics Audit",
            score=score,
            evidence=evidence,
            location=None,
            limitation="Visual plausibility uses AI reasoning and may misjudge fictional artwork or staged theatrical scenes.",
            source_file=filename,
        )

    except Exception as e:
        err_msg = str(e)
        err_lower = err_msg.lower()
        if any(k in err_lower for k in ["model_not_found", "deprecated", "does not exist", "not found", "decommissioned"]):
            evidence_err = (
                f"FAILED: Groq model error: '{settings.GROQ_VISION_MODEL}' was rejected ({err_msg}). "
                "Please update GROQ_VISION_MODEL in config.py or in .env."
            )
        else:
            evidence_err = f"FAILED: Visual plausibility check error: {err_msg}"

        return Signal(
            signal_id="txt_plaus_001",
            modality="text",
            name="Visual Plausibility & Physics Audit",
            score=None,
            evidence=evidence_err,
            location=None,
            limitation="Visual plausibility analysis requires an active Groq API connection.",
            source_file=filename,
        )
