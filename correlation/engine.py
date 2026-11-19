"""Cross-modal forensic correlation engine coordinator."""

from typing import List, Dict, Any, Optional
from core.schemas import Signal, CrossModalFinding, OverallIndicator, ForensicReport
from core.case_manager import CaseManager
from .rules_engine import evaluate_rule_based_correlation
from .llm_correlator import synthesize_llm_correlation
from .human_checks import generate_system_limitations, generate_recommended_human_checks


def correlate_forensic_signals(
    signals: List[Signal],
    inputs: List[str],
    case_manager: Optional[CaseManager] = None,
) -> Dict[str, Any]:
    """Coordinate multimodal signal aggregation, cross-modal reasoning, and human verification checks."""
    # 1. Deterministic Rule-Based Aggregation
    indicator, rule_findings = evaluate_rule_based_correlation(signals)
    warnings = list(getattr(indicator, "warnings", []))

    if case_manager:
        case_manager.log_action(
            f"Rule-based correlation calculated overall indicator: {indicator.level.upper()} "
            f"(confidence: {indicator.confidence:.0%})."
        )

    # 2. LLM Explainability & Cross-Modal Synthesis (strictly grounded, never hallucinating)
    cross_modal_findings, plain_english_summary = synthesize_llm_correlation(
        signals=signals,
        indicator=indicator,
        fallback_findings=rule_findings,
    )

    if case_manager:
        case_manager.log_action(
            f"Cross-modal reasoning completed with {len(cross_modal_findings)} validated findings."
        )

    # 3. Limitations and Human OSINT Verification Checks
    limitations = warnings + generate_system_limitations(signals)
    human_checks = generate_recommended_human_checks(signals)

    return {
        "overall_indicator": indicator,
        "cross_modal_findings": cross_modal_findings,
        "summary": plain_english_summary,
        "limitations": limitations,
        "recommended_human_checks": human_checks,
        "warnings": warnings,
    }
