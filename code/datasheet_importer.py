from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from catalogue_fabricants import (
    DEFAULT_DB,
    PROJECT_ROOT,
    INPUT_DIR,
    OUTPUT_DIR,
    UI_DIR,
    INVERTERS_HEADER,
    PANELS_HEADER,
    load_db,
    normalize_entry,
    read_csv_rows,
    save_db,
    today,
    upsert,
    write_csv_rows,
)


APP_VERSION = "0.20"
SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".text", ".md"}
DEFAULT_REPORT = OUTPUT_DIR / "datasheet_import_report.csv"
DEFAULT_PANELS_OUT = INPUT_DIR / "panneaux.csv"
DEFAULT_INVERTERS_OUT = INPUT_DIR / "onduleurs.csv"
DEFAULT_HTML = UI_DIR / "dimensionnement_solaire.html"


@dataclass
class LoadedDatasheet:
    text: str
    extractor: str
    tables: list[list[list[str]]]


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


NUMBER_TOKEN_PATTERN = r"-?\d(?:[\d\s.,]*\d)?"


def decimal(value: str | int | float | None) -> float | None:
    if value is None:
        return None
    match = re.search(NUMBER_TOKEN_PATTERN, str(value).strip())
    if not match:
        return None
    number = re.sub(r"\s+", "", match.group(0))
    if not number:
        return None

    sign = ""
    if number.startswith("-"):
        sign = "-"
        number = number[1:]

    if "," in number and "." in number:
        last_comma = number.rfind(",")
        last_dot = number.rfind(".")
        decimal_sep = "," if last_comma > last_dot else "."
        integer_part, decimal_part = number.rsplit(decimal_sep, 1)
        integer_part = re.sub(r"[.,]", "", integer_part)
        normalized = f"{sign}{integer_part}.{decimal_part}"
    elif "," in number:
        parts = number.split(",")
        if len(parts) > 2 or (len(parts) == 2 and len(parts[1]) == 3 and len(parts[0]) <= 3):
            normalized = sign + "".join(parts)
        else:
            normalized = sign + ".".join(parts)
    elif "." in number:
        parts = number.split(".")
        if len(parts) > 2 or (len(parts) == 2 and len(parts[1]) == 3 and len(parts[0]) <= 3):
            normalized = sign + "".join(parts)
        else:
            normalized = sign + number
    else:
        normalized = sign + number

    try:
        return float(normalized)
    except ValueError:
        return None


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


def load_document(path: Path) -> LoadedDatasheet:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        try:
            import pdfplumber

            with pdfplumber.open(path) as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
                tables = [table for page in pdf.pages for table in (page.extract_tables() or []) if table]
            if text.strip():
                return LoadedDatasheet(text, "pdfplumber", tables)
        except Exception:
            pass
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            return LoadedDatasheet(text, "pypdf", [])
        except Exception as exc:
            raise RuntimeError(f"PDF illisible: {exc}") from exc
    return LoadedDatasheet(path.read_text(encoding="utf-8", errors="ignore"), "text", [])


def load_text(path: Path) -> tuple[str, str]:
    loaded = load_document(path)
    return loaded.text, loaded.extractor


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
    if "sun2000" in haystack or "huawei" in haystack:
        for manufacturer in manufacturers:
            if "huawei" in manufacturer.lower():
                return manufacturer
        return "Huawei FusionSolar"
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
    pattern = rf"(?i)(?:{label_group}).{{0,{max_chars}}}?({NUMBER_TOKEN_PATTERN})\s*{unit_pattern}"
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
    pattern = rf"(?i)(?:{label_group}).{{0,{max_chars}}}?({NUMBER_TOKEN_PATTERN})\s*(kWp|Wp|kW|W|kVA|VA)\b"
    values: list[float] = []
    for number, unit in re.findall(pattern, compact):
        value = decimal(number)
        if value is None:
            continue
        unit = unit.lower()
        if unit in {"kw", "kva", "kwp"}:
            value *= 1000
        values.append(value)
    if not values:
        return None
    return max(values) if prefer == "max" else values[0]


def find_range(text: str, labels: list[str], unit: str = "V", max_chars: int = 160) -> tuple[float, float] | None:
    compact = clean_spaces(text)
    label_group = "|".join(f"(?:{label})" for label in labels)
    pattern = rf"(?i)(?:{label_group}).{{0,{max_chars}}}?({NUMBER_TOKEN_PATTERN})\s*(?:{unit})?\s*(?:-|~|to|a)\s*({NUMBER_TOKEN_PATTERN})\s*{unit}\b"
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

