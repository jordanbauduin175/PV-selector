from __future__ import annotations

import csv
import math
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, TOP, X, Y, filedialog, messagebox, ttk
import tkinter as tk


APP_VERSION = "v0.22"
APP_TITLE = f"Dimensionnement solaire {APP_VERSION} - selection panneaux / onduleurs"
APP_AUTHOR = "Bauduin Jordan"
APP_OWNER = "Open-Elec"
APP_URL = "https://www.open-elec.be"
SUPPORT_EMAIL = "info@open-elec.be"
COPYRIGHT_NOTICE = f"Copyright (c) 2026 {APP_AUTHOR} / {APP_OWNER}. Tous droits reserves."
PROJECT_ROOT = Path(__file__).resolve().parent.parent
INPUT_DIR = PROJECT_ROOT / "input"
ALL_PANELS_LABEL = "Tous les panneaux"
ALL_INVERTERS_LABEL = "Tous les onduleurs"
RGIE_UOC_FROID_MAX_V = 750.0
OPTIMAL_SLOPE_DEG = 35.0
COPPER_RESISTIVITY_OHM_MM2_M = 0.0175
MAX_JOULE_LOSS_PCT = 2.0
AC_VOLTAGE_DROP_REFERENCE_V = 230.0
ORIENTATION_OPTIONS = {
    "Sud": 0.0,
    "Sud-Est": -45.0,
    "Sud-Ouest": 45.0,
    "Est": -90.0,
    "Ouest": 90.0,
    "Nord-Est": -135.0,
    "Nord-Ouest": 135.0,
    "Nord": 180.0,
}
DISTRIBUTION_LIMITS_VA = {
    "Mono": 5000.0,
    "Biphase": 5000.0,
    "Tri delta (3x230)": 10000.0,
    "Tetra (3x400 + N)": 10000.0,
}


@dataclass(frozen=True)
class Panel:
    reference: str
    fabricant: str
    puissance_w: float
    largeur_m: float
    hauteur_m: float
    uoc_v: float
    isc_a: float
    umpp_v: float
    impp_a: float
    coef_tension_pct_c: float

    @property
    def surface_m2(self) -> float:
        return self.largeur_m * self.hauteur_m


@dataclass(frozen=True)
class Inverter:
    reference: str
    fabricant: str
    puissance_ac_w: float
    puissance_pv_max_w: float
    tension_dc_max_v: float
    tension_dc_nominale_v: float
    mppt_min_v: float
    mppt_max_v: float
    courant_max_mppt_a: float
    isc_max_mppt_a: float
    nombre_mppt: int
    strings_max_par_mppt: int
    phase: str


@dataclass(frozen=True)
class Candidate:
    panel: Panel
    inverter: Inverter
    modules_par_string: int
    nombre_strings: int
    repartition_mppt: tuple[int, ...]
    puissance_dc_w: float
    production_brute_kwh: float
    production_annuelle_kwh: float
    consommation_client_kwh: float
    distribution_label: str
    limite_distribution_va: float
    taux_couverture_pct: float
    ecart_conso_kwh: float
    coefficient_exposition: float
    facteur_orientation: float
    facteur_pente: float
    orientation_label: str
    pente_deg: float
    gisement_reference_kwh_kwc: float
    dc_distance_m: float
    dc_section_mm2: float
    dc_return_per_panel_m: float
    panel_cord_m: float
    dc_main_length_m: float
    dc_panel_cord_length_m: float
    dc_loss_w: float
    dc_voltage_drop_v: float
    dc_voltage_drop_pct: float
    ac_inv_td_distance_m: float
    ac_inv_td_section_mm2: float
    ac_td_meter_distance_m: float
    ac_td_meter_section_mm2: float
    ac_loss_w: float
    ac_voltage_drop_reference_v: float
    ac_inv_td_loss_w: float
    ac_td_meter_loss_w: float
    ac_voltage_drop_v: float
    ac_inv_td_voltage_drop_v: float
    ac_td_meter_voltage_drop_v: float
    ac_voltage_drop_pct: float
    ac_inv_td_voltage_drop_pct: float
    ac_td_meter_voltage_drop_pct: float
    total_loss_w: float
    total_loss_pct: float
    surface_m2: float
    surface_utilisee_pct: float
    ratio_dc_ac: float
    umpp_stc_v: float
    ecart_umpp_nominal_pct: float
    uoc_froid_v: float
    umpp_chaud_v: float
    umpp_froid_v: float
    impp_mppt_a: float
    isc_mppt_a: float

    @property
    def total_modules(self) -> int:
        return self.modules_par_string * self.nombre_strings


def parse_float(value: str) -> float:
    return float(str(value).strip().replace(",", "."))


def parse_int(value: str) -> int:
    return int(round(parse_float(value)))

def parse_optional_float(value: str | None) -> float:
    if value is None or str(value).strip() == "":
        return 0.0
    return parse_float(value)


def load_panels(path: Path) -> list[Panel]:
    panels: list[Panel] = []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            panels.append(
                Panel(
                    reference=row["reference"].strip(),
                    fabricant=row["fabricant"].strip(),
                    puissance_w=parse_float(row["puissance_w"]),
                    largeur_m=parse_float(row["largeur_m"]),
                    hauteur_m=parse_float(row["hauteur_m"]),
                    uoc_v=parse_float(row["uoc_v"]),
                    isc_a=parse_float(row["isc_a"]),
                    umpp_v=parse_float(row["umpp_v"]),
                    impp_a=parse_float(row["impp_a"]),
                    coef_tension_pct_c=parse_float(row["coef_tension_pct_c"]),
                )
            )
    return panels


