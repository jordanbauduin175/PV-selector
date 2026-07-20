from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from catalogue_fabricants import (
    DEFAULT_DB,
    INVERTERS_HEADER,
    PANELS_HEADER,
    load_db,
    normalize_entry,
    save_db,
    today,
    upsert,
    write_csv_rows,
)


APP_VERSION = "0.18"
SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".text", ".md"}
DEFAULT_REPORT = Path(__file__).with_name("datasheet_import_report.csv")
DEFAULT_PANELS_OUT = Path(__file__).with_name("panneaux.csv")
DEFAULT_INVERTERS_OUT = Path(__file__).with_name("onduleurs.csv")
DEFAULT_HTML = Path(__file__).with_name("dimensionnement_solaire.html")


@dataclass
class ParsedDatasheet:
    path: Path
    kind: str
    entry: dict
    missing_fields: list[str]
    confidence: float
    status: str
    message: str

    @property
    def complete(self) -> bool:
        return not self.missing_fields and self.status == "ready"


def decimal(value: str | int | float | None) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", ".")
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(match.group(0)) if match else None


def clean_spaces(text: str) -> str:
    replacements = {
        "\u00a0": " ",
        "\u202f": " ",
        "\u2013": "-",
        "\u2014": "-",
        "\u2212": "-",
        "\u00d7": "x",
    }
    for before, after in replacements.items():
        text = text.replace(before, after)
    return re.sub(r"\s+", " ", text)


def load_text(path: Path) -> tuple[str, str]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        try:
            import pdfplumber

            with pdfplumber.open(path) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
            if text.strip():
                return text, "pdfplumber"
        except Exception:
            pass
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            return text, "pypdf"
        except Exception as exc:
            raise RuntimeError(f"PDF illisible: {exc}") from exc
    return path.read_text(encoding="utf-8", errors="ignore"), "text"


def scan_datasheets(directory: Path) -> list[Path]:
    return sorted(
        path
        for path in directory.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS and path.name.lower() not in {"readme.md", "readme.txt"}
    )


def known_manufacturers(db: dict) -> list[str]:
    names = [item.get("name", "") for item in db.get("manufacturers", [])]
    names += [item.get("fabricant", "") for item in db.get("panels", [])]
    names += [item.get("fabricant", "") for item in db.get("inverters", [])]
    unique: dict[str, str] = {}
    for name in names:
        clean = str(name).strip()
        if clean:
            unique[clean.lower()] = clean
    return sorted(unique.values(), key=len, reverse=True)


def detect_manufacturer(text: str, path: Path, manufacturers: Iterable[str]) -> str:
    haystack = f"{path.parent.name} {path.stem} {text[:4000]}".lower()
    for manufacturer in manufacturers:
        if manufacturer.lower() in haystack:
            return manufacturer
    stem = re.sub(r"[_-]+", " ", path.stem).strip()
    first_words = " ".join(stem.split()[:2]).strip()
    return first_words or "A verifier"


def clean_reference(value: str, manufacturer: str = "") -> str:
    value = Path(value).stem
    value = re.sub(r"(?i)\b(data\s*sheet|datasheet|fiche\s*technique|technical|specification|spec)\b", " ", value)
    if manufacturer:
        value = re.sub(re.escape(manufacturer), " ", value, flags=re.IGNORECASE)
    value = re.sub(r"(?i)\b(fr|en|nl|de|eu|global|module|inverter|ondulateur|panneau|solar|pv)\b", " ", value)
    value = re.sub(r"\s+", " ", value.replace("_", " ").strip())
    value = re.sub(r"\s*-\s*", "-", value)
    value = value.replace(" ", "-")
    return value.strip("-")[:80] or "REF-A-VERIFIER"


def extract_reference(text: str, path: Path, manufacturer: str) -> str:
    compact = clean_spaces(text)
    patterns = [
        r"(?i)\b(?:model|model\s+name|module\s+type|type|reference|product\s+name)\b\s*[:#]?\s*([A-Z0-9][A-Z0-9._/\- ]{2,55})",
        r"(?i)\b(?:sunny\s+boy|sunny\s+tripower|sun2000|symo|primo|gen24|jkm|tsm|lr\d)[A-Z0-9._/\- ]{2,55}",
    ]
    for pattern in patterns:
        match = re.search(pattern, compact)
        if not match:
            continue
        candidate = match.group(1) if match.lastindex else match.group(0)
        candidate = clean_reference(candidate, manufacturer)
        if not re.search(r"(?i)electrical|mechanical|characteristics|parameters", candidate):
            return candidate
    return clean_reference(path.stem, manufacturer)


