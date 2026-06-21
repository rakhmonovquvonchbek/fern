from __future__ import annotations

import subprocess
import threading
import webbrowser
from pathlib import Path

from flask import Flask, jsonify, render_template

from fern.config import REPORT_PATH
from fern.ui.parser import audit_to_dict, parse_report

TEMPLATE_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"

_audit_lock = threading.Lock()
_audit_state = {"running": False, "error": None}


def create_app() -> Flask:
    app = Flask(__name__, template_folder=str(TEMPLATE_DIR), static_folder=str(STATIC_DIR))

    @app.route("/")
    def index():
        data = parse_report()
        has_report = REPORT_PATH.exists()
        return render_template("index.html", data=data, has_report=has_report)

    @app.route("/api/report")
    def api_report():
        data = parse_report()
        return jsonify(audit_to_dict(data))

    @app.route("/api/audit/run", methods=["POST"])
    def api_audit_run():
        with _audit_lock:
            if _audit_state["running"]:
                return jsonify({"ok": False, "error": "Audit already running"}), 409
            _audit_state["running"] = True
            _audit_state["error"] = None

        def run():
            try:
                result = subprocess.run(
                    ["fern", "audit"],
                    capture_output=True,
                    text=True,
                    timeout=600,
                )
                if result.returncode != 0:
                    with _audit_lock:
                        _audit_state["error"] = result.stderr or result.stdout or "Audit failed"
            except Exception as exc:
                with _audit_lock:
                    _audit_state["error"] = str(exc)
            finally:
                with _audit_lock:
                    _audit_state["running"] = False

        threading.Thread(target=run, daemon=True).start()
        return jsonify({"ok": True})

    @app.route("/api/audit/status")
    def api_audit_status():
        with _audit_lock:
            return jsonify({"running": _audit_state["running"], "error": _audit_state["error"]})

    return app


DEFAULT_UI_PORT = 5050


def run_ui(*, port: int = DEFAULT_UI_PORT, open_browser: bool = True) -> None:
    app = create_app()
    url = f"http://127.0.0.1:{port}"

    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    print(f"Fern UI running at {url}")
    print("Press Ctrl+C to stop.")
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
