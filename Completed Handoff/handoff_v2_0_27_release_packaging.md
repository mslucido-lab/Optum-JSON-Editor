# Pricing Editor — ChatGPT Handoff
## v2.0.27: Release Packaging
*Prepared: 2026-05-10*

---

## Context

You are creating a clean release package for the Pricing Editor v2.0. The working frontend file is `index_v2_0_26_filename_prompt.html`. The backend file is `main_v2_0_16.py`.

**Output:** A folder named `pricing-editor-v2.0.27` containing five files:

```
pricing-editor-v2.0.27/
  main.py
  index.html
  requirements.txt
  README.md
  TEST_PLAN.md
```

Do not change any logic in `main.py` or `index.html` beyond the version string updates listed below. This is packaging only.

---

## File 1 — `main.py`

Copy `main_v2_0_16.py` verbatim with two changes only:

**Change the version string** — find:
```python
APP_VERSION = "v2.0.16"
```
Replace with:
```python
APP_VERSION = "v2.0.27"
```

**Change the docstring date and version** — find:
```python
"""
main.py

Version: v2.0.16
Date: 2026-05-09
```
Replace with:
```python
"""
main.py

Version: v2.0.27
Date: 2026-05-10
```

No other changes to `main.py`.

---

## File 2 — `index.html`

Copy `index_v2_0_26_filename_prompt.html` verbatim with these changes only:

**HTML title** — find:
```html
<title>Pricing Editor v2.0.26</title>
```
Replace with:
```html
<title>Pricing Editor v2.0.27</title>
```

**APP_VERSION constants** — find:
```javascript
const APP_VERSION = "v2.0.26";
const APP_VERSION_JS = "v2_0_26";
```
Replace with:
```javascript
const APP_VERSION = "v2.0.27";
const APP_VERSION_JS = "v2_0_27";
```

**Change log** — add this entry at the very top of the existing change log comment block, above the `v2.0.26` entry:

```
v2.0.27
- Release packaging: version bump for distribution
- No functional changes from v2.0.26
```

No other changes to `index.html`.

---

## File 3 — `requirements.txt`

Create this file exactly as shown:

```
fastapi>=0.110.0
uvicorn>=0.29.0
```

---

## File 4 — `README.md`

Create this file exactly as shown:

```markdown
# Pricing Editor v2.0.27

A local web app for editing Optum AI Marketplace pricing JSON files.

---

## Requirements

- Python 3.11 or higher
- Google Chrome (required for native file open and save)
- Windows or Mac

---

## Install

Open a terminal in the `pricing-editor-v2.0.27` folder and run:

```
pip install -r requirements.txt
```

---

## Run

```
python -m uvicorn main:app --reload
```

Then open Chrome and go to:

```
http://127.0.0.1:8000
```

---

## Usage

### Open a file
Click **Open JSON** in the top bar and select a pricing JSON file.

### Create a new file
Click **New File** in the top bar. Select a template type:
- **API-Tiered-Public** — for API products with tiered monthly volume pricing (e.g. Medical Network APIs)
- **Software-MonthlyVolume-Public** — for software products with contract terms (e.g. Revenue Performance Advisor)

### Edit
Use the left nav to move between sections:
- **Metadata** — product name, description, contact fields, custom attributes
- **Contract Terms** — initial and auto-renewal terms (Software products)
- **Packages** — package details, volume bands, option items
- **Option Items** — implementations, add-ons
- **Custom Attrs** — discount tooltips and other custom attributes
- **Validation** — run frontend and backend validation before saving
- **Compare** — diff the current edits against the originally loaded file
- **Save / Export** — save a versioned copy or download to browser

### Preview
The right panel shows a live replica of the Optum pricing page as you edit. Click package cards to toggle selection and see the Order Summary update.

### Save
Click **Save Copy** to save a versioned JSON file. Three save modes are available:
- **Backend save** — requires a full Windows file path in the Save Target field; FastAPI writes the file to disk
- **Folder save** — click Select Folder & Save to pick a folder via Chrome's folder picker
- **Download** — click Download JSON to save to your browser's Downloads folder

All saved files use a versioned filename:
```
base-name_v2_0_27_YYYYMMDD_HHmmss.json
```

### discountItems
`discountItems` arrays are preserved automatically. They are never shown in the editor and are never modified. They will be present in every saved file exactly as they were in the source file.

---

## Browser compatibility

| Browser | Open | Save Copy (backend) | Folder Save | Download |
|---|---|---|---|---|
| Chrome (Mac/Win) | ✓ | ✓ | ✓ | ✓ |
| Edge (Win) | ✓ | ✓ | ✓ | ✓ |
| Firefox | ✓ | ✓ | ✗ | ✓ |
| Safari | ✓ | ✓ | ✗ | ✓ |

Chrome is recommended. Folder Save requires Chrome or Edge.

---

## Troubleshooting

**App won't start**
Make sure Python 3.11+ is installed and `pip install -r requirements.txt` completed without errors.

**Page shows "index.html not found"**
Both `main.py` and `index.html` must be in the same folder. Run `uvicorn` from that folder.

**Save Copy fails with "Target folder does not exist"**
The full path in the Save Target field must point to a folder that already exists on disk.

**Folder Save button missing**
Folder Save requires Chrome or Edge. Use Download JSON in other browsers.

**File opens but preview shows blank**
Check that the JSON file is a valid Optum pricing JSON with a `packages` array and `name` field at the top level.
```

