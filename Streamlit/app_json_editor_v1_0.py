"""
app_json_editor_v1_0.py

Version: v1.0
Date: 2026-03-19
Project: JSON Editor
Purpose: Load a JSON file, edit it safely, and save a new version.

Change Log:
- v1.0
  - Added JSON file uploader
  - Added editable top-level fields
  - Added editable contract term tables
  - Added raw JSON editor
  - Added validation panel
  - Added versioned JSON download
  - Added original vs edited preview
"""

import copy
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Tuple

import pandas as pd
import streamlit as st


APP_VERSION = "v1.0"


def deep_copy_json(data: Any) -> Any:
    return copy.deepcopy(data)


def parse_json_file(uploaded_file) -> Dict[str, Any]:
    raw = uploaded_file.read().decode("utf-8")
    return json.loads(raw)


def safe_json_dumps(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)


def coerce_scalar(value: str, original: Any) -> Any:
    if isinstance(original, bool):
        return value.strip().lower() in {"true", "1", "yes", "y"}
    if isinstance(original, int) and not isinstance(original, bool):
        try:
            return int(value)
        except Exception:
            return original
    if isinstance(original, float):
        try:
            return float(value)
        except Exception:
            return original
    if original is None:
        lowered = value.strip().lower()
        if lowered == "null":
            return None
        return value
    return value


def make_versioned_filename(original_name: str, app_version: str = APP_VERSION) -> str:
    base = re.sub(r"\.json$", "", original_name, flags=re.IGNORECASE)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    version_label = app_version.replace(".", "_")
    return f"{base}_{version_label}_{stamp}.json"


def validate_json_structure(data: Dict[str, Any]) -> List[str]:
    errors: List[str] = []

    required_top_level = [
        "name",
        "description",
        "slug",
        "contractTerms",
        "packages",
    ]

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
        try:
            term_value = row["termValue"]
            sort_order = row["sortOrder"]
            is_default = row["isDefault"]

            if str(term_value).strip() == "":
                continue

            term_entry = {
                "termValue": int(term_value) if str(term_value).strip().isdigit() else term_value,
                "termUnit": str(row["termUnit"]).strip(),
                "description": str(row["description"]).strip(),
                "isDefault": int(is_default) if str(is_default).strip() != "" else 0,
                "sortOrder": int(sort_order) if str(sort_order).strip() != "" else idx,
                "discountItems": [],
            }

            if idx < len(original_terms) and isinstance(original_terms[idx], dict):
                if "discountItems" in original_terms[idx]:
                    term_entry["discountItems"] = original_terms[idx].get("discountItems", [])

            rebuilt.append(term_entry)
        except Exception:
            continue
    return rebuilt


def init_state_from_upload(uploaded_file) -> None:
    parsed = parse_json_file(uploaded_file)
    st.session_state["original_filename"] = uploaded_file.name
    st.session_state["original_json"] = deep_copy_json(parsed)
    st.session_state["edited_json"] = deep_copy_json(parsed)
    st.session_state["raw_json_text"] = safe_json_dumps(parsed)
    st.session_state["load_complete"] = True


def sync_raw_text_from_edited() -> None:
    st.session_state["raw_json_text"] = safe_json_dumps(st.session_state["edited_json"])


def sync_edited_from_raw_text() -> Tuple[bool, str]:
    try:
        parsed = json.loads(st.session_state["raw_json_text"])
        st.session_state["edited_json"] = parsed
        return True, "Raw JSON applied successfully."
    except Exception as exc:
        return False, f"Raw JSON is invalid: {exc}"


