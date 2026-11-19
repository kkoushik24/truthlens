"""TruthLens Cross-Modal Correlation Module."""

from .rules_engine import evaluate_rule_based_correlation
from .llm_correlator import synthesize_llm_correlation
from .human_checks import generate_system_limitations, generate_recommended_human_checks
from .engine import correlate_forensic_signals

__all__ = [
    "evaluate_rule_based_correlation",
    "synthesize_llm_correlation",
    "generate_system_limitations",
    "generate_recommended_human_checks",
    "correlate_forensic_signals",
]
