"""Comprehensive report builder producing both JSON and PDF deliverables."""

import shutil
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from core.schemas import ForensicReport, Signal, CrossModalFinding, OverallIndicator
from core.case_manager import CaseManager
from .json_exporter import export_report_to_json
from .pdf_exporter import export_report_to_pdf


def generate_forensic_report_bundle(
    case_manager: CaseManager,
    signals: List[Signal],
    correlation_data: Dict[str, Any],
) -> Tuple[ForensicReport, Path, Path]:
    """Assemble final ForensicReport and export both JSON and PDF deliverables."""
    case_id = case_manager.case_id
    inputs = [p.name for p in case_manager.list_originals()]
    input_hashes = case_manager.input_hashes

    overall_indicator: OverallIndicator = correlation_data["overall_indicator"]
    cross_modal_findings: List[CrossModalFinding] = correlation_data["cross_modal_findings"]
    limitations: List[str] = correlation_data["limitations"]
    human_checks: List[str] = correlation_data["recommended_human_checks"]
    summary_text: str = correlation_data.get("summary", "")

    # Build Pydantic ForensicReport
    report = ForensicReport(
        case_id=case_id,
        inputs=inputs,
        input_hashes=input_hashes,
        signals=signals,
        cross_modal_findings=cross_modal_findings,
        overall_indicator=overall_indicator,
        limitations=limitations,
        recommended_human_checks=human_checks,
        history=case_manager.history,
    )

    # Export JSON to case root and artifacts directory
    json_path = case_manager.case_dir / "report.json"
    export_report_to_json(report, json_path)
    try:
        shutil.copy2(json_path, case_manager.artifacts_dir / "report.json")
    except Exception:
        pass
    case_manager.log_action(f"Forensic report JSON generated at {json_path.name}.")

    # Locate image artifacts to embed in PDF
    artifact_images: List[Path] = []
    if case_manager.artifacts_dir.exists():
        for p in sorted(case_manager.artifacts_dir.glob("*.png")):
            artifact_images.append(p)
        for p in sorted(case_manager.artifacts_dir.glob("*.jpg")):
            artifact_images.append(p)

    # Export PDF to case root and artifacts directory
    pdf_path = case_manager.case_dir / "report.pdf"
    export_report_to_pdf(
        report=report,
        output_path=pdf_path,
        artifact_images=artifact_images,
        summary_text=summary_text,
    )
    try:
        shutil.copy2(pdf_path, case_manager.artifacts_dir / "report.pdf")
    except Exception:
        pass
    case_manager.log_action(f"Forensic report PDF dossier generated at {pdf_path.name}.")

    return report, json_path, pdf_path
