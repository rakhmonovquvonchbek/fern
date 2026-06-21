#!/usr/bin/env bash
set -euo pipefail

PROJECT="${GCP_PROJECT:-probable-anchor-423716-h7}"
SERVICE="fern-api"
REGION="${GCP_REGION:-us-central1}"

echo "Deploying $SERVICE to Cloud Run (project: $PROJECT)..."

gcloud config set project "$PROJECT"

# Enable required APIs
gcloud services enable run.googleapis.com firestore.googleapis.com secretmanager.googleapis.com

# Create Firestore database if needed (Native mode)
if ! gcloud firestore databases describe --database="(default)" &>/dev/null; then
  gcloud firestore databases create --location="$REGION" --type=firestore-native
fi

gcloud run deploy "$SERVICE" \
  --source . \
  --region "$REGION" \
  --allow-unauthenticated \
  --set-env-vars "GCP_PROJECT=$PROJECT" \
  --set-secrets "ANTHROPIC_API_KEY=fern-anthropic-key:latest" \
  --memory 512Mi \
  --timeout 120

URL=$(gcloud run services describe "$SERVICE" --region "$REGION" --format='value(status.url)')
echo ""
echo "Deployed: $URL"
echo "Add to ~/.fern/config.json: \"api_url\": \"$URL\""
