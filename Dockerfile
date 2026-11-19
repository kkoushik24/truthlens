# Production Dockerfile for TruthLens Forensic Workstation
FROM python:3.11-slim-bookworm

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=8000

WORKDIR /app

# Install system dependencies required for OpenCV, audio processing, FFmpeg, and fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    libgl1 \
    libglib2.0-0 \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install CPU PyTorch & application dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Pre-download / cache required Hugging Face models if necessary
# RUN python setup_models.py

# Copy application source code
COPY . .

# Create cache and temporary directories with write permissions
RUN mkdir -p /tmp/truthlens_mpl cases demo_cases artifacts static && \
    chmod -R 777 /tmp/truthlens_mpl cases demo_cases artifacts static

# Expose default HTTP port
EXPOSE 8000

# Launch production FastAPI server with dynamic PORT support
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}"]
