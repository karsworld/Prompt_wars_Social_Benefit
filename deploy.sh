#!/usr/bin/env bash
# ============================================================
# BridgeLink — Full Google Cloud Run deployment script
# Usage: bash deploy.sh YOUR_PROJECT_ID
# ============================================================
set -euo pipefail

# ── Config ────────────────────────────────────────────────────
PROJECT_ID="${1:?Usage: bash deploy.sh YOUR_PROJECT_ID}"
REGION="us-central1"
SERVICE="bridgelink"
REPO="bridgelink-repo"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/${SERVICE}"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   BridgeLink → Cloud Run Deployer        ║"
echo "║   Project : ${PROJECT_ID}                "
echo "║   Region  : ${REGION}                    "
echo "╚══════════════════════════════════════════╝"
echo ""

# ── 1. Set project ─────────────────────────────────────────────
echo "▶ Setting active project..."
gcloud config set project "${PROJECT_ID}" --quiet

# ── 2. Enable required APIs ───────────────────────────────────
echo "▶ Enabling GCP APIs (this takes ~60s on first run)..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  --quiet

# ── 3. Create Artifact Registry repo (idempotent) ─────────────
echo "▶ Creating Artifact Registry repository..."
gcloud artifacts repositories create "${REPO}" \
  --repository-format=docker \
  --location="${REGION}" \
  --description="BridgeLink container images" \
  --quiet 2>/dev/null || echo "   (repo already exists — skipping)"

# ── 4. Configure Docker auth ──────────────────────────────────
echo "▶ Configuring Docker to authenticate with Artifact Registry..."
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

# ── 5. Store secrets in Secret Manager ───────────────────────
echo ""
echo "▶ Setting up Secret Manager secrets..."
echo "  You'll be prompted for your API keys."
echo ""

store_secret() {
  local NAME="$1"
  local PROMPT="$2"
  # Check if secret already exists
  if gcloud secrets describe "${NAME}" --project="${PROJECT_ID}" &>/dev/null; then
    read -r -p "  Secret '${NAME}' exists. Update it? [y/N] " UPDATE
    if [[ "${UPDATE,,}" == "y" ]]; then
      printf '%s' "$(read -r -s -p "  ${PROMPT}: " VAL; echo "${VAL}")" \
        | gcloud secrets versions add "${NAME}" --data-file=- --quiet
      echo ""
    fi
  else
    gcloud secrets create "${NAME}" \
      --replication-policy="automatic" \
      --quiet
    printf '%s' "$(read -r -s -p "  ${PROMPT}: " VAL; echo "${VAL}")" \
      | gcloud secrets versions add "${NAME}" --data-file=- --quiet
    echo ""
  fi
}

store_secret "GEMINI_API_KEY"       "Enter your Gemini API key"
store_secret "GOOGLE_MAPS_API_KEY"  "Enter your Google Maps API key"

# Grant Cloud Run SA access to secrets
echo "▶ Granting Cloud Run access to secrets..."
PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format="value(projectNumber)")
CR_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

for SECRET in GEMINI_API_KEY GOOGLE_MAPS_API_KEY; do
  gcloud secrets add-iam-policy-binding "${SECRET}" \
    --member="serviceAccount:${CR_SA}" \
    --role="roles/secretmanager.secretAccessor" \
    --quiet 2>/dev/null || true
done

# Also grant Cloud Build SA access
CB_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${CB_SA}" \
  --role="roles/run.admin" --quiet
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${CB_SA}" \
  --role="roles/iam.serviceAccountUser" --quiet

# ── 6. Build & push image ────────────────────────────────────
echo ""
echo "▶ Building Docker image..."
TAG=$(git rev-parse --short HEAD 2>/dev/null || echo "latest")
docker build -t "${IMAGE}:${TAG}" -t "${IMAGE}:latest" .

echo "▶ Pushing image to Artifact Registry..."
docker push "${IMAGE}:${TAG}"
docker push "${IMAGE}:latest"

# ── 7. Deploy to Cloud Run ────────────────────────────────────
echo ""
echo "▶ Deploying to Cloud Run..."
gcloud run deploy "${SERVICE}" \
  --image "${IMAGE}:${TAG}" \
  --region "${REGION}" \
  --platform managed \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --concurrency 80 \
  --min-instances 0 \
  --max-instances 5 \
  --set-secrets "GEMINI_API_KEY=GEMINI_API_KEY:latest,GOOGLE_MAPS_API_KEY=GOOGLE_MAPS_API_KEY:latest" \
  --quiet

# ── 8. Get service URL & smoke test ──────────────────────────
SERVICE_URL=$(gcloud run services describe "${SERVICE}" \
  --region="${REGION}" \
  --format="value(status.url)")

echo ""
echo "▶ Running smoke tests against ${SERVICE_URL}..."
echo ""

# Health check
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${SERVICE_URL}/health")
if [[ "${HTTP_STATUS}" == "200" ]]; then
  echo "  ✅ /health → 200 OK"
else
  echo "  ❌ /health → ${HTTP_STATUS} (expected 200)"
fi

# Config endpoint
CFG_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${SERVICE_URL}/api/config")
if [[ "${CFG_STATUS}" == "200" ]]; then
  echo "  ✅ /api/config → 200 OK"
else
  echo "  ❌ /api/config → ${CFG_STATUS}"
fi

# Root SPA
SPA_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${SERVICE_URL}/")
if [[ "${SPA_STATUS}" == "200" ]]; then
  echo "  ✅ / (SPA) → 200 OK"
else
  echo "  ❌ / (SPA) → ${SPA_STATUS}"
fi

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   🚀 BridgeLink is LIVE!                 ║"
echo "║   URL: ${SERVICE_URL}"
echo "╚══════════════════════════════════════════╝"
echo ""
