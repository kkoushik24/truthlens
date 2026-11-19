"""Forensic PDF Dossier Generator using modern fpdf2 APIs."""

from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from fpdf import FPDF
from fpdf.enums import XPos, YPos

from core.schemas import ForensicReport, Signal, CrossModalFinding


def sanitize_text(text: str) -> str:
    """Sanitize strings to avoid encoding errors in standard PDF fonts."""
    if not text:
        return ""
    replacements = {
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2014": "--", "\u2013": "-", "\u2026": "...", "\u2022": "*",
        "\xa0": " ", "\u2265": ">=", "\u2264": "<=", "\u2260": "!=",
    }
    for orig, rep in replacements.items():
        text = text.replace(orig, rep)
    return text.encode("latin-1", "replace").decode("latin-1")


class ForensicPDF(FPDF):
    """Custom FPDF layout with TruthLens headers, footers, and page numbers."""

    def __init__(self, case_id: str):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.case_id = case_id
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(100, 100, 100)
        self.cell(
            self.epw / 2, 6,
            sanitize_text(f"TRUTHLENS FORENSIC DOSSIER | CASE: {self.case_id}"),
            border=0, align="L",
            new_x=XPos.RIGHT, new_y=YPos.TOP,
        )
        self.cell(
            self.epw / 2, 6,
            "CONFIDENTIAL / INVESTIGATIVE",
            border=0, align="R",
            new_x=XPos.LMARGIN, new_y=YPos.NEXT,
        )
        self.set_draw_color(200, 200, 200)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(
            self.epw, 6,
            f"Page {self.page_no()}",
            border=0, align="C",
            new_x=XPos.LMARGIN, new_y=YPos.NEXT,
        )


def export_report_to_pdf(
    report: Union[ForensicReport, Dict[str, Any]],
    output_path: Union[str, Path],
    artifact_images: Optional[List[Path]] = None,
    summary_text: Optional[str] = None,
) -> Path:
    """Generate a multi-page forensic evaluation PDF dossier."""
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(report, dict):
        report_obj = ForensicReport(**report)
    else:
        report_obj = report

    pdf = ForensicPDF(case_id=report_obj.case_id)
    pdf.add_page()
    epw = pdf.epw  # Effective page width (190mm on A4 with 10mm margins)

    # --- TITLE BLOCK ---
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(20, 30, 50)
    pdf.cell(epw, 10, "Digital Media Forensic Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(epw, 6, f"Generated for Case: {report_obj.case_id}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L")
    pdf.ln(3)

    # --- OVERALL INDICATOR BADGE ---
    indicator_level = report_obj.overall_indicator.level.upper()
    confidence_pct = int(report_obj.overall_indicator.confidence * 100)

    color_map = {
        "LOW": (40, 167, 69),
        "MODERATE": (245, 140, 0),
        "ELEVATED": (220, 53, 69),
    }
    bg_r, bg_g, bg_b = color_map.get(indicator_level, (100, 100, 100))

    pdf.set_fill_color(bg_r, bg_g, bg_b)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 12)
    badge_text = f"  OVERALL INDICATOR: {indicator_level}  (Confidence: {confidence_pct}%)  "
    pdf.cell(epw, 9, sanitize_text(badge_text), fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.ln(4)

    # --- EXECUTIVE SUMMARY ---
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(epw, 6, "1. Executive Summary & Forensic Assessment", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(50, 50, 50)

    summary_content = summary_text or (
        f"Forensic evaluation synthesized {len(report_obj.signals)} atomic indicators across "
        f"{len(report_obj.inputs)} submitted media assets. An indicator level of {indicator_level} "
        f"was established with {confidence_pct}% calculated confidence. Detection scores represent "
        f"probabilistic indicators of tampering, never definitive verdicts."
    )
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(epw, 5, sanitize_text(summary_content))
    pdf.ln(4)

    # --- CRYPTOGRAPHIC CHAIN OF CUSTODY TABLE ---
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(epw, 6, "2. Cryptographic Integrity (Chain of Custody)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(240, 242, 245)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(50, 6, "Input Filename", border=1, fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(epw - 50, 6, "SHA-256 Cryptographic Checksum", border=1, fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Courier", "", 7)
    for filename, sha256_hash in report_obj.input_hashes.items():
        pdf.cell(50, 6, sanitize_text(filename[:26]), border=1, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.cell(epw - 50, 6, sha256_hash, border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)

    # --- MULTIMODAL SIGNALS TABLE ---
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(epw, 6, "3. Observed Forensic Signals", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(240, 242, 245)
    pdf.cell(20, 6, "Modality", border=1, fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(38, 6, "Test Name", border=1, fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(16, 6, "Score", border=1, fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.cell(epw - 74, 6, "Key Evidence Observed", border=1, fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", "", 7)
    for sig in report_obj.signals:
        score_str = f"{sig.score:.2f}" if sig.score is not None else "N/A"
        mod_str = sig.modality.upper()
        name_str = sig.name[:22]
        ev_str = sig.evidence[:95] + ("..." if len(sig.evidence) > 95 else "")

        pdf.cell(20, 6, sanitize_text(mod_str), border=1, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.cell(38, 6, sanitize_text(name_str), border=1, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.cell(16, 6, score_str, border=1, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.cell(epw - 74, 6, sanitize_text(ev_str), border=1, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)

    # --- CROSS-MODAL FINDINGS ---
    if report_obj.cross_modal_findings:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(30, 30, 30)
        pdf.cell(epw, 6, "4. Cross-Modal Correlated Findings", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        for cmf in report_obj.cross_modal_findings:
            eff_color = (220, 53, 69) if cmf.effect == "strengthens" else (40, 167, 69)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*eff_color)
            pdf.cell(25, 5, f"[{cmf.effect.upper()}]", new_x=XPos.RIGHT, new_y=YPos.TOP)

            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(40, 40, 40)
            cites = f" (Supporting: {', '.join(cmf.supporting_signals)})" if cmf.supporting_signals else ""
            finding_text = f"{cmf.finding}{cites}"
            pdf.multi_cell(epw - 25, 5, sanitize_text(finding_text))
            pdf.set_x(pdf.l_margin)
        pdf.ln(4)

    # --- VISUAL EVIDENCE ARTIFACTS ---
    if artifact_images:
        valid_imgs = [p for p in artifact_images if p.is_file() and p.suffix.lower() in [".png", ".jpg", ".jpeg"]]
        if valid_imgs:
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(30, 30, 30)
            pdf.cell(epw, 6, "5. Visual & Acoustic Artifact Evidence", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

            for img_path in valid_imgs[:2]:
                pdf.set_font("Helvetica", "I", 8)
                pdf.set_text_color(80, 80, 80)
                pdf.cell(epw, 5, sanitize_text(f"Artifact: {img_path.name}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
                try:
                    pdf.image(str(img_path), w=min(epw, 140))
                    pdf.ln(4)
                except Exception:
                    pass

    # --- LIMITATIONS & HUMAN CHECKLIST ---
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(epw, 6, "6. Forensic Limitations & System Caveats", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(70, 70, 70)
    for lim in report_obj.limitations:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(epw, 4, sanitize_text(f"* {lim}"))
    pdf.ln(3)

    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(epw, 6, "7. Recommended Human Verification Checklist (OSINT)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(40, 40, 40)
    for chk in report_obj.recommended_human_checks:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(epw, 4, sanitize_text(f"[ ] {chk}"))

    # Save PDF
    pdf.output(str(out_path))
    return out_path