def prefer_huawei_manufacturer(manufacturer: str, text: str) -> str:
    haystack = text.lower()
    if "sun2000" in haystack or "huawei" in haystack:
        return "Huawei FusionSolar"
    return manufacturer


def clean_cell(value: object) -> str:
    return clean_spaces(str(value or "")).strip()


def compact_label(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", clean_spaces(value).lower())


def normalize_huawei_reference(value: str) -> str | None:
    compact = re.sub(r"\s+", "", clean_spaces(value).upper())
    match = re.search(r"SUN2000-?\d+(?:[.,]\d+)?K(?:TL)?-[A-Z]{1,6}\d{1,3}", compact)
    if not match:
        return None
    return match.group(0).replace(",", ".")


def huawei_family_references(text: str) -> list[str]:
    compact = re.sub(r"\s+", "", clean_spaces(text).upper())
    refs: list[str] = []
    family_pattern = r"SUN2000-(\d+(?:[.,]\d+)?(?:/\d+(?:[.,]\d+)?)*)K(TL)?-([A-Z]{1,6}\d{1,3})"
    for match in re.finditer(family_pattern, compact):
        suffix = match.group(3)
        tl = match.group(2) or ""
        for rating in match.group(1).split("/"):
            refs.append(f"SUN2000-{rating.replace(',', '.')}K{tl}-{suffix}")
    for match in re.finditer(r"SUN2000-?\d+(?:[.,]\d+)?K(?:TL)?-[A-Z]{1,6}\d{1,3}", compact):
        refs.append(match.group(0).replace(",", "."))

    unique: dict[str, str] = {}
    for ref in refs:
        unique.setdefault(ref, ref)
    return list(unique.values())


def parse_power_cell(value: str) -> float | None:
    match = re.search(rf"({NUMBER_TOKEN_PATTERN})\s*(kWp|Wp|kW|W|kVA|VA)\b", value, flags=re.IGNORECASE)
    if not match:
        return decimal(value)
    parsed = decimal(match.group(1))
    if parsed is None:
        return None
    unit = match.group(2).lower()
    if unit in {"kw", "kva", "kwp"}:
        parsed *= 1000
    return parsed


def parse_range_cell(value: str) -> tuple[float, float] | None:
    numbers = [decimal(match.group(0)) for match in re.finditer(r"\d(?:[\d\s.,]*\d)?", value)]
    numbers = [number for number in numbers if number is not None]
    if len(numbers) < 2:
        return None
    return (min(numbers[0], numbers[1]), max(numbers[0], numbers[1]))


def parse_int_cell(value: str) -> int | None:
    parsed = decimal(value)
    if parsed is None:
        return None
    return max(1, round(parsed))


def huawei_base_entry(reference: str, manufacturer: str, path: Path, source_type: str) -> dict:
    return {
        "reference": reference,
        "fabricant": prefer_huawei_manufacturer(manufacturer, reference),
        "puissance_ac_w": None,
        "puissance_pv_max_w": None,
        "tension_dc_max_v": None,
        "mppt_min_v": None,
        "mppt_max_v": None,
        "courant_max_mppt_a": None,
        "isc_max_mppt_a": None,
        "nombre_mppt": None,
        "strings_max_par_mppt": None,
        "phase": None,
        "source_url": path.resolve().as_uri(),
        "source_type": source_type,
        "last_verified": today(),
        "notes": "Import automatique datasheet tableau Huawei SUN2000; verification technique recommandee.",
    }


def huawei_table_model_columns(rows: list[list[str]]) -> tuple[int, list[tuple[int, str]]]:
    for row_index, row in enumerate(rows[:12]):
        columns: list[tuple[int, str]] = []
        for column_index, cell in enumerate(row):
            ref = normalize_huawei_reference(cell)
            if ref:
                columns.append((column_index, ref))
        if len(columns) >= 2:
            return row_index, columns
    return -1, []


def huawei_section(row: list[str], current: str) -> str:
    compact = compact_label(" ".join(row))
    if "inputpv" in compact:
        return "pv"
    if "inputdcbattery" in compact or "battery" in compact:
        return "battery"
    if "outputongrid" in compact:
        return "on_grid"
    if "outputoffgrid" in compact:
        return "off_grid"
    return current


def huawei_row_label(row: list[str], model_columns: list[tuple[int, str]]) -> str:
    model_indexes = {index for index, _ in model_columns}
    for index, cell in enumerate(row):
        if index in model_indexes or not cell or normalize_huawei_reference(cell):
            continue
        if re.search(r"[A-Za-z]", cell):
            return cell
    return ""


def huawei_values_by_model(row: list[str], model_columns: list[tuple[int, str]]) -> dict[str, str]:
    direct_values = []
    for column_index, reference in model_columns:
        value = row[column_index] if column_index < len(row) else ""
        direct_values.append((reference, value))
    non_empty_direct = [(reference, value) for reference, value in direct_values if value]
    if len(non_empty_direct) == len(model_columns):
        return dict(non_empty_direct)
    if len(non_empty_direct) == 1:
        shared = non_empty_direct[0][1]
        return {reference: shared for _, reference in model_columns}

    candidates = [cell for cell in row[1:] if cell and not normalize_huawei_reference(cell)]
    if len(candidates) == len(model_columns):
        return {reference: candidates[index] for index, (_, reference) in enumerate(model_columns)}
    if len(candidates) == 1:
        return {reference: candidates[0] for _, reference in model_columns}
    return {reference: value for reference, value in direct_values if value}


def set_huawei_numeric_field(
    entries: dict[str, dict],
    values: dict[str, str],
    field: str,
    parser,
) -> None:
    for reference, value in values.items():
        parsed = parser(value)
        if parsed is not None and entries[reference].get(field) in {None, ""}:
            entries[reference][field] = parsed


def set_huawei_range_field(entries: dict[str, dict], values: dict[str, str]) -> None:
    for reference, value in values.items():
        parsed = parse_range_cell(value)
        if parsed is None:
            continue
        low, high = parsed
        if entries[reference].get("mppt_min_v") in {None, ""}:
            entries[reference]["mppt_min_v"] = low
        if entries[reference].get("mppt_max_v") in {None, ""}:
            entries[reference]["mppt_max_v"] = high


def apply_huawei_row(entries: dict[str, dict], row: list[str], model_columns: list[tuple[int, str]], section: str) -> None:
    label = huawei_row_label(row, model_columns).lower()
    compact = compact_label(label)
    if not label:
        return
    values = huawei_values_by_model(row, model_columns)
    if not values:
        return

    if section == "pv":
        if "recommended" in compact and "pv" in compact and "power" in compact:
            set_huawei_numeric_field(entries, values, "puissance_pv_max_w", parse_power_cell)
        elif "maxinputvoltage" in compact:
            set_huawei_numeric_field(entries, values, "tension_dc_max_v", decimal)
        elif "operatingvoltagerange" in compact or "mppvoltagerange" in compact or "mpptvoltagerange" in compact:
            set_huawei_range_field(entries, values)
        elif "maxinputcurrent" in compact and ("mppt" in compact or "mpp" in compact):
            set_huawei_numeric_field(entries, values, "courant_max_mppt_a", decimal)
        elif "shortcircuitcurrent" in compact or "maxisc" in compact:
            set_huawei_numeric_field(entries, values, "isc_max_mppt_a", decimal)
        elif "numberofmpptrackers" in compact or "numberofmppt" in compact:
            set_huawei_numeric_field(entries, values, "nombre_mppt", parse_int_cell)
        elif "inputpermpp" in compact or "inputpermppt" in compact:
            set_huawei_numeric_field(entries, values, "strings_max_par_mppt", parse_int_cell)
    elif section in {"on_grid", ""}:
        if "ratedoutputpower" in compact:
            set_huawei_numeric_field(entries, values, "puissance_ac_w", parse_power_cell)
        elif "gridconnection" in compact:
            phase = detect_phase(" ".join(row))
            if phase:
                for entry in entries.values():
                    entry["phase"] = phase


def parse_huawei_tables(document: LoadedDatasheet, path: Path, manufacturer: str, source_type: str) -> dict[str, dict]:
    entries: dict[str, dict] = {}
    for table in document.tables:
        rows = [[clean_cell(cell) for cell in row] for row in table if row]
        header_index, model_columns = huawei_table_model_columns(rows)
        if header_index < 0:
            continue
        for _, reference in model_columns:
            entries.setdefault(reference, huawei_base_entry(reference, manufacturer, path, source_type))
        section = ""
        for row in rows[header_index + 1 :]:
            next_section = huawei_section(row, section)
            if next_section != section:
                section = next_section
                continue
            apply_huawei_row(entries, row, model_columns, section)
    return entries


def huawei_number_tokens(line: str) -> list[str]:
    pattern = r"(?<![A-Za-z])(\d(?:[\d\s.,]*\d)?)"
    return [match.group(1) for match in re.finditer(pattern, line)]


def huawei_values_from_line(line: str, references: list[str], parser) -> dict[str, str]:
    if parser is parse_range_cell:
        matches = huawei_number_tokens(line)
        if len(matches) < 2:
            return {}
        value = f"{matches[0]}-{matches[1]}"
        return {reference: value for reference in references}

    if parser is parse_power_cell:
        pattern = rf"(?<![A-Za-z]){NUMBER_TOKEN_PATTERN}\s*(?:kWp|Wp|kW|W|kVA|VA)\b"
        matches = [match.group(0) for match in re.finditer(pattern, line, flags=re.IGNORECASE)]
    else:
        matches = huawei_number_tokens(line)
    if len(matches) >= len(references):
        return {reference: matches[index] for index, reference in enumerate(references)}
    if len(matches) == 1:
        return {reference: matches[0] for reference in references}
    return {}


def apply_huawei_text_line(entries: dict[str, dict], line: str, references: list[str], section: str) -> None:
    label = line.lower()
    compact = compact_label(label)
    if section == "pv":
        if "recommended" in compact and "pv" in compact and "power" in compact:
            set_huawei_numeric_field(entries, huawei_values_from_line(line, references, parse_power_cell), "puissance_pv_max_w", parse_power_cell)
        elif "maxinputvoltage" in compact:
            set_huawei_numeric_field(entries, huawei_values_from_line(line, references, decimal), "tension_dc_max_v", decimal)
        elif "operatingvoltagerange" in compact or "mppvoltagerange" in compact or "mpptvoltagerange" in compact:
            set_huawei_range_field(entries, huawei_values_from_line(line, references, parse_range_cell))
        elif "maxinputcurrent" in compact and ("mppt" in compact or "mpp" in compact):
            set_huawei_numeric_field(entries, huawei_values_from_line(line, references, decimal), "courant_max_mppt_a", decimal)
        elif "shortcircuitcurrent" in compact or "maxisc" in compact:
            set_huawei_numeric_field(entries, huawei_values_from_line(line, references, decimal), "isc_max_mppt_a", decimal)
        elif "numberofmpptrackers" in compact or "numberofmppt" in compact:
            set_huawei_numeric_field(entries, huawei_values_from_line(line, references, parse_int_cell), "nombre_mppt", parse_int_cell)
        elif "inputpermpp" in compact or "inputpermppt" in compact:
            set_huawei_numeric_field(entries, huawei_values_from_line(line, references, parse_int_cell), "strings_max_par_mppt", parse_int_cell)
    elif section in {"on_grid", ""}:
        if "ratedoutputpower" in compact:
            set_huawei_numeric_field(entries, huawei_values_from_line(line, references, parse_power_cell), "puissance_ac_w", parse_power_cell)
        elif "gridconnection" in compact:
            phase = detect_phase(line)
            if phase:
                for entry in entries.values():
                    entry["phase"] = phase


def parse_huawei_text(document: LoadedDatasheet, path: Path, manufacturer: str, source_type: str) -> dict[str, dict]:
    references = huawei_family_references(document.text)
    if len(references) < 2:
        return {}
    entries = {reference: huawei_base_entry(reference, manufacturer, path, source_type) for reference in references}
    section = ""
    for raw_line in document.text.splitlines():
        line = clean_spaces(raw_line).strip()
        if not line:
            continue
        next_section = huawei_section([line], section)
        if next_section != section:
            section = next_section
            continue
        apply_huawei_text_line(entries, line, references, section)
    return entries


def parse_huawei_multi_inverters(document: LoadedDatasheet, path: Path, manufacturer: str, source_type: str) -> list[dict]:
    if "sun2000" not in document.text.lower():
        return []
    manufacturer = prefer_huawei_manufacturer(manufacturer, document.text)
    entries = parse_huawei_tables(document, path, manufacturer, source_type)
    text_entries = parse_huawei_text(document, path, manufacturer, source_type)
    for reference, text_entry in text_entries.items():
        entry = entries.setdefault(reference, huawei_base_entry(reference, manufacturer, path, source_type))
        for field, value in text_entry.items():
            if entry.get(field) in {None, ""} and value not in {None, ""}:
                entry[field] = value
    phase = detect_phase(document.text)
    if phase:
        for entry in entries.values():
            if entry.get("phase") in {None, ""}:
                entry["phase"] = phase
    return [entry for entry in entries.values() if any(entry.get(field) not in {None, ""} for field in INVERTERS_HEADER[2:])]

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


def parsed_datasheet_item(path: Path, kind: str, entry: dict, header: list[str], extractor: str) -> ParsedDatasheet:
    missing = missing_fields(entry, header)
    confidence = round((len(header) - len(missing)) / len(header), 2)
    if missing:
        message = f"Champs manquants: {', '.join(missing)}"
        return ParsedDatasheet(path, kind, entry, missing, confidence, "review", message)
    entry["notes"] = f"{entry['notes']} Extracteur: {extractor}. Confiance: {confidence:.2f}."
    return ParsedDatasheet(path, kind, entry, [], confidence, "ready", "Pret pour import.")


def parse_datasheets(path: Path, db: dict, forced_kind: str = "auto") -> list[ParsedDatasheet]:
    try:
        document = load_document(path)
    except Exception as exc:
        return [ParsedDatasheet(path, "unknown", {}, [], 0.0, "error", str(exc))]

    text = document.text
    if not text.strip():
        return [ParsedDatasheet(path, "unknown", {}, [], 0.0, "error", "Aucun texte extractible.")]

    kind = detect_kind(text, path, forced_kind)
    if kind == "unknown":
        return [ParsedDatasheet(path, kind, {}, [], 0.0, "skipped", "Type non detecte.")]

    source_type = "datasheet_pdf" if path.suffix.lower() == ".pdf" else "datasheet_text"
    manufacturer = detect_manufacturer(text, path, known_manufacturers(db))
    header = PANELS_HEADER if kind == "panel" else INVERTERS_HEADER

    if kind == "inverter":
        entries = parse_huawei_multi_inverters(document, path, manufacturer, source_type)
        if len(entries) >= 2:
            return [parsed_datasheet_item(path, kind, entry, header, document.extractor) for entry in entries]
        entry = parse_inverter(text, path, manufacturer, source_type)
    else:
        entry = parse_panel(text, path, manufacturer, source_type)

    return [parsed_datasheet_item(path, kind, entry, header, document.extractor)]


def parse_datasheet(path: Path, db: dict, forced_kind: str = "auto") -> ParsedDatasheet:
    return parse_datasheets(path, db, forced_kind)[0]


def merge_existing_app_csvs(db: dict, panels_csv: Path, inverters_csv: Path) -> None:
    if panels_csv.exists():
        for row in read_csv_rows(panels_csv):
            try:
                entry = normalize_entry(row, PANELS_HEADER)
            except (KeyError, ValueError):
                continue
            entry["source_type"] = row.get("source_type", "").strip() or entry.get("source_type", "app_csv")
            upsert(db["panels"], entry)
    if inverters_csv.exists():
        for row in read_csv_rows(inverters_csv):
            try:
                entry = normalize_entry(
                    row,
                    INVERTERS_HEADER,
                    numeric_ints={"nombre_mppt", "strings_max_par_mppt"},
                )
            except (KeyError, ValueError):
                continue
            entry["source_type"] = row.get("source_type", "").strip() or entry.get("source_type", "app_csv")
            upsert(db["inverters"], entry)

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


def report_file_label(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


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
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        for item in parsed_items:
            writer.writerow(
                {
                    "file": report_file_label(item.path),
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
    parsed_items = [item for path in files for item in parse_datasheets(path, db, kind)]
    ready_items = [item for item in parsed_items if item.complete]

    if not dry_run and ready_items:
        merge_existing_app_csvs(db, panels_out, inverters_out)
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
        "html_synced": bool(html_path and not dry_run and ready_items),
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
    if not summary["dry_run"] and summary["ready"]:
        print(f"CSV panneaux : {summary['panels_out']}")
        print(f"CSV onduleurs : {summary['inverters_out']}")
        print(f"HTML synchronise : {'oui' if summary['html_synced'] else 'non'}")
    elif not summary["dry_run"]:
        print("Aucun fichier catalogue modifie : aucune fiche complete a importer.")


if __name__ == "__main__":
    main()
