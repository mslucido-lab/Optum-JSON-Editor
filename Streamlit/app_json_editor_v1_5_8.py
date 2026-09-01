"""
app_json_editor_v1_5_8.py

Version: v1.5.8
Date: 2026-03-19
Project: JSON Editor
Purpose: Load a JSON file, edit it safely, save a new version, and preview a pricing page.

Fixes:
- Prevented uploaded file from re-initializing session state on every rerun
- This fixes fields like package name disappearing after pressing Enter
"""

import copy
import hashlib
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st


APP_VERSION = "v1.5.8"


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


def init_state_from_upload(uploaded_file) -> None:
    parsed = parse_json_file(uploaded_file)
    st.session_state["original_filename"] = uploaded_file.name
    st.session_state["original_json"] = deep_copy_json(parsed)
    st.session_state["edited_json"] = deep_copy_json(parsed)
    st.session_state["raw_json_text"] = safe_json_dumps(parsed)
    st.session_state["load_complete"] = True
    st.session_state["uploaded_file_signature"] = get_uploaded_file_signature(uploaded_file)


def maybe_init_state_from_upload(uploaded_file) -> None:
    if uploaded_file is None:
        return

    current_sig = get_uploaded_file_signature(uploaded_file)
    prior_sig = st.session_state.get("uploaded_file_signature")

    if prior_sig != current_sig or not st.session_state.get("load_complete"):
        init_state_from_upload(uploaded_file)


def sync_raw_text_from_edited() -> None:
    st.session_state["raw_json_text"] = safe_json_dumps(st.session_state["edited_json"])


def sync_edited_from_raw_text() -> tuple[bool, str]:
    try:
        parsed = json.loads(st.session_state["raw_json_text"])
        st.session_state["edited_json"] = parsed
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
    if "selected_package_index" not in st.session_state:
        st.session_state["selected_package_index"] = 0
    if not packages:
        st.session_state["selected_package_index"] = 0
        return 0

    current = min(st.session_state["selected_package_index"], len(packages) - 1)
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
    errors = validate_json_structure(data)
    if errors:
        st.error("Validation found issues.")
        for err in errors:
            st.write(f"- {err}")
    else:
        st.success("Validation passed.")


def render_json_preview(data: Dict[str, Any]) -> None:
    tab1, tab2 = st.tabs(["Edited JSON", "Original JSON"])
    with tab1:
        st.code(safe_json_dumps(data), language="json")
    with tab2:
        st.code(safe_json_dumps(st.session_state["original_json"]), language="json")


