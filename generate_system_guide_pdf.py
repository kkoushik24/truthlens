"""Generate comprehensive TruthLens OS Architecture and Forensics Guide PDF."""

import os
from pathlib import Path
from fpdf import FPDF
from fpdf.enums import XPos, YPos


def sanitize_text(text: str) -> str:
    """Sanitize string for standard Latin-1 FPDF fonts."""
    if not text:
        return ""
    replacements = {
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2014": "--", "\u2013": "-", "\u2026": "...", "\u2022": "*",
        "\xa0": " ", "\u2265": ">=", "\u2264": "<=", "\u2260": "!=",
        "\u2192": "->", "\u2190": "<-", "\u2713": "[OK]", "\u2717": "[X]",
        "\u25aa": "-", "\u25cf": "*",
    }
    for orig, rep in replacements.items():
        text = text.replace(orig, rep)
    return text.encode("latin-1", "replace").decode("latin-1")


class TruthLensGuidePDF(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        if self.page_no() > 1:
            self.set_font("Helvetica", "B", 8)
            self.set_text_color(100, 116, 139)
            self.cell(
                self.epw / 2, 6,
                "TRUTHLENS OS | SYSTEM ARCHITECTURE & FORENSICS GUIDE",
                border=0, align="L",
                new_x=XPos.RIGHT, new_y=YPos.TOP,
            )
            self.cell(
                self.epw / 2, 6,
                "TEAM TROJAN QUAD | SAPTHAHACKS '26",
                border=0, align="R",
                new_x=XPos.LMARGIN, new_y=YPos.NEXT,
            )
            self.set_draw_color(226, 232, 240)
            self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
            self.ln(4)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(148, 163, 184)
        self.cell(
            self.epw / 2, 6,
            "Sapthagiri NPS University & Innovedge (@INNOVEDGE_SNPSU)",
            border=0, align="L",
            new_x=XPos.RIGHT, new_y=YPos.TOP,
        )
        self.cell(
            self.epw / 2, 6,
            f"Page {self.page_no()}",
            border=0, align="R",
            new_x=XPos.LMARGIN, new_y=YPos.NEXT,
        )

    def section_title(self, title: str, subtitle: str = ""):
        self.ln(3)
        self.set_fill_color(15, 23, 42)  # Dark slate
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 11)
        self.cell(self.epw, 7, sanitize_text(f"  {title.upper()}"), fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        if subtitle:
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(71, 85, 105)
            self.cell(self.epw, 5, sanitize_text(subtitle), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)

    def sub_heading(self, text: str):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(14, 116, 144)  # Deep cyan
        self.cell(self.epw, 6, sanitize_text(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def body_p(self, text: str):
        self.set_font("Helvetica", "", 9)
        self.set_text_color(30, 41, 59)
        self.multi_cell(self.epw, 4.5, sanitize_text(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1.5)

    def bullet(self, label: str, text: str):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(30, 41, 59)
        self.write(4.5, sanitize_text(f"- {label}: "))
        self.set_font("Helvetica", "", 9)
        self.set_text_color(71, 85, 105)
        self.write(4.5, sanitize_text(f"{text}\n"))
        self.ln(1)


def build_pdf(output_path: Path):
    pdf = TruthLensGuidePDF()
    pdf.add_page()

    # --- COVER / HERO BLOCK ---
    pdf.set_fill_color(5, 8, 17)  # Cyber dark space
    pdf.rect(pdf.l_margin, pdf.get_y(), pdf.epw, 42, "F")
    
    pdf.set_xy(pdf.l_margin + 5, pdf.get_y() + 4)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(0, 210, 255)  # Neon cyan
    pdf.cell(pdf.epw - 10, 8, "TRUTHLENS OS", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_x(pdf.l_margin + 5)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(241, 245, 249)
    pdf.cell(pdf.epw - 10, 6, "Autonomous Multimodal Digital Forensics Workstation", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_x(pdf.l_margin + 5)
    pdf.set_font("Helvetica", "", 8.5)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(pdf.epw - 10, 5, "SapthaHacks '26 Submission | Sapthagiri NPS University in collaboration with Innovedge", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_x(pdf.l_margin + 5)
    pdf.set_font("Helvetica", "B", 8.5)
    pdf.set_text_color(56, 189, 248)
    pdf.cell(pdf.epw - 10, 5, "Team Trojan Quad: Koushik, Yashwanth K N, Yohaan G Oommen, Likith Kumar R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_y(pdf.get_y() + 10)

    # --- EXECUTIVE SUMMARY ---
    pdf.section_title("1. Executive Summary & Core Philosophy", "Why probabilistic forensic risk tiers replace naive binary detectors")
    pdf.body_p(
        "TruthLens OS is an autonomous multimodal digital forensics workstation built to combat deepfakes, "
        "synthetic media manipulation, and contextual disinformation ('cheapfakes'). "
        "Traditional consumer tools make the fatal mistake of outputting black-box binary verdicts ('Real' vs 'Fake'). "
        "In legal, journalistic, and law-enforcement contexts, binary labels fail because compression artifacts "
        "(e.g., from WhatsApp or Instagram) generate false positives, and context mismatches (real photos with fake claims) "
        "go completely undetected."
    )
    pdf.body_p(
        "TruthLens complies with international Scientific Working Group on Digital Evidence (SWGDE) standards. "
        "It evaluates physical signal properties, pixel quantization math, acoustic physics, and multimodal "
        "contextual reasoning, outputting calibrated Forensic Risk Tiers: Low Risk, Moderate Risk, and Elevated Risk."
    )

    # --- SYSTEM ARCHITECTURE ---
    pdf.section_title("2. End-to-End System Architecture", "Data ingestion pipeline and cross-modal correlation topology")
    
    # Architecture Table
    col_w = [35, 75, 70]
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(241, 245, 249)
    pdf.set_text_color(15, 23, 42)
    headers = ["Pipeline Stage", "Core Technologies / Models", "Forensic Functional Role"]
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 6, h, border=1, fill=True, align="L")
    pdf.ln()

    stages = [
        ("1. Ingestion Vault", "FastAPI, SHA-256 Hashing, Python", "Multi-modal file staging & cryptographic chain-of-custody."),
        ("2. Image Forensics", "OpenCV, Pillow, ExifRead, Math", "Error Level Analysis (ELA) & hardware metadata integrity."),
        ("3. Audio Forensics", "Librosa, SciPy, SoundFile, FFmpeg", "Spectral rolloff & synthetic high-frequency cutoff analysis."),
        ("4. Video Keyframes", "OpenCV, imageio-ffmpeg", "Temporal motion variance & keyframe extraction across time."),
        ("5. Neural Engine", "Groq Cloud (Qwen 3.8-27B + LLaMA-3)", "Sub-2s visual artifact reasoning & claim verification."),
        ("6. Correlation Core", "Weighted Signal Fusion Engine", "Cross-modal consistency scoring & risk tier classification."),
        ("7. Legal Dossier", "FPDF2, Cryptographic Signature", "Tamper-evident, signed PDF report with SHA-256 hashes."),
    ]
    pdf.set_font("Helvetica", "", 8)
    for stage, tech, role in stages:
        pdf.set_text_color(15, 23, 42)
        pdf.cell(col_w[0], 6, stage, border=1)
        pdf.set_text_color(71, 85, 105)
        pdf.cell(col_w[1], 6, tech, border=1)
        pdf.cell(col_w[2], 6, role, border=1)
        pdf.ln()

    pdf.ln(3)

    # --- SEGMENT-BY-SEGMENT DEEP DIVE ---
    pdf.section_title("3. Forensic Segments & Algorithmic Mechanics", "Detailed technical analysis of every workstation module")

    pdf.sub_heading("Segment 1: Multi-Modal Staging Vault & Chain of Custody")
    pdf.body_p(
        "The workstation accepts four simultaneous input streams: Image (JPG, PNG, WEBP), Video (MP4, MOV, MKV), "
        "Audio (WAV, MP3, FLAC), and Contextual Claim text. Upon ingestion, the server computes an immutable SHA-256 "
        "hash for every file. This establishes a verifiable Chain of Custody, ensuring digital evidence cannot be altered "
        "undetected throughout the investigation lifecycle."
    )

    pdf.sub_heading("Segment 2: Calibrated Risk Tiers & Confidence Engine")
    pdf.bullet("Low Risk (0.00 - 0.35)", "Authentic compression baselines, valid metadata, organic acoustic harmonics, and factual alignment.")
    pdf.bullet("Moderate Risk (0.35 - 0.65)", "Inconclusive or mixed signals (e.g., social media stripped metadata but clean pixel structure).")
    pdf.bullet("Elevated Risk (0.65 - 1.00)", "Clear mathematical tampering, ELA compression divergence, voice synthesis cutoff, or direct claim contradiction.")
    pdf.body_p(
        "Confidence is computed as a function of signal coverage and variance across modalities, preventing single-point false positives."
    )

    pdf.sub_heading("Segment 3: Image Forensics (Error Level Analysis & EXIF)")
    pdf.bullet("Error Level Analysis (ELA)", "Every lossy JPEG resave compresses pixels according to standard quantization tables. "
               "When a foreign element is spliced into a photo, its error rate diverges from the base background. "
               "TruthLens resaves at 90% quality and computes: Difference = |I_original - I_resaved| * Scale. "
               "Edited regions glow brightly in cyan/purple while untouched regions remain dark.")
    pdf.bullet("Hardware & EXIF Baselines", "Parses Make, Model, Lens, Timestamp, and Editing Software tags (e.g. Photoshop). "
               "Intelligently accounts for social platforms (WhatsApp, X, Meta) that strip EXIF by default, avoiding false alarms.")

    pdf.sub_heading("Segment 4: Audio Acoustics Forensics")
    pdf.bullet("Spectral Rolloff & Cutoff", "Human voices produce natural harmonic overtones extending beyond 18,000 Hz. "
               "Neural vocoders (e.g. ElevenLabs, VITS, Bark) frequently exhibit unnatural sharp brick-wall cutoffs at 16,000 Hz. "
               "TruthLens executes STFT (Short-Time Fourier Transform) to isolate synthetic frequency limits.")
    pdf.bullet("Zero-Crossing Rate (ZCR)", "Measures voice transition smoothness vs digital robotic synthesis artifacts.")
    pdf.bullet("Spectrogram Visualizer", "Generates high-resolution frequency-vs-time spectrograms rendered dynamically in the UI.")

    pdf.sub_heading("Segment 5: Video Keyframes & Temporal Stability")
    pdf.body_p(
        "Deepfake face-swaps and generative video often deceive in a single frame but exhibit temporal flickering across time. "
        "TruthLens extracts 12 uniform keyframes across the timeline and measures structural variance and edge stability."
    )

    pdf.sub_heading("Segment 6: Contextual Misinformation Auditing (The Cheapfake Detector)")
    pdf.body_p(
        "Over 70% of viral online misinformation consists of 'cheapfakes': unedited, authentic imagery shared with fabricated captions "
        "(e.g., a 2017 storm photo recycled as 'Yesterday's hurricane'). "
        "TruthLens integrates Groq's high-throughput cloud Neural Engine (Qwen 3.8-27B Vision + LLaMA-3/GPT-OSS 120B). "
        "In under 2 seconds, the vision model extracts objective scene facts (weather, sunlight angle, vegetation, architecture) "
        "and mathematically verifies whether the contextual claim contradicts the physical facts."
    )

    pdf.sub_heading("Segment 7: Cross-Modal Correlation Matrix")
    pdf.body_p(
        "The correlation engine merges signal vectors into an alignment matrix: "
        "Image Facts <---> Audio Acoustics <---> Context Claims. "
        "Contradictions across streams exponentially increase the Forensic Risk Tier."
    )

    pdf.sub_heading("Segment 8: Legal-Grade Dossier & JSON Export")
    pdf.body_p(
        "TruthLens outputs a formal, printable PDF investigation dossier complete with case timestamps, operator ID, "
        "cryptographic SHA-256 evidence hashes, embedded forensic heatmaps, signal tables, and legal disclaimers. "
        "It also exposes full machine-readable JSON for integration into enterprise security systems (SIEMs)."
    )

    # --- TECHNICAL SPECIFICATION & DEPLOYMENT ---
    pdf.section_title("4. Deployment Topology & Tech Stack", "Cloud-native, containerized architecture")
    
    spec_w = [45, 135]
    specs = [
        ("Cloud Platform", "Render Cloud (Live Web Service with continuous deployment from GitHub main)."),
        ("Containerization", "Production Dockerfile based on Debian Bookworm (Python 3.11 slim)."),
        ("System Libraries", "FFmpeg (media demuxing), libsndfile1 (C audio decoding), OpenCV Headless."),
        ("Web Framework", "FastAPI (async high-concurrency REST endpoints), Uvicorn ASGI server."),
        ("AI Inference Engine", "Groq API: openai/gpt-oss-120b (Text/Context) & qwen/qwen3.8-27b (Vision)."),
        ("UI Architecture", "Tactical Cyberpunk Command Deck with squircle curves (HTML5/CSS3/ES6 JS)."),
        ("Repository", "https://github.com/kkoushik24/truthlens"),
    ]
    pdf.set_font("Helvetica", "B", 8)
    for label, val in specs:
        pdf.set_text_color(15, 23, 42)
        pdf.cell(spec_w[0], 5.5, label, border=1)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(71, 85, 105)
        pdf.cell(spec_w[1], 5.5, val, border=1)
        pdf.set_font("Helvetica", "B", 8)
        pdf.ln()

    pdf.ln(3)

    # --- DEMO SCENARIOS & PRESENTATION CHEAT SHEET ---
    pdf.section_title("5. Hackathon Defense & Judges' Q&A Guide", "Anticipated technical questions and evaluation points")

    pdf.bullet("Q1: How do you prevent false positives on compressed WhatsApp / Instagram images?",
               "Answer: Consumer detectors flag WhatsApp compression as fake. TruthLens checks ELA variance rather than absolute compression, and specifically flags missing EXIF as typical social-media behavior rather than tampering.")

    pdf.bullet("Q2: Why use Groq instead of running local multimodal LLMs?",
               "Answer: Groq LPU inference achieves sub-1.5 second turnaround for 27B-parameter vision and 120B-parameter reasoning models. This keeps the cloud container lightweight (<512MB RAM on Render) while outperforming heavy on-premise infrastructure.")

    pdf.bullet("Q3: What makes this superior to simple AI-detectors like Hive or Deepware?",
               "Answer: Hive only outputs a single image score. TruthLens audits the multi-modal triangle: Image + Audio + Context Claims, providing legal-grade chain-of-custody PDF dossiers with SHA-256 evidence integrity.")

    pdf.bullet("Q4: Can this be integrated into law-enforcement or journalistic workflows?",
               "Answer: Yes. The entire platform exposes standardized REST APIs (/api/analyze, /api/demos, /api/pdf/{id}, /api/json/{id}) allowing instant integration into newsroom CMS platforms and evidence management vaults.")

    pdf.output(str(output_path))
    print(f"PDF successfully generated at: {output_path}")


if __name__ == "__main__":
    out_file = Path(os.getcwd()) / "TruthLens_System_Architecture_and_Forensics_Guide.pdf"
    build_pdf(out_file)
