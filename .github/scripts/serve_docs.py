"""
Local documentation server that mimics GitHub Pages' 404.html behaviour.

When a path is not found, walks up the directory tree looking for a 404.html
and serves it (with a 404 status) so JS-based redirects work locally the same
way they do on GitHub Pages.

Usage:
    python .github/scripts/serve_docs.py [port] [directory]
"""

import http.server
import os
import sys


class GHPagesHandler(http.server.SimpleHTTPRequestHandler):
    def send_error(self, code, message=None, explain=None):
        if code == 404:
            path = self.translate_path(self.path)
            root = os.getcwd()
            check = os.path.dirname(path)
            while True:
                candidate = os.path.join(check, "404.html")
                if os.path.exists(candidate):
                    with open(candidate, "rb") as f:
                        content = f.read()
                    self.send_response(404)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(content)))
                    self.end_headers()
                    self.wfile.write(content)
                    return
                if not check.startswith(root) or check == root:
                    break
                check = os.path.dirname(check)
        super().send_error(code, message, explain)

    def log_message(self, fmt, *args):
        pass  # suppress per-request noise


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    directory = sys.argv[2] if len(sys.argv) > 2 else os.getcwd()
    os.chdir(directory)
    http.server.test(HandlerClass=GHPagesHandler, port=port, bind="")