def collect_included_features(package: Dict[str, Any]) -> List[str]:
    features: List[str] = []
    for group in package.get("optionItems", []):
        for item in group.get("optionLineItems", []):
            if item.get("isIncluded") == 1:
                feature_name = (
                    item.get("marketingTitle")
                    or item.get("internalName")
                    or item.get("shortDescription")
                    or "Included feature"
                )
                features.append(str(feature_name))
    return features


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

    selected_value = str(selected_term.get("termValue", "")).strip()
    selected_unit = str(selected_term.get("termUnit", "")).strip()
    selected_sort = str(selected_term.get("sortOrder", "")).strip()
    selected_label = f"{selected_value} {selected_unit}".strip()

    candidates = {
        selected_value.lower(),
        selected_label.lower(),
        selected_sort.lower(),
        str(selected_term_idx).lower(),
        str(selected_term_idx + 1).lower(),
    }

    for term_amount in term_amounts:
        raw_id = str(term_amount.get("initialTermId", "")).strip().lower()
        if raw_id and raw_id in candidates:
            return term_amount

    if 0 <= selected_term_idx < len(term_amounts):
        return term_amounts[selected_term_idx]

    return term_amounts[0] if term_amounts else None


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

    selected_value = str(selected_term.get("termValue", "")).strip()
    selected_unit = str(selected_term.get("termUnit", "")).strip()
    selected_sort = str(selected_term.get("sortOrder", "")).strip()
    selected_label = f"{selected_value} {selected_unit}".strip()

    candidates = {
        selected_value.lower(),
        selected_label.lower(),
        selected_sort.lower(),
        str(selected_term_idx).lower(),
        str(selected_term_idx + 1).lower(),
    }

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
        tier_name = mv.get("internalName", "")
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
        div[data-testid="stVerticalBlock"] div[data-testid="stContainer"] {
            border-radius: 16px;
        }
        .optum-breadcrumbs {
            font-size: 13px;
            color: #5f6368;
            margin-bottom: 18px;
        }
        .optum-title {
            font-size: 34px;
            font-weight: 700;
            color: #1f2933;
            line-height: 1.15;
            margin-bottom: 10px;
        }
        .optum-desc {
            font-size: 16px;
            color: #4b5563;
            line-height: 1.55;
            max-width: 860px;
            margin-bottom: 10px;
        }
        .optum-note {
            background: #f8fafb;
            border: 1px solid #e6ebef;
            border-radius: 10px;
            padding: 12px 14px;
            font-size: 14px;
            color: #4b5563;
            margin: 18px 0 26px 0;
        }
        .optum-card-title {
            font-size: 22px;
            font-weight: 700;
            color: #111827;
            margin-bottom: 8px;
        }
        .optum-card-subtitle {
            font-size: 12px;
            color: #4b5563;
            margin-bottom: 16px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .optum-price {
            font-size: 28px;
            font-weight: 800;
            color: #111827;
            line-height: 1;
            margin: 12px 0 6px 0;
        }
        .optum-price-caption {
            font-size: 12px;
            color: #6b7280;
            margin-bottom: 18px;
        }
        .optum-badge {
            display: inline-block;
            font-size: 12px;
            font-weight: 700;
            color: #00695c;
            background: #e7f6f3;
            border-radius: 999px;
            padding: 6px 10px;
            margin-bottom: 12px;
        }
        .optum-button {
            display: block;
            width: 100%;
            text-align: center;
            background: #0f766e;
            color: white;
            font-weight: 700;
            font-size: 14px;
            border-radius: 999px;
            padding: 10px 14px;
            margin: 10px 0 16px 0;
            box-sizing: border-box;
        }
        .optum-section-label {
            font-size: 11px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #6b7280;
            font-weight: 700;
            margin: 12px 0 8px 0;
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
            line-height: 1.4;
            padding: 10px 0 4px 0;
            border-top: 1px solid #eef2f5;
        }
        .optum-tier-caption {
            font-size: 11px;
            color: #6b7280;
            margin-bottom: 6px;
        }
        .optum-feature-section-title {
            font-size: 24px;
            font-weight: 700;
            color: #111827;
            margin: 32px 0 16px 0;
        }
        .optum-feature-group-title {
            font-size: 18px;
            font-weight: 700;
            color: #111827;
            margin: 14px 0 10px 0;
        }
        .optum-feature-package-title {
            font-size: 15px;
            font-weight: 700;
            color: #374151;
            margin: 8px 0;
        }
        .optum-faq-title {
            font-size: 24px;
            font-weight: 700;
            color: #111827;
            margin: 28px 0 16px 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="optum-breadcrumbs">Home &gt; Eligibility &gt; Pricing</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="optum-title">{title}</div>', unsafe_allow_html=True)

    if description:
        st.markdown(f'<div class="optum-desc">{description}</div>', unsafe_allow_html=True)

    st.markdown(
        '<div class="optum-note">For details about payment information or the order summary, please view the payment schedule.</div>',
        unsafe_allow_html=True,
    )

    if not packages:
        st.info("No packages found.")
        return

    if (contract_header or contract_initial_terms) and not use_text_tiers:
        st.markdown('<div class="optum-feature-section-title">Contract Terms</div>', unsafe_allow_html=True)

        if contract_header:
            st.markdown(
                f'<div class="optum-note">{contract_header}</div>',
                unsafe_allow_html=True,
            )

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
                st.caption(selected_term_description)
    elif contract_header:
        st.markdown(
            f'<div class="optum-note">{contract_header}</div>',
            unsafe_allow_html=True,
        )

    cols = st.columns(len(packages), gap="small")
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

                if is_default:
                    st.markdown('<div class="optum-badge">Recommended</div>', unsafe_allow_html=True)

                subtitle = tagline or marketing_title or ""
                st.markdown(f'<div class="optum-card-title">{package_name}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="optum-card-subtitle">{subtitle}</div>', unsafe_allow_html=True)

                if use_text_tiers:
                    display_amount = package.get("amount", "")
                    display_amount_description = package_amount_description

                    if display_amount not in ("", None):
                        st.markdown(f'<div class="optum-price">{format_money(display_amount)}</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="optum-price">Contact sales</div>', unsafe_allow_html=True)

                    caption_text = str(display_amount_description) if display_amount_description else "Pricing shown for selected configuration"
                    st.markdown(f'<div class="optum-price-caption">{caption_text}</div>', unsafe_allow_html=True)
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
                        display_amount_description = (
                            selected_volume.get("amountDescription", "")
                            or package_amount_description
                        )
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
                    st.markdown(f'<div class="optum-price-caption">{caption_text}</div>', unsafe_allow_html=True)
                    st.markdown('<div class="optum-button">Select</div>', unsafe_allow_html=True)

                    if selected_volume:
                        st.markdown('<div class="optum-section-label">Selected tier</div>', unsafe_allow_html=True)
                        selected_tier_name = selected_volume.get("internalName", "")
                        selected_max = selected_volume.get("maximumValue", "")
                        selected_min = selected_volume.get("minimumValue", "")

                        if selected_tier_name:
                            st.markdown(f'<div class="optum-tier-name">{selected_tier_name}</div>', unsafe_allow_html=True)

                        if selected_max not in ("", None):
                            st.write(f"Max volume: {selected_max}")
                        elif selected_min not in ("", None):
                            st.write(f"Min volume: {selected_min}")

                        selected_desc = selected_volume.get("amountDescription", "")
                        if selected_desc:
                            st.markdown(f'<div class="optum-tier-caption">{selected_desc}</div>', unsafe_allow_html=True)

    st.markdown('<div class="optum-feature-section-title">Included Features</div>', unsafe_allow_html=True)

    all_group_names = []
    for package in packages:
        for group in package.get("optionItems", []):
            group_name = group.get("optionItemType", "").strip()
            if not group_name:
                group_name = "Modules"
            if group_name not in all_group_names:
                all_group_names.append(group_name)

    if all_group_names:
        for group_name in all_group_names:
            st.markdown(f'<div class="optum-feature-group-title">{group_name}</div>', unsafe_allow_html=True)
            feature_cols = st.columns(len(packages))
            any_features_in_group = False

            for pkg_idx, package in enumerate(packages):
                with feature_cols[pkg_idx]:
                    st.markdown(
                        f'<div class="optum-feature-package-title">{package.get("name", "Package")}</div>',
                        unsafe_allow_html=True,
                    )

                    group_features = []
                    for group in package.get("optionItems", []):
                        current_group_name = group.get("optionItemType", "").strip() or "Modules"
                        if current_group_name == group_name:
                            for item in group.get("optionLineItems", []):
                                if item.get("isIncluded") == 1:
                                    feature_name = (
                                        item.get("marketingTitle")
                                        or item.get("internalName")
                                        or item.get("shortDescription")
                                        or "Included feature"
                                    )
                                    group_features.append(str(feature_name))

                    if group_features:
                        any_features_in_group = True
                        for feature in group_features:
                            st.write(f"• {feature}")
                    else:
                        st.caption("None included")

            if not any_features_in_group:
                st.caption("No included features found in this section.")
    else:
        st.info("No option groups were found for included features.")

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

    if page == "Product Info":
        render_top_level_editor(edited_json)
        sync_raw_text_from_edited()

    elif page == "Contract Terms":
        render_contract_terms_editor(edited_json)
        sync_raw_text_from_edited()

    elif page in ["Package Details", "Monthly Volume Tiers", "Option Groups"]:
        if not packages:
            st.info("No packages found.")
            return

        render_package_overview(packages)
        package_index = package_selector(packages)
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
