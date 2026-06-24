"""
serve_frontend.py – Serves the frontend on port 5500 (or any port).
This is a pure static file server and does NOT modify the backend.

Run with:  python serve_frontend.py
Then open: http://localhost:5500
"""
import http.server
import socketserver
import os

PORT = 5500
DIRECTORY = os.path.join(os.path.dirname(__file__), "frontend")

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)
    def log_message(self, format, *args):
        print(f"  [{self.address_string()}] {format % args}")

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"\n🌐  Frontend running at → http://localhost:{PORT}")
        print(f"📡  Make sure backend is running at → http://localhost:8000")
        print(f"🛑  Press Ctrl+C to stop\n")
        httpd.serve_forever()
