from __future__ import annotations

import csv
from email.parser import BytesParser
from email.policy import default as email_policy
import json
import mimetypes
import os
import sys
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from catalog_db import (
    ensure_database,
    list_items,
    preview_datasheet,
    save_upload,
    summary as db_summary,
    upsert_item,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
UI_DIR = PROJECT_ROOT / "ui"
INPUT_DIR = PROJECT_ROOT / "input"
DOCS_DIR = PROJECT_ROOT / "docs"
APP_VERSION = "0.27"
UI_VERSION = "v0.27"
APP_AUTHOR = "Bauduin Jordan"
APP_OWNER = "Open-Elec"
APP_URL = "https://www.open-elec.be"
SUPPORT_EMAIL = "info@open-elec.be"
COPYRIGHT_NOTICE = f"Copyright (c) 2026 {APP_AUTHOR} / {APP_OWNER}. Tous droits reserves."
MAX_UPLOAD_BYTES = int(os.environ.get("PV_SELECTOR_MAX_UPLOAD_MB", "25")) * 1024 * 1024


class RequestEntityTooLarge(ValueError):
    pass


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


def catalog_summary() -> dict:
    db_path = INPUT_DIR / "catalogue_fabricants_db.json"
    try:
        db = json.loads(db_path.read_text(encoding="utf-8-sig"))
    except (FileNotFoundError, json.JSONDecodeError):
        db = {}
    return {
        "schema_version": db.get("schema_version"),
        "updated_at": db.get("updated_at"),
        "manufacturers": len(db.get("manufacturers", [])),
        "panels": len(db.get("panels", [])),
        "inverters": len(db.get("inverters", [])),
    }


def csv_count(path: Path) -> int | None:
    try:
        return len(read_csv(path))
    except (FileNotFoundError, csv.Error, UnicodeDecodeError):
        return None


def debug_payload() -> dict:
    try:
        sqlite = db_summary()
    except Exception as exc:
        sqlite = {"error": str(exc)}
    return {
        "application": "PV Selector",
        "app_version": APP_VERSION,
        "backend_version": APP_VERSION,
        "ui_version": UI_VERSION,
        "catalog": catalog_summary(),
        "sqlite": sqlite,
        "author": APP_AUTHOR,
        "owner": APP_OWNER,
        "url": APP_URL,
        "support_email": SUPPORT_EMAIL,
        "copyright": COPYRIGHT_NOTICE,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version.split()[0],
        "port": os.environ.get("PORT", "8000"),
        "files": {
            "ui": (UI_DIR / "dimensionnement_solaire.html").exists(),
            "panels_csv": (INPUT_DIR / "panneaux.csv").exists(),
            "inverters_csv": (INPUT_DIR / "onduleurs.csv").exists(),
            "catalog_json": (INPUT_DIR / "catalogue_fabricants_db.json").exists(),
            "changelog": (DOCS_DIR / "CHANGELOG.md").exists(),
        },
        "csv_rows": {
            "panels": csv_count(INPUT_DIR / "panneaux.csv"),
            "inverters": csv_count(INPUT_DIR / "onduleurs.csv"),
        },
    }


class PVSelectorHandler(BaseHTTPRequestHandler):
    server_version = f"PVSelectorBackend/{APP_VERSION}"

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in {"", "/"}:
            self.send_file(UI_DIR / "dimensionnement_solaire.html", "text/html; charset=utf-8")
            return
        if path == "/health":
            self.send_json({"status": "ok", **debug_payload()})
            return
        if path == "/api/debug":
            self.send_json(debug_payload())
            return
        if path == "/api/catalog/panels":
            self.send_json(read_csv(INPUT_DIR / "panneaux.csv"))
            return
        if path == "/api/catalog/inverters":
            self.send_json(read_csv(INPUT_DIR / "onduleurs.csv"))
            return
        if path == "/api/catalog/summary":
            self.send_json(catalog_summary())
            return
        if path == "/api/db/summary":
            self.send_json(db_summary())
            return
        if path == "/api/db/panels":
            self.send_json({"items": list_items("panel"), "database": db_summary()})
            return
        if path == "/api/db/inverters":
            self.send_json({"items": list_items("inverter"), "database": db_summary()})
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

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            if path == "/api/datasheets/preview":
                self.handle_datasheet_preview()
                return
            if path == "/api/db/insert":
                self.handle_db_insert()
                return
            self.send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
        except RequestEntityTooLarge as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        except (json.JSONDecodeError, ValueError) as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except Exception as exc:
            self.send_json({"error": "Erreur serveur", "detail": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def read_body(self) -> bytes:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("Content-Length invalide.") from exc
        if length > MAX_UPLOAD_BYTES:
            limit_mb = MAX_UPLOAD_BYTES / 1024 / 1024
            raise RequestEntityTooLarge(f"Upload trop volumineux. Limite: {limit_mb:.0f} MB.")
        return self.rfile.read(length)

    def parse_multipart(self) -> tuple[dict[str, str], dict[str, dict]]:
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type.lower():
            raise ValueError("Content-Type attendu: multipart/form-data.")
        body = self.read_body()
        message = BytesParser(policy=email_policy).parsebytes(
            f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode("utf-8") + body
        )
        if not message.is_multipart():
            raise ValueError("Formulaire multipart invalide.")

        fields: dict[str, str] = {}
        files: dict[str, dict] = {}
        for part in message.iter_parts():
            name = part.get_param("name", header="content-disposition")
            if not name:
                continue
            filename = part.get_param("filename", header="content-disposition")
            payload = part.get_payload(decode=True) or b""
            if filename:
                files[name] = {
                    "filename": filename,
                    "content_type": part.get_content_type(),
                    "payload": payload,
                }
            else:
                charset = part.get_content_charset() or "utf-8"
                fields[name] = payload.decode(charset, errors="replace")
        return fields, files

    def handle_datasheet_preview(self) -> None:
        fields, files = self.parse_multipart()
        upload = files.get("datasheet") or files.get("file")
        if not upload:
            raise ValueError("Aucun fichier datasheet recu.")
        payload = upload["payload"]
        if not payload:
            raise ValueError("Le fichier datasheet est vide.")
        saved_path = save_upload(upload["filename"], payload)
        forced_kind = fields.get("kind", "auto")
        self.send_json(preview_datasheet(saved_path, forced_kind))

    def handle_db_insert(self) -> None:
        body = self.read_body()
        payload = json.loads(body.decode("utf-8") or "{}")
        kind = payload.get("kind")
        entry = payload.get("entry")
        if not isinstance(entry, dict):
            raise ValueError("Payload attendu: { kind, entry }.")
        saved = upsert_item(kind, entry)
        self.send_json({"status": "saved", "kind": kind, "entry": saved, "database": db_summary()})

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

    def send_json(self, payload: dict | list, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")


def main() -> None:
    port = int(os.environ.get("PORT", "8000"))
    database = ensure_database()
    server = ThreadingHTTPServer(("0.0.0.0", port), PVSelectorHandler)
    print(f"PV Selector backend {APP_VERSION} listening on 0.0.0.0:{port}")
    print(f"SQLite catalogue: {database}")
    server.serve_forever()


if __name__ == "__main__":
    main()