def values_near_labels(
    text: str,
    labels: list[str],
    units: str = "",
    max_chars: int = 120,
    multiplier: float = 1.0,
) -> list[float]:
    compact = clean_spaces(text)
    label_group = "|".join(f"(?:{label})" for label in labels)
    unit_pattern = rf"\s*(?:{units})\b" if units else ""
    pattern = rf"(?i)(?:{label_group}).{{0,{max_chars}}}?(-?\d+(?:[.,]\d+)?)\s*{unit_pattern}"
    values = []
    for match in re.finditer(pattern, compact):
        value = decimal(match.group(1))
        if value is not None:
            values.append(value * multiplier)
    return values


def first_value(text: str, labels: list[str], units: str = "", max_chars: int = 120) -> float | None:
    values = values_near_labels(text, labels, units, max_chars)
    return values[0] if values else None


def max_value(text: str, labels: list[str], units: str = "", max_chars: int = 120) -> float | None:
    values = values_near_labels(text, labels, units, max_chars)
    return max(values) if values else None


def find_power(text: str, labels: list[str], max_chars: int = 140, prefer: str = "max") -> float | None:
    compact = clean_spaces(text)
    label_group = "|".join(f"(?:{label})" for label in labels)
    pattern = rf"(?i)(?:{label_group}).{{0,{max_chars}}}?(-?\d+(?:[.,]\d+)?)\s*(kW|W|kVA|VA)\b"
    values: list[float] = []
    for number, unit in re.findall(pattern, compact):
        value = decimal(number)
        if value is None:
            continue
        unit = unit.lower()
        if unit in {"kw", "kva"}:
            value *= 1000
        values.append(value)
    if not values:
        return None
    return max(values) if prefer == "max" else values[0]


def find_range(text: str, labels: list[str], unit: str = "V", max_chars: int = 160) -> tuple[float, float] | None:
    compact = clean_spaces(text)
    label_group = "|".join(f"(?:{label})" for label in labels)
    pattern = rf"(?i)(?:{label_group}).{{0,{max_chars}}}?(\d+(?:[.,]\d+)?)\s*(?:-|to|a)\s*(\d+(?:[.,]\d+)?)\s*{unit}\b"
    match = re.search(pattern, compact)
    if not match:
        return None
    low = decimal(match.group(1))
    high = decimal(match.group(2))
    if low is None or high is None:
        return None
    return (min(low, high), max(low, high))


def find_dimensions_m(text: str) -> tuple[float | None, float | None]:
    compact = clean_spaces(text)
    patterns = [
        r"(?i)(?:dimension|size|mechanical).{0,140}?(\d{3,4}(?:[.,]\d+)?)\s*x\s*(\d{3,4}(?:[.,]\d+)?)\s*x?\s*\d{0,3}\s*mm",
        r"(?i)(\d{3,4}(?:[.,]\d+)?)\s*x\s*(\d{3,4}(?:[.,]\d+)?)\s*x\s*\d{1,3}\s*mm",
    ]
    for pattern in patterns:
        match = re.search(pattern, compact)
        if not match:
            continue
        a = decimal(match.group(1))
        b = decimal(match.group(2))
        if a and b:
            width = min(a, b) / 1000
            height = max(a, b) / 1000
            return width, height
    return None, None


def detect_kind(text: str, path: Path, forced_kind: str = "auto") -> str:
    if forced_kind in {"panel", "inverter"}:
        return forced_kind
    haystack = f"{path.name} {text[:6000]}".lower()
    inverter_score = sum(
        term in haystack
        for term in ["inverter", "ondulateur", "mppt", "ac output", "grid", "mpp tracker", "pv input"]
    )
    panel_score = sum(
        term in haystack
        for term in ["module", "solar panel", "photovoltaic module", "pmax", "stc", "open circuit voltage", "voc"]
    )
    if inverter_score > panel_score:
        return "inverter"
    if panel_score > 0:
        return "panel"
    return "unknown"


