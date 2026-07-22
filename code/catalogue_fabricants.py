from __future__ import annotations

import argparse
import csv
import json
from datetime import date
from pathlib import Path
from urllib.parse import quote_plus


APP_VERSION = "0.21"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = PROJECT_ROOT / "input"
OUTPUT_DIR = PROJECT_ROOT / "output"
UI_DIR = PROJECT_ROOT / "ui"
DEFAULT_DB = INPUT_DIR / "catalogue_fabricants_db.json"
PANELS_HEADER = [
    "reference",
    "fabricant",
    "puissance_w",
    "largeur_m",
    "hauteur_m",
    "uoc_v",
    "isc_a",
    "umpp_v",
    "impp_a",
    "coef_tension_pct_c",
]
INVERTERS_HEADER = [
    "reference",
    "fabricant",
    "puissance_ac_w",
    "puissance_pv_max_w",
    "tension_dc_max_v",
    "tension_dc_nominale_v",
    "mppt_min_v",
    "mppt_max_v",
    "courant_max_mppt_a",
    "isc_max_mppt_a",
    "nombre_mppt",
    "strings_max_par_mppt",
    "phase",
]


def today() -> str:
    return date.today().isoformat()


def load_db(path: Path) -> dict:
    if not path.exists():
        return {
            "schema_version": APP_VERSION,
            "updated_at": today(),
            "manufacturers": [],
            "panels": [],
            "inverters": [],
        }
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def save_db(path: Path, db: dict) -> None:
    db["schema_version"] = APP_VERSION
    db["updated_at"] = today()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(db, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def parse_float(value: str | float | int) -> float:
    return float(str(value).strip().replace(",", "."))


def parse_int(value: str | float | int) -> int:
    return int(round(parse_float(value)))


OPTIONAL_NUMERIC_FIELDS = {"tension_dc_nominale_v"}

def normalize_entry(entry: dict, header: list[str], numeric_ints: set[str] | None = None) -> dict:
    numeric_ints = numeric_ints or set()
    normalized: dict = {}
    for key in header:
        value = entry.get(key, "")
        if key in {"reference", "fabricant", "phase"}:
            normalized[key] = str(value).strip()
        elif key in numeric_ints:
            normalized[key] = parse_int(value)
        elif key in OPTIONAL_NUMERIC_FIELDS and str(value).strip() == "":
            normalized[key] = 0.0
        else:
            normalized[key] = parse_float(value)
    normalized["source_url"] = str(entry.get("source_url", "")).strip()
    normalized["source_type"] = str(entry.get("source_type", "manual")).strip() or "manual"
    normalized["last_verified"] = str(entry.get("last_verified", today())).strip() or today()
    normalized["notes"] = str(entry.get("notes", "")).strip()
    return normalized


def upsert(items: list[dict], entry: dict) -> None:
    key = (entry["fabricant"].lower(), entry["reference"].lower())
    for index, item in enumerate(items):
        if (item["fabricant"].lower(), item["reference"].lower()) == key:
            items[index] = entry
            return
    items.append(entry)


def read_csv_rows(path: Path) -> list[dict]:
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv_rows(path: Path, header: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in header})


def import_app_csv(args: argparse.Namespace) -> None:
    db_path = Path(args.db)
    db = load_db(db_path)
    if args.panels:
        for row in read_csv_rows(Path(args.panels)):
            entry = normalize_entry(row, PANELS_HEADER)
            entry["source_type"] = row.get("source_type", "").strip() or "app_csv"
            upsert(db["panels"], entry)
    if args.inverters:
        for row in read_csv_rows(Path(args.inverters)):
            entry = normalize_entry(
                row,
                INVERTERS_HEADER,
                numeric_ints={"nombre_mppt", "strings_max_par_mppt"},
            )
            entry["source_type"] = row.get("source_type", "").strip() or "app_csv"
            upsert(db["inverters"], entry)
    save_db(db_path, db)
    print(f"Catalogue mis a jour : {db_path}")


