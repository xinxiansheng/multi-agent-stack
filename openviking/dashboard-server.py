#!/usr/bin/env python3
"""
OpenViking Dashboard Server
============================
Lightweight HTTP dashboard for Observer knowledge cards and search.
Accessible via Tailscale from any device.

Endpoints:
  /           Observer Knowledge Cards dashboard
  /brain      Second Brain interface
  /refresh    Force rebuild dashboard
  /api/search Semantic search via OpenViking
  /api/add    Add memos to knowledge base
"""

import http.server
import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse, parse_qs

PORT = int(os.environ.get("OPENVIKING_DASHBOARD_PORT", "2034"))
OV_PROJECT = Path(os.environ.get(
    "OV_PROJECT", os.path.expanduser("~/projects/openviking-local")))
OV_MCP = os.environ.get("OPENVIKING_MCP_URL", "http://localhost:2033/mcp")

BUILD_SCRIPT = OV_PROJECT / "build-dashboard.py"
HTML_FILE = OV_PROJECT / "dashboard.html"
BRAIN_FILE = OV_PROJECT / "brain.html"
MEMO_DIR = OV_PROJECT / "memos"

# Use venv python if available, else system python
VENV_PYTHON = OV_PROJECT / ".venv" / "bin" / "python3"
PYTHON = str(VENV_PYTHON) if VENV_PYTHON.exists() else "python3"

_last_build = 0


def ensure_fresh():
    global _last_build
    now = time.time()
    if now - _last_build > 300 or not HTML_FILE.exists():
        if BUILD_SCRIPT.exists():
            subprocess.run(
                [PYTHON, str(BUILD_SCRIPT)],
                capture_output=True, timeout=120)
        _last_build = now


def call_openviking(tool_name: str, arguments: dict) -> dict:
    payload = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments},
    }).encode()
    req = urllib.request.Request(
        OV_MCP, data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path in ("/", "/index.html"):
            ensure_fresh()
            self._serve_file(HTML_FILE)

        elif parsed.path == "/brain":
            self._serve_file(BRAIN_FILE)

        elif parsed.path == "/refresh":
            global _last_build
            _last_build = 0
            ensure_fresh()
            self.send_response(302)
            self.send_header("Location", "/")
            self.end_headers()

        elif parsed.path == "/api/search":
            params = parse_qs(parsed.query)
            query = params.get("q", [""])[0]
            if not query:
                self._json_response({"error": "missing q param"}, 400)
                return
            try:
                result = call_openviking(
                    "search", {"query": query, "top_k": 20})
                self._json_response(result.get("result", {}))
            except Exception as e:
                self._json_response({"error": str(e)}, 500)

        elif parsed.path == "/api/smart_search":
            params = parse_qs(parsed.query)
            query = params.get("q", [""])[0]
            if not query:
                self._json_response({"error": "missing q param"}, 400)
                return
            try:
                result = call_openviking(
                    "smart_search", {"query": query})
                self._json_response(result.get("result", {}))
            except Exception as e:
                self._json_response({"error": str(e)}, 500)

        else:
            self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/add":
            content_length = int(self.headers.get("Content-Length", 0))
            body = (json.loads(self.rfile.read(content_length))
                    if content_length else {})
            text = body.get("text", "")
            source = body.get("source", "second-brain")
            if not text:
                self._json_response({"error": "missing text"}, 400)
                return
            try:
                MEMO_DIR.mkdir(exist_ok=True)
                ts = int(time.time())
                memo_file = MEMO_DIR / f"{source}-{ts}.md"
                memo_file.write_text(
                    f"# Memo ({source})\n\n{text}\n", encoding="utf-8")
                result = call_openviking(
                    "add_resource", {"resource_path": str(memo_file)})
                self._json_response(result.get("result", {}))
            except Exception as e:
                self._json_response({"error": str(e)}, 500)
        else:
            self.send_error(404)

    def _serve_file(self, filepath):
        if filepath.exists():
            content = filepath.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", len(content))
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_error(404, f"{filepath.name} not found")

    def _json_response(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


if __name__ == "__main__":
    server = http.server.HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Dashboard server on http://0.0.0.0:{PORT}/")
    print(f"  Observer Cards: http://localhost:{PORT}/")
    print(f"  Second Brain:   http://localhost:{PORT}/brain")
    server.serve_forever()
