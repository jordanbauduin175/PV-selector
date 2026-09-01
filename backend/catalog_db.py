from __future__ import annotations

import os
import re
import sqlite3
import sys
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CODE_DIR = PROJECT_ROOT / "code"
INPUT_DIR = PROJECT_ROOT / "input"
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from catalogue_fabricants import (  # noqa: E402
    INVERTERS_HEADER,
    PANELS_HEADER,
    load_db,
    normalize_entry,
    read_csv_rows,
    today,
)
from datasheet_importer import missing_fields, parse_datasheets  # noqa: E402


APP_VERSION = "0.27"
SUPPORTED_UPLOAD_SUFFIXES = {".pdf", ".txt", ".text", ".md"}
META_COLUMNS = ["source_url", "source_type", "last_verified", "notes"]
TABLE_BY_KIND = {"panel": "panels", "inverter": "inverters"}
CSV_BY_KIND = {"panel": INPUT_DIR / "panneaux.csv", "inverter": INPUT_DIR / "onduleurs.csv"}
HEADER_BY_KIND = {"panel": PANELS_HEADER, "inverter": INVERTERS_HEADER}
INTEGER_FIELDS_BY_KIND = {"panel": set(), "inverter": {"nombre_mppt", "strings_max_par_mppt"}}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def storage_dir() -> Path:
    configured = os.environ.get("PV_SELECTOR_STORAGE_DIR")
    if configured:
        return Path(configured).expanduser()
    persistent = Path("/storage")
    if persistent.exists() and os.access(persistent, os.W_OK):
        return persistent
    return PROJECT_ROOT / "storage"


def db_path() -> Path:
    configured = os.environ.get("PV_SELECTOR_DB_PATH")
    if configured:
        return Path(configured).expanduser()
    return storage_dir() / "pv_selector.sqlite3"


def uploads_dir() -> Path:
    return storage_dir() / "datasheets"


def connect() -> sqlite3.Connection:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    return connection