def export_app_csv(args: argparse.Namespace) -> None:
    db = load_db(Path(args.db))
    panels = sorted(db.get("panels", []), key=lambda item: (item["fabricant"], item["reference"]))
    inverters = sorted(db.get("inverters", []), key=lambda item: (item["fabricant"], item["reference"]))
    write_csv_rows(Path(args.panels_out), PANELS_HEADER, panels)
    write_csv_rows(Path(args.inverters_out), INVERTERS_HEADER, inverters)
    print(f"Panneaux exportes : {args.panels_out}")
    print(f"Onduleurs exportes : {args.inverters_out}")


def add_panel(args: argparse.Namespace) -> None:
    db_path = Path(args.db)
    db = load_db(db_path)
    entry = normalize_entry(vars(args), PANELS_HEADER)
    upsert(db["panels"], entry)
    save_db(db_path, db)
    print(f"Panneau stocke : {entry['fabricant']} {entry['reference']}")


def add_inverter(args: argparse.Namespace) -> None:
    db_path = Path(args.db)
    db = load_db(db_path)
    entry = normalize_entry(
        vars(args),
        INVERTERS_HEADER,
        numeric_ints={"nombre_mppt", "strings_max_par_mppt"},
    )
    upsert(db["inverters"], entry)
    save_db(db_path, db)
    print(f"Onduleur stocke : {entry['fabricant']} {entry['reference']}")


def haystack(item: dict) -> str:
    return " ".join(str(value) for value in item.values()).lower()


def search(args: argparse.Namespace) -> None:
    db = load_db(Path(args.db))
    query = args.query.lower()
    collections: list[tuple[str, list[dict]]] = []
    if args.kind in {"all", "panel"}:
        collections.append(("panel", db.get("panels", [])))
    if args.kind in {"all", "inverter"}:
        collections.append(("inverter", db.get("inverters", [])))
    if args.kind in {"all", "manufacturer"}:
        collections.append(("manufacturer", db.get("manufacturers", [])))

    matches: list[tuple[str, dict]] = []
    for kind, items in collections:
        for item in items:
            if query in haystack(item):
                matches.append((kind, item))

    if not matches:
        print("Aucun resultat local.")
        return

    for kind, item in matches:
        if kind == "manufacturer":
            print(f"[manufacturer] {item['name']} ({item['kind']}) - {item.get('homepage', '')}")
        else:
            source = item.get("source_url") or "source non renseignee"
            print(f"[{kind}] {item['fabricant']} {item['reference']} - {source}")


def list_sources(args: argparse.Namespace) -> None:
    db = load_db(Path(args.db))
    manufacturers = db.get("manufacturers", [])
    if args.kind != "all":
        manufacturers = [item for item in manufacturers if item.get("kind") == args.kind]
    for item in sorted(manufacturers, key=lambda row: (row.get("kind", ""), row.get("name", ""))):
        print(f"[{item.get('kind')}] {item.get('name')} - {item.get('homepage')}")


def search_queries(args: argparse.Namespace) -> None:
    terms = [
        f"{args.manufacturer} {args.product} datasheet official",
        f"site:{args.domain} {args.product} datasheet" if args.domain else "",
        f"{args.manufacturer} {args.product} fiche technique PDF",
    ]
    for term in [term for term in terms if term]:
        print(f"https://www.google.com/search?q={quote_plus(term)}")


def summary(args: argparse.Namespace) -> None:
    db = load_db(Path(args.db))
    print(f"Version schema : {db.get('schema_version')}")
    print(f"Fabricants sources : {len(db.get('manufacturers', []))}")
    print(f"Panneaux stockes : {len(db.get('panels', []))}")
    print(f"Onduleurs stockes : {len(db.get('inverters', []))}")

