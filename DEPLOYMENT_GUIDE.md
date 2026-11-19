# 🚀 TruthLens Deployment & Hosting Guide

TruthLens includes a **Standalone Interactive HTML5 Forensic Workstation** powered by a high-performance **FastAPI backend** (`server.py`), providing an ultra-responsive, zero-lag forensic suite with no Streamlit reload lag or markdown rendering quirks.

---

## 💻 Local Quickstart (Run In 5 Seconds)

To run the interactive web application locally on your machine:

```powershell
# 1. Start the FastAPI Production Server
python server.py
```

Open your browser and navigate to:
👉 **`http://localhost:8000`**

- **Instant Switching**: 0ms client-side tab switching across all forensic modalities.
- **Drag & Drop**: Native visual drag-and-drop staging zone for images, videos, and audio.
- **Interactive Claim Table**: Grounded atomic claims with color-coded status badges, evidence links, and plain-English reasons.
- **1-Click Preloaded Demos**: Inspect Case 1 (*Spliced Photo with Context Mismatch*) and Case 2 (*Authentic Wildlife*) with zero wait.
- **Exporting**: Download full cryptographic PDF dossiers and JSON audit trails directly.

---

## ⚡ Option 1: Render.com (Recommended — 1-Click Free Web Service)

Render provides free SSL web services running Docker or direct Python.

### Step-by-Step Instructions:
1. **Push your code to GitHub**:
   ```bash
   git init
   git add .
   git commit -m "TruthLens Modern Web Workstation"
   git branch -M main
   git remote add origin https://github.com/<your-username>/truthlens.git
   git push -u origin main
   ```
2. Go to [dashboard.render.com](https://dashboard.render.com/) and click **"New" > "Web Service"**.
3. Select **"Build and deploy from a Git repository"** and select your repository.
4. Set:
   * **Runtime**: `Python 3` or `Docker`
   * **Build Command**: `pip install -r requirements.txt` (or Docker automatically builds)
   * **Start Command**: `uvicorn server:app --host 0.0.0.0 --port $PORT`
5. Under **Environment Variables**, add:
   * `GROQ_API_KEY`: `gsk_your_groq_api_key`
   * `GROQ_TEXT_MODEL`: `openai/gpt-oss-120b`
   * `GROQ_VISION_MODEL`: `qwen/qwen3.8-27b`
   * `LLM_PROVIDER`: `groq`
6. Click **"Deploy Web Service"**!
   Render will deploy your site and provide a free public URL: `https://truthlens.onrender.com`.

---

## 🚂 Option 2: Railway.app (Fastest Deployment)

Railway automatically detects Python/Docker and deploys in under 2 minutes:

1. Go to [railway.app](https://railway.app/) and click **"New Project" > "Deploy from GitHub repo"**.
2. Select your repository.
3. In **Variables**, add:
   * `GROQ_API_KEY` = `gsk_your_groq_api_key`
4. Click **Deploy**. Railway will run `server:app` via `Procfile` / `railway.json` and grant you an HTTPS public domain.

---

## 🐳 Option 3: Docker Deployment (Local or Any VPS / DigitalOcean)

A complete production `Dockerfile` and `docker-compose.yml` are included in the workspace root.

### Using Docker Compose:
```bash
# 1. Create your .env file
echo "GROQ_API_KEY=gsk_your_key_here" > .env

# 2. Build and launch container in background
docker compose up -d --build

# 3. Check logs
docker compose logs -f
```
Open **`http://localhost:8000`** in your browser.

### Single Docker Command:
```bash
docker build -t truthlens:latest .
docker run -d -p 8000:8000 -e GROQ_API_KEY="gsk_your_key_here" --name truthlens truthlens:latest
```

---

## ☁️ Option 4: Deploying to Linux VPS (Ubuntu / Debian / AWS EC2)

```bash
# Clone and enter repo
git clone https://github.com/<your-username>/truthlens.git
cd truthlens

# Install system dependencies
sudo apt-get update && sudo apt-get install -y ffmpeg libsndfile1 python3-pip

# Install Python requirements
pip install -r requirements.txt

# Run with Gunicorn/Uvicorn background service or systemd
uvicorn server:app --host 0.0.0.0 --port 8000 --workers 2
```

---

## 🔐 Environment Variables Reference

| Variable | Description | Default |
| :--- | :--- | :--- |
| `GROQ_API_KEY` | Groq Cloud API Key (Required for Text & Vision) | None |
| `GROQ_TEXT_MODEL` | Text Model ID | `openai/gpt-oss-120b` |
| `GROQ_VISION_MODEL` | Vision Model ID | `qwen/qwen3.8-27b` |
| `LLM_PROVIDER` | Active LLM Provider | `groq` |
| `PORT` | Web Server Port | `8000` |
