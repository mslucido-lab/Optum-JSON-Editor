# Pricing Editor — Claude Review Handoff
## Current Build: v2.0.26 Filename Prompt + Save Polish
*Prepared: 2026-05-10*

---

## Context

This handoff covers the latest frontend patch after v2.0.25. The app is a local FastAPI + vanilla JavaScript tool for editing Optum AI Marketplace pricing JSON files.

Current working files:

- `main.py`
- `index.html`, expected to be copied from `index_v2_0_26_filename_prompt.html`

Run:

```bash
python -m uvicorn main:app --reload
```

Open:

```text
http://127.0.0.1:8000/?v=226
```

`main.py` was not changed.

---

## Current Version

Frontend constants should be:

```javascript
const APP_VERSION = "v2.0.26";
const APP_VERSION_JS = "v2_0_26";
```

HTML title should be:

```html
<title>Pricing Editor v2.0.26</title>
```

---

## Why v2.0.26 Was Needed

v2.0.24 and v2.0.25 fixed the Save Copy flow by using Chrome's folder picker when no full Windows path was available.

The remaining issue: when creating a new file, folder save used the default loaded filename `new-product.json`, producing saved files like:

```text
new-product_v2_0_25_YYYYMMDD_HHMMSS.json
```

The user needs to choose the real base filename before saving.

---

## What v2.0.26 Changed

### 1. Added an output base filename concept

New global:

```javascript
let outputFileNameOverride = "";
```

New helper functions:

```javascript
sanitizeJsonBaseName(value)
currentOutputBaseName()
promptForOutputBaseName()
versionedJsonFileName(baseOverride = null)
```

The versioned filename now uses:

```javascript
base + APP_VERSION_JS + timestamp + .json
```

Instead of always deriving the base from `currentFileName`.

---

### 2. Save / Export page now shows an output base filename field

The Save / Export page now includes:

```text
Output base filename
```

The user can enter something like:

```text
medical-network-apis
```

The final saved filename becomes:

```text
medical-network-apis_v2_0_26_YYYYMMDD_HHMMSS.json
```

Changing this field also updates `currentFileName` to `medical-network-apis.json`, so the file pill reflects the intended name.

---

### 3. Folder save prompts for filename when saving a new file

When `currentFileName === "new-product.json"`, folder save now prompts:

```text
Enter a filename for this JSON file. Do not include a folder path. .json is optional.
```

If the user cancels, no file is saved and the dirty state remains.

This applies to:

- Save Copy with no full path
- Select Folder & Save
- Save Again to Last Folder

---

### 4. Download JSON prompts for filename when saving a new file

If the current file is still `new-product.json`, Download JSON now prompts for a filename before downloading.

If the user cancels, no file is downloaded.

---

### 5. loadJson resets filename override

When a real file is opened, `loadJson()` now resets:

```javascript
outputFileNameOverride = "";
```

This prevents the previous new-file filename override from leaking into a later opened real JSON file.

---

## Review Areas for Claude

### 1. Filename prompt logic

Please review whether this logic is safe:

```javascript
const shouldAskName = options.askForFileName || currentFileName === "new-product.json" || !currentFileName || currentFileName === "No file loaded";
```

Confirm it prompts only when needed and does not annoy users saving normal opened files.

### 2. Filename sanitization

Current sanitization removes folder path segments and invalid Windows filename characters.

Please review:

```javascript
function sanitizeJsonBaseName(value) {
  const raw = String(value || "").trim().replace(/^.*[\\/]/, "").replace(/\.json$/i, "");
  const cleaned = raw.replace(/[<>:"/\\|?*\x00-\x1F]/g, "-").replace(/\s+/g, " ").trim();
  return cleaned || "pricing";
}
```

Confirm this is enough for local Windows use.

### 3. Save Copy and folder picker interaction

Review whether these flows are correct:

- New File → Save Copy → no full path → prompt filename → folder picker → save
- New File → Select Folder & Save → prompt filename → folder picker → save
- New File → Save Again to Last Folder → prompt filename if still `new-product.json` → save
- Open real file → Save Copy with full path → backend save, no filename prompt
- Open real file → Download JSON → no filename prompt unless file is still `new-product.json`

### 4. Dirty and clean state

After a successful folder save or download:

```javascript
markSaved(true)
```

After canceling the filename prompt or folder picker:

- no file should be saved
- dirty should remain true
- status should not claim success

### 5. Version hygiene

Expected:

- Title: v2.0.26
- `APP_VERSION`: v2.0.26
- `APP_VERSION_JS`: v2_0_26
- Downloaded/saved filenames contain `v2_0_26`

### 6. No main.py changes

`main.py` was not changed. The folder-save flow is client-side via File System Access API.

---

## Suggested Smoke Test

1. Start app.
2. Confirm landing page shows v2.0.26.
3. Click New File.
4. Create API template.
5. Confirm file pill starts as `new-product.json` and dirty dot is amber.
6. Click Save Copy.
7. Enter `test-api-product` in the filename prompt.
8. Select a folder.
9. Confirm file saved as `test-api-product_v2_0_26_...json`.
10. Confirm dirty indicator clears.
11. Create another new file.
12. Use Download JSON.
13. Enter `test-download-product`.
14. Confirm browser download filename contains `test-download-product_v2_0_26`.
15. Open a real JSON file.
16. Confirm file pill uses the real opened filename, not the previous override.
17. Save Copy with a full Windows path and confirm backend save still works.

---

## Files for Review

Review:

- `index_v2_0_26_filename_prompt.html`
- `main.py` only if needed for backend save behavior