def render_top_level_editor(data: Dict[str, Any]) -> None:
    st.subheader("Top-Level Fields")

    editable_keys = [
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

    for key in editable_keys:
        if key not in data:
            continue

        value = data[key]
        widget_key = f"top_{key}"

        if isinstance(value, str) and len(value) > 120:
            data[key] = st.text_area(key, value=value, key=widget_key, height=120)
        elif isinstance(value, str):
            data[key] = st.text_input(key, value=value, key=widget_key)
        elif isinstance(value, bool):
            data[key] = st.checkbox(key, value=value, key=widget_key)
        elif isinstance(value, int):
            data[key] = st.number_input(key, value=int(value), step=1, key=widget_key)
        elif isinstance(value, float):
            data[key] = st.number_input(key, value=float(value), key=widget_key)
        else:
            data[key] = st.text_input(key, value=str(value), key=widget_key)


def render_contract_terms_editor(data: Dict[str, Any]) -> None:
    st.subheader("Contract Terms")

    contract_terms = data.setdefault("contractTerms", {})

    header_keys = [
        "headerDescription",
        "toolTipText",
        "toolTipDescription",
        "isAutoRenewalEnabled",
    ]

    for key in header_keys:
        if key not in contract_terms:
            continue

        value = contract_terms[key]
        widget_key = f"ct_{key}"

        if isinstance(value, str) and len(value) > 100:
            contract_terms[key] = st.text_area(key, value=value, key=widget_key, height=100)
        elif isinstance(value, str):
            contract_terms[key] = st.text_input(key, value=value, key=widget_key)
        elif isinstance(value, bool):
            contract_terms[key] = st.checkbox(key, value=value, key=widget_key)
        elif isinstance(value, int):
            contract_terms[key] = int(st.number_input(key, value=int(value), step=1, key=widget_key))
        else:
            contract_terms[key] = st.text_input(key, value=str(value), key=widget_key)

    st.markdown("#### Initial Terms")
    initial_terms_original = contract_terms.get("contractInitialTerm", [])
    initial_df = normalize_terms_for_editor(initial_terms_original)
    edited_initial_df = st.data_editor(
        initial_df,
        num_rows="dynamic",
        use_container_width=True,
        key="contract_initial_term_editor",
    )
    contract_terms["contractInitialTerm"] = dataframe_to_terms(edited_initial_df, initial_terms_original)

    st.markdown("#### Auto Renewal Terms")
    auto_terms_original = contract_terms.get("contractAutoRenewalTerm", [])
    auto_df = normalize_terms_for_editor(auto_terms_original)
    edited_auto_df = st.data_editor(
        auto_df,
        num_rows="dynamic",
        use_container_width=True,
        key="contract_auto_term_editor",
    )
    contract_terms["contractAutoRenewalTerm"] = dataframe_to_terms(edited_auto_df, auto_terms_original)


def render_package_summary(data: Dict[str, Any]) -> None:
    st.subheader("Packages")

    packages = data.get("packages", [])
    if not packages:
        st.info("No packages found.")
        return

    rows = []
    for i, package in enumerate(packages):
        rows.append(
            {
                "Index": i,
                "Name": package.get("name", ""),
                "Internal Name": package.get("internalName", ""),
                "Sort Order": package.get("sortOrder", ""),
                "Monthly Volume Count": len(package.get("monthlyVolumes", [])),
                "Option Group Count": len(package.get("optionItems", [])),
            }
        )

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    selected_index = st.selectbox(
        "Select package to edit",
        options=list(range(len(packages))),
        format_func=lambda i: f"{i}: {packages[i].get('name', 'Unnamed Package')}",
        key="selected_package_index",
    )

    package = packages[selected_index]

    st.markdown("#### Package Details")

    for key in [
        "internalName",
        "name",
        "marketingTitle",
        "tagline",
        "shortDescription",
        "longDescription",
        "amount",
        "amountDescription",
        "unit",
        "sortOrder",
        "includedModuleText",
    ]:
        if key not in package:
            continue

        value = package[key]
        widget_key = f"pkg_{selected_index}_{key}"

        if isinstance(value, str) and len(value) > 100:
            package[key] = st.text_area(key, value=value, key=widget_key, height=100)
        elif isinstance(value, str):
            package[key] = st.text_input(key, value=value, key=widget_key)
        elif isinstance(value, int):
            package[key] = int(st.number_input(key, value=int(value), step=1, key=widget_key))
        elif isinstance(value, float):
            package[key] = float(st.number_input(key, value=float(value), key=widget_key))
        else:
            package[key] = st.text_input(key, value=str(value), key=widget_key)

    with st.expander("Monthly Volumes", expanded=False):
        monthly_volumes = package.get("monthlyVolumes", [])
        if not monthly_volumes:
            st.info("No monthly volumes found.")
        else:
            mv_rows = []
            for idx, item in enumerate(monthly_volumes):
                mv_rows.append(
                    {
                        "Index": idx,
                        "internalName": item.get("internalName", ""),
                        "minimumValue": item.get("minimumValue", ""),
                        "maximumValue": item.get("maximumValue", ""),
                        "amount": item.get("amount", ""),
                        "transactionUnitAmount": item.get("transactionUnitAmount", ""),
                        "sortOrder": item.get("sortOrder", ""),
                    }
                )
            st.dataframe(pd.DataFrame(mv_rows), use_container_width=True, hide_index=True)

    with st.expander("Option Groups", expanded=False):
        option_items = package.get("optionItems", [])
        if not option_items:
            st.info("No option groups found.")
        else:
            og_rows = []
            for idx, item in enumerate(option_items):
                og_rows.append(
                    {
                        "Index": idx,
                        "optionItemType": item.get("optionItemType", ""),
                        "headerDescription": item.get("headerDescription", ""),
                        "optionLineItems": len(item.get("optionLineItems", [])),
                    }
                )
            st.dataframe(pd.DataFrame(og_rows), use_container_width=True, hide_index=True)


def render_raw_json_editor() -> None:
    st.subheader("Raw JSON Editor")
    st.session_state["raw_json_text"] = st.text_area(
        "Edit raw JSON directly",
        value=st.session_state.get("raw_json_text", ""),
        height=500,
        key="raw_json_editor_text_area",
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Apply Raw JSON Changes"):
            ok, message = sync_edited_from_raw_text()
            if ok:
                st.success(message)
            else:
                st.error(message)
    with col2:
        if st.button("Reset Raw JSON to Edited Copy"):
            sync_raw_text_from_edited()
            st.success("Raw JSON reset from current edited copy.")


def render_validation_panel(data: Dict[str, Any]) -> None:
    st.subheader("Validation")
    errors = validate_json_structure(data)

    if errors:
        st.error("Validation found issues.")
        for err in errors:
            st.write(f"- {err}")
    else:
        st.success("Validation passed.")


def render_json_preview(data: Dict[str, Any], title: str) -> None:
    st.subheader(title)
    st.code(safe_json_dumps(data), language="json")


def main() -> None:
    st.set_page_config(page_title="JSON Editor", layout="wide")
    st.title("JSON Editor")
    st.caption(f"Application Version: {APP_VERSION}")

    with st.sidebar:
        st.header("File")
        uploaded_file = st.file_uploader("Upload a JSON file", type=["json"])

        if uploaded_file is not None:
            try:
                init_state_from_upload(uploaded_file)
                st.success(f"Loaded: {uploaded_file.name}")
            except Exception as exc:
                st.error(f"Could not load JSON file: {exc}")

        if st.session_state.get("load_complete"):
            st.markdown("---")
            st.header("Navigation")
            page = st.radio(
                "Go to",
                [
                    "Top-Level Fields",
                    "Contract Terms",
                    "Packages",
                    "Raw JSON",
                    "Validation",
                    "Preview",
                ],
                key="page_selector",
            )

            st.markdown("---")
            st.header("Save")
            original_name = st.session_state.get("original_filename", "edited.json")
            suggested_name = make_versioned_filename(original_name)

            if st.button("Refresh Raw JSON from Edited Data"):
                sync_raw_text_from_edited()
                st.success("Raw JSON refreshed.")

            download_text = safe_json_dumps(st.session_state["edited_json"])
            st.download_button(
                label="Download New Version",
                data=download_text,
                file_name=suggested_name,
                mime="application/json",
            )
        else:
            page = None

    if not st.session_state.get("load_complete"):
        st.info("Upload a JSON file to begin.")
        st.write("Version control rule for this file: save each new Python file locally with its version number.")
        return

    edited_json = st.session_state["edited_json"]

    if page == "Top-Level Fields":
        render_top_level_editor(edited_json)
        sync_raw_text_from_edited()

    elif page == "Contract Terms":
        render_contract_terms_editor(edited_json)
        sync_raw_text_from_edited()

    elif page == "Packages":
        render_package_summary(edited_json)
        sync_raw_text_from_edited()

    elif page == "Raw JSON":
        render_raw_json_editor()

    elif page == "Validation":
        render_validation_panel(edited_json)

    elif page == "Preview":
        tab1, tab2 = st.tabs(["Edited JSON", "Original JSON"])
        with tab1:
            render_json_preview(edited_json, "Edited JSON Preview")
        with tab2:
            render_json_preview(st.session_state["original_json"], "Original JSON Preview")


if __name__ == "__main__":
    main()
