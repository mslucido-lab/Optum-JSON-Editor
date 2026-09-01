# Pricing Editor — ChatGPT Handoff Doc
## Drop 1: Layout & Navigation → v1.7.0
*Prepared: 2026-05-09*

---

## Context

You are extending an existing Streamlit app: `app_json_editor_v1_6_17.py`. The full file will be pasted below this doc. Do not rewrite it from scratch — make targeted changes only.

**Output:** A new file named `app_json_editor_v1_7_0.py` with an updated change log block at the top.

**Stack:** Python + Streamlit only. No new dependencies. No database. Runs locally via `streamlit run`.

---

## What This Drop Does

Three changes. Implement all three in one file. Do not split across versions.

---

## Change 1 — Persistent right panel: Pricing Preview + JSON tabs

### What it is
Every editor section currently uses the full page width. Wrap each section in `st.columns([2, 1])` so the right column always shows a tabbed panel with two views: **Pricing Preview** and **JSON Output**.

### Exact implementation

In `main()`, after the page routing block, wherever a section renders (Product Info, Contract Terms, Package Details, Monthly Volume Tiers, Option Groups), wrap the render call in a two-column layout:

```python
col_editor, col_preview = st.columns([2, 1])

with col_editor:
    # existing render call goes here (unchanged)
    if page == "Product Info":
        render_top_level_editor(edited_json)
        sync_raw_text_from_edited()
    elif page == "Contract Terms":
        ...etc

with col_preview:
    render_right_panel(edited_json)
```

### New function: `render_right_panel(data)`

Create this new function. It renders a tabbed panel with two tabs:

```python
def render_right_panel(data: Dict[str, Any]) -> None:
    tab_preview, tab_json = st.tabs(["Pricing Preview", "JSON Output"])
    with tab_preview:
        render_pricing_page_compact(data)
    with tab_json:
        render_json_preview(data)
```

### New function: `render_pricing_page_compact(data)`

This is a **condensed version** of the existing `render_pricing_page()` — same data, but stripped down to fit a narrow column. It should NOT use `st.columns` internally (the outer column is already narrow). Rules:

- Show product name and a truncated `headerDescription` (strip HTML tags, max 120 chars, add `…` if truncated)
- List package names with their base `amount` — one line each, no sub-tables
- If `contractTerms.contractInitialTerm` has entries, show them as a selectbox labeled "Contract Term"
- Show option group names and item counts (e.g. "Implementations: 1 item")
- Show `paymentSchedule` text at the bottom (strip HTML, truncate to 100 chars)
- No custom CSS injections — plain Streamlit widgets only in this compact view

Use this helper for stripping HTML (already exists in the file — reuse it):
```python
clean_preview_text(text)
```

### Sections that do NOT get the right panel

These sections already use the full width intentionally — do not wrap them:
- `Pricing Page Preview` (it IS the preview)
- `Raw JSON`
- `Validation`
- `JSON Preview`

---

## Change 2 — Package tabs inside the editor panel

### What it is
Replace the `st.selectbox` package selector (currently rendered by `package_selector()`) with `st.tabs()` — one tab per package, rendered inside the editor column, above the package edit fields.

### Exact implementation

**In `main()`**, in the `elif page in ["Package Details", "Monthly Volume Tiers", "Option Groups"]:` block, replace this pattern:

```python
render_package_overview(packages)
package_index = package_selector(packages)
render_package_actions(packages, package_index)
clamp_selected_package_index()
package_index = st.session_state["selected_package_index"]
package = packages[package_index]

st.markdown("---")
st.markdown(f"### Editing Package: {package.get('name', 'Unnamed Package')}")
```

With this new pattern (still inside `col_editor`):

```python
render_package_overview(packages)
render_package_actions_global(packages)

tab_labels = [p.get("name", f"Package {i}") for i, p in enumerate(packages)]
pkg_tabs = st.tabs(tab_labels)

for tab_idx, pkg_tab in enumerate(pkg_tabs):
    with pkg_tab:
        package = packages[tab_idx]
        st.session_state["selected_package_index"] = tab_idx

        if page == "Package Details":
            render_package_details_editor(package)
        elif page == "Monthly Volume Tiers":
            render_monthly_volumes_editor(package)
        elif page == "Option Groups":
            render_option_groups_editor(package)

        sync_raw_text_from_edited()
```

### New function: `render_package_actions_global(packages)`

Refactor the existing `render_package_actions(packages, selected_index)` into a version that does not depend on a selected index for Add/Duplicate/Delete, because with tabs there is no single "selected" package. Replace it with:

