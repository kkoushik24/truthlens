"""TruthLens Configuration and Environment Variables."""

import os
import tempfile
from pathlib import Path
from dotenv import load_dotenv

# Set writable Matplotlib config directory to avoid sandbox/permission warnings
mpl_cache_dir = Path(tempfile.gettempdir()) / "truthlens_mpl"
mpl_cache_dir.mkdir(parents=True, exist_ok=True)
os.environ["MPLCONFIGDIR"] = str(mpl_cache_dir)

# Load .env file specifically from project root if it exists
BASE_DIR = Path(__file__).resolve().parent.parent
env_file = BASE_DIR / ".env"
if env_file.is_file():
    load_dotenv(dotenv_path=env_file, override=True)



class Settings:
    # Storage & Cases
    BASE_DIR: Path = BASE_DIR
    CASES_DIR: Path = Path(os.getenv("CASES_DIR", BASE_DIR / "cases"))
    DEMO_CASES_DIR: Path = Path(os.getenv("DEMO_CASES_DIR", BASE_DIR / "demo_cases"))
    SAMPLES_DIR: Path = Path(os.getenv("SAMPLES_DIR", BASE_DIR / "samples"))

    # API Keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    HF_TOKEN: str = os.getenv("HF_TOKEN", "")

    # Provider and Model Swapping Configurations
    LLM_PROVIDER: str = os.getenv(
        "LLM_PROVIDER", "groq" if os.getenv("GROQ_API_KEY") else "gemini"
    ).lower()
    GROQ_VISION_MODEL: str = os.getenv(
        "GROQ_VISION_MODEL", "qwen/qwen3.8-27b"
    )
    GROQ_TEXT_MODEL: str = os.getenv(
        "GROQ_TEXT_MODEL", "openai/gpt-oss-120b"
    )
    IMAGE_AI_DETECTOR_MODEL: str = os.getenv(
        "IMAGE_AI_DETECTOR_MODEL", "umm-maybe/AI-image-detector"
    )
    IMAGE_AI_DETECTOR_MODELS: list = [
        os.getenv("IMAGE_AI_DETECTOR_MODEL", "umm-maybe/AI-image-detector")
    ]
    AUDIO_VOICE_DETECTOR_MODEL: str = os.getenv(
        "AUDIO_VOICE_DETECTOR_MODEL", "MelodyMachine/Deepfake-audio-detection-V2"
    )
    AUDIO_VOICE_DETECTOR_MODELS: list = [
        os.getenv("AUDIO_VOICE_DETECTOR_MODEL", "MelodyMachine/Deepfake-audio-detection-V2")
    ]
    WHISPER_MODEL_SIZE: str = os.getenv("WHISPER_MODEL_SIZE", "tiny")

    # Processing Parameters
    DEFAULT_ELA_QUALITY: int = int(os.getenv("DEFAULT_ELA_QUALITY", "90"))
    MAX_VIDEO_FRAMES: int = int(os.getenv("MAX_VIDEO_FRAMES", "12"))
    MAX_IMAGE_PROCESS_DIM: int = int(os.getenv("MAX_IMAGE_PROCESS_DIM", "1600"))
    AUTO_DOWNLOAD_HF_MODELS: bool = os.getenv(
        "AUTO_DOWNLOAD_HF_MODELS", "False"
    ).lower() in ("true", "1", "yes")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")

    def ensure_directories(self) -> None:
        """Create necessary base storage directories."""
        self.CASES_DIR.mkdir(parents=True, exist_ok=True)
        self.DEMO_CASES_DIR.mkdir(parents=True, exist_ok=True)
        self.SAMPLES_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()
