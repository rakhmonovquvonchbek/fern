# Fern

> Built with [Cursor](https://cursor.com) for the Cursor Hackathon.

**Privacy-first subscription auditor.** Find forgotten free trials and subscriptions by reading Gmail — not your bank account.

10 of 14 subscription trackers (Rocket Money, Trim, Hiatus) require bank linking and expose your full transaction history. Fern reads only subscription-related emails and stays entirely local on your machine.

> 🔒 **Your data stays local.** Never share `~/.fern/credentials.json` or `~/.fern/token.json`.

## Why Fern

- **No bank access** — competitors require linking your bank account
- **Global** — works anywhere Gmail works (not US-only)
- **Trial-focused** — catches free trials converting to paid that others miss
- **Local-first** — credentials, tokens, and reports live in `~/.fern/` on your machine

## Install

### One command

```bash
curl -fsSL https://getfern.app/install | bash
```

### Or via pip

```bash
pip install fern-audit
mkdir -p ~/.fern
```

Then follow Gmail OAuth setup (see below) and run `fern setup`.

## Gmail OAuth setup

1. [Google Cloud Console](https://console.cloud.google.com/) → New project
2. Enable **Gmail API**
3. OAuth consent screen → External → add your email as test user
4. Credentials → OAuth Client ID → **Desktop app** → Download JSON
5. Save as `~/.fern/credentials.json`

## Usage

```bash
fern setup       # Connect Gmail (one-time)
fern audit       # Scan inbox, write report + cancellation drafts
fern ui          # Open local dashboard at http://127.0.0.1:5050
fern gmail-test  # Print first 10 subscription emails
```

## Output

All output goes to `~/.fern/`:

```
~/.fern/
├── credentials.json    # Your Gmail OAuth client (you provide)
├── token.json          # Cached OAuth token (auto-generated)
├── config.json         # install_id, settings, api_url
├── .env                # Optional ANTHROPIC_API_KEY
└── output/
    ├── report.md
    ├── drafts/
    └── cache/
```

## Free tier vs unlimited

- **Free:** 3 lifetime audits via Fern's shared API (no Anthropic key needed)
- **Unlimited:** Add your own key to `~/.fern/.env`:

```bash
ANTHROPIC_API_KEY=sk-ant-...
```

Get a free key at [console.anthropic.com](https://console.anthropic.com).

## Privacy & telemetry

On first run, Fern asks (opt-in, default **No**):

> Can Fern send anonymous usage stats (audit count, OS)? No personal data ever.

If enabled, only `{install_id, os, audit_count}` is sent — never email content or service names.

## Development

```bash
git clone ... && cd fern
python -m venv .venv && source .venv/bin/activate
pip install -e .
fern audit
```

See [PUBLISHING.md](PUBLISHING.md) for PyPI release steps.

## License

MIT
