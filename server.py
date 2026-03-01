#!/usr/bin/env python3
"""
Lightweight HTTP server for the Auto Trading Analyzer PWA.
Runs in the background and serves the static frontend.

Usage:
    python3 server.py          # start server (background) and open browser
    python3 server.py --stop   # stop the background server
    python3 server.py --status # check if server is running
"""

import http.server
import os
import sys
import signal
import socket
import webbrowser
import json
from pathlib import Path

DEFAULT_PORT = 8000
APP_DIR = Path(__file__).resolve().parent
PID_FILE = APP_DIR / ".server.pid"


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    """Serves files from APP_DIR with proper MIME types and no noisy logs."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(APP_DIR), **kwargs)

    def log_message(self, format, *args):
        pass  # suppress request logs

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, must-revalidate")
        self.send_header("Access-Control-Allow-Origin", "*")
        if self.path.endswith(".json"):
            self.send_header("Content-Type", "application/json")
        if self.path.endswith(".js"):
            self.send_header("Content-Type", "application/javascript")
        super().end_headers()


def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def find_free_port():
    """Find a free port starting from DEFAULT_PORT."""
    for port in range(DEFAULT_PORT, DEFAULT_PORT + 100):
        if not is_port_in_use(port):
            return port
    return None


def read_pid_file():
    """Read PID and port from the pid file. Returns (pid, port) or (None, None)."""
    if PID_FILE.exists():
        try:
            data = json.loads(PID_FILE.read_text())
            pid = data["pid"]
            port = data["port"]
            os.kill(pid, 0)  # check if process exists
            return pid, port
        except (ValueError, KeyError, json.JSONDecodeError, ProcessLookupError, PermissionError):
            PID_FILE.unlink(missing_ok=True)
    return None, None


def write_pid_file(pid, port):
    PID_FILE.write_text(json.dumps({"pid": pid, "port": port}))


def stop_server():
    pid, port = read_pid_file()
    if pid:
        os.kill(pid, signal.SIGTERM)
        PID_FILE.unlink(missing_ok=True)
        print(f"Server stopped (PID {pid}, was on port {port})")
    else:
        print("Server is not running")


def show_status():
    pid, port = read_pid_file()
    if pid:
        print(f"Server is running (PID {pid}) at http://localhost:{port}")
    else:
        print("Server is not running")


def start_server():
    pid, port = read_pid_file()
    if pid:
        print(f"Server already running (PID {pid}) at http://localhost:{port}")
        webbrowser.open(f"http://localhost:{port}")
        return

    port = find_free_port()
    if port is None:
        print("Error: no free port found in range 8000-8099")
        sys.exit(1)

    # Fork to background (Unix/macOS)
    if sys.platform != "win32":
        child_pid = os.fork()
        if child_pid > 0:
            # Parent: save PID, open browser, exit
            write_pid_file(child_pid, port)
            print(f"Server started (PID {child_pid}) at http://localhost:{port}")
            webbrowser.open(f"http://localhost:{port}")
            return
        else:
            # Child: detach and run server
            os.setsid()
            devnull = os.open(os.devnull, os.O_RDWR)
            os.dup2(devnull, 0)
            os.dup2(devnull, 1)
            os.dup2(devnull, 2)
            server = http.server.HTTPServer(("0.0.0.0", port), QuietHandler)
            server.serve_forever()
    else:
        # Windows: use subprocess to run in background
        import subprocess
        proc = subprocess.Popen(
            [sys.executable, __file__, "--serve", str(port)],
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        write_pid_file(proc.pid, port)
        print(f"Server started (PID {proc.pid}) at http://localhost:{port}")
        webbrowser.open(f"http://localhost:{port}")


def serve_foreground(port=None):
    """Run server in foreground (used by --serve and Launch Agent)."""
    if port is None:
        port = find_free_port() or DEFAULT_PORT
    write_pid_file(os.getpid(), port)
    print(f"Serving on http://localhost:{port}")
    server = http.server.HTTPServer(("0.0.0.0", port), QuietHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        PID_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    if "--stop" in sys.argv:
        stop_server()
    elif "--status" in sys.argv:
        show_status()
    elif "--serve" in sys.argv:
        # Optional port argument after --serve
        idx = sys.argv.index("--serve")
        port = int(sys.argv[idx + 1]) if len(sys.argv) > idx + 1 else None
        serve_foreground(port)
    else:
        start_server()
