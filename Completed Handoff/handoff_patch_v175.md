# Pricing Editor — ChatGPT Handoff Doc
## Patch: v1.7.5
*Prepared: 2026-05-09*

---

## Context

You are making three small, targeted changes to `app_json_editor_v1_7_4.py`. The full file will be pasted below this doc.

**Output:** A new file named `app_json_editor_v1_7_5.py`.

Do not change anything not listed here. This is a patch, not a refactor.

---

## Change 1 — Fix file header date

**Location:** Top of file, inside the docstring.

**Current:**
```
Date: 2026-03-24
```

**Replace with:**
```
Date: 2026-05-09
```

Also update the change log block at the top. Add this entry above the existing `v1.7.4` entry:

```python
- v1.7.5
  - Fixed file header date (was showing original 03-24 date across all v1.7.x versions)
  - Added per-tab Duplicate and Delete buttons inside each package tab
  - Collapsed package overview table into an expander above the package tabs
```

And update:
```python
APP_VERSION = "v1.7.5"
```

---

## Change 2 — Add Duplicate and Delete inside each package tab

### Where to make the change

In `main()`, inside the package tab loop. The current loop body looks like this:

```python
for tab_idx, pkg_tab in enumerate(pkg_tabs):
    with pkg_tab:
        package = packages[tab_idx]
        st.session_state["_editor_widget_prefix"] = f"pkg_{tab_idx}_{page.replace(' ', '_').lower()}"

        if page == "Package Details":
            render_package_details_editor(package)
        elif page == "Monthly Volume Tiers":
            render_monthly_volumes_editor(package)
        elif page == "Option Groups":
            render_option_groups_editor(package)

        sync_raw_text_from_edited()
```

**Replace with:**

```python
for tab_idx, pkg_tab in enumerate(pkg_tabs):
    with pkg_tab:
        package = packages[tab_idx]
        st.session_state["_editor_widget_prefix"] = f"pkg_{tab_idx}_{page.replace(' ', '_').lower()}"

        # Per-tab package actions
        action_col1, action_col2, action_spacer = st.columns([1, 1, 4])
        with action_col1:
            if st.button(
                "⧉ Duplicate",
                key=scoped_widget_key(f"dup_pkg_{tab_idx}"),
                use_container_width=True,
            ):
                source_pkg = deep_copy_json(package)
                source_pkg["name"] = f"{source_pkg.get('name', 'Package')} Copy"
                source_pkg["internalName"] = f"{source_pkg.get('internalName', 'Package')} Copy"
                packages.insert(tab_idx + 1, source_pkg)
                normalize_package_sort_orders(packages)
                mark_dirty()
                sync_raw_text_from_edited()
                st.rerun()

        with action_col2:
            delete_disabled = len(packages) <= 1
            if st.button(
                "✕ Delete",
                key=scoped_widget_key(f"del_pkg_{tab_idx}"),
                use_container_width=True,
                disabled=delete_disabled,
            ):
                packages.pop(tab_idx)
                normalize_package_sort_orders(packages)
                mark_dirty()
                sync_raw_text_from_edited()
                st.rerun()

        st.markdown("---")

        if page == "Package Details":
            render_package_details_editor(package)
        elif page == "Monthly Volume Tiers":
            render_monthly_volumes_editor(package)
        elif page == "Option Groups":
            render_option_groups_editor(package)

        sync_raw_text_from_edited()
```

### Key rules for this change

- The `scoped_widget_key()` call uses the already-set prefix (`pkg_{tab_idx}_{page}`) so keys are guaranteed unique across tabs.
- Delete is disabled (greyed out) when only one package remains — never allow zero packages.
- After either action: `normalize_package_sort_orders` → `mark_dirty` → `sync_raw_text_from_edited` → `st.rerun()`. This exact order matches the existing pattern in `render_package_actions()`.
- Do NOT touch `render_package_actions_global()` — the global Add Package button above the tabs stays as-is.
- Do NOT touch the old `render_package_actions()` function — leave it in the file untouched.

---

## Change 3 — Collapse package overview table into an expander

### Where to make the change

In `main()`, in the `else` branch of the packages block. The current code is:

```python
render_package_overview(packages)
st.session_state["_editor_widget_prefix"] = "global"
render_package_actions_global(packages)
```

**Replace with:**

```python
with st.expander("Package Summary", expanded=False):
    render_package_overview(packages)
st.session_state["_editor_widget_prefix"] = "global"
render_package_actions_global(packages)
```

That is the entire change. One `with st.expander(...)` wrapper around the existing `render_package_overview(packages)` call. Do not modify `render_package_overview()` itself.

The expander defaults to collapsed (`expanded=False`) so the tab UI is the first thing visible when navigating to Package Details, Monthly Volume Tiers, or Option Groups.

---

## What NOT to change

- Do not modify any validation logic
- Do not modify `render_pricing_page()`, `render_json_preview()`, or `render_raw_json_editor()`
- Do not modify `render_package_overview()` itself — only wrap the call site
- Do not modify `render_package_actions()` — leave it in place for rollback
- Do not add new dependencies
- Do not change the sidebar nav

---

## Acceptance criteria

1. File header date shows `2026-05-09`
2. `APP_VERSION` is `"v1.7.5"`
3. Change log has a `v1.7.5` entry at the top
4. On Package Details / Monthly Volume Tiers / Option Groups, each package tab shows a Duplicate and Delete button above the editor fields
5. Clicking Duplicate creates a copy named `[name] Copy` inserted immediately after the duplicated package
6. Clicking Delete removes that package and is disabled when only one package remains
7. Package summary table is collapsed by default inside an expander labeled "Package Summary"
8. Global `+ Add Package` button above the tabs still works
9. No new Streamlit duplicate widget key errors
10. Python syntax check passes: `python -m py_compile app_json_editor_v1_7_5.py`
