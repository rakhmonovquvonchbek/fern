#!/usr/bin/env bash
# Fern installer — curl -fsSL https://getfern.app/install | bash
set -euo pipefail

FERN_HOME="${HOME}/.fern"
CREDENTIALS="${FERN_HOME}/credentials.json"

step_ok() { echo "✓ $1"; }
step_fail() { echo "✗ $1"; exit 1; }

echo "🌿 Fern installer"
echo ""

# Step 1: Python 3.10+
if ! command -v python3 &>/dev/null; then
  step_fail "Python 3 not found. Install from https://www.python.org/downloads/"
fi

PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
  step_fail "Python 3.10+ required (found $PY_VERSION). Install from https://www.python.org/downloads/"
fi
step_ok "Python $PY_VERSION found"

# Step 2: pip install
if ! python3 -m pip install --upgrade fern-audit 2>/dev/null; then
  echo "  pip install fern-audit failed — trying with --user"
  python3 -m pip install --user --upgrade fern-audit || step_fail "pip install failed. Try: python3 -m pip install fern-audit"
fi
step_ok "fern-audit installed"

# Step 3: Create ~/.fern
mkdir -p "${FERN_HOME}/output/drafts" "${FERN_HOME}/output/cache"
step_ok "Created ~/.fern"

# Step 4: Gmail credentials instructions
if [ ! -f "$CREDENTIALS" ]; then
  echo ""
  echo "Gmail OAuth setup (one-time):"
  echo "  1. https://console.cloud.google.com/ → New project"
  echo "  2. Enable Gmail API (APIs & Services → Library)"
  echo "  3. OAuth consent screen → External → add your email as test user"
  echo "  4. Credentials → OAuth Client ID → Desktop app → Download JSON"
  echo "  5. Save as: ${CREDENTIALS}"
  echo ""
  read -r -p "Press Enter once credentials.json is saved (or Ctrl+C to exit)... "
fi

if [ ! -f "$CREDENTIALS" ]; then
  step_fail "Missing ${CREDENTIALS}. Download OAuth JSON from Google Cloud Console."
fi
step_ok "Gmail credentials found"

# Step 5: fern setup
if ! command -v fern &>/dev/null; then
  export PATH="${HOME}/.local/bin:${PATH}"
fi
fern setup || step_fail "fern setup failed — check credentials and try again"
step_ok "Gmail connected"

# Step 6: First audit prompt
echo ""
read -r -p "Run your first audit now? [Y/n] " RUN_AUDIT
RUN_AUDIT=${RUN_AUDIT:-Y}
if [[ "$RUN_AUDIT" =~ ^[Yy]$ ]]; then
  fern audit && step_ok "First audit complete — run 'fern ui' to view results"
else
  echo "Run 'fern audit' whenever you're ready."
fi

echo ""
echo "🔒 Fern: Your data stays local. Never share ~/.fern/credentials.json or ~/.fern/token.json"
echo "✅ Done. Commands: fern audit | fern ui"
