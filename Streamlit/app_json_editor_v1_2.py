# app_json_editor_v1_2.py

"""
Version: v1.2
Date: 2026-03-19
Project: JSON Editor

Purpose:
- Adds live pricing page preview
- Keeps full editor from v1.1
"""

import copy
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st


APP_VERSION = "v1.2"


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


def init_state_from_upload(uploaded_file) -> None:
    parsed = parse_json_file(uploaded_file)
    st.session_state["original_filename"] = uploaded_file.name
    st.session_state["original_json"] = deep_copy_json(parsed)
    st.session_state["edited_json"] = deep_copy_json(parsed)
    st.session_state["raw_json_text"] = safe_json_dumps(parsed)
    st.session_state["load_complete"] = True


# -------- NEW PREVIEW --------

def render_pricing_page(data: Dict[str, Any]) -> None:
    st.title(data.get("name", "Product"))
    st.write(data.get("description", ""))

    packages = data.get("packages", [])

    if not packages:
        st.info("No packages found")
        return

    cols = st.columns(len(packages))

    for i, package in enumerate(packages):
        with cols[i]:
            st.markdown("### " + package.get("name", "Package"))

            if package.get("tagline"):
                st.caption(package.get("tagline"))

            st.markdown("#### Pricing")

            for mv in package.get("monthlyVolumes", []):
                min_v = mv.get("minimumValue", "")
                max_v = mv.get("maximumValue", "")
                amt = mv.get("amount", 0)
                st.write(f"{min_v} - {max_v}: ${amt}")

            st.markdown("#### Features")

            for group in package.get("optionItems", []):
                for item in group.get("optionLineItems", []):
                    if item.get("isIncluded") == 1:
                        st.write(f"- {item.get('internalName')}")


def main() -> None:
    st.set_page_config(page_title="JSON Editor", layout="wide")
    st.title("JSON Editor")
    st.caption(f"Application Version: {APP_VERSION}")

    with st.sidebar:
        uploaded_file = st.file_uploader("Upload a JSON file", type=["json"])

        if uploaded_file is not None:
            try:
                init_state_from_upload(uploaded_file)
                st.success(f"Loaded: {uploaded_file.name}")
            except Exception as exc:
                st.error(f"Could not load JSON file: {exc}")

        page = None
        if st.session_state.get("load_complete"):
            page = st.radio("Go to", ["Preview"])

            original_name = st.session_state.get("original_filename", "edited.json")
            suggested_name = make_versioned_filename(original_name)

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

    if page == "Preview":
        render_pricing_page(edited_json)


if __name__ == "__main__":
    main()