def parse_panel(text: str, path: Path, manufacturer: str, source_type: str) -> dict:
    width_m, height_m = find_dimensions_m(text)
    return {
        "reference": extract_reference(text, path, manufacturer),
        "fabricant": manufacturer,
        "puissance_w": find_power(
            text,
            [
                r"maximum\s+power",
                r"max\.?\s+power",
                r"pmax",
                r"pmpp",
                r"nominal\s+power",
                r"rated\s+power",
            ],
            prefer="max",
        ),
        "largeur_m": width_m,
        "hauteur_m": height_m,
        "uoc_v": first_value(text, [r"open\s*[- ]?circuit\s+voltage", r"\bvoc\b", r"\buoc\b"], "V"),
        "isc_a": first_value(text, [r"short\s*[- ]?circuit\s+current", r"\bisc\b"], "A"),
        "umpp_v": first_value(text, [r"voltage\s+at\s+maximum\s+power", r"\bvmp\b", r"\bvmpp\b", r"\bumpp\b"], "V"),
        "impp_a": first_value(text, [r"current\s+at\s+maximum\s+power", r"\bimp\b", r"\bimpp\b"], "A"),
        "coef_tension_pct_c": first_value(
            text,
            [
                r"temperature\s+coefficient.{0,40}\bvoc\b",
                r"temp\.?\s+coefficient.{0,40}\bvoc\b",
                r"\bvoc\b.{0,40}temperature\s+coefficient",
                r"\bbeta.{0,20}voc\b",
            ],
            r"%/?(?:degC|C|K)",
            160,
        ),
        "source_url": path.resolve().as_uri(),
        "source_type": source_type,
        "last_verified": today(),
        "notes": "Import automatique datasheet; verification technique recommandee.",
    }


def detect_phase(text: str) -> str | None:
    compact = clean_spaces(text).lower()
    if re.search(r"\b(three|tri)[ -]?phase\b|3\s*phase|3/n/pe|3l", compact):
        return "tri"
    if re.search(r"\b(single|mono)[ -]?phase\b|1\s*phase|1/n/pe", compact):
        return "mono"
    return None


def parse_inverter(text: str, path: Path, manufacturer: str, source_type: str) -> dict:
    mppt_range = find_range(
        text,
        [
            r"mpp\s+voltage\s+range",
            r"mppt\s+voltage\s+range",
            r"operating\s+voltage\s+range",
            r"mpp\s+operating\s+voltage",
        ],
    )
    nombre_mppt = first_value(
        text,
        [
            r"number\s+of\s+mpp\s+trackers",
            r"number\s+of\s+mppt",
            r"mpp\s+trackers",
            r"mppt\s+number",
        ],
        "",
        90,
    )
    strings_total = first_value(
        text,
        [
            r"number\s+of\s+pv\s+inputs",
            r"pv\s+inputs",
            r"dc\s+inputs",
            r"string\s+inputs",
        ],
        "",
        90,
    )
    strings_per_mppt = first_value(
        text,
        [
            r"strings\s+per\s+mpp",
            r"strings\s+per\s+mppt",
            r"inputs\s+per\s+mpp",
            r"inputs\s+per\s+mppt",
        ],
        "",
        90,
    )
    if strings_per_mppt is None and strings_total and nombre_mppt:
        strings_per_mppt = max(1, round(strings_total / nombre_mppt))

    return {
        "reference": extract_reference(text, path, manufacturer),
        "fabricant": manufacturer,
        "puissance_ac_w": find_power(
            text,
            [
                r"rated\s+ac\s+power",
                r"nominal\s+ac\s+power",
                r"ac\s+nominal\s+power",
                r"rated\s+output\s+power",
                r"nominal\s+output\s+power",
                r"ac\s+output\s+power",
            ],
            prefer="max",
        ),
        "puissance_pv_max_w": find_power(
            text,
            [
                r"max\.?\s+pv\s+power",
                r"maximum\s+pv\s+power",
                r"max\.?\s+dc\s+power",
                r"max\.?\s+recommended\s+pv\s+power",
                r"recommended\s+max\.?\s+pv\s+power",
            ],
            prefer="max",
        ),
        "tension_dc_max_v": first_value(
            text,
            [r"max\.?\s+input\s+voltage", r"maximum\s+input\s+voltage", r"max\.?\s+dc\s+voltage"],
            "V",
        ),
        "mppt_min_v": mppt_range[0] if mppt_range else None,
        "mppt_max_v": mppt_range[1] if mppt_range else None,
        "courant_max_mppt_a": first_value(
            text,
            [
                r"max\.?\s+input\s+current.{0,40}mpp",
                r"max\.?\s+input\s+current.{0,40}mppt",
                r"maximum\s+input\s+current.{0,40}mpp",
                r"max\.?\s+dc\s+current",
            ],
            "A",
            160,
        ),
        "isc_max_mppt_a": first_value(
            text,
            [
                r"max\.?\s+short\s*[- ]?circuit\s+current",
                r"maximum\s+short\s*[- ]?circuit\s+current",
                r"max\.?\s+isc",
                r"short\s*[- ]?circuit\s+current.{0,40}mpp",
            ],
            "A",
            160,
        ),
        "nombre_mppt": nombre_mppt,
        "strings_max_par_mppt": strings_per_mppt,
        "phase": detect_phase(text),
        "source_url": path.resolve().as_uri(),
        "source_type": source_type,
        "last_verified": today(),
        "notes": "Import automatique datasheet; verification technique recommandee.",
    }