```python
def render_package_actions_global(packages: List[Dict[str, Any]]) -> None:
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("+ Add Package", use_container_width=True):
            packages.append(default_package())
            normalize_package_sort_orders(packages)
            sync_raw_text_from_edited()
            st.rerun()
```

Keep the old `render_package_actions()` function in the file but stop calling it — do not delete it, in case it's needed for rollback.

### Session state note
`st.tabs()` does not expose a selected index — Streamlit renders all tabs and shows one. This means `st.session_state["selected_package_index"]` will always be set to the last tab rendered in the loop. That's acceptable for v1.7.0. Duplicate and Delete per-package can be added in a later version inside each tab body if needed.

---

## Change 3 — Persistent status header

### What it is
A sticky summary line below the app title showing: filename, unsaved state, validation status, and package count. Always visible regardless of which section is active.

### Exact implementation

In `main()`, after `st.title(...)` and `st.caption(...)`, add this block (runs on every page):

```python
if st.session_state.get("load_complete"):
    edited_json = st.session_state["edited_json"]
    original_filename = st.session_state.get("original_filename", "—")
    pkg_count = len(edited_json.get("packages", []))

    all_errors: List[str] = []
    all_errors.extend(validate_json_structure(edited_json))
    all_errors.extend(validate_contract_term_defaults(edited_json))
    all_errors.extend(validate_orphan_term_references(edited_json))

    is_dirty = st.session_state.get("is_dirty", False)
    dirty_indicator = "🟡 Unsaved changes" if is_dirty else "🟢 Saved"
    val_indicator = f"🔴 {len(all_errors)} error(s)" if all_errors else "✅ Valid JSON"

    st.markdown(
        f"`{original_filename}` &nbsp;|&nbsp; {dirty_indicator} &nbsp;|&nbsp; "
        f"{val_indicator} &nbsp;|&nbsp; {pkg_count} package(s)",
        unsafe_allow_html=True,
    )
    st.markdown("---")
```

### Tracking unsaved state

Set `st.session_state["is_dirty"] = True` at the top of any render function that mutates `edited_json`. Set it to `False` immediately after a successful download (in the `st.download_button` callback or just after it in the sidebar block).

Specifically, add `st.session_state["is_dirty"] = True` at the top of:
- `render_top_level_editor()`
- `render_contract_terms_editor()`
- `render_package_details_editor()`
- `render_monthly_volumes_editor()`
- `render_option_groups_editor()`
- `render_option_groups_top_level_editor()` (if present)

And add this after the `st.download_button` call in the sidebar:
```python
st.session_state["is_dirty"] = False
```

Also initialize in `maybe_init_state_from_upload()`:
```python
st.session_state["is_dirty"] = False
```

---

## Change log entry to add at top of file

```python
# - v1.7.0
#   - Wrapped all editor sections in st.columns([2, 1]) for persistent right panel
#   - Added render_right_panel() with Pricing Preview and JSON Output tabs
#   - Added render_pricing_page_compact() for narrow-column preview
#   - Replaced package selectbox with st.tabs() — one tab per package
#   - Added render_package_actions_global() replacing index-dependent version
#   - Added persistent status header below app title showing filename, unsaved state, validation, package count
#   - Added is_dirty session state flag to track unsaved changes
```

---

## What NOT to change

- Do not touch the sidebar nav radio or sidebar layout — it stays exactly as-is
- Do not modify any validation logic (`validate_json_structure`, `validate_contract_term_defaults`, `validate_orphan_term_references`)
- Do not modify `render_pricing_page()` — the full preview section is untouched
- Do not modify `render_json_preview()` or `render_raw_json_editor()`
- Do not add new pip dependencies
- Do not change `APP_VERSION` to anything other than `"v1.7.0"`
- Do not rename the file — output should be `app_json_editor_v1_7_0.py`
- Preserve the discount passthrough pattern — `discountItems` must never appear in the UI

---

## Acceptance criteria

1. All 9 sidebar nav sections still work and route correctly
2. Product Info, Contract Terms, Package Details, Monthly Volume Tiers, and Option Groups all show the right panel alongside the editor
3. The right panel tabs between Pricing Preview (compact) and JSON Output
4. Package Details / Monthly Volume Tiers / Option Groups show one tab per package — clicking a tab shows that package's fields
5. The status header is visible on every section and shows the correct filename, dirty state, error count, and package count
6. Download still works and clears the dirty indicator
7. No regressions in validation logic
