from __future__ import annotations

import csv
import json
import mimetypes
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse


PROJECT_ROOT = Path(__file__).resolve().parent.parent
UI_DIR = PROJECT_ROOT / "ui"
INPUT_DIR = PROJECT_ROOT / "input"
DOCS_DIR = PROJECT_ROOT / "docs"
APP_VERSION = "0.20"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def json_bytes(payload: dict | list) -> bytes:
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def safe_child(base_dir: Path, relative_path: str) -> Path | None:
    candidate = (base_dir / unquote(relative_path).lstrip("/")).resolve()
    try:
        candidate.relative_to(base_dir.resolve())
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


class PVSelectorHandler(BaseHTTPRequestHandler):
    server_version = "PVSelectorBackend/0.20"

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in {"", "/"}:
            self.send_file(UI_DIR / "dimensionnement_solaire.html", "text/html; charset=utf-8")
            return
        if path == "/health":
            self.send_json({"status": "ok", "version": APP_VERSION})
            return
        if path == "/api/catalog/panels":
            self.send_json(read_csv(INPUT_DIR / "panneaux.csv"))
            return
        if path == "/api/catalog/inverters":
            self.send_json(read_csv(INPUT_DIR / "onduleurs.csv"))
            return
        if path == "/api/catalog/summary":
            db_path = INPUT_DIR / "catalogue_fabricants_db.json"
            db = json.loads(db_path.read_text(encoding="utf-8-sig"))
            self.send_json(
                {
                    "schema_version": db.get("schema_version"),
                    "manufacturers": len(db.get("manufacturers", [])),
                    "panels": len(db.get("panels", [])),
                    "inverters": len(db.get("inverters", [])),
                }
            )
            return
        if path == "/input/panneaux.csv":
            self.send_file(INPUT_DIR / "panneaux.csv", "text/csv; charset=utf-8")
            return
        if path == "/input/onduleurs.csv":
            self.send_file(INPUT_DIR / "onduleurs.csv", "text/csv; charset=utf-8")
            return
        if path.startswith("/ui/"):
            self.send_static(UI_DIR, path.removeprefix("/ui/"))
            return
        if path.startswith("/docs/"):
            self.send_static(DOCS_DIR, path.removeprefix("/docs/"))
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def send_static(self, base_dir: Path, relative_path: str) -> None:
        target = safe_child(base_dir, relative_path)
        if not target:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or target.suffix.lower() in {".md", ".csv", ".json"}:
            content_type += "; charset=utf-8"
        self.send_file(target, content_type)

    def send_file(self, path: Path, content_type: str) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        payload = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def send_json(self, payload: dict | list) -> None:
        data = json_bytes(payload)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), PVSelectorHandler)
    print(f"PV Selector backend listening on 0.0.0.0:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
