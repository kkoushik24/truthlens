"""Grounded Groq LLM-assisted forensic correlation and plain-English summary synthesis."""

import json
from typing import List, Dict, Any, Tuple, Optional

from core.schemas import Signal, CrossModalFinding, OverallIndicator
from core.config import settings


def _parse_and_validate_findings(
    parsed: Dict[str, Any],
    signals: List[Signal],
    fallback_findings: List[CrossModalFinding],
    default_summary: str,
) -> Tuple[List[CrossModalFinding], str]:
    """Validate LLM-generated findings against verified signal IDs."""
    summary = parsed.get("summary", default_summary)
    raw_findings = parsed.get("cross_modal_findings", [])

    known_ids = set(s.signal_id for s in signals)
    validated_findings: List[CrossModalFinding] = []

    for rf in raw_findings:
        f_text = str(rf.get("finding", "")).strip()
        sup_ids = [str(sid) for sid in rf.get("supporting_signals", []) if str(sid) in known_ids]
        eff = str(rf.get("effect", "strengthens")).lower()
        if eff not in ["strengthens", "weakens"]:
            eff = "strengthens"

        if f_text and sup_ids:
            validated_findings.append(
                CrossModalFinding(
                    finding=f_text,
                    supporting_signals=sup_ids,
                    effect=eff,
                )
            )

    return (validated_findings if validated_findings else fallback_findings, summary)


def synthesize_llm_correlation(
    signals: List[Signal],
    indicator: OverallIndicator,
    fallback_findings: List[CrossModalFinding],
) -> Tuple[List[CrossModalFinding], str]:
    """Use Groq LLM to synthesize an explainable cross-modal narrative and findings.

    Strictly constrained to only reference provided signals; never invents external facts.
    Falls back gracefully to deterministic rule-based findings when offline or without API key.
    """
    valid_signals = [s for s in signals if s.score is not None]

    # Deterministic default summary
    default_summary = (
        f"Forensic analysis compiled {len(signals)} multi-modal indicators resulting in an "
        f"overall indicator level of '{indicator.level.upper()}' (confidence: {indicator.confidence:.0%}). "
        f"Findings highlight {len([s for s in valid_signals if s.score >= 0.60])} elevated indicators "
        f"and {len([s for s in valid_signals if s.score < 0.35])} corroborating baseline indicators."
    )

    if not settings.GROQ_API_KEY or len(settings.GROQ_API_KEY.strip()) < 5:
        return fallback_findings, default_summary

    # Prepare structured input signals for LLM
    signal_summaries = []
    for s in valid_signals:
        loc_str = str(s.location) if s.location else "None"
        signal_summaries.append(
            f"- ID: {s.signal_id} | Modality: {s.modality} | Name: {s.name} | Score: {s.score} | Location: {loc_str}\n"
            f"  Evidence: {s.evidence}\n"
            f"  Limitation: {s.limitation}"
        )
    signals_block = "\n".join(signal_summaries)

    prompt = (
        "You are TruthLens's forensic reporting engine. Synthesize the multimodal indicators into an explainable report.\n\n"
        "STRICT RULES:\n"
        "1. NEVER output binary verdicts like 'FAKE' or 'REAL'. Only use indicator levels: low / moderate / elevated.\n"
        "2. NEVER invent or hallucinate evidence. Only reference observations explicitly stated in the provided signals.\n"
        "3. Every cross-modal finding MUST cite exact supporting signal IDs (e.g. 'img_ela_001', 'txt_plaus_001').\n"
        "4. Each finding must state whether it 'strengthens' or 'weakens' suspicion.\n\n"
        f"OVERALL COMPUTED INDICATOR: {indicator.level} (Confidence: {indicator.confidence:.2f})\n\n"
        f"VERIFIED FORENSIC SIGNALS:\n{signals_block}\n\n"
        "Respond ONLY with a valid JSON object matching this schema:\n"
        "{\n"
        '  "summary": "1-2 short paragraphs in plain English explaining the overall indicator without jargon",\n'
        '  "cross_modal_findings": [\n'
        '    {\n'
        '      "finding": "Plain-English description connecting two or more signals",\n'
        '      "supporting_signals": ["signal_id_1", "signal_id_2"],\n'
        '      "effect": "strengthens" or "weakens"\n'
        '    }\n'
        '  ]\n'
        "}"
    )

    try:
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model=settings.GROQ_TEXT_MODEL,
            response_format={"type": "json_object"},
            temperature=0.1,
            timeout=15.0,
        )
        content = chat_completion.choices[0].message.content
        parsed = json.loads(content)
        return _parse_and_validate_findings(parsed, signals, fallback_findings, default_summary)
    except Exception as e:
        err_str = str(e).lower()
        if any(k in err_str for k in ["model_not_found", "deprecated", "does not exist", "not found", "decommissioned"]):
            print(
                f"[TruthLens Warning] Groq text model '{settings.GROQ_TEXT_MODEL}' was rejected by API. "
                "Please update GROQ_TEXT_MODEL in config.py or in .env."
            )
        return fallback_findings, default_summary