def load_inverters(path: Path) -> list[Inverter]:
    inverters: list[Inverter] = []
    with path.open("r", newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            inverters.append(
                Inverter(
                    reference=row["reference"].strip(),
                    fabricant=row["fabricant"].strip(),
                    puissance_ac_w=parse_float(row["puissance_ac_w"]),
                    puissance_pv_max_w=parse_float(row["puissance_pv_max_w"]),
                    tension_dc_max_v=parse_float(row["tension_dc_max_v"]),
                    tension_dc_nominale_v=parse_optional_float(row.get("tension_dc_nominale_v")),
                    mppt_min_v=parse_float(row["mppt_min_v"]),
                    mppt_max_v=parse_float(row["mppt_max_v"]),
                    courant_max_mppt_a=parse_float(row["courant_max_mppt_a"]),
                    isc_max_mppt_a=parse_float(row["isc_max_mppt_a"]),
                    nombre_mppt=parse_int(row["nombre_mppt"]),
                    strings_max_par_mppt=parse_int(row["strings_max_par_mppt"]),
                    phase=row["phase"].strip(),
                )
            )
    return inverters


def voltage_at_temperature(voltage_stc: float, coef_pct_c: float, temperature_c: float) -> float:
    return voltage_stc * (1 + (coef_pct_c / 100.0) * (temperature_c - 25.0))


def clamp(value: float, min_value: float, max_value: float) -> float:
    return min(max_value, max(min_value, value))


def is_single_or_biphase_distribution(distribution_label: str) -> bool:
    return distribution_label in {"Mono", "Biphase"}


def allowed_inverters_for_distribution(inverters: list[Inverter], distribution_label: str) -> list[Inverter]:
    if not is_single_or_biphase_distribution(distribution_label):
        return inverters
    return [inverter for inverter in inverters if inverter.phase != "tri"]


def exposure_coefficient(orientation_deg: float, slope_deg: float) -> tuple[float, float, float]:
    deviation = min(abs(orientation_deg), 360.0 - abs(orientation_deg))
    if deviation <= 90.0:
        orientation_factor = 1 - 0.20 * (deviation / 90.0) ** 1.35
    else:
        orientation_factor = 0.80 - 0.35 * ((deviation - 90.0) / 90.0) ** 1.15
    slope_factor = 1 - abs(slope_deg - OPTIMAL_SLOPE_DEG) * 0.0055
    orientation_factor = clamp(orientation_factor, 0.45, 1.0)
    slope_factor = clamp(slope_factor, 0.78, 1.0)
    return clamp(orientation_factor * slope_factor, 0.35, 1.0), orientation_factor, slope_factor


def cable_resistance(length_m: float, section_mm2: float) -> float:
    return COPPER_RESISTIVITY_OHM_MM2_M * length_m / section_mm2


def ac_electrical_model(inverter: Inverter, distribution_label: str) -> tuple[float, float, int, float]:
    if inverter.phase == "tri":
        voltage_v = 400.0 if distribution_label == "Tetra (3x400 + N)" else 230.0
        current_a = inverter.puissance_ac_w / (math.sqrt(3.0) * voltage_v)
        drop_factor = 1.0 if distribution_label == "Tetra (3x400 + N)" else math.sqrt(3.0)
        return voltage_v, current_a, 3, drop_factor
    voltage_v = 230.0
    current_a = inverter.puissance_ac_w / voltage_v
    return voltage_v, current_a, 2, 2.0


def calculate_cable_losses(
    panel: Panel,
    inverter: Inverter,
    modules_par_string: int,
    nombre_strings: int,
    distribution_label: str,
    dc_distance_m: float,
    dc_section_mm2: float,
    dc_return_per_panel_m: float,
    panel_cord_m: float,
    ac_inv_td_distance_m: float,
    ac_inv_td_section_mm2: float,
    ac_td_meter_distance_m: float,
    ac_td_meter_section_mm2: float,
) -> dict[str, float]:
    dc_main_length_m = (2 * dc_distance_m) + (modules_par_string * dc_return_per_panel_m)
    dc_panel_cord_length_m = modules_par_string * panel_cord_m
    dc_resistance = cable_resistance(dc_main_length_m, dc_section_mm2) + cable_resistance(
        dc_panel_cord_length_m, 4.0
    )
    dc_current = panel.impp_a
    dc_voltage_drop = dc_current * dc_resistance
    dc_loss = dc_current * dc_current * dc_resistance * nombre_strings
    dc_string_voltage = panel.umpp_v * modules_par_string
    dc_voltage_drop_pct = (dc_voltage_drop / dc_string_voltage * 100.0) if dc_string_voltage else 0.0

    ac_voltage, ac_current, ac_conductors, ac_drop_factor = ac_electrical_model(inverter, distribution_label)
    ac_inv_td_resistance = cable_resistance(ac_inv_td_distance_m, ac_inv_td_section_mm2)
    ac_td_meter_resistance = cable_resistance(ac_td_meter_distance_m, ac_td_meter_section_mm2)
    ac_resistance = ac_inv_td_resistance + ac_td_meter_resistance
    ac_inv_td_loss = ac_conductors * ac_current * ac_current * ac_inv_td_resistance
    ac_td_meter_loss = ac_conductors * ac_current * ac_current * ac_td_meter_resistance
    ac_loss = ac_inv_td_loss + ac_td_meter_loss
    ac_inv_td_voltage_drop = ac_drop_factor * ac_current * ac_inv_td_resistance
    ac_td_meter_voltage_drop = ac_drop_factor * ac_current * ac_td_meter_resistance
    ac_voltage_drop = ac_inv_td_voltage_drop + ac_td_meter_voltage_drop
    ac_voltage_drop_pct = ac_voltage_drop / AC_VOLTAGE_DROP_REFERENCE_V * 100.0
    ac_inv_td_voltage_drop_pct = ac_inv_td_voltage_drop / AC_VOLTAGE_DROP_REFERENCE_V * 100.0
    ac_td_meter_voltage_drop_pct = ac_td_meter_voltage_drop / AC_VOLTAGE_DROP_REFERENCE_V * 100.0

    return {
        "dc_main_length_m": dc_main_length_m,
        "dc_panel_cord_length_m": dc_panel_cord_length_m,
        "dc_loss_w": dc_loss,
        "dc_voltage_drop_v": dc_voltage_drop,
        "dc_voltage_drop_pct": dc_voltage_drop_pct,
        "ac_loss_w": ac_loss,
        "ac_voltage_drop_reference_v": AC_VOLTAGE_DROP_REFERENCE_V,
        "ac_inv_td_loss_w": ac_inv_td_loss,
        "ac_td_meter_loss_w": ac_td_meter_loss,
        "ac_voltage_drop_v": ac_voltage_drop,
        "ac_inv_td_voltage_drop_v": ac_inv_td_voltage_drop,
        "ac_td_meter_voltage_drop_v": ac_td_meter_voltage_drop,
        "ac_voltage_drop_pct": ac_voltage_drop_pct,
        "ac_inv_td_voltage_drop_pct": ac_inv_td_voltage_drop_pct,
        "ac_td_meter_voltage_drop_pct": ac_td_meter_voltage_drop_pct,
        "total_loss_w": dc_loss + ac_loss,
    }


def distribute_strings(nombre_strings: int, nombre_mppt: int) -> tuple[int, ...]:
    base = nombre_strings // nombre_mppt
    extra = nombre_strings % nombre_mppt
    return tuple(base + (1 if index < extra else 0) for index in range(nombre_mppt))


def optimize(
    panels: list[Panel],
    inverters: list[Inverter],
    surface_disponible_m2: float,
    taux_occupation_pct: float,
    consommation_client_kwh: float,
    distribution_label: str,
    orientation_label: str,
    pente_deg: float,
    gisement_reference_kwh_kwc: float,
    dc_distance_m: float,
    dc_section_mm2: float,
    dc_return_per_panel_m: float,
    panel_cord_m: float,
    ac_inv_td_distance_m: float,
    ac_inv_td_section_mm2: float,
    ac_td_meter_distance_m: float,
    ac_td_meter_section_mm2: float,
    temperature_min_c: float,
    temperature_max_module_c: float,
) -> tuple[list[Candidate], dict[str, int]]:
    usable_surface = max(0.0, surface_disponible_m2 * taux_occupation_pct / 100.0)
    orientation_deg = ORIENTATION_OPTIONS.get(orientation_label, 0.0)
    limite_distribution_va = DISTRIBUTION_LIMITS_VA.get(distribution_label, DISTRIBUTION_LIMITS_VA["Mono"])
    coefficient_exposition, facteur_orientation, facteur_pente = exposure_coefficient(orientation_deg, pente_deg)
    rejected = {
        "surface": 0,
        "phase": 0,
        "distribution": 0,
        "uoc_rgie": 0,
        "uoc": 0,
        "umpp_min": 0,
        "umpp_max": 0,
        "courant": 0,
        "puissance_pv": 0,
        "pertes": 0,
    }
    candidates: list[Candidate] = []

    for panel in panels:
        if panel.surface_m2 <= 0:
            continue
        max_modules_surface = math.floor(usable_surface / panel.surface_m2)
        if max_modules_surface <= 0:
            rejected["surface"] += 1
            continue

        for inverter in inverters:
            max_strings = inverter.nombre_mppt * inverter.strings_max_par_mppt
            if is_single_or_biphase_distribution(distribution_label) and inverter.phase == "tri":
                rejected["phase"] += max_modules_surface * max_strings
                continue
            if inverter.puissance_ac_w > limite_distribution_va:
                rejected["distribution"] += max_modules_surface * max_strings
                continue
            for modules_par_string in range(1, max_modules_surface + 1):
                uoc_froid = voltage_at_temperature(
                    panel.uoc_v * modules_par_string,
                    panel.coef_tension_pct_c,
                    temperature_min_c,
                )
                umpp_chaud = voltage_at_temperature(
                    panel.umpp_v * modules_par_string,
                    panel.coef_tension_pct_c,
                    temperature_max_module_c,
                )
                umpp_froid = voltage_at_temperature(
                    panel.umpp_v * modules_par_string,
                    panel.coef_tension_pct_c,
                    temperature_min_c,
                )
                umpp_stc = panel.umpp_v * modules_par_string
                ecart_umpp_nominal_pct = (
                    (umpp_stc - inverter.tension_dc_nominale_v) / inverter.tension_dc_nominale_v * 100.0
                    if inverter.tension_dc_nominale_v > 0
                    else 0.0
                )

                if uoc_froid > RGIE_UOC_FROID_MAX_V:
                    rejected["uoc_rgie"] += max_strings
                    continue
                if uoc_froid > inverter.tension_dc_max_v:
                    rejected["uoc"] += max_strings
                    continue
                if umpp_chaud < inverter.mppt_min_v:
                    rejected["umpp_min"] += max_strings
                    continue
                if umpp_froid > inverter.mppt_max_v:
                    rejected["umpp_max"] += max_strings
                    continue

                for nombre_strings in range(1, max_strings + 1):
                    total_modules = modules_par_string * nombre_strings
                    surface = total_modules * panel.surface_m2
                    if total_modules > max_modules_surface:
                        rejected["surface"] += 1
                        continue

                    repartition = distribute_strings(nombre_strings, inverter.nombre_mppt)
                    if max(repartition) > inverter.strings_max_par_mppt:
                        rejected["courant"] += 1
                        continue

                    impp_mppt = max(repartition) * panel.impp_a
                    isc_mppt = max(repartition) * panel.isc_a
                    if impp_mppt > inverter.courant_max_mppt_a or isc_mppt > inverter.isc_max_mppt_a:
                        rejected["courant"] += 1
                        continue

                    puissance_dc = total_modules * panel.puissance_w
                    if inverter.puissance_pv_max_w > 0 and puissance_dc > inverter.puissance_pv_max_w:
                        rejected["puissance_pv"] += 1
                        continue

                    losses = calculate_cable_losses(
                        panel,
                        inverter,
                        modules_par_string,
                        nombre_strings,
                        distribution_label,
                        dc_distance_m,
                        dc_section_mm2,
                        dc_return_per_panel_m,
                        panel_cord_m,
                        ac_inv_td_distance_m,
                        ac_inv_td_section_mm2,
                        ac_td_meter_distance_m,
                        ac_td_meter_section_mm2,
                    )
                    total_loss_pct = (
                        losses["total_loss_w"] / puissance_dc * 100.0 if puissance_dc > 0 else 0.0
                    )
                    if total_loss_pct > MAX_JOULE_LOSS_PCT:
                        rejected["pertes"] += 1
                        continue

                    production_brute = (
                        puissance_dc / 1000.0 * gisement_reference_kwh_kwc * coefficient_exposition
                    )
                    production_annuelle = production_brute * (1 - total_loss_pct / 100.0)
                    taux_couverture = (
                        production_annuelle / consommation_client_kwh * 100.0
                        if consommation_client_kwh > 0
                        else 0.0
                    )
                    candidates.append(
                        Candidate(
                            panel=panel,
                            inverter=inverter,
                            modules_par_string=modules_par_string,
                            nombre_strings=nombre_strings,
                            repartition_mppt=repartition,
                            puissance_dc_w=puissance_dc,
                            production_brute_kwh=production_brute,
                            production_annuelle_kwh=production_annuelle,
                            consommation_client_kwh=consommation_client_kwh,
                            distribution_label=distribution_label,
                            limite_distribution_va=limite_distribution_va,
                            taux_couverture_pct=taux_couverture,
                            ecart_conso_kwh=production_annuelle - consommation_client_kwh,
                            coefficient_exposition=coefficient_exposition,
                            facteur_orientation=facteur_orientation,
                            facteur_pente=facteur_pente,
                            orientation_label=orientation_label,
                            pente_deg=pente_deg,
                            gisement_reference_kwh_kwc=gisement_reference_kwh_kwc,
                            dc_distance_m=dc_distance_m,
                            dc_section_mm2=dc_section_mm2,
                            dc_return_per_panel_m=dc_return_per_panel_m,
                            panel_cord_m=panel_cord_m,
                            dc_main_length_m=losses["dc_main_length_m"],
                            dc_panel_cord_length_m=losses["dc_panel_cord_length_m"],
                            dc_loss_w=losses["dc_loss_w"],
                            dc_voltage_drop_v=losses["dc_voltage_drop_v"],
                            dc_voltage_drop_pct=losses["dc_voltage_drop_pct"],
                            ac_inv_td_distance_m=ac_inv_td_distance_m,
                            ac_inv_td_section_mm2=ac_inv_td_section_mm2,
                            ac_td_meter_distance_m=ac_td_meter_distance_m,
                            ac_td_meter_section_mm2=ac_td_meter_section_mm2,
                            ac_loss_w=losses["ac_loss_w"],
                            ac_voltage_drop_reference_v=losses["ac_voltage_drop_reference_v"],
                            ac_inv_td_loss_w=losses["ac_inv_td_loss_w"],
                            ac_td_meter_loss_w=losses["ac_td_meter_loss_w"],
                            ac_voltage_drop_v=losses["ac_voltage_drop_v"],
                            ac_inv_td_voltage_drop_v=losses["ac_inv_td_voltage_drop_v"],
                            ac_td_meter_voltage_drop_v=losses["ac_td_meter_voltage_drop_v"],
                            ac_voltage_drop_pct=losses["ac_voltage_drop_pct"],
                            ac_inv_td_voltage_drop_pct=losses["ac_inv_td_voltage_drop_pct"],
                            ac_td_meter_voltage_drop_pct=losses["ac_td_meter_voltage_drop_pct"],
                            total_loss_w=losses["total_loss_w"],
                            total_loss_pct=total_loss_pct,
                            surface_m2=surface,
                            surface_utilisee_pct=(surface / usable_surface * 100.0) if usable_surface else 0.0,
                            ratio_dc_ac=(puissance_dc / inverter.puissance_ac_w)
                            if inverter.puissance_ac_w
                            else 0.0,
                            umpp_stc_v=umpp_stc,
                            ecart_umpp_nominal_pct=ecart_umpp_nominal_pct,
                            uoc_froid_v=uoc_froid,
                            umpp_chaud_v=umpp_chaud,
                            umpp_froid_v=umpp_froid,
                            impp_mppt_a=impp_mppt,
                            isc_mppt_a=isc_mppt,
                        )
                    )

    if consommation_client_kwh > 0:
        candidates.sort(
            key=lambda item: (
                abs(item.ecart_conso_kwh) / consommation_client_kwh,
                max(0.0, item.ecart_conso_kwh),
                -item.puissance_dc_w,
            )
        )
    else:
        candidates.sort(
            key=lambda item: (
                item.puissance_dc_w,
                item.surface_utilisee_pct,
                -abs(item.ratio_dc_ac - 1.15),
            ),
            reverse=True,
        )
    return candidates, rejected


def format_kw(value_w: float) -> str:
    return f"{value_w / 1000:.2f}"


def format_num(value: float, decimals: int = 1) -> str:
    return f"{value:.{decimals}f}"

def format_signed_num(value: float, decimals: int = 1) -> str:
    return f"{value:+.{decimals}f}"


def rejected_lines(rejected: dict[str, int]) -> list[str]:
    labels = {
        "surface": "surface",
        "phase": "phase onduleur",
        "distribution": "limite reseau",
        "uoc_rgie": "Uoc froid RGIE",
        "uoc": "Uoc froid onduleur",
        "umpp_min": "Umpp sous MPPT min",
        "umpp_max": "Umpp au-dessus MPPT max",
        "courant": "courants MPPT/Isc",
        "puissance_pv": "puissance PV max",
        "pertes": "pertes > 2 %",
    }
    return [f"- Rejets {label} : {rejected.get(key, 0)}" for key, label in labels.items()]


def ranking_explanation(item: Candidate) -> list[str]:
    if item.consommation_client_kwh > 0:
        gap_ratio = abs(item.ecart_conso_kwh) / item.consommation_client_kwh * 100
        overproduction = max(0.0, item.ecart_conso_kwh)
        return [
            "- Critere 1 : minimiser l'ecart entre production annuelle nette et consommation client.",
            f"- Score ecart meilleur choix : abs({format_num(item.ecart_conso_kwh, 0)}) / {format_num(item.consommation_client_kwh, 0)} = {format_num(gap_ratio, 2)} %",
            "- Critere 2 : si deux ecarts sont identiques, eviter la surproduction.",
            f"- Surproduction du meilleur choix : {format_num(overproduction, 0)} kWh/an",
            "- Critere 3 : departager ensuite par puissance DC, surface utile exploitee, puis ratio DC/AC proche de 1,15.",
        ]
    return [
        "- Critere 1 : sans consommation client, maximiser la puissance DC installee.",
        "- Critere 2 : departager ensuite par surface utile exploitee.",
        "- Critere 3 : departager enfin par ratio DC/AC proche de 1,15.",
    ]


def build_calculation_report(
    item: Candidate,
    rejected: dict[str, int],
    result_count: int,
    surface_disponible_m2: float,
    taux_occupation_pct: float,
    panel_filter: str,
    inverter_filter: str,
    temperature_min_c: float,
    temperature_max_module_c: float,
) -> str:
    surface_utile = max(0.0, surface_disponible_m2 * taux_occupation_pct / 100.0)
    max_modules_surface = math.floor(surface_utile / item.panel.surface_m2) if item.panel.surface_m2 > 0 else 0
    coef_pct = item.panel.coef_tension_pct_c
    factor_cold = 1 + (coef_pct / 100.0) * (temperature_min_c - 25.0)
    factor_hot = 1 + (coef_pct / 100.0) * (temperature_max_module_c - 25.0)
    uoc_string_stc = item.panel.uoc_v * item.modules_par_string
    umpp_string_stc = item.panel.umpp_v * item.modules_par_string
    dc_string_voltage = item.panel.umpp_v * item.modules_par_string
    dc_return_length = item.modules_par_string * item.dc_return_per_panel_m
    dc_main_base_length = 2 * item.dc_distance_m
    dc_resistance = cable_resistance(item.dc_main_length_m, item.dc_section_mm2) + cable_resistance(
        item.dc_panel_cord_length_m, 4.0
    )
    dc_current = item.panel.impp_a
    ac_voltage, ac_current, _ac_conductors, _ac_drop_factor = ac_electrical_model(
        item.inverter, item.distribution_label
    )
    ac_inv_td_resistance = cable_resistance(item.ac_inv_td_distance_m, item.ac_inv_td_section_mm2)
    ac_td_meter_resistance = cable_resistance(item.ac_td_meter_distance_m, item.ac_td_meter_section_mm2)
    ac_total_distance = item.ac_inv_td_distance_m + item.ac_td_meter_distance_m
    rejected_total = sum(rejected.values())
    if item.consommation_client_kwh > 0:
        coverage_line = (
            f"- Couverture client : {format_num(item.production_annuelle_kwh, 0)} / "
            f"{format_num(item.consommation_client_kwh, 0)} x 100 = {format_num(item.taux_couverture_pct, 1)} %"
        )
    else:
        coverage_line = "- Couverture client : non calculee, consommation client non renseignee."

    lines = [
        "# Note de calcul - meilleur choix solaire",
        "",
        f"Version application : {APP_VERSION}",
        f"Auteur : {APP_AUTHOR}",
        f"Site : {APP_URL}",
        COPYRIGHT_NOTICE,
        f"Date export : {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## 1. Donnees d'entree",
        "",
        f"- Surface disponible : {format_num(surface_disponible_m2, 2)} m2",
        f"- Taux d'occupation : {format_num(taux_occupation_pct, 1)} %",
        f"- Surface utile : {format_num(surface_disponible_m2, 2)} x {format_num(taux_occupation_pct, 1)} / 100 = {format_num(surface_utile, 2)} m2",
        f"- Consommation client : {format_num(item.consommation_client_kwh, 0)} kWh/an",
        f"- Distribution : {item.distribution_label}, limite onduleur {format_kw(item.limite_distribution_va)} kVA",
        f"- Orientation / pente : {item.orientation_label}, {format_num(item.pente_deg, 0)} degres",
        f"- Gisement reference : {format_num(item.gisement_reference_kwh_kwc, 0)} kWh/kWc/an",
        f"- Temperature min / module max : {format_num(temperature_min_c, 0)} C / {format_num(temperature_max_module_c, 0)} C",
        f"- Filtres materiel : {panel_filter} / {inverter_filter}",
        "",
        "## 2. Materiel retenu",
        "",
        f"- Panneau : {item.panel.reference} ({item.panel.fabricant})",
        f"- Puissance panneau : {format_num(item.panel.puissance_w, 0)} Wc",
        f"- Dimensions panneau : {format_num(item.panel.largeur_m, 3)} x {format_num(item.panel.hauteur_m, 3)} m = {format_num(item.panel.surface_m2, 3)} m2",
        f"- Uoc / Isc / Umpp / Impp : {format_num(item.panel.uoc_v, 2)} V / {format_num(item.panel.isc_a, 2)} A / {format_num(item.panel.umpp_v, 2)} V / {format_num(item.panel.impp_a, 2)} A",
        f"- Coefficient tension : {format_num(coef_pct, 2)} %/C",
        f"- Onduleur : {item.inverter.reference} ({item.inverter.fabricant}, {item.inverter.phase})",
        f"- Puissance AC / PV max : {format_num(item.inverter.puissance_ac_w, 0)} W / {format_num(item.inverter.puissance_pv_max_w, 0)} W",
        f"- Plage MPPT : {format_num(item.inverter.mppt_min_v, 0)} a {format_num(item.inverter.mppt_max_v, 0)} V",
        f"- Tension DC nominale rated input : {format_num(item.inverter.tension_dc_nominale_v, 0)} V" if item.inverter.tension_dc_nominale_v > 0 else "- Tension DC nominale rated input : non renseignee",
        f"- Courant max MPPT / Isc max MPPT : {format_num(item.inverter.courant_max_mppt_a, 2)} A / {format_num(item.inverter.isc_max_mppt_a, 2)} A",
        "",
        "## 3. Construction de la configuration",
        "",
        f"- Modules max par surface : floor({format_num(surface_utile, 2)} / {format_num(item.panel.surface_m2, 3)}) = {max_modules_surface}",
        f"- Choix retenu : {item.nombre_strings} strings x {item.modules_par_string} modules/string = {item.total_modules} modules",
        f"- Repartition MPPT : {' / '.join(str(value) for value in item.repartition_mppt)}",
        f"- Surface utilisee : {item.total_modules} x {format_num(item.panel.surface_m2, 3)} = {format_num(item.surface_m2, 2)} m2 ({format_num(item.surface_utilisee_pct, 1)} % de la surface utile)",
        f"- Puissance DC : {item.total_modules} x {format_num(item.panel.puissance_w, 0)} = {format_num(item.puissance_dc_w, 0)} Wc ({format_kw(item.puissance_dc_w)} kWc)",
        f"- Ratio DC/AC : {format_num(item.puissance_dc_w, 0)} / {format_num(item.inverter.puissance_ac_w, 0)} = {format_num(item.ratio_dc_ac, 3)}",
        "",
        "## 4. Validations electriques DC",
        "",
        f"- Facteur froid : 1 + ({format_num(coef_pct, 2)} / 100) x ({format_num(temperature_min_c, 0)} - 25) = {format_num(factor_cold, 4)}",
        f"- Facteur chaud : 1 + ({format_num(coef_pct, 2)} / 100) x ({format_num(temperature_max_module_c, 0)} - 25) = {format_num(factor_hot, 4)}",
        f"- Uoc string STC : {format_num(item.panel.uoc_v, 2)} x {item.modules_par_string} = {format_num(uoc_string_stc, 2)} V",
        f"- Uoc froid : {format_num(uoc_string_stc, 2)} x {format_num(factor_cold, 4)} = {format_num(item.uoc_froid_v, 2)} V",
        f"- Validation RGIE : {format_num(item.uoc_froid_v, 2)} V <= {format_num(RGIE_UOC_FROID_MAX_V, 0)} V DC",
        f"- Validation onduleur : {format_num(item.uoc_froid_v, 2)} V <= {format_num(item.inverter.tension_dc_max_v, 0)} V DC max",
        f"- Umpp string STC : {format_num(item.panel.umpp_v, 2)} x {item.modules_par_string} = {format_num(umpp_string_stc, 2)} V",
        f"- Ecart au rated input : ({format_num(umpp_string_stc, 2)} - {format_num(item.inverter.tension_dc_nominale_v, 0)}) / {format_num(item.inverter.tension_dc_nominale_v, 0)} x 100 = {format_signed_num(item.ecart_umpp_nominal_pct, 2)} %" if item.inverter.tension_dc_nominale_v > 0 else "- Ecart au rated input : non calcule, tension nominale onduleur absente",
        f"- Umpp chaud : {format_num(umpp_string_stc, 2)} x {format_num(factor_hot, 4)} = {format_num(item.umpp_chaud_v, 2)} V >= MPPT min {format_num(item.inverter.mppt_min_v, 0)} V",
        f"- Umpp froid : {format_num(umpp_string_stc, 2)} x {format_num(factor_cold, 4)} = {format_num(item.umpp_froid_v, 2)} V <= MPPT max {format_num(item.inverter.mppt_max_v, 0)} V",
        f"- Impp par MPPT : max({' / '.join(str(value) for value in item.repartition_mppt)}) x {format_num(item.panel.impp_a, 2)} = {format_num(item.impp_mppt_a, 2)} A <= {format_num(item.inverter.courant_max_mppt_a, 2)} A",
        f"- Isc par MPPT : max({' / '.join(str(value) for value in item.repartition_mppt)}) x {format_num(item.panel.isc_a, 2)} = {format_num(item.isc_mppt_a, 2)} A <= {format_num(item.inverter.isc_max_mppt_a, 2)} A",
        f"- Puissance PV max onduleur : {format_num(item.puissance_dc_w, 0)} W <= {format_num(item.inverter.puissance_pv_max_w, 0)} W",
        "",
        "## 5. Pertes cables DC",
        "",
        f"- Longueur principale DC/string : 2 x {format_num(item.dc_distance_m, 2)} + ({item.modules_par_string} x {format_num(item.dc_return_per_panel_m, 2)}) = {format_num(dc_main_base_length, 2)} + {format_num(dc_return_length, 2)} = {format_num(item.dc_main_length_m, 2)} m",
        f"- Cordons panneaux : {item.modules_par_string} x {format_num(item.panel_cord_m, 2)} = {format_num(item.dc_panel_cord_length_m, 2)} m en 4 mm2",
        f"- Resistance DC/string : rho x L / S = {format_num(dc_resistance, 5)} ohm",
        f"- Chute tension DC/string : I x R = {format_num(dc_current, 2)} x {format_num(dc_resistance, 5)} = {format_num(item.dc_voltage_drop_v, 3)} V",
        f"- Reference tension string : {format_num(dc_string_voltage, 2)} V ; chute = {format_num(item.dc_voltage_drop_pct, 3)} %",
        f"- Perte Joule DC : I2 x R x strings = {format_num(dc_current, 2)}2 x {format_num(dc_resistance, 5)} x {item.nombre_strings} = {format_num(item.dc_loss_w, 2)} W",
        "",
        "## 6. Pertes cables AC",
        "",
        f"- Courant AC calcule : {format_num(ac_current, 2)} A sur reseau {format_num(ac_voltage, 0)} V",
        f"- Troncon onduleur-TD : {format_num(item.ac_inv_td_distance_m, 2)} m en {format_num(item.ac_inv_td_section_mm2, 0)} mm2, R = {format_num(ac_inv_td_resistance, 5)} ohm",
        f"- Perte onduleur-TD : {format_num(item.ac_inv_td_loss_w, 2)} W ; chute {format_num(item.ac_inv_td_voltage_drop_v, 3)} V = {format_num(item.ac_inv_td_voltage_drop_pct, 3)} % sur {format_num(item.ac_voltage_drop_reference_v, 0)} V",
        f"- Troncon TD-compteur : {format_num(item.ac_td_meter_distance_m, 2)} m en {format_num(item.ac_td_meter_section_mm2, 0)} mm2, R = {format_num(ac_td_meter_resistance, 5)} ohm",
        f"- Perte TD-compteur : {format_num(item.ac_td_meter_loss_w, 2)} W ; chute {format_num(item.ac_td_meter_voltage_drop_v, 3)} V = {format_num(item.ac_td_meter_voltage_drop_pct, 3)} % sur {format_num(item.ac_voltage_drop_reference_v, 0)} V",
        f"- Distance AC totale : {format_num(ac_total_distance, 2)} m",
        f"- Pertes AC totales : {format_num(item.ac_loss_w, 2)} W ; chute {format_num(item.ac_voltage_drop_v, 3)} V = {format_num(item.ac_voltage_drop_pct, 3)} % sur {format_num(item.ac_voltage_drop_reference_v, 0)} V",
        f"- Pertes Joule totales : {format_num(item.dc_loss_w, 2)} + {format_num(item.ac_loss_w, 2)} = {format_num(item.total_loss_w, 2)} W",
        f"- Taux pertes total : {format_num(item.total_loss_w, 2)} / {format_num(item.puissance_dc_w, 0)} x 100 = {format_num(item.total_loss_pct, 3)} % <= {format_num(MAX_JOULE_LOSS_PCT, 1)} %",
        "",
        "## 7. Production estimee",
        "",
        f"- Coefficient exposition : {format_num(item.facteur_orientation, 3)} orientation x {format_num(item.facteur_pente, 3)} pente = {format_num(item.coefficient_exposition, 3)}",
        f"- Production brute : {format_num(item.puissance_dc_w / 1000, 3)} kWc x {format_num(item.gisement_reference_kwh_kwc, 0)} x {format_num(item.coefficient_exposition, 3)} = {format_num(item.production_brute_kwh, 0)} kWh/an",
        f"- Production nette : {format_num(item.production_brute_kwh, 0)} x (1 - {format_num(item.total_loss_pct, 3)} / 100) = {format_num(item.production_annuelle_kwh, 0)} kWh/an",
        coverage_line,
        f"- Ecart production - consommation : {format_num(item.production_annuelle_kwh, 0)} - {format_num(item.consommation_client_kwh, 0)} = {format_num(item.ecart_conso_kwh, 0)} kWh/an",
        "",
        "## 8. Suite logique des decisions",
        "",
        f"- Configurations valides : {result_count}",
        f"- Rejets pendant la recherche : {rejected_total}",
        *rejected_lines(rejected),
        "",
        *ranking_explanation(item),
        "",
        "## 9. Conclusion",
        "",
        f"Le meilleur choix actuel est {item.total_modules} modules {item.panel.reference} avec onduleur {item.inverter.reference}.",
        f"Il produit environ {format_num(item.production_annuelle_kwh, 0)} kWh/an nets pour {format_num(item.consommation_client_kwh, 0)} kWh/an de consommation client, avec {format_num(item.total_loss_pct, 2)} % de pertes Joule.",
        "Le facteur prix n'est pas encore integre ; l'export prepare la logique pour ajouter ce critere plus tard.",
    ]
    return "\n".join(lines)


class SolarOptimizerApp:
    def __init__(self, root: tk.Tk, base_dir: Path) -> None:
        self.root = root
        self.base_dir = base_dir
        self.panels_path = base_dir / "panneaux.csv"
        self.inverters_path = base_dir / "onduleurs.csv"
        self.panels: list[Panel] = []
        self.inverters: list[Inverter] = []
        self.results: list[Candidate] = []
        self.rejected: dict[str, int] = {}
        self.combos: dict[str, ttk.Combobox] = {}

        root.title(APP_TITLE)
        root.geometry("1180x720")
        root.minsize(980, 620)

        self.surface_var = tk.StringVar(value="40")
        self.occupation_var = tk.StringVar(value="85")
        self.consommation_var = tk.StringVar(value="4500")
        self.distribution_var = tk.StringVar(value="Mono")
        self.panel_filter_var = tk.StringVar(value=ALL_PANELS_LABEL)
        self.inverter_filter_var = tk.StringVar(value=ALL_INVERTERS_LABEL)
        self.orientation_var = tk.StringVar(value="Sud")
        self.pente_var = tk.StringVar(value="35")
        self.gisement_var = tk.StringVar(value="950")
        self.dc_distance_var = tk.StringVar(value="15")
        self.dc_section_var = tk.StringVar(value="6")
        self.dc_return_per_panel_var = tk.StringVar(value="1.13")
        self.panel_cord_var = tk.StringVar(value="1.2")
        self.ac_inv_td_distance_var = tk.StringVar(value="10")
        self.ac_inv_td_section_var = tk.StringVar(value="6")
        self.ac_td_meter_distance_var = tk.StringVar(value="10")
        self.ac_td_meter_section_var = tk.StringVar(value="10")
        self.tmin_var = tk.StringVar(value="-10")
        self.tmax_var = tk.StringVar(value="70")
        self.limit_var = tk.StringVar(value="50")
        self.status_var = tk.StringVar(value="")

        self._build_ui()
        self.reload_catalogs(show_popup=False)
        self.calculate()

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=12)
        outer.pack(fill=BOTH, expand=True)

        top = ttk.Frame(outer)
        top.pack(fill=X, side=TOP)

        site = ttk.LabelFrame(top, text="Contraintes du site", padding=10)
        site.pack(side=LEFT, fill=X, expand=True, padx=(0, 8))

        self._field(site, "Surface disponible (m2)", self.surface_var, 0, 0)
        self._field(site, "Occupation (%)", self.occupation_var, 0, 2)
        self._field(site, "Conso client (kWh/an)", self.consommation_var, 1, 0)
        self._combo(site, "Type de distribution", self.distribution_var, list(DISTRIBUTION_LIMITS_VA), 1, 2)
        self._combo(site, "Filtre panneau", self.panel_filter_var, [ALL_PANELS_LABEL], 2, 0)
        self._combo(site, "Filtre onduleur", self.inverter_filter_var, [ALL_INVERTERS_LABEL], 2, 2)
        self._combo(site, "Orientation toiture", self.orientation_var, list(ORIENTATION_OPTIONS), 3, 0)
        self._field(site, "Pente toiture (degres)", self.pente_var, 3, 2)
        self._field(site, "Gisement ref. (kWh/kWc/an)", self.gisement_var, 4, 0)
        self._field(site, "Distance DC/string (m)", self.dc_distance_var, 4, 2)
        self._combo(site, "Section DC (mm2)", self.dc_section_var, ["4", "6", "10", "16"], 5, 0)
        self._field(site, "Retour/panneau (m)", self.dc_return_per_panel_var, 5, 2)
        self._field(site, "Cordons 4mm2/module (m)", self.panel_cord_var, 6, 0)
        self._field(site, "Distance onduleur-TD (m)", self.ac_inv_td_distance_var, 6, 2)
        self._combo(site, "Section onduleur-TD (mm2)", self.ac_inv_td_section_var, ["4", "6", "10", "16"], 7, 0)
        self._field(site, "Distance TD-compteur (m)", self.ac_td_meter_distance_var, 7, 2)
        self._combo(site, "Section TD-compteur (mm2)", self.ac_td_meter_section_var, ["6", "10", "16"], 8, 0)
        self._field(site, "Temperature min (C)", self.tmin_var, 8, 2)
        self._field(site, "Temperature module max (C)", self.tmax_var, 9, 0)
        self._field(site, "Resultats max", self.limit_var, 9, 2)

        actions = ttk.LabelFrame(top, text="Actions", padding=10)
        actions.pack(side=RIGHT, fill=Y)
        ttk.Button(actions, text="Calculer", command=self.calculate).pack(fill=X, pady=(0, 6))
        ttk.Button(actions, text="Recharger catalogues", command=self.reload_catalogs).pack(fill=X, pady=(0, 6))
        ttk.Button(actions, text="Exporter CSV", command=self.export_results).pack(fill=X, pady=(0, 6))
        ttk.Button(actions, text="Exporter calcul", command=self.export_calculation).pack(fill=X)

        body = ttk.PanedWindow(outer, orient=tk.VERTICAL)
        body.pack(fill=BOTH, expand=True, pady=(12, 8))

        table_frame = ttk.Frame(body)
        body.add(table_frame, weight=4)

        columns = (
            "rang",
            "panneau",
            "onduleur",
            "modules",
            "strings",
            "surface",
            "pdc",
            "prod",
            "couverture",
            "pac",
            "ratio",
            "pertes",
            "uoc",
            "umpp",
            "ecart_nominal",
            "isc",
        )
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=14)
        headings = {
            "rang": "#",
            "panneau": "Panneau",
            "onduleur": "Onduleur",
            "modules": "Modules",
            "strings": "Strings",
            "surface": "Surface m2",
            "pdc": "Pdc kWc",
            "prod": "Prod/an kWh",
            "couverture": "Couv. %",
            "pac": "Pac kW",
            "ratio": "DC/AC",
            "pertes": "Pertes %",
            "uoc": "Uoc froid V",
            "umpp": "Umpp V",
            "ecart_nominal": "Ecart rated %",
            "isc": "Isc/MPPT A",
        }
        widths = {
            "rang": 44,
            "panneau": 145,
            "onduleur": 145,
            "modules": 75,
            "strings": 120,
            "surface": 95,
            "pdc": 85,
            "prod": 95,
            "couverture": 80,
            "pac": 75,
            "ratio": 75,
            "pertes": 80,
            "uoc": 95,
            "umpp": 120,
            "ecart_nominal": 105,
            "isc": 95,
        }
        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(column, width=widths[column], anchor=tk.CENTER, stretch=column in {"panneau", "onduleur"})

        scroll_y = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scroll_x = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        scroll_x.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        self.tree.bind("<<TreeviewSelect>>", self.show_selected_detail)

        detail_frame = ttk.LabelFrame(body, text="Detail de la configuration", padding=8)
        body.add(detail_frame, weight=2)
        self.detail = tk.Text(detail_frame, height=9, wrap="word")
        self.detail.pack(fill=BOTH, expand=True)
        self.detail.configure(state="disabled")

        ttk.Label(outer, textvariable=self.status_var).pack(anchor="w")

    def _field(self, parent: ttk.LabelFrame, label: str, variable: tk.StringVar, row: int, col: int) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=col, sticky="w", padx=(0, 8), pady=4)
        entry = ttk.Entry(parent, textvariable=variable, width=16)
        entry.grid(row=row, column=col + 1, sticky="ew", padx=(0, 16), pady=4)
        entry.bind("<Return>", lambda _event: self.calculate())
        parent.columnconfigure(col + 1, weight=1)

    def _combo(self, parent: ttk.LabelFrame, label: str, variable: tk.StringVar, values: list[str], row: int, col: int) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=col, sticky="w", padx=(0, 8), pady=4)
        combo = ttk.Combobox(parent, textvariable=variable, values=values, width=14, state="readonly")
        combo.grid(row=row, column=col + 1, sticky="ew", padx=(0, 16), pady=4)
        combo.bind("<<ComboboxSelected>>", lambda _event: self.calculate())
        self.combos[label] = combo
        parent.columnconfigure(col + 1, weight=1)

    def _refresh_filter_options(self) -> None:
        panel_values = [ALL_PANELS_LABEL] + [panel.reference for panel in self.panels]
        allowed_inverters = allowed_inverters_for_distribution(self.inverters, self.distribution_var.get())
        inverter_values = [ALL_INVERTERS_LABEL] + [inverter.reference for inverter in allowed_inverters]
        self.combos["Filtre panneau"].configure(values=panel_values)
        self.combos["Filtre onduleur"].configure(values=inverter_values)
        if self.panel_filter_var.get() not in panel_values:
            self.panel_filter_var.set(ALL_PANELS_LABEL)
        if self.inverter_filter_var.get() not in inverter_values:
            self.inverter_filter_var.set(ALL_INVERTERS_LABEL)

    def _filtered_catalogs(self) -> tuple[list[Panel], list[Inverter], str, str]:
        panel_filter = self.panel_filter_var.get()
        inverter_filter = self.inverter_filter_var.get()
        panels = self.panels if panel_filter == ALL_PANELS_LABEL else [
            panel for panel in self.panels if panel.reference == panel_filter
        ]
        allowed_inverters = allowed_inverters_for_distribution(self.inverters, self.distribution_var.get())
        inverters = allowed_inverters if inverter_filter == ALL_INVERTERS_LABEL else [
            inverter for inverter in allowed_inverters if inverter.reference == inverter_filter
        ]
        return panels, inverters, panel_filter, inverter_filter

    def reload_catalogs(self, show_popup: bool = True) -> None:
        try:
            self.panels = load_panels(self.panels_path)
            self.inverters = load_inverters(self.inverters_path)
        except Exception as exc:
            messagebox.showerror("Erreur catalogue", str(exc))
            return

        self.status_var.set(
            f"Catalogues charges : {len(self.panels)} panneaux, {len(self.inverters)} onduleurs"
        )
        self._refresh_filter_options()
        if show_popup:
            messagebox.showinfo("Catalogues", "Catalogues recharges.")

    def calculate(self) -> None:
        try:
            surface = parse_float(self.surface_var.get())
            occupation = parse_float(self.occupation_var.get())
            consommation = parse_float(self.consommation_var.get())
            distribution = self.distribution_var.get()
            orientation = self.orientation_var.get()
            pente = parse_float(self.pente_var.get())
            gisement = parse_float(self.gisement_var.get())
            dc_distance = parse_float(self.dc_distance_var.get())
            dc_section = parse_float(self.dc_section_var.get())
            dc_return_per_panel = parse_float(self.dc_return_per_panel_var.get())
            panel_cord = parse_float(self.panel_cord_var.get())
            ac_inv_td_distance = parse_float(self.ac_inv_td_distance_var.get())
            ac_inv_td_section = parse_float(self.ac_inv_td_section_var.get())
            ac_td_meter_distance = parse_float(self.ac_td_meter_distance_var.get())
            ac_td_meter_section = parse_float(self.ac_td_meter_section_var.get())
            tmin = parse_float(self.tmin_var.get())
            tmax = parse_float(self.tmax_var.get())
            limit = max(1, parse_int(self.limit_var.get()))
        except ValueError:
            messagebox.showerror("Valeur invalide", "Verifie les valeurs saisies.")
            return

        if surface <= 0 or occupation <= 0:
            messagebox.showerror("Valeur invalide", "La surface et le taux d'occupation doivent etre positifs.")
            return
        if consommation < 0 or gisement <= 0 or pente < 0 or pente > 90:
            messagebox.showerror("Valeur invalide", "Verifie la conso, le gisement et la pente toiture.")
            return
        if min(dc_distance, dc_return_per_panel, panel_cord, ac_inv_td_distance, ac_td_meter_distance) < 0:
            messagebox.showerror("Valeur invalide", "Verifie les distances de cable.")
            return

        self._refresh_filter_options()
        filtered_panels, filtered_inverters, panel_filter, inverter_filter = self._filtered_catalogs()
        self.results, self.rejected = optimize(
            filtered_panels,
            filtered_inverters,
            surface,
            occupation,
            consommation,
            distribution,
            orientation,
            pente,
            gisement,
            dc_distance,
            dc_section,
            dc_return_per_panel,
            panel_cord,
            ac_inv_td_distance,
            ac_inv_td_section,
            ac_td_meter_distance,
            ac_td_meter_section,
            tmin,
            tmax,
        )
        visible_results = self.results[:limit]
        self.tree.delete(*self.tree.get_children())
        for index, item in enumerate(visible_results, start=1):
            strings_label = f"{item.nombre_strings} x {item.modules_par_string}"
            self.tree.insert(
                "",
                END,
                iid=str(index - 1),
                values=(
                    index,
                    item.panel.reference,
                    item.inverter.reference,
                    item.total_modules,
                    strings_label,
                    format_num(item.surface_m2, 1),
                    format_kw(item.puissance_dc_w),
                    format_num(item.production_annuelle_kwh, 0),
                    format_num(item.taux_couverture_pct, 0),
                    format_kw(item.inverter.puissance_ac_w),
                    format_num(item.ratio_dc_ac, 2),
                    format_num(item.total_loss_pct, 2),
                    format_num(item.uoc_froid_v, 0),
                    f"{format_num(item.umpp_chaud_v, 0)}-{format_num(item.umpp_froid_v, 0)}",
                    format_signed_num(item.ecart_umpp_nominal_pct, 1) if item.inverter.tension_dc_nominale_v > 0 else "-",
                    format_num(item.isc_mppt_a, 1),
                ),
            )

        total_rejected = sum(self.rejected.values())
        self.status_var.set(
            f"{len(self.results)} configurations valides, filtres : {panel_filter} / {inverter_filter}, {total_rejected} ecartees."
        )
        if visible_results:
            self.tree.selection_set("0")
            self.tree.focus("0")
            self.show_selected_detail()
        else:
            self._set_detail("Aucune configuration valide avec les catalogues et contraintes actuels.")

    def show_selected_detail(self, _event: object | None = None) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        index = int(selected[0])
        if index >= len(self.results):
            return
        item = self.results[index]
        text = "\n".join(
            [
                f"Panneau : {item.panel.reference} ({item.panel.fabricant})",
                f"Onduleur : {item.inverter.reference} ({item.inverter.fabricant}, {item.inverter.phase})",
                f"Filtres actifs : {self.panel_filter_var.get()} / {self.inverter_filter_var.get()}",
                f"Architecture : {item.nombre_strings} strings de {item.modules_par_string} modules, repartition MPPT {item.repartition_mppt}",
                f"Puissance DC : {format_kw(item.puissance_dc_w)} kWc ; puissance AC : {format_kw(item.inverter.puissance_ac_w)} kW ; ratio DC/AC : {format_num(item.ratio_dc_ac, 2)}",
                f"Repere DC nominal : Umpp STC string {format_num(item.umpp_stc_v, 1)} V ; rated input {format_num(item.inverter.tension_dc_nominale_v, 1)} V ; ecart {format_signed_num(item.ecart_umpp_nominal_pct, 1)} %" if item.inverter.tension_dc_nominale_v > 0 else "Repere DC nominal : rated input non renseigne pour cet onduleur",
                f"Surface utilisee : {format_num(item.surface_m2, 2)} m2 ({format_num(item.surface_utilisee_pct, 1)} % de la surface utile)",
                f"Client : conso {format_num(item.consommation_client_kwh, 0)} kWh/an ; production brute {format_num(item.production_brute_kwh, 0)} kWh/an ; production nette {format_num(item.production_annuelle_kwh, 0)} kWh/an ; couverture {format_num(item.taux_couverture_pct, 1)} %",
                f"Distribution : {item.distribution_label}, limite onduleur {format_kw(item.limite_distribution_va)} kVA",
                f"Exposition : {item.orientation_label}, pente {format_num(item.pente_deg, 0)} degres, coefficient {format_num(item.coefficient_exposition, 2)} ({format_num(item.facteur_orientation, 2)} orientation x {format_num(item.facteur_pente, 2)} pente)",
                f"Pertes DC : {format_num(item.dc_loss_w, 1)} W ; chute {format_num(item.dc_voltage_drop_v, 2)} V ({format_num(item.dc_voltage_drop_pct, 2)} %) ; longueur string {format_num(item.dc_main_length_m, 2)} m en {format_num(item.dc_section_mm2, 0)} mm2 + cordons {format_num(item.dc_panel_cord_length_m, 2)} m en 4 mm2",
                f"Schema : PV -> onduleur -> TD -> compteur",
                f"Pertes AC onduleur-TD : {format_num(item.ac_inv_td_loss_w, 1)} W ; chute {format_num(item.ac_inv_td_voltage_drop_v, 2)} V ({format_num(item.ac_inv_td_voltage_drop_pct, 2)} % sur {format_num(item.ac_voltage_drop_reference_v, 0)} V) ; {format_num(item.ac_inv_td_distance_m, 1)} m en {format_num(item.ac_inv_td_section_mm2, 0)} mm2",
                f"Pertes AC TD-compteur : {format_num(item.ac_td_meter_loss_w, 1)} W ; chute {format_num(item.ac_td_meter_voltage_drop_v, 2)} V ({format_num(item.ac_td_meter_voltage_drop_pct, 2)} % sur {format_num(item.ac_voltage_drop_reference_v, 0)} V) ; {format_num(item.ac_td_meter_distance_m, 1)} m en {format_num(item.ac_td_meter_section_mm2, 0)} mm2",
                f"Pertes AC totales : {format_num(item.ac_loss_w, 1)} W ; chute {format_num(item.ac_voltage_drop_v, 2)} V ({format_num(item.ac_voltage_drop_pct, 2)} % sur {format_num(item.ac_voltage_drop_reference_v, 0)} V)",
                f"Pertes totales : {format_num(item.total_loss_w, 1)} W ({format_num(item.total_loss_pct, 2)} %)",
                "",
                "Controles valides :",
                f"- Uoc froid = {format_num(item.uoc_froid_v, 1)} V <= limite RGIE {format_num(RGIE_UOC_FROID_MAX_V, 0)} V DC",
                f"- Uoc froid = {format_num(item.uoc_froid_v, 1)} V <= tension DC max onduleur {format_num(item.inverter.tension_dc_max_v, 1)} V",
                f"- Umpp chaud = {format_num(item.umpp_chaud_v, 1)} V >= MPPT min {format_num(item.inverter.mppt_min_v, 1)} V",
                f"- Umpp froid = {format_num(item.umpp_froid_v, 1)} V <= MPPT max {format_num(item.inverter.mppt_max_v, 1)} V",
                f"- Repere rated input : Umpp STC {format_num(item.umpp_stc_v, 1)} V vs nominal {format_num(item.inverter.tension_dc_nominale_v, 1)} V = {format_signed_num(item.ecart_umpp_nominal_pct, 1)} %" if item.inverter.tension_dc_nominale_v > 0 else "- Repere rated input : non renseigne, non bloquant",
                f"- Impp par MPPT = {format_num(item.impp_mppt_a, 1)} A <= courant max {format_num(item.inverter.courant_max_mppt_a, 1)} A",
                f"- Isc par MPPT = {format_num(item.isc_mppt_a, 1)} A <= Isc max {format_num(item.inverter.isc_max_mppt_a, 1)} A",
                f"- Puissance PV = {format_num(item.puissance_dc_w, 0)} W <= puissance PV max {format_num(item.inverter.puissance_pv_max_w, 0)} W",
                f"- Puissance AC onduleur = {format_kw(item.inverter.puissance_ac_w)} kVA <= limite distribution {format_kw(item.limite_distribution_va)} kVA",
                f"- Pertes Joule totales = {format_num(item.total_loss_pct, 2)} % <= {format_num(MAX_JOULE_LOSS_PCT, 1)} %",
            ]
        )
        self._set_detail(text)

    def _set_detail(self, text: str) -> None:
        self.detail.configure(state="normal")
        self.detail.delete("1.0", END)
        self.detail.insert("1.0", text)
        self.detail.configure(state="disabled")

    def export_results(self) -> None:
        if not self.results:
            messagebox.showinfo("Export", "Aucun resultat a exporter.")
            return

        path = filedialog.asksaveasfilename(
            title="Exporter les resultats",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")],
            initialfile="resultats_dimensionnement_solaire.csv",
        )
        if not path:
            return

        with Path(path).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "rang",
                    "panneau",
                    "onduleur",
                    "filtre_panneau",
                    "filtre_onduleur",
                    "modules",
                    "nombre_strings",
                    "modules_par_string",
                    "repartition_mppt",
                    "surface_m2",
                    "puissance_dc_kwc",
                    "production_brute_kwh",
                    "production_annuelle_kwh",
                    "consommation_client_kwh_an",
                    "taux_couverture_pct",
                    "ecart_conso_kwh",
                    "coefficient_exposition",
                    "type_distribution",
                    "limite_distribution_kva",
                    "pertes_totales_w",
                    "pertes_totales_pct",
                    "pertes_dc_w",
                    "chute_tension_dc_v",
                    "chute_tension_dc_pct",
                    "distance_dc_onduleur_panneaux_m",
                    "section_dc_mm2",
                    "retour_string_m",
                    "cordons_panneaux_4mm2_m",
                    "pertes_ac_w",
                    "pertes_ac_onduleur_td_w",
                    "pertes_ac_td_compteur_w",
                    "chute_tension_ac_v",
                    "chute_tension_ac_onduleur_td_v",
                    "chute_tension_ac_td_compteur_v",
                    "chute_tension_ac_pct",
                    "reference_pct_chute_ac_v",
                    "chute_tension_ac_onduleur_td_pct",
                    "chute_tension_ac_td_compteur_pct",
                    "distance_ac_onduleur_td_m",
                    "section_ac_onduleur_td_mm2",
                    "distance_ac_td_compteur_m",
                    "section_ac_td_compteur_mm2",
                    "orientation",
                    "pente_deg",
                    "gisement_reference_kwh_kwc_an",
                    "puissance_ac_kw",
                    "ratio_dc_ac",
                    "uoc_froid_v",
                    "limite_rgie_uoc_froid_v",
                    "umpp_chaud_v",
                    "umpp_froid_v",
                    "umpp_stc_v",
                    "tension_dc_nominale_onduleur_v",
                    "ecart_umpp_nominal_pct",
                    "impp_mppt_a",
                    "isc_mppt_a",
                ]
            )
            for index, item in enumerate(self.results, start=1):
                writer.writerow(
                    [
                        index,
                        item.panel.reference,
                        item.inverter.reference,
                        self.panel_filter_var.get(),
                        self.inverter_filter_var.get(),
                        item.total_modules,
                        item.nombre_strings,
                        item.modules_par_string,
                        " / ".join(str(value) for value in item.repartition_mppt),
                        round(item.surface_m2, 2),
                        round(item.puissance_dc_w / 1000, 3),
                        round(item.production_brute_kwh, 0),
                        round(item.production_annuelle_kwh, 0),
                        round(item.consommation_client_kwh, 0),
                        round(item.taux_couverture_pct, 2),
                        round(item.ecart_conso_kwh, 0),
                        round(item.coefficient_exposition, 3),
                        item.distribution_label,
                        round(item.limite_distribution_va / 1000, 2),
                        round(item.total_loss_w, 2),
                        round(item.total_loss_pct, 3),
                        round(item.dc_loss_w, 2),
                        round(item.dc_voltage_drop_v, 3),
                        round(item.dc_voltage_drop_pct, 3),
                        round(item.dc_distance_m, 2),
                        round(item.dc_section_mm2, 0),
                        round(item.modules_par_string * item.dc_return_per_panel_m, 2),
                        round(item.dc_panel_cord_length_m, 2),
                        round(item.ac_loss_w, 2),
                        round(item.ac_inv_td_loss_w, 2),
                        round(item.ac_td_meter_loss_w, 2),
                        round(item.ac_voltage_drop_v, 3),
                        round(item.ac_inv_td_voltage_drop_v, 3),
                        round(item.ac_td_meter_voltage_drop_v, 3),
                        round(item.ac_voltage_drop_pct, 3),
                        round(item.ac_voltage_drop_reference_v, 0),
                        round(item.ac_inv_td_voltage_drop_pct, 3),
                        round(item.ac_td_meter_voltage_drop_pct, 3),
                        round(item.ac_inv_td_distance_m, 2),
                        round(item.ac_inv_td_section_mm2, 0),
                        round(item.ac_td_meter_distance_m, 2),
                        round(item.ac_td_meter_section_mm2, 0),
                        item.orientation_label,
                        round(item.pente_deg, 0),
                        round(item.gisement_reference_kwh_kwc, 0),
                        round(item.inverter.puissance_ac_w / 1000, 3),
                        round(item.ratio_dc_ac, 3),
                        round(item.uoc_froid_v, 2),
                        round(RGIE_UOC_FROID_MAX_V, 0),
                        round(item.umpp_chaud_v, 2),
                        round(item.umpp_froid_v, 2),
                        round(item.umpp_stc_v, 2),
                        round(item.inverter.tension_dc_nominale_v, 2),
                        round(item.ecart_umpp_nominal_pct, 3) if item.inverter.tension_dc_nominale_v > 0 else "",
                        round(item.impp_mppt_a, 2),
                        round(item.isc_mppt_a, 2),
                    ]
                )

        messagebox.showinfo("Export", f"Resultats exportes vers :\n{path}")

    def export_calculation(self) -> None:
        if not self.results:
            messagebox.showinfo("Export calcul", "Aucun resultat a exporter.")
            return

        try:
            surface = parse_float(self.surface_var.get())
            occupation = parse_float(self.occupation_var.get())
            tmin = parse_float(self.tmin_var.get())
            tmax = parse_float(self.tmax_var.get())
        except ValueError:
            messagebox.showerror("Valeur invalide", "Verifie les valeurs saisies avant l'export calcul.")
            return

        path = filedialog.asksaveasfilename(
            title="Exporter la note de calcul",
            defaultextension=".md",
            filetypes=[("Markdown", "*.md"), ("Texte", "*.txt")],
            initialfile=f"note_calcul_solaire_{datetime.now().date().isoformat()}.md",
        )
        if not path:
            return

        report = build_calculation_report(
            self.results[0],
            self.rejected,
            len(self.results),
            surface,
            occupation,
            self.panel_filter_var.get(),
            self.inverter_filter_var.get(),
            tmin,
            tmax,
        )
        Path(path).write_text(report, encoding="utf-8")
        messagebox.showinfo("Export calcul", f"Note de calcul exportee vers :\n{path}")


