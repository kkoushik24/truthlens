"""JSON export serializer for TruthLens forensic reports."""

import json
from pathlib import Path
from typing import Union, Dict, Any

from core.schemas import ForensicReport


def export_report_to_json(
    report: Union[ForensicReport, Dict[str, Any]],
    output_path: Path,
    indent: int = 2,
) -> Path:
    """Validate and export a ForensicReport to formatted JSON format."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(report, dict):
        report_obj = ForensicReport(**report)
    elif isinstance(report, ForensicReport):
        report_obj = report
    else:
        raise TypeError("Report must be a ForensicReport instance or valid dict.")

    report_dict = report_obj.model_dump()

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=indent, ensure_ascii=False)

    return output_path
