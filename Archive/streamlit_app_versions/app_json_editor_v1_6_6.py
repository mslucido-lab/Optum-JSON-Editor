"""
app_json_editor_v1_6_6.py

Version: v1.6.6
Date: 2026-03-23
Project: JSON Editor
Purpose: Load a JSON file, edit it safely, save a new version, and preview a pricing page.

Change Log:
- v1.6.6
  - Restyled pricing preview to more closely match the Optum source page
  - Centered the preview content and refined spacing, card sizing, and typography
  - Reworked Included Features into a cleaner package comparison matrix
- v1.6.5
  - Added line numbers to JSON preview
  - Added search functionality for Edited JSON
  - Added search functionality for Original JSON
- v1.6.4
  - Fixed orphan validation to support compact term IDs like 1Y, 3Y, 5Y
  - Aligned validation logic with preview matching
- v1.6.3
  - Updated orphan validation to match inferred initialTermId logic
  - Uses the same inferred term keys as the pricing preview
- v1.6.2
  - Added orphan term reference validation for deleted contract terms
  - Blocks download when orphaned child term nodes exist
  - Added auto-clean option to remove orphaned term amounts
- v1.6.1
  - Moved contract terms section in Pricing Page Preview below the package cards
  - Added add and delete controls for initial contract terms in Contract Terms editor
- v1.6.0
  - Merged package add, duplicate, and delete controls into v1.5.9
  - Added safer selected package index handling after package actions
  - Added package actions panel above package editing screens
  - Added default package template and package sort order normalization
- v1.5.9
  - Prevented uploaded file from re-initializing session state on every rerun
  - Fixed fields like package name disappearing after pressing Enter
  - Added pricing page preview
"""

import copy
import hashlib
import html
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st


APP_VERSION = "v1.6.6"


def deep_copy_json(data: Any) -> Any:
    return copy.deepcopy(data)


def parse_json_file(uploaded_file) -> Dict[str, Any]:
    raw = uploaded_file.read().decode("utf-8")
    return json.loads(raw)