---

## File 5 — `TEST_PLAN.md`

Create this file exactly as shown:

```markdown
# Pricing Editor v2.0.27 — Test Plan

Run these tests after any version update or code change before releasing.

---

## Setup

1. Copy `index_v2_0_27.html` to `index.html`
2. Start the backend: `python -m uvicorn main:app --reload`
3. Open Chrome and go to `http://127.0.0.1:8000`

---

## 1. App Load

- [ ] Page title shows `Pricing Editor v2.0.27`
- [ ] Top bar shows `Open JSON` and `New File` buttons
- [ ] No file loaded state shows correctly
- [ ] No console errors on page load

---

## 2. Open File

- [ ] Click Open JSON → Chrome file picker appears
- [ ] Select `item_mn__08092024.json` → file loads
- [ ] File pill shows `item_mn__08092024.json`
- [ ] Amber dirty dot is NOT shown (file just opened, no edits)
- [ ] Left nav sections are all accessible
- [ ] Preview panel shows Optum-fidelity pricing page with package cards

---

## 3. Metadata Editing

- [ ] Edit product name → preview H1 updates on every keystroke
- [ ] Edit header description → preview description updates with HTML rendering
- [ ] Amber dirty dot appears after first edit

---

## 4. Package Editing

- [ ] Navigate to Packages
- [ ] Edit base amount on Eligibility → preview card price updates
- [ ] Edit volume band cell → dotted tier rows in preview update
- [ ] Add a volume band → new tier row appears in preview
- [ ] Delete a volume band → row removed from preview
- [ ] Duplicate a package → new tab appears in package tabs
- [ ] Delete a package → tab removed; Delete disabled when only one remains

---

## 5. Preview Behavior

- [ ] Click a package card checkbox → Order Summary monthly subtotal updates
- [ ] Click two package cards → Implementation section shows strikethrough price + $0.00
- [ ] Implementation waiver tooltip text appears when 2+ packages are checked
- [ ] Click one package card to uncheck → waiver tooltip disappears, full impl price returns
- [ ] Add-ons accordion expands and collapses on click
- [ ] JSON tab shows raw formatted JSON

---

## 6. Validation

- [ ] Click Validate → backend validation runs
- [ ] Results grouped by section (Metadata, Packages, etc.)
- [ ] Validation pill in top bar updates

---

## 7. Compare

- [ ] Navigate to Compare
- [ ] Edit a field then view Compare → change appears in diff
- [ ] sortOrder toggle and empty value toggle work

---

## 8. Save — Backend Save

- [ ] Navigate to Save / Export
- [ ] Enter a full Windows path in Save Target field
- [ ] Click Save Copy → backend saves versioned file
- [ ] Confirm versioned filename contains `v2_0_27`
- [ ] Dirty dot clears after successful save

---

## 9. Save — Folder Save

