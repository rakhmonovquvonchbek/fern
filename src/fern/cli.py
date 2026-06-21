from __future__ import annotations

import argparse
import sys

from fern.banner import SECURITY_MSG
from fern.config import DEFAULT_MONTHS, REPORT_PATH, ensure_fern_home, ensure_output_dirs
from fern.dedupe import dedupe_records
from fern.drafts import write_drafts
from fern.extractor.api_client import FreeLimitReached, extract_all_routed
from fern.extractor.claude import load_all_cached_records
from fern.gmail.client import create_client
from fern.gmail.search import build_search_queries, fetch_parsed_emails, list_merged_message_ids
from fern.migrate import migrate_legacy_config
from fern.report import write_report
from fern.settings import increment_audit_count
from fern.telemetry import ask_telemetry_opt_in, send_ping
from fern.ui.server import DEFAULT_UI_PORT, run_ui


def _bootstrap() -> None:
    ensure_fern_home()
    migrate_legacy_config()


def _print_credentials_help() -> None:
    print(
        "\nGmail OAuth setup (one-time):\n"
        "  1. Go to https://console.cloud.google.com/ → create a project\n"
        "  2. Enable Gmail API: APIs & Services → Library → Gmail API\n"
        "  3. OAuth consent screen → External → add your email as test user\n"
        "  4. Credentials → Create OAuth Client ID → Desktop app → Download JSON\n"
        "  5. Save as ~/.fern/credentials.json\n"
    )


def cmd_setup(args: argparse.Namespace) -> int:
    from fern.config import CREDENTIALS_PATH

    _bootstrap()
    if not CREDENTIALS_PATH.exists():
        print("Missing ~/.fern/credentials.json")
        _print_credentials_help()
        return 1

    print("Connecting to Gmail...")
    service = create_client()
    emails = list(fetch_parsed_emails(service, limit=1))
    if not emails:
        print("Connected, but no subscription emails found yet.")
    else:
        email = emails[0]
        print(f"✓ Gmail connected — sample: [{email.date}] {email.subject}")

    ask_telemetry_opt_in()
    print("\n✅ Fern is ready. Run `fern audit` to scan your inbox.")
    return 0


def cmd_gmail_test(args: argparse.Namespace) -> int:
    print("Connecting to Gmail...")
    service = create_client()
    queries = build_search_queries(months=args.months)
    print("Running 4 search queries (merged by message ID):")
    for index, query in enumerate(queries, start=1):
        print(f"  {index}. {query}")
    print()

    message_ids = list_merged_message_ids(service, months=args.months, limit=args.limit)
    print(f"Found {len(message_ids)} unique message(s).\n")

    count = 0
    for email in fetch_parsed_emails(
        service, months=args.months, limit=args.limit, message_ids=message_ids
    ):
        count += 1
        print(f"[{email.date}] {email.sender}")
        print(f"Subject: {email.subject}")
        print(f"Preview: {email.preview}")
        print("---")

    if count == 0:
        print("No subscription-related emails found.")
        return 1

    print(f"\nShowing {count} email(s).")
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    ensure_output_dirs()

    records = []
    if args.skip_extract:
        records = load_all_cached_records()
        if not records:
            print("No cached extractions in ~/.fern/output/cache/. Run audit without --skip-extract first.")
            return 1
        print(f"Loaded {len(records)} cached record(s).")
    else:
        print("Connecting to Gmail...")
        service = create_client()
        if args.verbose:
            for index, query in enumerate(build_search_queries(months=args.months), start=1):
                print(f"  Query {index}: {query}")
        emails = list(fetch_parsed_emails(service, months=args.months, limit=args.limit))
        print(f"Found {len(emails)} unique email(s) to analyze.")

        if not emails:
            print("No subscription-related emails found.")
            return 1

        try:
            records = extract_all_routed(
                emails, use_cache=not args.no_cache, verbose=args.verbose
            )
        except FreeLimitReached as exc:
            print(f"\n{exc}", file=sys.stderr)
            print(SECURITY_MSG, file=sys.stderr)
            return 1

        print(f"Extracted {len(records)} record(s) from emails.")

    deduped = dedupe_records(records)
    print(f"Deduplicated to {len(deduped)} service(s).")

    write_report(deduped, REPORT_PATH)
    print(f"Report written to {REPORT_PATH}")

    draft_paths = write_drafts(deduped)
    print(f"Wrote {len(draft_paths)} cancellation draft(s) to ~/.fern/output/drafts/")

    if not args.skip_extract:
        increment_audit_count()
        send_ping()

    return 0


def cmd_ui(args: argparse.Namespace) -> int:
    run_ui(port=args.port, open_browser=not args.no_browser)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fern",
        description="Fern — privacy-first subscription auditor",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    setup = subparsers.add_parser("setup", help="Configure Gmail OAuth and verify connection")
    setup.set_defaults(func=cmd_setup)

    gmail_test = subparsers.add_parser(
        "gmail-test",
        help="Connect to Gmail and print subscription-related emails",
    )
    gmail_test.add_argument("--months", type=int, default=DEFAULT_MONTHS)
    gmail_test.add_argument("--limit", type=int, default=10)
    gmail_test.set_defaults(func=cmd_gmail_test)

    audit = subparsers.add_parser("audit", help="Run full subscription audit")
    audit.add_argument("--months", type=int, default=DEFAULT_MONTHS)
    audit.add_argument("--limit", type=int, default=None)
    audit.add_argument("--skip-extract", action="store_true")
    audit.add_argument("--no-cache", action="store_true")
    audit.add_argument("--verbose", action="store_true")
    audit.set_defaults(func=cmd_audit)

    ui = subparsers.add_parser("ui", help="Launch local web UI")
    ui.add_argument("--port", type=int, default=DEFAULT_UI_PORT)
    ui.add_argument("--no-browser", action="store_true")
    ui.set_defaults(func=cmd_ui)

    return parser


def main(argv: list[str] | None = None) -> None:
    _bootstrap()
    print(SECURITY_MSG)
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        code = args.func(args)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        code = 1
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        code = 1
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        code = 130
    sys.exit(code)


if __name__ == "__main__":
    main()
