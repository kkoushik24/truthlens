# Production Dockerfile for TruthLens Forensic Workstation
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=8000

WORKDIR /app

# Install system dependencies required for FFmpeg and audio decoding
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Create writable runtime directories
RUN mkdir -p /tmp/truthlens_mpl cases demo_cases artifacts static && \
    chmod -R 777 /tmp/truthlens_mpl cases demo_cases artifacts static

# Expose default HTTP port
EXPOSE 8000

# Launch production server with dynamic PORT binding
CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000}"]