def run_app() -> None:
    base_dir = INPUT_DIR
    root = tk.Tk()
    SolarOptimizerApp(root, base_dir)
    root.mainloop()


def run_self_test() -> None:
    base_dir = INPUT_DIR
    panels = load_panels(base_dir / "panneaux.csv")
    inverters = load_inverters(base_dir / "onduleurs.csv")
    results, rejected = optimize(
        panels=panels,
        inverters=inverters,
        surface_disponible_m2=40,
        taux_occupation_pct=85,
        consommation_client_kwh=4500,
        distribution_label="Mono",
        orientation_label="Sud",
        pente_deg=35,
        gisement_reference_kwh_kwc=950,
        dc_distance_m=15,
        dc_section_mm2=6,
        dc_return_per_panel_m=1.13,
        panel_cord_m=1.2,
        ac_inv_td_distance_m=10,
        ac_inv_td_section_mm2=6,
        ac_td_meter_distance_m=10,
        ac_td_meter_section_mm2=10,
        temperature_min_c=-10,
        temperature_max_module_c=70,
    )
    if not results:
        raise SystemExit("Aucun resultat valide pendant le test.")
    best = results[0]
    report = build_calculation_report(best, rejected, len(results), 40, 85, ALL_PANELS_LABEL, ALL_INVERTERS_LABEL, -10, 70)
    if "Note de calcul" not in report or "Suite logique des decisions" not in report:
        raise SystemExit("La note de calcul n'a pas ete generee correctement.")
    print(f"OK - {len(results)} configurations valides")
    print(
        f"Meilleure config: {best.panel.reference} + {best.inverter.reference}, "
        f"{best.total_modules} modules, {best.puissance_dc_w / 1000:.2f} kWc, "
        f"{best.production_annuelle_kwh:.0f} kWh/an, couverture {best.taux_couverture_pct:.0f}%"
    )
    print(f"Note de calcul: {len(report.splitlines())} lignes")
    print(f"Rejets: {rejected}")


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        run_self_test()
    else:
        run_app()