def create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS panels (
            reference TEXT NOT NULL,
            fabricant TEXT NOT NULL,
            puissance_w REAL NOT NULL,
            largeur_m REAL NOT NULL,
            hauteur_m REAL NOT NULL,
            uoc_v REAL NOT NULL,
            isc_a REAL NOT NULL,
            umpp_v REAL NOT NULL,
            impp_a REAL NOT NULL,
            coef_isc_pct_c REAL NOT NULL DEFAULT 0,
            coef_tension_pct_c REAL NOT NULL,
            source_url TEXT NOT NULL DEFAULT '',
            source_type TEXT NOT NULL DEFAULT 'manual',
            last_verified TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (fabricant, reference)
        );

        CREATE TABLE IF NOT EXISTS inverters (
            reference TEXT NOT NULL,
            fabricant TEXT NOT NULL,
            puissance_ac_w REAL NOT NULL,
            puissance_pv_max_w REAL NOT NULL,
            tension_dc_max_v REAL NOT NULL,
            tension_dc_nominale_v REAL NOT NULL DEFAULT 0,
            startup_input_voltage_v REAL NOT NULL DEFAULT 0,
            mppt_min_v REAL NOT NULL,
            mppt_max_v REAL NOT NULL,
            courant_max_mppt_a REAL NOT NULL,
            isc_max_mppt_a REAL NOT NULL,
            nombre_mppt INTEGER NOT NULL,
            strings_max_par_mppt INTEGER NOT NULL,
            phase TEXT NOT NULL,
            source_url TEXT NOT NULL DEFAULT '',
            source_type TEXT NOT NULL DEFAULT 'manual',
            last_verified TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (fabricant, reference)
        );

        CREATE TABLE IF NOT EXISTS import_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            kind TEXT NOT NULL,
            status TEXT NOT NULL,
            confidence REAL NOT NULL DEFAULT 0,
            reference TEXT NOT NULL DEFAULT '',
            fabricant TEXT NOT NULL DEFAULT '',
            message TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );
        """
    )
    ensure_column(connection, "inverters", "startup_input_voltage_v", "REAL NOT NULL DEFAULT 0")


def ensure_column(connection: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def normalize_kind(kind: str) -> str:
    value = str(kind or "").strip().lower()
    aliases = {
        "panels": "panel",
        "panneau": "panel",
        "panneaux": "panel",
        "module": "panel",
        "modules": "panel",
        "inverters": "inverter",
        "ond": "inverter",
        "onduleur": "inverter",
        "onduleurs": "inverter",
    }
    value = aliases.get(value, value)
    if value not in TABLE_BY_KIND:
        raise ValueError("Type attendu: panel ou inverter.")
    return value


def header_for_kind(kind: str) -> list[str]:
    return HEADER_BY_KIND[normalize_kind(kind)]


def table_for_kind(kind: str) -> str:
    return TABLE_BY_KIND[normalize_kind(kind)]


def _normalize_for_kind(kind: str, entry: dict) -> dict:
    normalized_kind = normalize_kind(kind)
    normalized = normalize_entry(
        entry,
        HEADER_BY_KIND[normalized_kind],
        numeric_ints=INTEGER_FIELDS_BY_KIND[normalized_kind],
    )
    if normalized_kind == "inverter":
        normalized["phase"] = normalized["phase"].lower()
    return normalized


def _missing_required(kind: str, entry: dict) -> list[str]:
    return missing_fields(entry, HEADER_BY_KIND[normalize_kind(kind)])


def _validate_entry(kind: str, entry: dict) -> None:
    missing = _missing_required(kind, entry)
    if missing:
        raise ValueError(f"Champs requis manquants ou invalides: {', '.join(missing)}")


def _upsert_with_connection(connection: sqlite3.Connection, kind: str, entry: dict, validate: bool = True) -> dict:
    normalized_kind = normalize_kind(kind)
    normalized = _normalize_for_kind(normalized_kind, entry)
    if validate:
        _validate_entry(normalized_kind, normalized)

    table = TABLE_BY_KIND[normalized_kind]
    columns = HEADER_BY_KIND[normalized_kind] + META_COLUMNS
    row = {column: normalized.get(column, "") for column in columns}
    row["source_type"] = row["source_type"] or "manual"
    row["last_verified"] = row["last_verified"] or today()
    now = utc_now()
    insert_columns = columns + ["created_at", "updated_at"]
    values = [row[column] for column in columns] + [now, now]
    placeholders = ", ".join("?" for _ in insert_columns)
    update_columns = [column for column in columns if column not in {"fabricant", "reference"}] + ["updated_at"]
    update_clause = ", ".join(f"{column}=excluded.{column}" for column in update_columns)
    connection.execute(
        f"""
        INSERT INTO {table} ({", ".join(insert_columns)})
        VALUES ({placeholders})
        ON CONFLICT(fabricant, reference) DO UPDATE SET {update_clause}
        """,
        values,
    )
    return row


def _count(connection: sqlite3.Connection, table: str) -> int:
    return int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _seed_kind_if_empty(connection: sqlite3.Connection, kind: str) -> int:
    table = TABLE_BY_KIND[kind]
    if _count(connection, table):
        return 0
    csv_path = CSV_BY_KIND[kind]
    if not csv_path.exists():
        return 0

    imported = 0
    for row in read_csv_rows(csv_path):
        try:
            seeded = dict(row)
            seeded["source_type"] = seeded.get("source_type", "").strip() or "app_csv_seed"
            seeded["last_verified"] = seeded.get("last_verified", "").strip() or today()
            _upsert_with_connection(connection, kind, seeded, validate=False)
            imported += 1
        except (KeyError, TypeError, ValueError):
            continue
    return imported


def ensure_database() -> Path:
    with closing(connect()) as connection:
        create_schema(connection)
        _seed_kind_if_empty(connection, "panel")
        _seed_kind_if_empty(connection, "inverter")
        connection.commit()
    return db_path()


def summary() -> dict:
    path = ensure_database()
    with closing(connect()) as connection:
        create_schema(connection)
        return {
            "schema_version": APP_VERSION,
            "path": str(path),
            "storage_dir": str(storage_dir()),
            "uploads_dir": str(uploads_dir()),
            "panels": _count(connection, "panels"),
            "inverters": _count(connection, "inverters"),
            "import_events": _count(connection, "import_events"),
        }


def list_items(kind: str) -> list[dict]:
    normalized_kind = normalize_kind(kind)
    ensure_database()
    table = TABLE_BY_KIND[normalized_kind]
    columns = HEADER_BY_KIND[normalized_kind] + META_COLUMNS
    with closing(connect()) as connection:
        create_schema(connection)
        rows = connection.execute(
            f"""
            SELECT {", ".join(columns)}
            FROM {table}
            ORDER BY fabricant COLLATE NOCASE, reference COLLATE NOCASE
            """
        ).fetchall()
    return [dict(row) for row in rows]


def upsert_item(kind: str, entry: dict) -> dict:
    ensure_database()
    with closing(connect()) as connection:
        saved = _upsert_with_connection(connection, kind, entry, validate=True)
        connection.commit()
    return saved


def sanitize_filename(filename: str) -> str:
    clean = Path(filename or "datasheet").name
    clean = re.sub(r"[^A-Za-z0-9_.-]+", "_", clean).strip("._")
    return clean or "datasheet"


def save_upload(filename: str, payload: bytes) -> Path:
    clean = sanitize_filename(filename)
    suffix = Path(clean).suffix.lower()
    if suffix not in SUPPORTED_UPLOAD_SUFFIXES:
        raise ValueError("Format non supporte. Formats acceptes: PDF, TXT, TEXT, MD.")
    target_dir = uploads_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    target = target_dir / f"{stamp}-{uuid4().hex[:8]}-{clean}"
    target.write_bytes(payload)
    return target


def _preview_entry(kind: str, entry: dict) -> dict:
    if kind not in HEADER_BY_KIND:
        return {key: value for key, value in entry.items() if value is not None}
    fields = HEADER_BY_KIND[kind] + META_COLUMNS
    return {field: "" if entry.get(field) is None else entry.get(field, "") for field in fields}


def record_import_event(filename: str, item: dict) -> None:
    ensure_database()
    with closing(connect()) as connection:
        create_schema(connection)
        connection.execute(
            """
            INSERT INTO import_events
                (filename, kind, status, confidence, reference, fabricant, message, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                filename,
                item.get("kind", ""),
                item.get("status", ""),
                float(item.get("confidence", 0) or 0),
                item.get("entry", {}).get("reference", ""),
                item.get("entry", {}).get("fabricant", ""),
                item.get("message", ""),
                utc_now(),
            ),
        )
        connection.commit()


def preview_datasheet(path: Path, forced_kind: str = "auto") -> dict:
    forced = str(forced_kind or "auto").strip().lower()
    if forced not in {"auto", "panel", "inverter"}:
        raise ValueError("Type d'analyse attendu: auto, panel ou inverter.")

    manufacturer_db = load_db(INPUT_DIR / "catalogue_fabricants_db.json")
    parsed_items = parse_datasheets(path, manufacturer_db, forced)
    items: list[dict] = []
    for parsed in parsed_items:
        kind = parsed.kind if parsed.kind in HEADER_BY_KIND else parsed.kind
        item = {
            "kind": kind,
            "status": parsed.status,
            "complete": parsed.complete,
            "confidence": parsed.confidence,
            "message": parsed.message,
            "missing_fields": parsed.missing_fields,
            "fields": HEADER_BY_KIND.get(kind, []) + (META_COLUMNS if kind in HEADER_BY_KIND else []),
            "entry": _preview_entry(kind, parsed.entry),
            "source_file": path.name,
        }
        items.append(item)
        record_import_event(path.name, item)

    return {
        "schema_version": APP_VERSION,
        "filename": path.name,
        "items": items,
        "database": summary(),
    }