def safe_json_dumps(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


def make_versioned_filename(original_name: str, app_version: str = APP_VERSION) -> str:
    base = re.sub(r"\.json$", "", original_name, flags=re.IGNORECASE)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    version_label = app_version.replace(".", "_")
    return f"{base}_{version_label}_{stamp}.json"


def get_uploaded_file_signature(uploaded_file) -> str:
    file_bytes = uploaded_file.getvalue()
    digest = hashlib.md5(file_bytes).hexdigest()
    return f"{uploaded_file.name}:{len(file_bytes)}:{digest}"


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


def init_state_from_upload(uploaded_file) -> None:
    parsed = parse_json_file(uploaded_file)
    st.session_state["original_filename"] = uploaded_file.name
    st.session_state["original_json"] = deep_copy_json(parsed)
    st.session_state["edited_json"] = deep_copy_json(parsed)
    st.session_state["raw_json_text"] = safe_json_dumps(parsed)
    st.session_state["load_complete"] = True
    st.session_state["uploaded_file_signature"] = get_uploaded_file_signature(uploaded_file)
    st.session_state["selected_package_index"] = 0


def maybe_init_state_from_upload(uploaded_file) -> None:
    if uploaded_file is None:
        return

    current_sig = get_uploaded_file_signature(uploaded_file)
    prior_sig = st.session_state.get("uploaded_file_signature")

    if prior_sig != current_sig or not st.session_state.get("load_complete"):
        init_state_from_upload(uploaded_file)


def clamp_selected_package_index() -> None:
    packages = st.session_state.get("edited_json", {}).get("packages", [])
    if not packages:
        st.session_state["selected_package_index"] = 0
        return

    current = st.session_state.get("selected_package_index", 0)
    if not isinstance(current, int):
        current = 0
    st.session_state["selected_package_index"] = max(0, min(current, len(packages) - 1))


def sync_raw_text_from_edited() -> None:
    st.session_state["raw_json_text"] = safe_json_dumps(st.session_state["edited_json"])


def sync_edited_from_raw_text():
    try:
        parsed = json.loads(st.session_state["raw_json_text"])
        st.session_state["edited_json"] = parsed
        clamp_selected_package_index()
        return True, "Raw JSON applied successfully."
    except Exception as exc:
        return False, f"Raw JSON is invalid: {exc}"


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


def normalize_package_sort_orders(packages: List[Dict[str, Any]]) -> None:
    for idx, package in enumerate(packages):
        if isinstance(package, dict):
            package["sortOrder"] = idx


def normalize_initial_term_sort_orders(terms: List[Dict[str, Any]]) -> None:
    for idx, term in enumerate(terms):
        if isinstance(term, dict):
            term["sortOrder"] = idx


def edit_scalar_field(obj: Dict[str, Any], key: str, label: Optional[str] = None, height: int = 100) -> None:
    if key not in obj:
        return

    value = obj.get(key)
    widget_key = f"{label or key}_{id(obj)}"

    if isinstance(value, str):
        if len(value) > 120 or "<br" in value or "<strong" in value or "<ul" in value:
            obj[key] = st.text_area(label or key, value=value, key=widget_key, height=height)
        else:
            obj[key] = st.text_input(label or key, value=value, key=widget_key)
    elif isinstance(value, bool):
        obj[key] = st.checkbox(label or key, value=value, key=widget_key)
    elif isinstance(value, int) and not isinstance(value, bool):
        obj[key] = int(st.number_input(label or key, value=int(value), step=1, key=widget_key))
    elif isinstance(value, float):
        obj[key] = float(st.number_input(label or key, value=float(value), key=widget_key))
    elif value is None:
        obj[key] = st.text_input(label or key, value="", key=widget_key)
    else:
        obj[key] = st.text_input(label or key, value=str(value), key=widget_key)


def normalize_terms_for_editor(terms: List[Dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for item in terms:
        rows.append(
            {
                "termValue": item.get("termValue"),
                "termUnit": item.get("termUnit", ""),
                "description": item.get("description", ""),
                "isDefault": int(item.get("isDefault", 0)),
                "sortOrder": item.get("sortOrder", 0),
            }
        )
    if not rows:
        rows = [{"termValue": "", "termUnit": "", "description": "", "isDefault": 0, "sortOrder": 0}]
    return pd.DataFrame(rows)


def dataframe_to_terms(df: pd.DataFrame, original_terms: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rebuilt: List[Dict[str, Any]] = []
    for idx, row in df.fillna("").iterrows():
        term_value = row["termValue"]
        if str(term_value).strip() == "":
            continue

        entry = {
            "termValue": int(term_value) if str(term_value).strip().isdigit() else term_value,
            "termUnit": str(row["termUnit"]).strip(),
            "description": str(row["description"]).strip(),
            "isDefault": int(row["isDefault"]) if str(row["isDefault"]).strip() != "" else 0,
            "sortOrder": int(row["sortOrder"]) if str(row["sortOrder"]).strip() != "" else idx,
            "discountItems": [],
        }

        if idx < len(original_terms) and isinstance(original_terms[idx], dict):
            entry["discountItems"] = original_terms[idx].get("discountItems", [])

        rebuilt.append(entry)
    return rebuilt


def render_top_level_editor(data: Dict[str, Any]) -> None:
    st.subheader("Product Info")

    keys = [
        "name",
        "description",
        "slug",
        "maxQuantity",
        "catalogCode",
        "viewTemplate",
        "imageName",
        "headerDescription",
        "toolTipText",
        "toolTipDescription",
        "paymentSchedule",
    ]
    for key in keys:
        edit_scalar_field(data, key)


def render_contract_terms_editor(data: Dict[str, Any]) -> None:
    st.subheader("Contract Terms")
    contract_terms = data.setdefault("contractTerms", {})

    for key in ["headerDescription", "toolTipText", "toolTipDescription", "isAutoRenewalEnabled"]:
        edit_scalar_field(contract_terms, key)

    st.markdown("#### Initial Terms")
    initial_terms = contract_terms.setdefault("contractInitialTerm", [])

    top_cols = st.columns([1, 1, 4])
    with top_cols[0]:
        if st.button("Add Initial Term"):
            new_term = default_contract_initial_term()
            new_term["sortOrder"] = len(initial_terms)
            initial_terms.append(new_term)
            sync_raw_text_from_edited()
            st.rerun()
    with top_cols[1]:
        if initial_terms and st.button("Delete Last Initial Term"):
            initial_terms.pop()
            normalize_initial_term_sort_orders(initial_terms)
            sync_raw_text_from_edited()
            st.rerun()

    initial_original = contract_terms.get("contractInitialTerm", [])
    initial_df = normalize_terms_for_editor(initial_original)
    edited_initial = st.data_editor(
        initial_df,
        num_rows="dynamic",
        use_container_width=True,
        key="initial_terms_editor",
    )
    contract_terms["contractInitialTerm"] = dataframe_to_terms(edited_initial, initial_original)

    st.markdown("#### Auto Renewal Terms")
    auto_original = contract_terms.get("contractAutoRenewalTerm", [])
    auto_df = normalize_terms_for_editor(auto_original)
    edited_auto = st.data_editor(
        auto_df,
        num_rows="dynamic",
        use_container_width=True,
        key="auto_terms_editor",
    )
    contract_terms["contractAutoRenewalTerm"] = dataframe_to_terms(edited_auto, auto_original)


def package_selector(packages: List[Dict[str, Any]]) -> int:
    clamp_selected_package_index()
    if not packages:
        return 0

    current = st.session_state["selected_package_index"]
    selected = st.selectbox(
        "Select package",
        options=list(range(len(packages))),
        index=current,
        format_func=lambda i: f"{i}: {packages[i].get('name', 'Unnamed Package')}",
    )
    st.session_state["selected_package_index"] = selected
    return selected


def render_package_overview(packages: List[Dict[str, Any]]) -> None:
    st.subheader("Packages")
    rows = []
    for i, package in enumerate(packages):
        rows.append(
            {
                "Index": i,
                "Name": package.get("name", ""),
                "Internal Name": package.get("internalName", ""),
                "Sort Order": package.get("sortOrder", ""),
                "Monthly Volumes": len(package.get("monthlyVolumes", [])),
                "Option Groups": len(package.get("optionItems", [])),
            }
        )
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def render_package_actions(packages: List[Dict[str, Any]], selected_index: int) -> None:
    st.subheader("Package Actions")

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("Add New Package", use_container_width=True):
            packages.append(default_package())
            normalize_package_sort_orders(packages)
            st.session_state["selected_package_index"] = len(packages) - 1
            sync_raw_text_from_edited()
            st.rerun()

    with col2:
        if packages and st.button("Duplicate Selected Package", use_container_width=True):
            source_pkg = deep_copy_json(packages[selected_index])
            original_name = source_pkg.get("name", "Package")
            original_internal = source_pkg.get("internalName", "Package")
            source_pkg["name"] = f"{original_name} Copy"
            source_pkg["internalName"] = f"{original_internal} Copy"
            packages.insert(selected_index + 1, source_pkg)
            normalize_package_sort_orders(packages)
            st.session_state["selected_package_index"] = selected_index + 1
            sync_raw_text_from_edited()
            st.rerun()

    with col3:
        if st.button("Delete Selected Package", use_container_width=True, disabled=(len(packages) == 0)):
            if packages:
                packages.pop(selected_index)
                normalize_package_sort_orders(packages)
                if packages:
                    st.session_state["selected_package_index"] = min(selected_index, len(packages) - 1)
                else:
                    st.session_state["selected_package_index"] = 0
                sync_raw_text_from_edited()
                st.rerun()

    if packages:
        current_name = packages[selected_index].get("name", "Unnamed Package")
        st.caption(f"Current package: {current_name}")


def render_package_details_editor(package: Dict[str, Any]) -> None:
    st.subheader("Package Details")
    keys = [
        "internalName",
        "name",
        "marketingTitle",
        "tagline",
        "toolTipDescription",
        "shortDescription",
        "longDescription",
        "amount",
        "amountDescription",
        "unit",
        "subCount",
        "subUnitType",
        "subUnit",
        "subUnitDescription",
        "isDefault",
        "isCountable",
        "countableMin",
        "countableMax",
        "sortOrder",
        "includedModuleText",
    ]
    for key in keys:
        edit_scalar_field(package, key)


def render_term_amount_editor(term_amount: Dict[str, Any], mv_idx: int, ta_idx: int) -> None:
    st.markdown(f"**Term Amount {ta_idx + 1}**")
    cols = st.columns(4)
    with cols[0]:
        edit_scalar_field(term_amount, "initialTermId")
    with cols[1]:
        edit_scalar_field(term_amount, "amount")
    with cols[2]:
        if "transactionUnitAmount" in term_amount:
            edit_scalar_field(term_amount, "transactionUnitAmount")
    with cols[3]:
        if "transactionUnitOverageAmount" in term_amount:
            edit_scalar_field(term_amount, "transactionUnitOverageAmount")


def render_monthly_volumes_editor(package: Dict[str, Any]) -> None:
    st.subheader("Monthly Volume Tiers")
    monthly_volumes = package.setdefault("monthlyVolumes", [])

    top_cols = st.columns([1, 1, 4])
    with top_cols[0]:
        if st.button("Add Tier"):
            monthly_volumes.append(default_monthly_volume())
            monthly_volumes[-1]["sortOrder"] = len(monthly_volumes) - 1
    with top_cols[1]:
        if monthly_volumes and st.button("Delete Last Tier"):
            monthly_volumes.pop()

    if not monthly_volumes:
        st.info("No monthly volume tiers found.")
        return

    for mv_idx, mv in enumerate(monthly_volumes):
        with st.expander(f"Tier {mv_idx + 1}: {mv.get('internalName', 'Monthly Volume')}", expanded=(mv_idx == 0)):
            cols = st.columns(3)
            with cols[0]:
                if st.button(f"Delete This Tier {mv_idx + 1}", key=f"del_mv_{mv_idx}"):
                    monthly_volumes.pop(mv_idx)
                    st.rerun()

            edit_keys = [
                "internalName",
                "minimumValue",
                "maximumValue",
                "amount",
                "amountDescription",
                "transactionUnitAmount",
                "unit",
                "subCount",
                "subUnitType",
                "subUnit",
                "subUnitDescription",
                "isDefault",
                "sortOrder",
            ]
            for key in edit_keys:
                edit_scalar_field(mv, key)

            st.markdown("#### Term Amounts")
            term_amounts = mv.setdefault("termAmounts", [])

            term_top_cols = st.columns([1, 1, 4])
            with term_top_cols[0]:
                if st.button("Add Term Amount", key=f"add_ta_{mv_idx}"):
                    term_amounts.append(default_term_amount())
            with term_top_cols[1]:
                if term_amounts and st.button("Delete Last Term Amount", key=f"del_last_ta_{mv_idx}"):
                    term_amounts.pop()

            if not term_amounts:
                st.info("No term amounts for this tier.")
            else:
                for ta_idx, term_amount in enumerate(term_amounts):
                    st.markdown("---")
                    ta_cols = st.columns([5, 1])
                    with ta_cols[0]:
                        render_term_amount_editor(term_amount, mv_idx, ta_idx)
                    with ta_cols[1]:
                        if st.button("Delete", key=f"del_ta_{mv_idx}_{ta_idx}"):
                            term_amounts.pop(ta_idx)
                            st.rerun()


def render_option_line_item_editor(line_item: Dict[str, Any], group_idx: int, line_idx: int) -> None:
    edit_keys = [
        "catalogCode",
        "internalName",
        "marketingTitle",
        "tagline",
        "toolTipDescription",
        "shortDescription",
        "longDescription",
        "amount",
        "amountDescription",
        "useTransactionUnitAmount",
        "unit",
        "subCount",
        "subUnitType",
        "subUnit",
        "subUnitDescription",
        "isIncluded",
        "isDefault",
        "isCountable",
        "countableMin",
        "countableMax",
        "sortOrder",
    ]
    for key in edit_keys:
        edit_scalar_field(line_item, key)

    st.markdown("#### Line Item Term Amounts")
    term_amounts = line_item.setdefault("termAmounts", [])
    cols = st.columns([1, 1, 4])
    with cols[0]:
        if st.button("Add Line Item Term Amount", key=f"add_li_ta_{group_idx}_{line_idx}"):
            term_amounts.append(default_term_amount())
    with cols[1]:
        if term_amounts and st.button("Delete Last Line Item Term Amount", key=f"del_li_last_ta_{group_idx}_{line_idx}"):
            term_amounts.pop()

    for ta_idx, term_amount in enumerate(term_amounts):
        st.markdown("---")
        ta_cols = st.columns([5, 1])
        with ta_cols[0]:
            render_term_amount_editor(term_amount, group_idx, ta_idx)
        with ta_cols[1]:
            if st.button("Delete", key=f"del_li_ta_{group_idx}_{line_idx}_{ta_idx}"):
                term_amounts.pop(ta_idx)
                st.rerun()


def render_option_groups_editor(package: Dict[str, Any]) -> None:
    st.subheader("Option Groups")
    option_groups = package.setdefault("optionItems", [])

    top_cols = st.columns([1, 1, 4])
    with top_cols[0]:
        if st.button("Add Option Group"):
            option_groups.append(default_option_group())
    with top_cols[1]:
        if option_groups and st.button("Delete Last Group"):
            option_groups.pop()

    if not option_groups:
        st.info("No option groups found.")
        return

    for group_idx, group in enumerate(option_groups):
        title = group.get("optionItemType", f"Group {group_idx + 1}")
        with st.expander(f"Group {group_idx + 1}: {title}", expanded=(group_idx == 0)):
            cols = st.columns([1, 5])
            with cols[0]:
                if st.button(f"Delete Group {group_idx + 1}", key=f"delete_group_{group_idx}"):
                    option_groups.pop(group_idx)
                    st.rerun()

            for key in [
                "optionItemType",
                "headerDescription",
                "toolTipText",
                "toolTipDescription",
                "headerDescription2",
                "toolTipText2",
                "toolTipDescription2",
            ]:
                edit_scalar_field(group, key)

            st.markdown("#### Option Line Items")
            line_items = group.setdefault("optionLineItems", [])

            line_top_cols = st.columns([1, 1, 4])
            with line_top_cols[0]:
                if st.button("Add Line Item", key=f"add_line_item_{group_idx}"):
                    line_items.append(default_option_line_item())
            with line_top_cols[1]:
                if line_items and st.button("Delete Last Line Item", key=f"del_last_line_item_{group_idx}"):
                    line_items.pop()

            if not line_items:
                st.info("No line items in this group.")
            else:
                for line_idx, line_item in enumerate(line_items):
                    line_title = line_item.get("internalName", f"Line Item {line_idx + 1}")
                    with st.expander(f"Line Item {line_idx + 1}: {line_title}", expanded=False):
                        top = st.columns([1, 5])
                        with top[0]:
                            if st.button("Delete Line Item", key=f"del_line_item_{group_idx}_{line_idx}"):
                                line_items.pop(line_idx)
                                st.rerun()
                        render_option_line_item_editor(line_item, group_idx, line_idx)


def render_raw_json_editor() -> None:
    st.subheader("Raw JSON Editor")
    st.session_state["raw_json_text"] = st.text_area(
        "Edit raw JSON directly",
        value=st.session_state.get("raw_json_text", ""),
        height=550,
        key="raw_json_text_area",
    )

    cols = st.columns(2)
    with cols[0]:
        if st.button("Apply Raw JSON Changes"):
            ok, msg = sync_edited_from_raw_text()
            if ok:
                st.success(msg)
            else:
                st.error(msg)
    with cols[1]:
        if st.button("Reset Raw JSON to Edited Copy"):
            sync_raw_text_from_edited()
            st.success("Raw JSON reset from edited copy.")


def render_validation_panel(data: Dict[str, Any]) -> None:
    st.subheader("Validation")
    errors: List[str] = []
    errors.extend(validate_json_structure(data))
    errors.extend(validate_orphan_term_references(data))

    if errors:
        st.error("Validation found issues.")
        for err in errors:
            st.write(f"- {err}")

        if st.button("Auto-remove orphaned term amounts"):
            cleaned = auto_remove_orphan_term_amounts(data)
            sync_raw_text_from_edited()
            st.success(f"Removed {cleaned} orphaned term amounts.")
            st.rerun()
    else:
        st.success("Validation passed.")


def find_json_preview_matches(json_text: str, search_text: str) -> List[Dict[str, Any]]:
    matches: List[Dict[str, Any]] = []
    if not search_text.strip():
        return matches

    needle = search_text.lower()
    lines = json_text.splitlines()

    for idx, line in enumerate(lines):
        if needle in line.lower():
            matches.append(
                {
                    "line_number": idx + 1,
                    "line_text": line,
                }
            )

    return matches


def render_json_preview_panel(json_text: str, search_key: str) -> None:
    search_text = st.text_input("Search JSON", value="", key=search_key, placeholder="Search keys, values, IDs")
    matches = find_json_preview_matches(json_text, search_text)

    if search_text.strip():
        if matches:
            st.caption(f"Found {len(matches)} matching line(s).")
            with st.expander("Matching lines", expanded=True):
                for match in matches[:200]:
                    st.write(f"Line {match['line_number']}: {match['line_text']}")
                if len(matches) > 200:
                    st.caption(f"Showing first 200 of {len(matches)} matches.")
        else:
            st.caption("No matches found.")

    st.code(json_text, language="json", line_numbers=True)


def render_json_preview(data: Dict[str, Any]) -> None:
    tab1, tab2 = st.tabs(["Edited JSON", "Original JSON"])
    with tab1:
        render_json_preview_panel(safe_json_dumps(data), "json_preview_search_edited")
    with tab2:
        render_json_preview_panel(safe_json_dumps(st.session_state["original_json"]), "json_preview_search_original")


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


def get_default_contract_term_index(contract_initial_terms: List[Dict[str, Any]]) -> int:
    default_term_index = 0
    for term_idx, term in enumerate(contract_initial_terms):
        if int(term.get("isDefault", 0)) == 1:
            default_term_index = term_idx
            break
    return default_term_index


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


def render_text_volume_tiers(volumes: List[Dict[str, Any]]) -> None:
    if not volumes:
        st.caption("No monthly volume tiers found")
        return

    for mv in volumes:
        min_value = mv.get("minimumValue", "")
        max_value = mv.get("maximumValue", "")
        amount = mv.get("amount", "")
        transaction_unit_amount = mv.get("transactionUnitAmount", "")
        amount_description = mv.get("amountDescription", "")
        sub_count = mv.get("subCount", "")
        sub_unit_type = mv.get("subUnitType", "")
        unit = mv.get("unit", "")

        range_parts = []
        if min_value not in ("", None) and max_value not in ("", None):
            range_parts.append(f"{min_value} to {max_value}")
        elif max_value not in ("", None):
            range_parts.append(f"Up to {max_value}")
        elif min_value not in ("", None):
            range_parts.append(f"From {min_value}")

        price_parts = []
        if amount not in ("", None, 0, 0.0):
            price_parts.append(format_money(amount))
        if transaction_unit_amount not in ("", None, 0, 0.0):
            per_unit = format_money(transaction_unit_amount)
            if sub_count not in ("", None) and sub_unit_type:
                price_parts.append(f"{per_unit} per {sub_count} {sub_unit_type}")
            elif sub_unit_type:
                price_parts.append(f"{per_unit} per {sub_unit_type}")
            elif unit:
                price_parts.append(f"{per_unit} per {unit}")
            else:
                price_parts.append(per_unit)

        line_parts = []
        if range_parts:
            line_parts.append(" | ".join(range_parts))
        if price_parts:
            line_parts.append(" | ".join(price_parts))

        if line_parts:
            line_text = " | ".join(line_parts)
            st.markdown(f'<div class="optum-tier-line-text">{line_text}</div>', unsafe_allow_html=True)

        if amount_description:
            st.markdown(f'<div class="optum-tier-caption">{amount_description}</div>', unsafe_allow_html=True)


def html_escape(value: Any) -> str:
    return html.escape(str(value or ""))


def get_package_included_features(package: Dict[str, Any], group_name: str) -> List[str]:
    features: List[str] = []

    for group in package.get("optionItems", []) or []:
        current_group_name = (group.get("optionItemType", "") or "").strip() or "Modules"
        if current_group_name != group_name:
            continue

        for item in group.get("optionLineItems", []) or []:
            if item.get("isIncluded") == 1:
                feature_name = (
                    item.get("marketingTitle")
                    or item.get("internalName")
                    or item.get("shortDescription")
                    or "Included feature"
                )
                feature_name = str(feature_name).strip()
                if feature_name and feature_name not in features:
                    features.append(feature_name)

    return features


def render_feature_comparison_matrix(packages: List[Dict[str, Any]], group_names: List[str]) -> None:
    if not packages or not group_names:
        st.info("No option groups were found for included features.")
        return

    for group_name in group_names:
        st.markdown(f'<div class="optum-feature-group-title">{html_escape(group_name)}</div>', unsafe_allow_html=True)

        header_cells = ['<div class="optum-matrix-cell optum-matrix-feature-head">Feature</div>']
        for package in packages:
            header_cells.append(
                f'<div class="optum-matrix-cell optum-matrix-package-head">{html_escape(package.get("name", "Package"))}</div>'
            )
        grid_cols = f"minmax(260px, 1.6fr) repeat({len(packages)}, minmax(120px, 1fr))"
        st.markdown(f'<div class="optum-matrix optum-matrix-header" style="grid-template-columns: {grid_cols};">{"".join(header_cells)}</div>', unsafe_allow_html=True)

        group_feature_names: List[str] = []
        for package in packages:
            for feature_name in get_package_included_features(package, group_name):
                if feature_name not in group_feature_names:
                    group_feature_names.append(feature_name)

        if not group_feature_names:
            st.markdown('<div class="optum-empty-state">No included features found in this section.</div>', unsafe_allow_html=True)
            continue

        for feature_name in group_feature_names:
            row_cells = [f'<div class="optum-matrix-cell optum-matrix-feature">{html_escape(feature_name)}</div>']
            for package in packages:
                package_features = get_package_included_features(package, group_name)
                if feature_name in package_features:
                    row_cells.append('<div class="optum-matrix-cell optum-matrix-check">✓</div>')
                else:
                    row_cells.append('<div class="optum-matrix-cell optum-matrix-empty">&nbsp;</div>')
            st.markdown(f'<div class="optum-matrix" style="grid-template-columns: {grid_cols};">{"".join(row_cells)}</div>', unsafe_allow_html=True)


def render_pricing_page(data: Dict[str, Any]) -> None:
    st.subheader("Pricing Page Preview")

    title = data.get("name", "Product")
    description = data.get("description", "")
    contract_terms = data.get("contractTerms", {})
    packages = data.get("packages", [])
    view_template = data.get("viewTemplate", "")

    contract_header = contract_terms.get("headerDescription", "")
    contract_initial_terms = contract_terms.get("contractInitialTerm", [])

    contract_term_labels = build_contract_term_labels(contract_initial_terms)
    default_term_index = get_default_contract_term_index(contract_initial_terms) if contract_initial_terms else 0

    selected_term_idx = st.session_state.get("preview_contract_term_select", default_term_index)
    if contract_initial_terms:
        if not isinstance(selected_term_idx, int):
            selected_term_idx = default_term_index
        if selected_term_idx < 0 or selected_term_idx >= len(contract_initial_terms):
            selected_term_idx = default_term_index
        selected_term = contract_initial_terms[selected_term_idx]
    else:
        selected_term = None

    use_text_tiers = str(view_template).strip() == "API-Tiered-Public"

    st.markdown(
        """
        <style>
        .block-container {
            max-width: 1280px;
            padding-top: 2rem;
            padding-bottom: 4rem;
        }
        .optum-page-shell {
            max-width: 1180px;
            margin: 0 auto;
        }
        .optum-breadcrumbs {
            font-size: 13px;
            color: #6b7280;
            margin-bottom: 20px;
        }
        .optum-title {
            font-size: 38px;
            font-weight: 700;
            color: #111827;
            line-height: 1.12;
            margin-bottom: 12px;
            letter-spacing: -0.02em;
        }
        .optum-desc {
            font-size: 16px;
            color: #4b5563;
            line-height: 1.6;
            max-width: 900px;
            margin-bottom: 12px;
        }
        .optum-note {
            background: #f7fafc;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            padding: 14px 16px;
            font-size: 14px;
            line-height: 1.5;
            color: #4b5563;
            margin: 20px 0 30px 0;
        }
        .optum-section-title {
            font-size: 28px;
            font-weight: 700;
            color: #111827;
            margin: 40px 0 14px 0;
            letter-spacing: -0.02em;
        }
        div[data-testid="stVerticalBlock"] div[data-testid="stContainer"] {
            border-radius: 18px;
        }
        [data-testid="stVerticalBlockBorderWrapper"] {
            border-color: #e5e7eb !important;
            border-radius: 18px !important;
            box-shadow: 0 1px 3px rgba(16,24,40,0.04);
            background: #ffffff;
        }
        .optum-card-subtle {
            font-size: 11px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #6b7280;
            font-weight: 700;
            margin-bottom: 12px;
        }
        .optum-badge {
            display: inline-block;
            font-size: 11px;
            font-weight: 700;
            color: #0f766e;
            background: #ecfdf5;
            border: 1px solid #a7f3d0;
            border-radius: 999px;
            padding: 5px 9px;
            margin-bottom: 12px;
        }
        .optum-card-title {
            font-size: 24px;
            font-weight: 700;
            color: #111827;
            line-height: 1.2;
            min-height: 58px;
            margin-bottom: 10px;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }
        .optum-card-subtitle {
            font-size: 13px;
            color: #6b7280;
            line-height: 1.45;
            min-height: 38px;
            margin-bottom: 18px;
            overflow: hidden;
        }
        .optum-price {
            font-size: 34px;
            font-weight: 800;
            color: #111827;
            line-height: 1;
            margin: 14px 0 8px 0;
            letter-spacing: -0.02em;
        }
        .optum-price-caption {
            font-size: 12px;
            line-height: 1.5;
            color: #6b7280;
            min-height: 38px;
            margin-bottom: 16px;
        }
        .optum-button {
            display: block;
            width: 100%;
            text-align: center;
            background: #115e59;
            color: white;
            font-weight: 700;
            font-size: 14px;
            border-radius: 999px;
            padding: 10px 14px;
            margin: 10px 0 18px 0;
            box-sizing: border-box;
        }
        .optum-section-label {
            font-size: 11px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #6b7280;
            font-weight: 700;
            margin: 14px 0 8px 0;
        }
        .optum-divider {
            height: 1px;
            background: #eef2f7;
            margin: 14px 0;
        }
        .optum-tier-name {
            font-size: 13px;
            color: #374151;
            font-weight: 700;
            margin-bottom: 2px;
        }
        .optum-tier-line-text {
            font-size: 13px;
            color: #111827;
            line-height: 1.45;
            padding: 10px 0 4px 0;
            border-top: 1px solid #eef2f5;
        }
        .optum-tier-caption {
            font-size: 11px;
            color: #6b7280;
            line-height: 1.45;
            margin-bottom: 6px;
        }
        .optum-term-helper {
            font-size: 13px;
            color: #6b7280;
            margin-top: 6px;
        }
        .optum-matrix {
            display: grid;
            gap: 0;
            border-left: 1px solid #e5e7eb;
            border-right: 1px solid #e5e7eb;
        }
        .optum-matrix-cell {
            padding: 14px 16px;
            border-bottom: 1px solid #e5e7eb;
            background: #ffffff;
            font-size: 14px;
            color: #111827;
        }
        .optum-matrix-header .optum-matrix-cell {
            background: #f8fafc;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: #6b7280;
            font-weight: 700;
        }
        .optum-matrix-feature {
            font-weight: 500;
        }
        .optum-matrix-check {
            text-align: center;
            font-size: 18px;
            font-weight: 700;
            color: #115e59;
        }
        .optum-matrix-empty {
            background: #fbfdff;
        }
        .optum-empty-state {
            border: 1px solid #e5e7eb;
            border-top: none;
            border-radius: 0 0 12px 12px;
            padding: 14px 16px;
            font-size: 14px;
            color: #6b7280;
            background: #ffffff;
            margin-bottom: 18px;
        }
        .optum-faq-title {
            font-size: 28px;
            font-weight: 700;
            color: #111827;
            margin: 40px 0 16px 0;
            letter-spacing: -0.02em;
        }
        @media (max-width: 1100px) {
            .optum-title {
                font-size: 32px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="optum-page-shell">', unsafe_allow_html=True)
    st.markdown('<div class="optum-breadcrumbs">Home &gt; Eligibility &gt; Pricing</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="optum-title">{html_escape(title)}</div>', unsafe_allow_html=True)

    if description:
        st.markdown(f'<div class="optum-desc">{html_escape(description)}</div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="optum-note">For details about payment information or the order summary, please view the payment schedule.</div>',
        unsafe_allow_html=True,
    )

    if not packages:
        st.info("No packages found.")
        st.markdown('</div>', unsafe_allow_html=True)
        return

    cols = st.columns(len(packages), gap="medium")
    for idx, package in enumerate(packages):
        with cols[idx]:
            border_container = st.container(border=True)
            with border_container:
                is_default = int(package.get("isDefault", 0)) == 1
                package_name = package.get("name", "Package")
                marketing_title = package.get("marketingTitle", "")
                tagline = package.get("tagline", "")
                package_amount_description = package.get("amountDescription", "")
                volumes = package.get("monthlyVolumes", [])

                st.markdown('<div class="optum-card-subtle">Package</div>', unsafe_allow_html=True)
                if is_default:
                    st.markdown('<div class="optum-badge">Recommended</div>', unsafe_allow_html=True)

                subtitle = tagline or marketing_title or ""
                st.markdown(f'<div class="optum-card-title">{html_escape(package_name)}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="optum-card-subtitle">{html_escape(subtitle)}</div>', unsafe_allow_html=True)

                if use_text_tiers:
                    display_amount = package.get("amount", "")
                    display_amount_description = package_amount_description

                    if display_amount not in ("", None):
                        st.markdown(f'<div class="optum-price">{format_money(display_amount)}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="optum-price">Contact sales</div>', unsafe_allow_html=True)

                    caption_text = str(display_amount_description) if display_amount_description else "Pricing shown for selected configuration"
                    st.markdown(f'<div class="optum-price-caption">{html_escape(caption_text)}</div>', unsafe_allow_html=True)
                    st.markdown('<div class="optum-button">Select</div>', unsafe_allow_html=True)

                    render_text_volume_tiers(volumes)

                else:
                    st.markdown('<div class="optum-section-label">Monthly volume</div>', unsafe_allow_html=True)

                    selected_volume = None
                    if volumes:
                        labels = []
                        default_index = 0
                        for mv_idx, mv in enumerate(volumes):
                            max_value = mv.get("maximumValue", "")
                            min_value = mv.get("minimumValue", "")

                            if max_value not in ("", None):
                                label = f"Up to {max_value}"
                            elif min_value not in ("", None):
                                label = f"Up to {min_value}"
                            else:
                                label = f"Tier {mv_idx + 1}"

                            labels.append(label)

                            if int(mv.get("isDefault", 0)) == 1:
                                default_index = mv_idx

                        selected_idx = st.selectbox(
                            "Select monthly volume",
                            options=list(range(len(volumes))),
                            index=default_index,
                            format_func=lambda i: labels[i],
                            key=f"preview_volume_select_{idx}",
                            label_visibility="collapsed",
                        )
                        selected_volume = volumes[selected_idx]
                    else:
                        st.caption("No monthly volume tiers found")

                    matched_term_amount = None
                    if selected_volume:
                        matched_term_amount = resolve_term_amount_for_volume(
                            selected_volume,
                            selected_term,
                            selected_term_idx,
                        )

                    if matched_term_amount:
                        display_amount = matched_term_amount.get(
                            "amount",
                            selected_volume.get("amount", package.get("amount", "")),
                        )
                        transaction_amount = matched_term_amount.get("transactionUnitAmount", "")
                        display_amount_description = selected_volume.get("amountDescription", "") or package_amount_description
                        if transaction_amount not in ("", None, 0, 0.0):
                            display_amount_description = f"{display_amount_description} | Per unit: {format_money(transaction_amount)}".strip(" |")
                    elif selected_volume:
                        display_amount = selected_volume.get("amount", package.get("amount", ""))
                        display_amount_description = selected_volume.get("amountDescription", "") or package_amount_description
                    else:
                        display_amount = package.get("amount", "")
                        display_amount_description = package_amount_description

                    if display_amount not in ("", None):
                        st.markdown(f'<div class="optum-price">{format_money(display_amount)}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="optum-price">Contact sales</div>', unsafe_allow_html=True)

                    caption_text = str(display_amount_description) if display_amount_description else "Pricing shown for selected configuration"
                    st.markdown(f'<div class="optum-price-caption">{html_escape(caption_text)}</div>', unsafe_allow_html=True)
                    st.markdown('<div class="optum-button">Select</div>', unsafe_allow_html=True)

                    if selected_volume:
                        st.markdown('<div class="optum-divider"></div>', unsafe_allow_html=True)
                        st.markdown('<div class="optum-section-label">Selected tier</div>', unsafe_allow_html=True)
                        selected_tier_name = selected_volume.get("internalName", "")
                        selected_max = selected_volume.get("maximumValue", "")
                        selected_min = selected_volume.get("minimumValue", "")

                        if selected_tier_name:
                            st.markdown(f'<div class="optum-tier-name">{html_escape(selected_tier_name)}</div>', unsafe_allow_html=True)

                        if selected_max not in ("", None):
                            st.markdown(f'<div class="optum-tier-caption">Max volume: {html_escape(selected_max)}</div>', unsafe_allow_html=True)
                        elif selected_min not in ("", None):
                            st.markdown(f'<div class="optum-tier-caption">Min volume: {html_escape(selected_min)}</div>', unsafe_allow_html=True)

                        selected_desc = selected_volume.get("amountDescription", "")
                        if selected_desc:
                            st.markdown(f'<div class="optum-tier-caption">{html_escape(selected_desc)}</div>', unsafe_allow_html=True)

    if contract_header or contract_initial_terms:
        st.markdown('<div class="optum-section-title">Contract Terms</div>', unsafe_allow_html=True)

        if contract_header:
            st.markdown(f'<div class="optum-note">{html_escape(contract_header)}</div>', unsafe_allow_html=True)

        if contract_initial_terms:
            selected_term_idx = st.selectbox(
                "Select contract term",
                options=list(range(len(contract_initial_terms))),
                index=selected_term_idx,
                format_func=lambda i: contract_term_labels[i],
                key="preview_contract_term_select",
            )
            selected_term = contract_initial_terms[selected_term_idx]

            selected_term_description = selected_term.get("description", "")
            if selected_term_description:
                st.markdown(f'<div class="optum-term-helper">{html_escape(selected_term_description)}</div>', unsafe_allow_html=True)

    st.markdown('<div class="optum-section-title">Included Features</div>', unsafe_allow_html=True)

    all_group_names = []
    for package in packages:
        for group in package.get("optionItems", []):
            group_name = group.get("optionItemType", "").strip() or "Modules"
            if group_name not in all_group_names:
                all_group_names.append(group_name)

    render_feature_comparison_matrix(packages, all_group_names)

    faq_items = data.get("faqItems", []) or data.get("faqs", [])
    st.markdown('<div class="optum-faq-title">Frequently Asked Questions</div>', unsafe_allow_html=True)
    if isinstance(faq_items, list) and faq_items:
        for faq in faq_items:
            question = faq.get("question") or faq.get("title") or "Question"
            answer = faq.get("answer") or faq.get("description") or ""
            with st.expander(question):
                st.write(answer)
    else:
        st.info("No FAQ items were found in this JSON.")

    st.markdown('</div>', unsafe_allow_html=True)

def main() -> None:
    st.set_page_config(page_title="JSON Editor", layout="wide")
    st.title("JSON Editor")
    st.caption(f"Application Version: {APP_VERSION}")

    with st.sidebar:
        st.header("File")
        uploaded_file = st.file_uploader("Upload a JSON file", type=["json"])

        if uploaded_file is not None:
            try:
                maybe_init_state_from_upload(uploaded_file)
                st.success(f"Loaded: {uploaded_file.name}")
            except Exception as exc:
                st.error(f"Could not load JSON file: {exc}")

        page = None
        if st.session_state.get("load_complete"):
            st.markdown("---")
            st.header("Sections")
            page = st.radio(
                "Go to",
                [
                    "Product Info",
                    "Contract Terms",
                    "Package Details",
                    "Monthly Volume Tiers",
                    "Option Groups",
                    "Pricing Page Preview",
                    "Raw JSON",
                    "Validation",
                    "JSON Preview",
                ],
            )

            st.markdown("---")
            st.header("Save")
            original_name = st.session_state.get("original_filename", "edited.json")
            suggested_name = make_versioned_filename(original_name)

            if st.button("Refresh Raw JSON from Edited Data"):
                sync_raw_text_from_edited()
                st.success("Raw JSON refreshed.")

            all_errors: List[str] = []
            all_errors.extend(validate_json_structure(st.session_state["edited_json"]))
            all_errors.extend(validate_orphan_term_references(st.session_state["edited_json"]))

            if all_errors:
                st.error("Fix validation errors before downloading.")
            else:
                st.download_button(
                    label="Download New Version",
                    data=safe_json_dumps(st.session_state["edited_json"]),
                    file_name=suggested_name,
                    mime="application/json",
                )

    if not st.session_state.get("load_complete"):
        st.info("Upload a JSON file to begin.")
        return

    edited_json = st.session_state["edited_json"]
    packages = edited_json.get("packages", [])
    clamp_selected_package_index()

    if page == "Product Info":
        render_top_level_editor(edited_json)
        sync_raw_text_from_edited()

    elif page == "Contract Terms":
        render_contract_terms_editor(edited_json)
        sync_raw_text_from_edited()

    elif page in ["Package Details", "Monthly Volume Tiers", "Option Groups"]:
        if not packages:
            st.info("No packages found.")
            st.subheader("Package Actions")
            if st.button("Add New Package"):
                packages.append(default_package())
                normalize_package_sort_orders(packages)
                st.session_state["selected_package_index"] = 0
                sync_raw_text_from_edited()
                st.rerun()
            return

        render_package_overview(packages)
        package_index = package_selector(packages)
        render_package_actions(packages, package_index)
        clamp_selected_package_index()
        package_index = st.session_state["selected_package_index"]
        package = packages[package_index]

        st.markdown("---")
        st.markdown(f"### Editing Package: {package.get('name', 'Unnamed Package')}")

        if page == "Package Details":
            render_package_details_editor(package)
        elif page == "Monthly Volume Tiers":
            render_monthly_volumes_editor(package)
        elif page == "Option Groups":
            render_option_groups_editor(package)

        sync_raw_text_from_edited()

    elif page == "Pricing Page Preview":
        render_pricing_page(edited_json)

    elif page == "Raw JSON":
        render_raw_json_editor()

    elif page == "Validation":
        render_validation_panel(edited_json)

    elif page == "JSON Preview":
        render_json_preview(edited_json)


if __name__ == "__main__":
    main()