def missing_fields(entry: dict, header: list[str]) -> list[str]:
    missing: list[str] = []
    for field in header:
        value = entry.get(field)
        if value in {None, ""}:
            missing.append(field)
            continue
        if field not in {"reference", "fabricant", "phase"}:
            numeric = decimal(value)
            if numeric is None:
                missing.append(field)
            elif field == "coef_tension_pct_c" and numeric == 0:
                missing.append(field)
            elif field != "coef_tension_pct_c" and numeric <= 0:
                missing.append(field)
    if "phase" in header and entry.get("phase") not in {"mono", "tri"}:
        missing.append("phase")
    return sorted(set(missing), key=header.index)


def parse_datasheet(path: Path, db: dict, forced_kind: str = "auto") -> ParsedDatasheet:
    try:
        text, extractor = load_text(path)
    except Exception as exc:
        return ParsedDatasheet(path, "unknown", {}, [], 0.0, "error", str(exc))

    if not text.strip():
        return ParsedDatasheet(path, "unknown", {}, [], 0.0, "error", "Aucun texte extractible.")

    kind = detect_kind(text, path, forced_kind)
    if kind == "unknown":
        return ParsedDatasheet(path, kind, {}, [], 0.0, "skipped", "Type non detecte.")

    source_type = "datasheet_pdf" if path.suffix.lower() == ".pdf" else "datasheet_text"
    manufacturer = detect_manufacturer(text, path, known_manufacturers(db))
    entry = parse_panel(text, path, manufacturer, source_type) if kind == "panel" else parse_inverter(text, path, manufacturer, source_type)
    header = PANELS_HEADER if kind == "panel" else INVERTERS_HEADER
    missing = missing_fields(entry, header)
    confidence = round((len(header) - len(missing)) / len(header), 2)
    if missing:
        message = f"Champs manquants: {', '.join(missing)}"
        return ParsedDatasheet(path, kind, entry, missing, confidence, "review", message)
    entry["notes"] = f"{entry['notes']} Extracteur: {extractor}. Confiance: {confidence:.2f}."
    return ParsedDatasheet(path, kind, entry, [], confidence, "ready", "Pret pour import.")


def sorted_rows(rows: list[dict]) -> list[dict]:
    return sorted(rows, key=lambda item: (str(item.get("fabricant", "")), str(item.get("reference", ""))))


def export_app_csvs(db: dict, panels_out: Path, inverters_out: Path) -> None:
    write_csv_rows(panels_out, PANELS_HEADER, sorted_rows(db.get("panels", [])))
    write_csv_rows(inverters_out, INVERTERS_HEADER, sorted_rows(db.get("inverters", [])))


def template_literal_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("`", "'")


