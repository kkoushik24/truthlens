"""Case and workspace manager for forensic investigations.

Ensures evidence isolation, strictly immutable originals, artifact storage,
and an audit history log.
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Union
import shutil

from .config import settings
from .hashing import calculate_sha256, calculate_bytes_sha256
from .schemas import HistoryItem


class CaseManager:
    """Handles directory isolation, immutable input storage, and history logging for a case."""

    def __init__(self, case_id: Optional[str] = None):
        now_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        random_suffix = uuid.uuid4().hex[:6].upper()
        self.case_id: str = case_id or f"CASE-{now_str}-{random_suffix}"

        # Setup directory paths
        self.case_dir: Path = settings.CASES_DIR / self.case_id
        self.originals_dir: Path = self.case_dir / "originals"
        self.artifacts_dir: Path = self.case_dir / "artifacts"

        self.originals_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)

        self.input_hashes: Dict[str, str] = {}
        self.history: List[HistoryItem] = []

        self.log_action(f"Case {self.case_id} initialized.")

    def log_action(self, action_description: str) -> None:
        """Append an action to the case audit log with an ISO 8601 UTC timestamp."""
        now_iso = datetime.now(timezone.utc).isoformat()
        self.history.append(HistoryItem(time=now_iso, action=action_description))

    def save_original(self, filename: str, content: Union[bytes, Path, str]) -> Path:
        """Save an uploaded file directly into the immutable originals directory.
        
        Computes SHA-256 and records it without modifying file bytes.
        """
        # Sanitize filename to avoid directory traversal
        safe_name = Path(filename).name
        target_path = self.originals_dir / safe_name

        if isinstance(content, bytes):
            with open(target_path, "wb") as f:
                f.write(content)
            sha256_hash = calculate_bytes_sha256(content)
        elif isinstance(content, (str, Path)):
            src_path = Path(content)
            if not src_path.is_file():
                raise FileNotFoundError(f"Source file not found: {content}")
            shutil.copy2(src_path, target_path)
            sha256_hash = calculate_sha256(target_path)
        else:
            raise TypeError("Content must be raw bytes or a valid file Path/str.")

        self.input_hashes[safe_name] = sha256_hash
        self.log_action(
            f"Original file '{safe_name}' stored with SHA-256: {sha256_hash[:12]}..."
        )
        return target_path

    def get_artifact_path(self, filename: str) -> Path:
        """Get the full path for a generated forensic artifact (e.g., heatmap, spectrogram)."""
        safe_name = Path(filename).name
        return self.artifacts_dir / safe_name

    def list_originals(self) -> List[Path]:
        """List all preserved original input files."""
        return sorted(list(self.originals_dir.iterdir()))
