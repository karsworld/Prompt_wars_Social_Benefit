# BridgeLink 🔗 — Gemini 2.5 Disaster Response

> **Next-gen AI triage for the PromptWars Challenge.**
> Capture incidents via voice, image, or text. BridgeLink uses **Gemini 2.5 Flash** to extract high-fidelity JSON data, visualize incidents on Google Maps, and archive reports to Google Cloud Storage for permanent record-keeping.

---

## ✨ Features

- 🎙️ **Multimodal Input**: Supports text reports, real-time photos, and audio recordings.
- 🧠 **AI Triage**: Powered by the latest `google-genai` SDK and `gemini-2.5-flash`.
- 🗺️ **Interactive Mapping**: Instant visualization of incident locations via Google Maps JS API.
- 📂 **Cloud Archival**: Automatic JSON archival to Google Cloud Storage (GCS) upon dispatch confirmation.
- 🚀 **One-Click Deploy**: Production-ready deployment script for Google Cloud Run with Secret Manager integration.

---

## 🏗️ Architecture

| Layer | Technology |
|---|---|
| **Backend** | Python 3.12 · FastAPI · Uvicorn |
| **AI Engine** | Gemini 2.5 Flash · Google GenAI SDK |
| **Storage** | Google Cloud Storage (JSON Archival) |
| **Frontend** | Vanilla HTML/CSS/JS (Glassmorphic Design) |
| **Maps** | Google Maps JavaScript API |
| **Production** | Google Cloud Run · Artifact Registry · Secret Manager |

---

## 🛠️ Local Development

### 1. Requirements
- Python 3.12+
- A Google Cloud Project with Billing enabled.

### 2. Setup Environment
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure Secrets
Copy `.env.example` to `.env` and fill in your keys:
```bash
cp .env.example .env
```
- **Gemini API Key**: Get it from [Google AI Studio](https://aistudio.google.com/).
- **Maps API Key**: Get it from [Google Cloud Console](https://console.cloud.google.com/google/maps-apis/).

### 4. Optional: Local Cloud Storage (GCS)
To test archival locally without `gcloud` installed:
1. Create a Service Account in GCP and grant it the **Storage Object Admin** role.
2. Download the JSON key file and save it as `gcp-key.json` in the root folder.
3. Set `GOOGLE_APPLICATION_CREDENTIALS` in your `.env` to the absolute path of that file.

### 5. Run the App
```bash
uvicorn app.main:app --reload --port 8080
```
Open [http://localhost:8080](http://localhost:8080) in your browser.

---

## 🚀 Deployment

BridgeLink includes a robust deployment script that handles API enablement, Secret Manager setup, and Cloud Run deployment.

```bash
chmod +x deploy.sh
./deploy.sh YOUR_PROJECT_ID
```

---

## 🆘 Troubleshooting

### 📍 Google Maps: "Oops! Something went wrong"
If the map doesn't load and you see `ApiNotActivatedMapError` in the console:
1. Go to the [Google Maps JavaScript API Library](https://console.cloud.google.com/google/maps-apis/api/maps-backend.googleapis.com/overview).
2. Click **ENABLE**.
3. Wait ~30 seconds and refresh your app.

### 💎 Gemini: 404 Not Found
If the AI fails to analyze, ensure you are using a valid model. BridgeLink defaults to `models/gemini-2.5-flash`. Check your [AI Studio](https://aistudio.google.com/) for available models.

---

## 🛡️ Security & Performance
- **Zero-Trust Secrets**: `.gitignore` prevents `.env` and `*.json` keys from entering version control.
- **Input Sanitization**: All user inputs are cleaned and truncated before AI processing.
- **Production Performance**: Cloud Run generates a lightweight Docker image optimized for concurrency.