def sync_html_catalogs(html_path: Path, panels_csv: Path, inverters_csv: Path) -> bool:
    if not html_path.exists():
        return False
    html = html_path.read_text(encoding="utf-8")
    panels = template_literal_escape(panels_csv.read_text(encoding="utf-8").strip())
    inverters = template_literal_escape(inverters_csv.read_text(encoding="utf-8").strip())

    def replace_const(source: str, const_name: str, value: str) -> str:
        pattern = rf"(const\s+{const_name}\s*=\s*`)([\s\S]*?)(`;)"
        updated, count = re.subn(pattern, lambda match: f"{match.group(1)}{value}{match.group(3)}", source, count=1)
        if count != 1:
            raise RuntimeError(f"Constante HTML introuvable: {const_name}")
        return updated

    html = replace_const(html, "DEFAULT_PANELS_CSV", panels)
    html = replace_const(html, "DEFAULT_INVERTERS_CSV", inverters)
    html_path.write_text(html, encoding="utf-8")
    return True


def write_report(path: Path, parsed_items: list[ParsedDatasheet]) -> None:
    header = [
        "file",
        "kind",
        "status",
        "confidence",
        "fabricant",
        "reference",
        "missing_fields",
        "message",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        for item in parsed_items:
            writer.writerow(
                {
                    "file": str(item.path),
                    "kind": item.kind,
                    "status": item.status,
                    "confidence": item.confidence,
                    "fabricant": item.entry.get("fabricant", ""),
                    "reference": item.entry.get("reference", ""),
                    "missing_fields": ";".join(item.missing_fields),
                    "message": item.message,
                }
            )


def import_directory(
    directory: Path,
    db_path: Path = DEFAULT_DB,
    kind: str = "auto",
    dry_run: bool = False,
    panels_out: Path = DEFAULT_PANELS_OUT,
    inverters_out: Path = DEFAULT_INVERTERS_OUT,
    report_path: Path = DEFAULT_REPORT,
    html_path: Path | None = DEFAULT_HTML,
) -> dict:
    directory = directory.resolve()
    if not directory.exists() or not directory.is_dir():
        raise FileNotFoundError(f"Repertoire introuvable: {directory}")

    db = load_db(db_path)
    files = scan_datasheets(directory)
    parsed_items = [parse_datasheet(path, db, kind) for path in files]
    ready_items = [item for item in parsed_items if item.complete]

    if not dry_run:
        for item in ready_items:
            if item.kind == "panel":
                entry = normalize_entry(item.entry, PANELS_HEADER)
                upsert(db["panels"], entry)
            elif item.kind == "inverter":
                entry = normalize_entry(
                    item.entry,
                    INVERTERS_HEADER,
                    numeric_ints={"nombre_mppt", "strings_max_par_mppt"},
                )
                upsert(db["inverters"], entry)
        save_db(db_path, db)
        export_app_csvs(db, panels_out, inverters_out)
        if html_path:
            sync_html_catalogs(html_path, panels_out, inverters_out)

    write_report(report_path, parsed_items)

    return {
        "files": len(files),
        "ready": len(ready_items),
        "review": sum(1 for item in parsed_items if item.status == "review"),
        "skipped": sum(1 for item in parsed_items if item.status == "skipped"),
        "errors": sum(1 for item in parsed_items if item.status == "error"),
        "report": str(report_path),
        "dry_run": dry_run,
        "panels_out": str(panels_out),
        "inverters_out": str(inverters_out),
        "html_synced": bool(html_path and not dry_run),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import datasheets panneaux/onduleurs vers le catalogue solaire.")
    parser.add_argument("directory", help="Repertoire contenant les datasheets PDF ou TXT.")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="Base JSON catalogue.")
    parser.add_argument("--kind", choices=["auto", "panel", "inverter"], default="auto")
    parser.add_argument("--dry-run", action="store_true", help="Analyse sans import dans le catalogue.")
    parser.add_argument("--panels-out", default=str(DEFAULT_PANELS_OUT))
    parser.add_argument("--inverters-out", default=str(DEFAULT_INVERTERS_OUT))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--html", default=str(DEFAULT_HTML), help="HTML a synchroniser avec les CSV exportes.")
    parser.add_argument("--no-html-sync", action="store_true", help="Ne pas synchroniser l'HTML.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
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


if __name__ == "__main__":
    main()


