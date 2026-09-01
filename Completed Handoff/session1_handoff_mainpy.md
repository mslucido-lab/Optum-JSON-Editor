# Pricing Editor v2.0 — Session 1 Handoff
## Build: `main.py` (FastAPI Backend)
*Prepared: 2026-05-09*

---

## What this session produces

A single file: **`main.py`**

This is the complete FastAPI backend for the Pricing Editor v2.0. It has no frontend dependency — you can build and test it entirely before `index.html` exists.

---

## Context

This is a ground-up rewrite of a local Streamlit tool (`app_json_editor_v1_7_5.py`, pasted below). The Streamlit UI is being replaced by a FastAPI backend + vanilla JS frontend. v1.7.5 is provided as a **reference only** — do not port the Streamlit rendering functions. Port only the pure Python business logic functions listed explicitly in this doc.

The app edits Optum AI Marketplace pricing JSON files locally on a Mac. It runs entirely offline. No database. No authentication.

---

## Stack

```
Python 3.11+
fastapi
uvicorn
```

Install:
```bash
pip install fastapi uvicorn
```

Run:
```bash
uvicorn main:app --reload
```

The app will be accessible at `http://localhost:8000` in Chrome.

---

## File header

```python
"""
main.py

Version: v2.0.0
Date: 2026-05-09
Project: Pricing Page JSON Editor
Purpose: FastAPI backend for the v2.0 local web app.
         Serves index.html, handles file save, and exposes validation endpoints.
         File open is handled client-side (File System Access API) — no /open route needed.
"""
```

---

## Imports

```python
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
```

---

## App setup

```python
APP_VERSION = "v2.0.0"

app = FastAPI(title="Pricing Editor", version=APP_VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Pydantic models

```python
class SaveRequest(BaseModel):
    path: str
    data: Dict[str, Any]

class ValidateRequest(BaseModel):
    data: Dict[str, Any]
```

---

## Routes

### `GET /`

Serves `index.html` from the same directory as `main.py`.

```python
@app.get("/")
async def serve_index():
    index_path = Path(__file__).parent / "index.html"
    if not index_path.exists():
        return JSONResponse({"error": "index.html not found"}, status_code=404)
    return FileResponse(str(index_path), media_type="text/html")