- [ ] Navigate to Save / Export
- [ ] Click Select Folder & Save → Chrome folder picker appears
- [ ] Select a folder → file saves with versioned filename
- [ ] Confirm file appears in selected folder
- [ ] Confirm versioned filename contains `v2_0_27`
- [ ] Click Save Again to Last Folder → saves to same folder without picker

---

## 10. Save — Download

- [ ] Click Download JSON
- [ ] File downloads to browser Downloads folder
- [ ] Confirm versioned filename contains `v2_0_27`

---

## 11. New File — API Template

- [ ] Click New File
- [ ] Modal appears centered with dark overlay
- [ ] API-Tiered-Public description visible by default
- [ ] Click Create
- [ ] File pill shows `new-product.json`
- [ ] Amber dirty dot active immediately
- [ ] Preview shows "New Product" with one package card pre-checked
- [ ] Contract Terms section is empty
- [ ] Custom Attrs shows two attributes with empty values
- [ ] Option Items shows Implementations and empty Add-ons group

---

## 12. New File — Software Template

- [ ] Click New File → select Software-MonthlyVolume-Public → Create
- [ ] Contract Terms section shows one initial term (1 Year, default)
- [ ] All other new file behaviors same as API template

---

## 13. New File — Save Flow

- [ ] Create a new file
- [ ] Click Save Copy → filename prompt appears
- [ ] Enter `test-product` → folder picker or path prompt appears
- [ ] Save completes → file named `test-product_v2_0_27_....json`
- [ ] Download JSON → filename prompt → download named `test-product_v2_0_27_....json`

---

## 14. New File → Open Real File

- [ ] Create a new file
- [ ] Click Open JSON → load `rpa_04152025_latest.json`
- [ ] File pill updates to `rpa_04152025_latest.json`
- [ ] No stale `new-product.json` state
- [ ] Preview shows RPA product correctly
- [ ] Dirty dot is NOT shown

---

## 15. discountItems Preservation

- [ ] Load `item_mn__08092024.json`
- [ ] Edit any field
- [ ] Save a copy
- [ ] Open the saved copy
- [ ] Confirm `discountItems` arrays are present and unchanged
  (check via Raw JSON section or open in a text editor)

---

## 16. Modal UX

- [ ] New File modal closes on Cancel
- [ ] New File modal closes on Escape key
- [ ] New File modal closes on clicking the dark overlay outside the box
- [ ] New File with unsaved changes → "unsaved changes" prompt fires before modal opens

---

## Sign-off

Tester: _______________
Date: _______________
Version: v2.0.27
All items passed: ☐ Yes  ☐ No — issues noted above
```

---

## Version string summary

| File | Field | Value |
|---|---|---|
| `main.py` | `APP_VERSION` | `v2.0.27` |
| `main.py` | docstring Version | `v2.0.27` |
| `main.py` | docstring Date | `2026-05-10` |
| `index.html` | `<title>` | `Pricing Editor v2.0.27` |
| `index.html` | `APP_VERSION` | `v2.0.27` |
| `index.html` | `APP_VERSION_JS` | `v2_0_27` |

---

## What NOT to change

- Do not modify any logic, function, CSS, or HTML structure in either file beyond the version strings above
- Do not add new routes, functions, or dependencies
- Do not rename files inside the package folder
- Do not zip the folder — deliver the folder as five individual files

---

## Acceptance criteria

1. Folder contains exactly five files: `main.py`, `index.html`, `requirements.txt`, `README.md`, `TEST_PLAN.md`
2. `python -m py_compile main.py` passes with no errors
3. `main.py` version string is `v2.0.27`
4. `index.html` title is `Pricing Editor v2.0.27`
5. `APP_VERSION_JS` is `v2_0_27`
6. `requirements.txt` installs without errors: `pip install -r requirements.txt`
7. App starts: `python -m uvicorn main:app --reload`
8. `http://127.0.0.1:8000` loads in Chrome with no console errors
9. `README.md` renders correctly in any Markdown viewer
10. `TEST_PLAN.md` renders correctly in any Markdown viewer
11. No logic changes from `index_v2_0_26_filename_prompt.html` or `main_v2_0_16.py`

---

## Files

Attach both:
- `index_v2_0_26_filename_prompt.html`
- `main_v2_0_16.py`