def import_datasheets(args: argparse.Namespace) -> None:
    from datasheet_importer import import_directory

    summary = import_directory(
        directory=Path(args.directory),
        db_path=Path(args.db),
        kind=args.kind,
        dry_run=args.dry_run,
        panels_out=Path(args.panels_out),
        inverters_out=Path(args.inverters_out),
        report_path=Path(args.report),
        html_path=None if args.no_html_sync else Path(args.html),
    )
    mode = "analyse seule" if summary["dry_run"] else "import"
    print(f"Mode : {mode}")
    print(f"Datasheets lues : {summary['files']}")
    print(f"Fiches importables : {summary['ready']}")
    print(f"A verifier : {summary['review']}")
    print(f"Ignorer : {summary['skipped']}")
    print(f"Erreurs : {summary['errors']}")
    print(f"Rapport : {summary['report']}")
    if not summary["dry_run"]:
        print(f"CSV panneaux : {summary['panels_out']}")
        print(f"CSV onduleurs : {summary['inverters_out']}")
        print(f"HTML synchronise : {'oui' if summary['html_synced'] else 'non'}")

def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--db", default=str(DEFAULT_DB), help="Chemin de la base JSON catalogue.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Catalogue fabricants PV v0.21")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("summary")
    add_common(p)
    p.set_defaults(func=summary)

    p = sub.add_parser("import-app-csv")
    add_common(p)
    p.add_argument("--panels", default=str(INPUT_DIR / "panneaux.csv"))
    p.add_argument("--inverters", default=str(INPUT_DIR / "onduleurs.csv"))
    p.set_defaults(func=import_app_csv)

    p = sub.add_parser("export-app-csv")
    add_common(p)
    p.add_argument("--panels-out", default=str(OUTPUT_DIR / "panneaux_catalogue_export.csv"))
    p.add_argument("--inverters-out", default=str(OUTPUT_DIR / "onduleurs_catalogue_export.csv"))
    p.set_defaults(func=export_app_csv)

    p = sub.add_parser("search")
    add_common(p)
    p.add_argument("query")
    p.add_argument("--kind", choices=["all", "panel", "inverter", "manufacturer"], default="all")
    p.set_defaults(func=search)

    p = sub.add_parser("list-sources")
    add_common(p)
    p.add_argument("--kind", choices=["all", "panel", "inverter"], default="all")
    p.set_defaults(func=list_sources)
    p = sub.add_parser("import-datasheets")
    add_common(p)
    p.add_argument("directory", help="Repertoire contenant les datasheets PDF ou TXT.")
    p.add_argument("--kind", choices=["auto", "panel", "inverter"], default="auto")
    p.add_argument("--dry-run", action="store_true", help="Analyse sans import dans le catalogue.")
    p.add_argument("--panels-out", default=str(INPUT_DIR / "panneaux.csv"))
    p.add_argument("--inverters-out", default=str(INPUT_DIR / "onduleurs.csv"))
    p.add_argument("--report", default=str(OUTPUT_DIR / "datasheet_import_report.csv"))
    p.add_argument("--html", default=str(UI_DIR / "dimensionnement_solaire.html"))
    p.add_argument("--no-html-sync", action="store_true", help="Ne pas synchroniser l'HTML.")
    p.set_defaults(func=import_datasheets)

    p = sub.add_parser("search-queries")
    add_common(p)
    p.add_argument("--manufacturer", required=True)
    p.add_argument("--product", required=True)
    p.add_argument("--domain", default="")
    p.set_defaults(func=search_queries)

    p = sub.add_parser("add-panel")
    add_common(p)
    for field in PANELS_HEADER:
        p.add_argument(f"--{field.replace('_', '-')}", required=field not in OPTIONAL_NUMERIC_FIELDS)
    p.add_argument("--source-url", default="")
    p.add_argument("--source-type", default="manual")
    p.add_argument("--last-verified", default=today())
    p.add_argument("--notes", default="")
    p.set_defaults(func=add_panel)

    p = sub.add_parser("add-inverter")
    add_common(p)
    for field in INVERTERS_HEADER:
        p.add_argument(f"--{field.replace('_', '-')}", required=field not in OPTIONAL_NUMERIC_FIELDS)
    p.add_argument("--source-url", default="")
    p.add_argument("--source-type", default="manual")
    p.add_argument("--last-verified", default=today())
    p.add_argument("--notes", default="")
    p.set_defaults(func=add_inverter)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
