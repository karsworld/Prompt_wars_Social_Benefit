# BridgeLink 🔗

> **Gemini-powered crisis reporting for the PromptWars Challenge.**
> Capture incidents via voice, image, or text — Gemini 1.5 Flash extracts priority, location, and category, then dispatches the right help.

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12 · FastAPI · Uvicorn |
| AI | Gemini 1.5 Flash (temp 0.2) |
| Frontend | Vanilla HTML/CSS/JS (zero frameworks) |
| Maps | Google Maps JavaScript API |
| Deploy | Docker → Google Cloud Run |
| Tests | pytest |

---

## Project Structure

```
AntiGravity/
├── app/
│   ├── main.py              # FastAPI entrypoint
│   ├── models/schemas.py    # Pydantic models
│   ├── routes/
│   │   ├── capture.py       # POST /api/capture
│   │   ├── confirm.py       # POST /api/confirm
│   │   ├── config.py        # GET  /api/config
│   │   └── health.py        # GET  /health
│   ├── services/
│   │   ├── gemini.py        # Gemini 1.5 Flash integration
│   │   └── sanitizer.py     # Input sanitization
│   └── static/              # SPA (index.html + CSS + JS)
├── tests/test_parsing.py
├── Dockerfile
├── .dockerignore
├── .env.example
└── requirements.txt
```

---

## Local Development

### 1. Set up environment

```bash
cd /Users/karuna/Documents/Projects/AntiGravity
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure secrets

```bash
cp .env.example .env
# Edit .env and set:
#   GEMINI_API_KEY=...
#   GOOGLE_MAPS_API_KEY=...
```

### 3. Run the app

```bash
uvicorn app.main:app --reload --port 8080
# Open http://localhost:8080
```

### 4. Run tests

```bash
pytest tests/ -v
```

---

## Cloud Run Deployment

### One-time setup

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com containerregistry.googleapis.com
```

### Build & Deploy

```bash
# Build and push image
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/bridgelink .

# Deploy to Cloud Run
gcloud run deploy bridgelink \
  --image gcr.io/YOUR_PROJECT_ID/bridgelink \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "GEMINI_API_KEY=your_key_here,GOOGLE_MAPS_API_KEY=your_maps_key_here"
```

### Subsequent deploys

```bash
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/bridgelink . && \
gcloud run deploy bridgelink --image gcr.io/YOUR_PROJECT_ID/bridgelink --region us-central1
```

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GEMINI_API_KEY` | ✅ | Google AI Studio key |
| `GOOGLE_MAPS_API_KEY` | ✅ | Maps JS API key (restrict to your domain) |
| `PORT` | Auto | Set by Cloud Run (default: 8080) |

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/capture` | Analyze incident (multipart/form-data) |
| `POST` | `/api/confirm` | Dispatch confirmed card (JSON) |
| `GET` | `/api/config` | Returns maps key for frontend |
| `GET` | `/health` | Readiness probe |
| `GET` | `/docs` | Swagger UI |

---

## Security Notes

- All text inputs are HTML-sanitized and truncated to 2,000 chars
- Image MIME type and integrity are validated server-side before sending to Gemini
- No API keys are hardcoded — all via environment variables
- Docker container runs as a non-root user
- Restrict your Maps API key to your Cloud Run domain in Google Cloud Console

---

## Accessibility

- WCAG AAA color contrast throughout
- Full ARIA labels on all interactive elements
- Keyboard-navigable tabs and buttons
- `aria-live` regions for dynamic content updates
- Screen-reader friendly priority badge announcements
