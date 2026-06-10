#!/usr/bin/env python3
"""
Local server + Claude API proxy for the RFP Response Assistant.

Usage:
  1. Put this file in the same folder as rfp-response-assistant.html
  2. Run:   ANTHROPIC_API_KEY=sk-ant-your-key python3 serve.py
     (Windows PowerShell:  $env:ANTHROPIC_API_KEY="sk-ant-your-key"; python serve.py)
  3. Open:  http://localhost:8000/rfp-response-assistant.html

The page calls /api/messages on this server; the server adds your API key and
forwards the request to api.anthropic.com. The key never touches the browser,
and there are no CORS / file:// / ad-blocker issues. Leave the API key field
in the app's AI settings empty when using this.
"""
import os
import sys
import json
import urllib.request
import urllib.error
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = int(os.environ.get("PORT", "8000"))
API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
API_URL = "https://api.anthropic.com/v1/messages"


class Handler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/api/messages":
            self.send_error(404, "Not found")
            return
        if not API_KEY:
            self._send_json(500, {"error": {"type": "config_error",
                "message": "ANTHROPIC_API_KEY is not set. Restart serve.py with the key in your environment."}})
            return
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        req = urllib.request.Request(API_URL, data=body, headers={
            "Content-Type": "application/json",
            "x-api-key": API_KEY,
            "anthropic-version": "2023-06-01",
        })
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data, code = r.read(), r.status
        except urllib.error.HTTPError as e:
            data, code = e.read(), e.code
        except Exception as e:
            self._send_json(502, {"error": {"type": "proxy_error", "message": str(e)}})
            return
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, code, obj):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        sys.stderr.write("[serve.py] %s\n" % (fmt % args))


if __name__ == "__main__":
    if not API_KEY:
        print("WARNING: ANTHROPIC_API_KEY is not set — the page will load, but AI calls will fail.")
        print('Run:  ANTHROPIC_API_KEY=sk-ant-your-key python3 serve.py')
    print(f"Serving on http://localhost:{PORT}")
    print(f"Open:  http://localhost:{PORT}/rfp-response-assistant.html")
    HTTPServer(("localhost", PORT), Handler).serve_forever()
