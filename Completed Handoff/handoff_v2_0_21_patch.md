# Pricing Editor — ChatGPT Handoff
## v2.0.21: Three Targeted Fixes
*Prepared: 2026-05-10*

---

## Context

You are making three small, targeted fixes to `index_v2_0_20_addons_expander.html`. The full file will be attached.

**Output:** A new file named `index_v2_0_21.html`.

Do not touch `main.py`. Do not change anything not listed here.

---

## Fix 1 — `previewAddonAmount()`: add `transactionUnitAmount` fallback

**Why:** The current function only reads `item.amount`. Some JSON files have addon line items where `amount` is `0` and the actual price is in `transactionUnitAmount`. This fix uses whichever field is non-zero, preferring `amount`.

**Find this function** (search for `function previewAddonAmount`):

```javascript
function previewAddonAmount(item) {
  const amount = parseFloat(item.amount ?? 0);
  const unit = item.unit || item.subUnitDescription || item.subUnit || '';
  const money = previewFmt$(amount);
  return `${money}${unit ? `<span class="op-addon-unit">${esc(unit)}</span>` : ''}`;
}
```

**Replace it with:**

```javascript
function previewAddonAmount(item) {
  const amt = parseFloat(item.amount ?? 0);
  const txn = parseFloat(item.transactionUnitAmount ?? 0);
  const amount = amt !== 0 ? amt : txn;
  const unit = item.unit || item.subUnitDescription || item.subUnit || '';
  const money = previewFmt$(amount);
  return `${money}${unit ? `<span class="op-addon-unit">${esc(unit)}</span>` : ''}`;
}
```

---

## Fix 2 — `loadJson()`: clear checked packages on file load

**Why:** `previewCheckedPackages` is a persistent `Set`. When a second JSON file is opened, package indices from the previous file remain checked. If the new file has fewer packages, stale indices cause visual ghost-selections on package cards.

**Find this function** (search for `function loadJson`):

```javascript
function loadJson(text, name) {
  try {
    data = JSON.parse(text);
    originalData = clone(data);
    currentFileName = name || "loaded.json";
    currentFilePath = recallPathForFile(currentFileName) || currentFileName;
    dirty = false;
    validationErrors = [];
    validationIssues = [];
    validationRan = false;
    activePackageIndex = 0;
    runFrontendValidation(true);
    render();
  } catch (err) {
    alert("Could not parse JSON: " + err.message);
  }
}
```

**Replace it with:**

```javascript
function loadJson(text, name) {
  try {
    data = JSON.parse(text);
    originalData = clone(data);
    currentFileName = name || "loaded.json";
    currentFilePath = recallPathForFile(currentFileName) || currentFileName;
    dirty = false;
    validationErrors = [];
    validationIssues = [];
    validationRan = false;
    activePackageIndex = 0;
    previewCheckedPackages.clear();
    previewAddonsOpen = false;
    runFrontendValidation(true);
    render();
  } catch (err) {
    alert("Could not parse JSON: " + err.message);
  }
}
```

The two new lines are `previewCheckedPackages.clear();` and `previewAddonsOpen = false;`. Everything else is unchanged.

---

## Fix 3 — Version strings

Update these three version strings:

**HTML title** — find:
```html
<title>Pricing Editor v2.0.20</title>
```
Replace with:
```html
<title>Pricing Editor v2.0.21</title>
```

**APP_VERSION_JS constant** — find:
```javascript
const APP_VERSION_JS = "v2_0_20";
```
Replace with:
```javascript
const APP_VERSION_JS = "v2_0_21";
```

**Change log comment block** — add this entry at the very top of the existing change log, above the `v2.0.20` entry:

```
v2.0.21
- previewAddonAmount: falls back to transactionUnitAmount when amount is 0
- loadJson: clears previewCheckedPackages on file load to prevent ghost selections
- loadJson: resets previewAddonsOpen to false on file load
```

---

## What NOT to change

- Do not touch `renderOptumPreview()` beyond what is described above
- Do not touch `main.py`
- Do not touch any editor section, nav, validation, compare, save, or panel logic
- Do not add new functions, CSS, or globals
- Do not restructure, reformat, or reorder any existing code

---

## Acceptance criteria

1. Loading a second JSON file clears all package checkboxes in the preview
2. Loading a second JSON file collapses the Add-ons accordion
3. For a line item where `amount` is `0` and `transactionUnitAmount` is non-zero, the preview shows the `transactionUnitAmount` value
4. For a line item where `amount` is non-zero, the preview continues to show `amount` (no regression)
5. HTML title shows `v2.0.21`
6. Download filename contains `v2_0_21`
7. Python syntax check on `main.py` still passes (unchanged)
8. JavaScript syntax check passes: extract the script block and run `node --check`
9. No console errors on page load, file open, or package checkbox interaction

---

## Files

Attach `index_v2_0_20_addons_expander.html`. No other files needed.
