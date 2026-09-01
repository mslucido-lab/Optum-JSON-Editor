"""
main.py

Version: v2.0.16
Date: 2026-05-09
Project: Pricing Page JSON Editor
Purpose: FastAPI backend for the v2.0 local web app.
         Serves index.html, handles file save, and exposes validation endpoints.
         File open is handled client-side (File System Access API) — no /open route needed.
"""

import copy
import hashlib
import html
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel


APP_VERSION = "v2.0.16"

app = FastAPI(title="Pricing Editor", version=APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SaveRequest(BaseModel):
    path: str
    data: Dict[str, Any]


class ValidateRequest(BaseModel):
    data: Dict[str, Any]


@app.get("/")
async def serve_index():
    index_path = Path(__file__).parent / "index.html"
    if not index_path.exists():
        return JSONResponse({"error": "index.html not found"}, status_code=404)
    return FileResponse(str(index_path), media_type="text/html")


@app.get("/health")
async def health():
    return {"status": "ok", "version": APP_VERSION}


@app.get("/version")
async def version():
    return {"app": "Pricing Editor", "version": APP_VERSION}


@app.post("/save")
async def save_file(request: SaveRequest):
    try:
        if not request.path or not str(request.path).lower().endswith(".json"):
            raise ValueError("Save path must be a full .json file path.")

        target_path = Path(request.path)
        target_parent = target_path.parent
        if not target_parent.exists():
            raise FileNotFoundError(f"Target folder does not exist: {target_parent}")
        if not target_parent.is_dir():
            raise NotADirectoryError(f"Target parent is not a folder: {target_parent}")

        versioned_name = make_versioned_filename(target_path.name)
        versioned_path = target_parent / versioned_name

        with open(versioned_path, "w", encoding="utf-8") as f:
            json.dump(request.data, f, indent=2, ensure_ascii=False)

        return {
            "saved_as": versioned_name,
            "path": str(versioned_path),
            "version": APP_VERSION,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/validate")
async def validate(request: ValidateRequest):
    errors: List[str] = []
    errors.extend(validate_json_structure(request.data))
    errors.extend(validate_contract_term_defaults(request.data))
    errors.extend(validate_orphan_term_references(request.data))
    errors.extend(validate_editor_business_rules(request.data))
    return {
        "errors": errors,
        "valid": len(errors) == 0,
        "version": APP_VERSION,
    }


# --- Business logic ported from app_json_editor_v1_7_5.py ---

# Utility functions
def deep_copy_json(data: Any) -> Any:
    return copy.deepcopy(data)

def safe_json_dumps(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)

def make_versioned_filename(original_name: str, app_version: str = APP_VERSION) -> str:
    base = re.sub(r"\.json$", "", original_name, flags=re.IGNORECASE)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    version_label = app_version.replace(".", "_")
    return f"{base}_{version_label}_{stamp}.json"

def format_money(value: Any) -> str:
    try:
        number = float(value)
        if number.is_integer():
            return f"${int(number):,}"
        return f"${number:,.2f}"
    except Exception:
        if value in ("", None):
            return ""
        return f"${value}"

def clean_preview_text(text: str) -> str:
    if not text:
        return ""

    text = str(text)
    text = html.unescape(text)

    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</li>\s*", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<li[^>]*>\s*", "• ", text, flags=re.IGNORECASE)

    text = re.sub(r"</p>\s*", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<p[^>]*>\s*", "", text, flags=re.IGNORECASE)

    text = re.sub(r"</div>\s*", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<div[^>]*>\s*", "", text, flags=re.IGNORECASE)

    text = re.sub(r"<[^>]+>", "", text)

    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)

    return text.strip()

def truncate_preview_text(text: str, max_chars: int) -> str:
    cleaned = clean_preview_text(text)
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 1].rstrip() + "…"


# Validation functions
def validate_json_structure(data: Dict[str, Any]) -> List[str]:
    errors: List[str] = []

    required_top_level = ["name", "description", "slug", "contractTerms", "packages"]
    for key in required_top_level:
        if key not in data:
            errors.append(f"Missing required top-level key: {key}")

    if "packages" in data and not isinstance(data["packages"], list):
        errors.append("packages must be a list")

    if "contractTerms" in data and not isinstance(data["contractTerms"], dict):
        errors.append("contractTerms must be an object")

    contract_terms = data.get("contractTerms", {})
    if isinstance(contract_terms, dict):
        for key in ["contractInitialTerm", "contractAutoRenewalTerm"]:
            if key in contract_terms and not isinstance(contract_terms[key], list):
                errors.append(f"contractTerms.{key} must be a list")

    packages = data.get("packages", [])
    if isinstance(packages, list):
        for i, package in enumerate(packages):
            if not isinstance(package, dict):
                errors.append(f"packages[{i}] must be an object")
                continue
            if "name" not in package:
                errors.append(f"packages[{i}] is missing name")
            if "monthlyVolumes" in package and not isinstance(package["monthlyVolumes"], list):
                errors.append(f"packages[{i}].monthlyVolumes must be a list")
            if "optionItems" in package and not isinstance(package["optionItems"], list):
                errors.append(f"packages[{i}].optionItems must be a list")

    return errors

def validate_contract_term_defaults(data: Dict[str, Any]) -> List[str]:
    errors: List[str] = []

    contract_terms = data.get("contractTerms", {})
    initial_terms = contract_terms.get("contractInitialTerm", []) or []

    if not isinstance(initial_terms, list) or not initial_terms:
        return errors

    default_count = 0
    default_labels: List[str] = []

    for idx, term in enumerate(initial_terms):
        is_default = int(term.get("isDefault", 0) or 0)
        if is_default == 1:
            default_count += 1
            term_value = str(term.get("termValue", "")).strip()
            term_unit = str(term.get("termUnit", "")).strip()
            label = f"{term_value}{term_unit}".strip() or f"Term {idx + 1}"
            default_labels.append(label)

    if default_count == 0:
        errors.append("contractTerms.contractInitialTerm must have exactly one term with isDefault = 1. None is currently set.")
    elif default_count > 1:
        labels = ", ".join(default_labels)
        errors.append(
            f"contractTerms.contractInitialTerm must have exactly one term with isDefault = 1. Found {default_count}: {labels}"
        )

    return errors

def build_valid_initial_term_reference_set(initial_terms: List[Dict[str, Any]]) -> set[str]:
    valid_terms: set[str] = set()

    for idx, term in enumerate(initial_terms):
        term_value = str(term.get("termValue", "")).strip()
        term_unit = str(term.get("termUnit", "")).strip()
        sort_order = str(term.get("sortOrder", "")).strip()

        spaced_label = f"{term_value} {term_unit}".strip()
        compact_label = f"{term_value}{term_unit}".strip()

        if term_value:
            valid_terms.add(term_value.lower())
        if term_unit:
            valid_terms.add(term_unit.lower())
        if spaced_label:
            valid_terms.add(spaced_label.lower())
        if compact_label:
            valid_terms.add(compact_label.lower())
        if sort_order:
            valid_terms.add(sort_order.lower())

        valid_terms.add(str(idx).lower())
        valid_terms.add(str(idx + 1).lower())

    return valid_terms

def validate_orphan_term_references(data: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    contract_terms = data.get("contractTerms", {})
    initial_terms = contract_terms.get("contractInitialTerm", []) or []
    valid_terms = build_valid_initial_term_reference_set(initial_terms)
    packages = data.get("packages", []) or []

    for p_idx, package in enumerate(packages):
        for mv_idx, mv in enumerate(package.get("monthlyVolumes", []) or []):
            for ta_idx, ta in enumerate(mv.get("termAmounts", []) or []):
                ref = str(ta.get("initialTermId", "")).strip().lower()
                if ref and ref not in valid_terms:
                    errors.append(
                        f"Package {p_idx + 1}, Tier {mv_idx + 1}, Term Amount {ta_idx + 1} has invalid term reference '{ta.get("initialTermId", "")}'"
                    )

        for g_idx, group in enumerate(package.get("optionItems", []) or []):
            for li_idx, line in enumerate(group.get("optionLineItems", []) or []):
                for ta_idx, ta in enumerate(line.get("termAmounts", []) or []):
                    ref = str(ta.get("initialTermId", "")).strip().lower()
                    if ref and ref not in valid_terms:
                        errors.append(
                            f"Package {p_idx + 1}, Group {g_idx + 1}, Line Item {li_idx + 1}, Term Amount {ta_idx + 1} has invalid term reference '{ta.get("initialTermId", "")}'"
                        )

    return errors

def _is_blank(value: Any) -> bool:
    return value is None or str(value).strip() == ""


def _duplicate_values(values: List[Any]) -> set[str]:
    seen: set[str] = set()
    dupes: set[str] = set()
    for value in values:
        key = str(value or "").strip().lower()
        if not key:
            continue
        if key in seen:
            dupes.add(key)
        seen.add(key)
    return dupes


def _validate_duplicate_sort_orders(items: List[Dict[str, Any]], label: str, errors: List[str]) -> None:
    seen: dict[str, int] = {}
    for idx, item in enumerate(items or []):
        sort_order = item.get("sortOrder") if isinstance(item, dict) else None
        if sort_order in (None, ""):
            continue
        key = str(sort_order)
        if key in seen:
            errors.append(f"{label} has duplicate sortOrder {key} at rows {seen[key] + 1} and {idx + 1}.")
        else:
            seen[key] = idx


def validate_editor_business_rules(data: Dict[str, Any]) -> List[str]:
    """Additional v2 editor guardrails used by the frontend and backend."""
    errors: List[str] = []

    for key in ["name", "description", "slug"]:
        if _is_blank(data.get(key)):
            errors.append(f"Metadata field '{key}' is blank.")

    contract_terms = data.get("contractTerms", {}) if isinstance(data.get("contractTerms", {}), dict) else {}
    initial_terms = contract_terms.get("contractInitialTerm", []) or []
    if isinstance(initial_terms, list):
        for idx, term in enumerate(initial_terms):
            if not isinstance(term, dict):
                continue
            if _is_blank(term.get("termValue")):
                errors.append(f"Contract initial term {idx + 1} is missing termValue.")
            if _is_blank(term.get("termUnit")):
                errors.append(f"Contract initial term {idx + 1} is missing termUnit.")
        _validate_duplicate_sort_orders(initial_terms, "Contract initial terms", errors)

    packages = data.get("packages", []) or []
    if isinstance(packages, list):
        package_names = [pkg.get("name") if isinstance(pkg, dict) else "" for pkg in packages]
        dupes = _duplicate_values(package_names)
        for idx, pkg in enumerate(packages):
            if not isinstance(pkg, dict):
                continue
            package_label = pkg.get("name") or pkg.get("internalName") or f"Package {idx + 1}"
            if _is_blank(pkg.get("name")):
                errors.append(f"Package {idx + 1} is missing name.")
            if str(pkg.get("name") or "").strip().lower() in dupes:
                errors.append(f"Duplicate package name: {pkg.get('name')}.")

            volumes = pkg.get("monthlyVolumes", []) or []
            if isinstance(volumes, list):
                _validate_duplicate_sort_orders(volumes, f"Package '{package_label}' monthly volumes", errors)
                numeric_ranges: list[tuple[float, float, int]] = []
                for mv_idx, mv in enumerate(volumes):
                    if not isinstance(mv, dict):
                        continue
                    min_value = mv.get("minimumValue")
                    max_value = mv.get("maximumValue")
                    if _is_blank(min_value):
                        errors.append(f"Package '{package_label}' volume band {mv_idx + 1} is missing minimumValue.")
                    if _is_blank(max_value):
                        errors.append(f"Package '{package_label}' volume band {mv_idx + 1} is missing maximumValue.")
                    try:
                        min_num = float(min_value)
                        max_num = float(max_value)
                    except (TypeError, ValueError):
                        continue
                    if min_num > max_num:
                        errors.append(f"Package '{package_label}' volume band {mv_idx + 1} has minimumValue greater than maximumValue.")
                    numeric_ranges.append((min_num, max_num, mv_idx))
                numeric_ranges.sort(key=lambda row: row[0])
                for prior, current in zip(numeric_ranges, numeric_ranges[1:]):
                    if current[0] <= prior[1]:
                        errors.append(f"Package '{package_label}' volume bands {prior[2] + 1} and {current[2] + 1} overlap.")
                    elif current[0] > prior[1] + 1:
                        errors.append(f"Package '{package_label}' has a gap between volume bands {prior[2] + 1} and {current[2] + 1}.")

            option_groups = pkg.get("optionItems", []) or []
            if isinstance(option_groups, list):
                _validate_duplicate_sort_orders(option_groups, f"Package '{package_label}' option groups", errors)
                for group_idx, group in enumerate(option_groups):
                    if not isinstance(group, dict):
                        continue
                    group_label = group.get("optionItemType") or f"Group {group_idx + 1}"
                    if _is_blank(group.get("optionItemType")):
                        errors.append(f"Package '{package_label}' option group {group_idx + 1} is missing optionItemType.")
                    line_items = group.get("optionLineItems", []) or []
                    if isinstance(line_items, list):
                        _validate_duplicate_sort_orders(line_items, f"Package '{package_label}' option group '{group_label}' line items", errors)
                        for li_idx, item in enumerate(line_items):
                            if not isinstance(item, dict):
                                continue
                            if _is_blank(item.get("internalName")) and _is_blank(item.get("marketingTitle")):
                                errors.append(f"Package '{package_label}' option group '{group_label}' line item {li_idx + 1} is missing a name/title.")
        _validate_duplicate_sort_orders(packages, "Packages", errors)

    top_option_groups = data.get("optionItems", []) or []
    if isinstance(top_option_groups, list):
        _validate_duplicate_sort_orders(top_option_groups, "Top-level option groups", errors)
        for group_idx, group in enumerate(top_option_groups):
            if not isinstance(group, dict):
                continue
            group_label = group.get("optionItemType") or f"Top-level group {group_idx + 1}"
            if _is_blank(group.get("optionItemType")):
                errors.append(f"Top-level option group {group_idx + 1} is missing optionItemType.")
            line_items = group.get("optionLineItems", []) or []
            if isinstance(line_items, list):
                _validate_duplicate_sort_orders(line_items, f"Top-level option group '{group_label}' line items", errors)
                for li_idx, item in enumerate(line_items):
                    if isinstance(item, dict) and _is_blank(item.get("internalName")) and _is_blank(item.get("marketingTitle")):
                        errors.append(f"Top-level option group '{group_label}' line item {li_idx + 1} is missing a name/title.")

    custom_attrs = data.get("customAttributes", []) or []
    if isinstance(custom_attrs, list):
        dupes = _duplicate_values([attr.get("name") if isinstance(attr, dict) else "" for attr in custom_attrs])
        for idx, attr in enumerate(custom_attrs):
            if not isinstance(attr, dict):
                continue
            name = str(attr.get("name") or "").strip()
            if not name:
                errors.append(f"Custom attribute {idx + 1} is missing name.")
            elif name.lower() in dupes:
                errors.append(f"Duplicate custom attribute name: {name}.")
        _validate_duplicate_sort_orders(custom_attrs, "Custom attributes", errors)

    return errors


def auto_remove_orphan_term_amounts(data: Dict[str, Any]) -> int:
    contract_terms = data.get("contractTerms", {})
    initial_terms = contract_terms.get("contractInitialTerm", []) or []
    valid_terms = build_valid_initial_term_reference_set(initial_terms)
    cleaned = 0

    for package in data.get("packages", []) or []:
        for mv in package.get("monthlyVolumes", []) or []:
            original = mv.get("termAmounts", []) or []
            filtered = [
                ta for ta in original
                if str(ta.get("initialTermId", "")).strip().lower() in valid_terms
            ]
            cleaned += len(original) - len(filtered)
            mv["termAmounts"] = filtered

        for group in package.get("optionItems", []) or []:
            for line in group.get("optionLineItems", []) or []:
                original = line.get("termAmounts", []) or []
                filtered = [
                    ta for ta in original
                    if str(ta.get("initialTermId", "")).strip().lower() in valid_terms
                ]
                cleaned += len(original) - len(filtered)
                line["termAmounts"] = filtered

    return cleaned


# Contract term helpers
def build_contract_term_labels(contract_initial_terms: List[Dict[str, Any]]) -> List[str]:
    labels: List[str] = []
    for term_idx, term in enumerate(contract_initial_terms):
        term_value = term.get("termValue", "")
        term_unit = term.get("termUnit", "")
        label = str(term_value).strip()
        if term_unit:
            label = f"{label} {term_unit}".strip()
        if not label:
            label = f"Term {term_idx + 1}"
        labels.append(label)
    return labels

def get_default_contract_term_index(contract_initial_terms: List[Dict[str, Any]]) -> int:
    default_term_index = 0
    for term_idx, term in enumerate(contract_initial_terms):
        if int(term.get("isDefault", 0)) == 1:
            default_term_index = term_idx
            break
    return default_term_index

def build_term_reference_candidates(selected_term: Dict[str, Any], selected_term_idx: int) -> set[str]:
    selected_value = str(selected_term.get("termValue", "")).strip()
    selected_unit = str(selected_term.get("termUnit", "")).strip()
    selected_sort = str(selected_term.get("sortOrder", "")).strip()

    selected_label_spaced = f"{selected_value} {selected_unit}".strip()
    selected_label_compact = f"{selected_value}{selected_unit}".strip()

    return {
        selected_value.lower(),
        selected_unit.lower(),
        selected_label_spaced.lower(),
        selected_label_compact.lower(),
        selected_sort.lower(),
        str(selected_term_idx).lower(),
        str(selected_term_idx + 1).lower(),
    }

def resolve_term_amount_for_volume(
    volume: Dict[str, Any],
    selected_term: Optional[Dict[str, Any]],
    selected_term_idx: int,
) -> Optional[Dict[str, Any]]:
    term_amounts = volume.get("termAmounts", [])
    if not term_amounts:
        return None

    if selected_term is None:
        return term_amounts[0] if term_amounts else None

    candidates = build_term_reference_candidates(selected_term, selected_term_idx)

    for term_amount in term_amounts:
        raw_id = str(term_amount.get("initialTermId", "")).strip().lower()
        if raw_id and raw_id in candidates:
            return term_amount

    if 0 <= selected_term_idx < len(term_amounts):
        return term_amounts[selected_term_idx]

    return term_amounts[0] if term_amounts else None


# Default template functions
def default_monthly_volume() -> Dict[str, Any]:
    return {
        "internalName": "New Monthly Volume",
        "minimumValue": 1,
        "maximumValue": 1000,
        "amount": 0.0,
        "amountDescription": "",
        "transactionUnitAmount": 0.0,
        "unit": "month",
        "subCount": 0,
        "subUnitType": "transactions",
        "subUnit": "month",
        "subUnitDescription": "",
        "isDefault": 0,
        "sortOrder": 0,
        "termAmounts": [],
        "discountItems": [],
    }

def default_option_group() -> Dict[str, Any]:
    return {
        "optionItemType": "New Group",
        "headerDescription": "",
        "toolTipText": "",
        "toolTipDescription": "",
        "headerDescription2": "",
        "toolTipText2": "",
        "toolTipDescription2": "",
        "customAttributes": [],
        "discountItems": [],
        "optionLineItems": [],
    }

def default_option_line_item() -> Dict[str, Any]:
    return {
        "catalogCode": "",
        "internalName": "New Option",
        "marketingTitle": "",
        "tagline": "",
        "toolTipDescription": "",
        "shortDescription": "",
        "longDescription": "",
        "amount": 0,
        "amountDescription": "",
        "useTransactionUnitAmount": 0,
        "unit": "",
        "subCount": 0,
        "subUnitType": "",
        "subUnit": "",
        "subUnitDescription": "",
        "isIncluded": 0,
        "isDefault": 0,
        "isCountable": 0,
        "countableMin": 0,
        "countableMax": 0,
        "sortOrder": 0,
        "customAttributes": [],
        "discountItems": [],
        "termAmounts": [],
    }

def default_term_amount() -> Dict[str, Any]:
    return {
        "initialTermId": "",
        "amount": 0.0,
        "transactionUnitAmount": 0.0,
        "transactionUnitOverageAmount": 0.0,
    }

def default_contract_initial_term() -> Dict[str, Any]:
    return {
        "termValue": 1,
        "termUnit": "Y",
        "description": "",
        "isDefault": 0,
        "sortOrder": 0,
        "discountItems": [],
    }

def default_package() -> Dict[str, Any]:
    return {
        "internalName": "New Package",
        "name": "New Package",
        "marketingTitle": "",
        "tagline": "",
        "toolTipDescription": "",
        "shortDescription": "",
        "longDescription": "",
        "amount": 0,
        "amountDescription": "",
        "unit": "month",
        "subCount": 0,
        "subUnitType": "",
        "subUnit": "",
        "subUnitDescription": "",
        "isDefault": 0,
        "isCountable": 0,
        "countableMin": 0,
        "countableMax": 0,
        "sortOrder": 0,
        "includedModuleText": "",
        "customAttributes": [],
        "productItems": [],
        "monthlyVolumes": [],
        "discountItems": [],
        "optionItems": [],
    }


# Normalization functions
def normalize_package_sort_orders(packages: List[Dict[str, Any]]) -> None:
    for idx, package in enumerate(packages):
        if isinstance(package, dict):
            package["sortOrder"] = idx

def normalize_initial_term_sort_orders(terms: List[Dict[str, Any]]) -> None:
    for idx, term in enumerate(terms):
        if isinstance(term, dict):
            term["sortOrder"] = idx

