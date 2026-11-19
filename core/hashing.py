"""Cryptographic hashing utilities to maintain chain of custody and file integrity."""

import hashlib
from pathlib import Path
from typing import Union


def calculate_sha256(file_path: Union[str, Path], chunk_size: int = 65536) -> str:
    """Calculate the SHA-256 hash of a file by streaming chunks.
    
    Guarantees constant low memory usage even for large video/audio files.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Cannot hash non-existent file: {file_path}")

    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            sha256.update(chunk)
    return sha256.hexdigest()


def calculate_bytes_sha256(data: bytes) -> str:
    """Calculate the SHA-256 hash of raw bytes in memory."""
    return hashlib.sha256(data).hexdigest()