```

### `POST /save`

Receives the edited JSON payload and a target file path. Writes the file to disk. Returns the versioned filename and full path.

```python
@app.post("/save")
async def save_file(request: SaveRequest):
    try:
        target_path = Path(request.path)
        versioned_name = make_versioned_filename(target_path.name)
        versioned_path = target_path.parent / versioned_name

        with open(versioned_path, "w", encoding="utf-8") as f:
            json.dump(request.data, f, indent=2, ensure_ascii=False)

        return {
            "saved_as": versioned_name,
            "path": str(versioned_path),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### `POST /validate`

Runs all three validators against the submitted JSON. Returns errors list and a boolean valid flag.

```python
@app.post("/validate")
async def validate(request: ValidateRequest):
    errors: List[str] = []
    errors.extend(validate_json_structure(request.data))
    errors.extend(validate_contract_term_defaults(request.data))
    errors.extend(validate_orphan_term_references(request.data))
    return {
        "errors": errors,
        "valid": len(errors) == 0,
    }
```

---

## Business logic functions — port verbatim from v1.7.5

The following functions must be copied from `app_json_editor_v1_7_5.py` into `main.py` **exactly as written**, with two changes only:

1. Remove any `import streamlit` or `st.` references (none of these functions use Streamlit — this is a precaution)
2. Remove `get_uploaded_file_signature()` and `parse_json_file()` — those are Streamlit file uploader helpers not needed here

**Functions to port:**

### Utility

- `deep_copy_json(data)` — uses `copy.deepcopy`
- `safe_json_dumps(data)` — `json.dumps` with indent=2
- `make_versioned_filename(original_name, app_version=APP_VERSION)` — generates timestamped filename
- `format_money(value)` — formats float as `$X.XX`
- `clean_preview_text(text)` — strips HTML tags, preserves line breaks
- `truncate_preview_text(text, max_chars)` — calls `clean_preview_text` then truncates

### Validation

- `validate_json_structure(data)` — checks required top-level keys, type checks
- `validate_contract_term_defaults(data)` — ensures exactly one `isDefault=1` in contractInitialTerm
- `validate_orphan_term_references(data)` — checks `initialTermId` values in termAmounts reference valid terms
- `build_valid_initial_term_reference_set(initial_terms)` — builds the set of valid term references
- `auto_remove_orphan_term_amounts(data)` — removes orphan termAmount entries in-place, returns count removed

### Contract terms helpers

- `build_contract_term_labels(contract_initial_terms)` — builds display labels for term selector
- `get_default_contract_term_index(contract_initial_terms)` — returns index of default term
- `build_term_reference_candidates(selected_term, selected_term_idx)` — builds candidate set for term resolution
- `resolve_term_amount_for_volume(volume, selected_term, selected_term_idx)` — resolves correct termAmount for a volume band

### Default templates

- `default_monthly_volume()` — returns a blank monthlyVolume dict
- `default_option_group()` — returns a blank optionItem dict
- `default_option_line_item()` — returns a blank optionLineItem dict
- `default_term_amount()` — returns a blank termAmount dict
- `default_contract_initial_term()` — returns a blank contractInitialTerm dict
- `default_package()` — returns a blank package dict

### Normalization

- `normalize_package_sort_orders(packages)` — sets sortOrder = index for each package
- `normalize_initial_term_sort_orders(terms)` — sets sortOrder = index for each term

---

## Complete `main.py` structure

The final file should be structured in this order:

```
1. Module docstring
2. Imports
3. APP_VERSION constant
4. FastAPI app setup + CORS middleware
5. Pydantic models (SaveRequest, ValidateRequest)
6. Routes: GET /, POST /save, POST /validate
7. --- Business logic (ported from v1.7.5) ---
8. Utility functions
9. Validation functions
10. Contract term helpers
11. Default template functions
12. Normalization functions
```

---

## What NOT to include in `main.py`

Do not port any of these from v1.7.5:

- Any function that starts with `render_` — these are all Streamlit UI functions
- `parse_json_file()` — Streamlit file uploader helper
- `get_uploaded_file_signature()` — Streamlit file uploader helper
- `init_state_from_upload()` — Streamlit session state
- `maybe_init_state_from_upload()` — Streamlit session state
- `clamp_selected_package_index()` — Streamlit session state
- `sync_raw_text_from_edited()` — Streamlit session state
- `sync_edited_from_raw_text()` — Streamlit session state
- `mark_dirty()` / `mark_saved()` — Streamlit session state
- `scoped_widget_key()` — Streamlit widget key management
- `edit_scalar_field()` — Streamlit widget rendering
- `normalize_terms_for_editor()` — pandas/Streamlit dataframe helper
- `dataframe_to_terms()` — pandas/Streamlit dataframe helper
- `make_package_tab_label()` — Streamlit tab label helper
- Anything that imports or references `streamlit`, `pandas`, or `st.`

---

## Testing

After writing `main.py`, verify each route before proceeding to Session 2.

### Start the server
```bash
uvicorn main:app --reload
```

### Test GET /
```bash
curl http://localhost:8000/
# Expected: 404 JSON (index.html doesn't exist yet — that's correct)
```

### Test POST /validate — valid file
```bash
curl -X POST http://localhost:8000/validate \
  -H "Content-Type: application/json" \
  -d '{"data": {"name": "Test", "description": "Test", "slug": "test", "contractTerms": {}, "packages": []}}'
# Expected: {"errors": [], "valid": true}
```

### Test POST /validate — missing required key
```bash
curl -X POST http://localhost:8000/validate \
  -H "Content-Type: application/json" \
  -d '{"data": {"name": "Test"}}'
# Expected: {"errors": ["Missing required top-level key: description", ...], "valid": false}
```

### Test POST /validate — with contract terms, no default
```bash
curl -X POST http://localhost:8000/validate \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "name": "Test", "description": "Test", "slug": "test",
      "contractTerms": {
        "contractInitialTerm": [
          {"termValue": 1, "termUnit": "Y", "isDefault": 0, "sortOrder": 0}
        ]
      },
      "packages": []
    }
  }'
# Expected: errors includes "contractTerms.contractInitialTerm must have exactly one term with isDefault = 1. None is currently set."
```

### Test POST /save
```bash
curl -X POST http://localhost:8000/save \
  -H "Content-Type: application/json" \
  -d '{
    "path": "/tmp/test_pricing.json",
    "data": {"name": "Test", "slug": "test", "packages": []}
  }'
# Expected: {"saved_as": "test_pricing_v2_0_0_YYYYMMDD_HHMMSS.json", "path": "/tmp/test_pricing_v2_0_0_...json"}
# Verify the file was actually written to /tmp/
```

### Verify `make_versioned_filename` output
```bash
curl -X POST http://localhost:8000/save \
  -H "Content-Type: application/json" \
  -d '{"path": "/tmp/item_mn__08092024.json", "data": {}}'
# saved_as should match pattern: item_mn__08092024_v2_0_0_YYYYMMDD_HHMMSS.json
```

---

## Acceptance criteria for Session 1

1. `uvicorn main:app --reload` starts with no errors
2. `GET /` returns 404 JSON (index.html not yet present — correct)
3. `POST /validate` with a valid payload returns `{"errors": [], "valid": true}`
4. `POST /validate` with a missing required key returns the correct error string
5. `POST /validate` with a contract term where no default is set returns the correct error string
6. `POST /save` writes a file to disk with the correct versioned naming convention
7. `POST /save` with an invalid path returns HTTP 500 with a descriptive error
8. Python syntax check passes: `python -m py_compile main.py`
9. No Streamlit imports anywhere in `main.py`
10. No pandas imports anywhere in `main.py`

---

## Reference file

The full contents of `app_json_editor_v1_7_5.py` are pasted below. Use it as the source for the business logic functions listed above. Do not use it for anything else.

---

[PASTE app_json_editor_v1_7_5.py HERE]
