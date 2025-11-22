"""Desktop launcher for the Coastal Waves inventory dashboard.

Starts the FastAPI backend in a background thread and opens the
existing static dashboard inside a desktop window using pywebview.
"""
from __future__ import annotations

import os
import socket
import sys
import threading
import time
from pathlib import Path

import uvicorn
try:
    import webview
except ImportError as exc:  # pragma: no cover - runtime dependency guard
    webview = None
    _webview_import_error = exc
else:
    _webview_import_error = None

REPO_ROOT = Path(__file__).resolve().parent
BACKEND_MODULE = "app.main:app"
API_HOST = "127.0.0.1"
API_PORT = 8000

# Ensure the backend package is importable when running from the repo root or a bundled exe.
sys.path.append(str(REPO_ROOT / "backend"))


def _api_is_reachable(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((host, port)) == 0


def _run_api():
    uvicorn.run(
        BACKEND_MODULE,
        host=API_HOST,
        port=API_PORT,
        reload=False,
        log_level="info",
    )


def _wait_for_api(timeout: float = 10.0) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        if _api_is_reachable(API_HOST, API_PORT):
            return True
        time.sleep(0.2)
    return False


def main():
    os.chdir(REPO_ROOT)
    api_thread = threading.Thread(target=_run_api, daemon=True)
    api_thread.start()

    if not _wait_for_api():
        raise RuntimeError("Backend failed to start on port 8000")

    if webview is None:
        raise ModuleNotFoundError(
            "pywebview is required for the desktop shell. Install dependencies with "
            "`pip install -r requirements-desktop.txt`."
        ) from _webview_import_error

    webview.create_window(
        "Coastal Waves Inventory",
        url=f"http://{API_HOST}:{API_PORT}/app/",
        width=1200,
        height=800,
    )
    webview.start()


if __name__ == "__main__":
    main()
