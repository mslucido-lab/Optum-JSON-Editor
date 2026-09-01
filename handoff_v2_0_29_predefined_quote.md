# Pricing Editor — Claude Handoff
## v2.0.29: Predefined Quote (multi-item) schema support
*Prepared: 2026-09-01*

---

## Context

You are making targeted changes to `index.html` (currently `v2.0.28.2`). The full file will be attached.

**Output:** a new file named `index_v2_0_29.html`.

Do **not** modify `main.py` in this pass (backend `/save` already writes any JSON shape; `/validate` handling is addressed frontend-side — see Step 8).

All work is additive. The legacy single-item schema must keep loading, editing, validating, comparing, and saving **byte-for-byte as it does today**. The new schema is a second mode the editor auto-detects.

---

## Overview — the two schemas

### Legacy "Item" schema (unchanged, still the default)

Top-level object **is** the product item:

```json
{ "name": "...", "slug": "...", "viewTemplate": "API-Tiered-Public",
  "contractTerms": {...}, "packages": [...], "optionItems": [...],
  "customAttributes": [...], "discountItems": [] }
```

Sample files: `Sample JSONs/item_mn__08092024.json`, `rpa_04152025_latest.json`.

### New "Predefined Quote" schema (the file to support)

Reference file: **`Sample JSONs/QuoteItem_Predefined_MN_Updated.json`** (identical to `Sample JSONs/Predefined Quote Template.json`).

An **envelope** that wraps one or more items in a `quoteItems` array:

```json
{
  "name": "Predefined Quote for Medical Network",
  "description": "Predefined Quote for Medical Network",
  "type": 0,
  "catalogCode": "CHC-m0ck00008806",
  "paymentSchedule": "No payment is required to check out ...",
  "quoteItems": [
    { "subViewTemplate": "Monthly Minimum", "isDefault": 1, "sortOrder": 0, "item": { /* full legacy Item schema */ } },
    { "subViewTemplate": "Based on Usage",  "isDefault": 0, "sortOrder": 1, "item": { /* full legacy Item schema */ } }
  ]
}
```

Key facts:

- Each `quoteItems[i].item` is **exactly the legacy Item schema** — same `packages`, `optionItems`, `contractTerms`, `customAttributes`, `viewTemplate`, etc. No new keys inside `item`.
- `subViewTemplate` is a display-variant label (e.g. `"Monthly Minimum"`, `"Based on Usage"`). Free text.
- Exactly one entry should carry `isDefault: 1`.
- `sortOrder` is the display order (0-based).
- Envelope-level `name`, `description`, `type`, `catalogCode`, `paymentSchedule` are **separate** from the per-item copies of those fields.

The design goal: the editor works on **one active item at a time**, using every existing section/renderer untouched, plus a thin switcher for choosing which quote item is active and a small card for the envelope fields.

---

## Architecture — keep `data` pointing at the active item

Every existing renderer, `byPath`, `setByPath`, `getIndexPath`, `setIndexPath`, `renderOptumPreview`, and validation reads the global `data`. **Do not refactor those.** Instead:

- Introduce `fileRoot` — the entire parsed file (envelope in the new mode, or the item itself in legacy mode).
- Keep `data` as a **reference to the active item object**:
  - legacy mode: `data === fileRoot`
  - predefined-quote mode: `data === fileRoot.quoteItems[activeQuoteItemIndex].item`
- Because `data` is the same object reference that lives inside `fileRoot`, every `setByPath`/`setIndexPath` mutation already writes through to the envelope. No write-back step needed.
- Serialization (save / download / raw / copy / compare baseline) switches to `serializeDocument()` which returns `fileRoot`.

---

## Step 1 — New globals

In the globals block near `let data = null;` (around line 873–893) add:

```javascript
let fileRoot = null;            // entire parsed document
let docMode = "legacyItem";     // "legacyItem" | "predefinedQuote"
let activeQuoteItemIndex = 0;
```

---

## Step 2 — Detection + mode helpers

Add these helpers near `clone()` / `ensureLoaded()` (anywhere above `loadJson`):

```javascript
function detectDocMode(obj) {
  if (obj && typeof obj === "object" && !Array.isArray(obj)
      && Array.isArray(obj.quoteItems)
      && obj.quoteItems.some(q => q && typeof q === "object" && q.item && typeof q.item === "object")) {
    return "predefinedQuote";
  }
  return "legacyItem";
}

function normalizeQuoteItems(root) {
  if (!Array.isArray(root.quoteItems)) root.quoteItems = [];
  root.quoteItems = root.quoteItems.filter(q => q && typeof q === "object" && q.item && typeof q.item === "object");
  root.quoteItems.forEach((q, i) => {
    if (typeof q.subViewTemplate !== "string") q.subViewTemplate = "";
    q.sortOrder = Number.isFinite(q.sortOrder) ? q.sortOrder : i;
    q.isDefault = q.isDefault === 1 ? 1 : 0;
  });
  root.quoteItems.sort((a, b) => a.sortOrder - b.sortOrder);
  root.quoteItems.forEach((q, i) => { q.sortOrder = i; });
  // NOTE: no auto-injection of isDefault. A file (or Raw Apply result) with zero
  // or multiple defaults is preserved as-is and flagged by frontend validation
  // (Step 9). defaultQuoteItemIndex() falls back to 0 only for the active pointer.
}

function defaultQuoteItemIndex(root) {
  const i = (root.quoteItems || []).findIndex(q => q.isDefault === 1);
  return i >= 0 ? i : 0;
}

function activeQuoteEntry() {
  return docMode === "predefinedQuote" ? (fileRoot.quoteItems[activeQuoteItemIndex] || null) : null;
}

function setActiveQuoteItem(idx) {
  if (docMode !== "predefinedQuote") { data = fileRoot; return; }
  activeQuoteItemIndex = clampNumber(idx, 0, fileRoot.quoteItems.length - 1);
  data = fileRoot.quoteItems[activeQuoteItemIndex].item;
  activePackageIndex = 0;
  activePackageMode = "details";
  previewCheckedPackages.clear();
  previewAddonsOpen = false;
}

function serializeDocument() {
  return docMode === "predefinedQuote" ? fileRoot : data;
}
```

---

## Step 3 — `loadJson`

Replace the body of `loadJson` (lines ~2584–2603) with:

```javascript
function loadJson(text, name) {
  try {
    const parsed = JSON.parse(text);
    fileRoot = parsed;
    docMode = detectDocMode(parsed);
    if (docMode === "predefinedQuote") {
      normalizeQuoteItems(fileRoot);
      activeQuoteItemIndex = defaultQuoteItemIndex(fileRoot);
      data = fileRoot.quoteItems[activeQuoteItemIndex].item;
    } else {
      activeQuoteItemIndex = 0;
      data = fileRoot;
    }
    originalData = clone(fileRoot);
    currentFileName = name || "loaded.json";
    outputFileNameOverride = "";
    currentFilePath = recallPathForFile(currentFileName) || currentFileName;
    dirty = false;
    validationErrors = [];
    validationIssues = [];
    validationRan = false;
    activePackageIndex = 0;
    previewCheckedPackages.clear();
    previewAddonsOpen = false;
    runFrontendValidation(true);
    renderQuoteItemBar();
    render();
  } catch (err) {
    alert("Could not parse JSON: " + err.message);
  }
}
```

Note `originalData` is now a clone of the **whole document**.

---

## Step 4 — Quote Item switcher bar (HTML + renderer)

### 4a. HTML

Immediately after the closing `</div>` of `.topbar` (line ~808) and **before** `<div class="main">`, insert:

```html
  <div id="quoteItemBar" class="quote-item-bar hidden"></div>
```

### 4b. CSS

Append to the `<style>` block:

```css
/* v2.0.29 */
.quote-item-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding: 6px 12px;
  background: #1b2130;
  border-bottom: 1px solid #2a3040;
  font-size: 11px;
  color: #8fa3bb;
}
.quote-item-bar.hidden { display: none; }
.quote-item-bar .qi-label { font-weight: 700; color: #f0f4ff; text-transform: uppercase; letter-spacing: .04em; }
.quote-item-bar select { background: #252b38; color: #f0f4ff; border: 1px solid #3a4255; border-radius: 4px; padding: 3px 6px; font-size: 11px; }
.quote-item-bar .qi-star { color: #f5b301; }
.quote-item-bar .btn.qi-btn { padding: 3px 8px; font-size: 11px; }
.quote-item-bar .qi-spacer { flex: 1; }
```

### 4c. Renderer

Add near `updateShell`:

```javascript
function renderQuoteItemBar() {
  const bar = document.getElementById("quoteItemBar");
  if (!bar) return;
  if (docMode !== "predefinedQuote" || !fileRoot || !Array.isArray(fileRoot.quoteItems)) {
    bar.classList.add("hidden");
    bar.innerHTML = "";
    return;
  }
  const items = fileRoot.quoteItems;
  const opts = items.map((q, i) => {
    const label = (q.subViewTemplate && q.subViewTemplate.trim()) || `Quote Item ${i + 1}`;
    const star = q.isDefault === 1 ? " ★" : "";
    return `<option value="${i}" ${i === activeQuoteItemIndex ? "selected" : ""}>${esc(label)}${star}</option>`;
  }).join("");
  bar.classList.remove("hidden");
  bar.innerHTML = `
    <span class="qi-label">Quote Item</span>
    <select id="qiSelect">${opts}</select>
    <span>${activeQuoteItemIndex + 1} / ${items.length}</span>
    <button class="btn qi-btn" id="qiSetDefault" title="Mark this quote item as the default">Set Default</button>
    <button class="btn qi-btn" id="qiAdd" title="Add a fresh blank API-Tiered quote item">+ Add</button>
    <button class="btn qi-btn" id="qiDuplicate" title="Append a copy of the active quote item">Duplicate</button>
    <button class="btn qi-btn" id="qiUp">▲</button>
    <button class="btn qi-btn" id="qiDown">▼</button>
    <button class="btn qi-btn" id="qiDelete" title="Delete the active quote item">Delete</button>
    <span class="qi-spacer"></span>
    <span>envelope: ${esc(fileRoot.name || "(unnamed)")}</span>`;

  document.getElementById("qiSelect").onchange = e => {
    setActiveQuoteItem(Number(e.target.value));
    markDirtyNoBaseline();          // selection change is not a data edit — see note
    renderQuoteItemBar();
    render();
  };
  document.getElementById("qiSetDefault").onclick = () => {
    fileRoot.quoteItems.forEach((q, i) => { q.isDefault = i === activeQuoteItemIndex ? 1 : 0; });
    markDirty(); renderQuoteItemBar();
  };
  document.getElementById("qiAdd").onclick = () => addQuoteItem(blankTemplate("API-Tiered-Public"), false);
  document.getElementById("qiDuplicate").onclick = () => addQuoteItem(clone(data), true);
  document.getElementById("qiUp").onclick = () => moveQuoteItem(-1);
  document.getElementById("qiDown").onclick = () => moveQuoteItem(1);
  document.getElementById("qiDelete").onclick = () => deleteQuoteItem();
}

function markDirtyNoBaseline() {
  // switching the active quote item mutates no JSON; just refresh shell + preview
  runFrontendValidation(false);
  updateShell();
  renderPreview();
}

function addQuoteItem(itemObj, isDuplicate = false) {
  const entry = {
    subViewTemplate: isDuplicate
      ? `${activeQuoteEntry()?.subViewTemplate || "Quote Item"} (copy)`
      : "New Sub View",
    isDefault: 0,
    sortOrder: fileRoot.quoteItems.length,
    item: itemObj || blankTemplate("API-Tiered-Public"),
  };
  fileRoot.quoteItems.push(entry);
  normalizeQuoteItems(fileRoot);
  setActiveQuoteItem(fileRoot.quoteItems.length - 1);
  markDirty();
  renderQuoteItemBar();
  render();
}

function moveQuoteItem(delta) {
  const items = fileRoot.quoteItems;
  const to = activeQuoteItemIndex + delta;
  if (to < 0 || to >= items.length) return;
  const [row] = items.splice(activeQuoteItemIndex, 1);
  items.splice(to, 0, row);
  items.forEach((q, i) => { q.sortOrder = i; });
  setActiveQuoteItem(to);
  markDirty();
  renderQuoteItemBar();
  render();
}

function deleteQuoteItem() {
  const items = fileRoot.quoteItems;
  if (items.length <= 1) { alert("A predefined quote must keep at least one quote item."); return; }
  const label = activeQuoteEntry()?.subViewTemplate || `Quote Item ${activeQuoteItemIndex + 1}`;
  if (!confirm(`Delete quote item "${label}"? This cannot be undone.`)) return;
  items.splice(activeQuoteItemIndex, 1);
  normalizeQuoteItems(fileRoot);
  setActiveQuoteItem(Math.min(activeQuoteItemIndex, items.length - 1));
  markDirty();
  renderQuoteItemBar();
  render();
}
```

---

## Step 5 — Envelope + per-item metadata card

In `renderMetadata()` (line ~1262), immediately inside `section-panel-body`, before the existing `collapsibleCard("Product Identity", ...)`, add:

```javascript
${docMode === "predefinedQuote" ? collapsibleCard("Predefined Quote — envelope", `
  <div class="grid cols2">
    ${envField("name", "Quote Name")}
    ${envField("catalogCode", "Quote Catalog Code")}
    ${envField("description", "Quote Description")}
    ${envField("type", "Type", "number")}
    ${envField("paymentSchedule", "Payment Schedule", "textarea")}
  </div>
  <div class="grid cols3" style="margin-top:10px">
    ${quoteEntryField("subViewTemplate", "Sub View Template (this item)")}
    ${quoteEntryField("sortOrder", "Sort Order", "number")}
    <div class="field"><label>Default quote item</label>
      <div>${activeQuoteEntry()?.isDefault === 1 ? "Yes ★" : "No — use Set Default in the top bar"}</div>
    </div>
  </div>`, {open: true, sub: `${fileRoot.quoteItems.length} quote item(s)`}) : ""}
```

Add these binding helpers near `field()`:

```javascript
function envField(key, label, type = "text") {
  const v = fileRoot?.[key] ?? "";
  if (type === "textarea") {
    return `<div class="field"><label>${esc(label)}</label><textarea rows="3" data-env-key="${esc(key)}">${esc(v)}</textarea></div>`;
  }
  return `<div class="field"><label>${esc(label)}</label><input type="${esc(type)}" value="${esc(v)}" data-env-key="${esc(key)}" /></div>`;
}

function quoteEntryField(key, label, type = "text") {
  const entry = activeQuoteEntry() || {};
  const v = entry[key] ?? "";
  return `<div class="field"><label>${esc(label)}</label><input type="${esc(type)}" value="${esc(v)}" data-qentry-key="${esc(key)}" /></div>`;
}
```

Then in `renderMetadata()` where it calls `bindPathInputs()` / `bindMetadataPanelCollapse()` at the end, add:

```javascript
editor.querySelectorAll("[data-env-key]").forEach(el => {
  const handler = () => {
    const key = el.dataset.envKey;
    const cur = fileRoot[key];
    fileRoot[key] = parseInputValue(el.value, cur);
    markDirty();
  };
  el.addEventListener("input", handler);
  el.addEventListener("change", handler);
});
editor.querySelectorAll("[data-qentry-key]").forEach(el => {
  const handler = () => {
    const entry = activeQuoteEntry(); if (!entry) return;
    const key = el.dataset.qentryKey;
    entry[key] = parseInputValue(el.value, entry[key]);
    markDirty();
    renderQuoteItemBar();
  };
  el.addEventListener("input", handler);
  el.addEventListener("change", handler);
});
```

---

## Step 6 — Serialization touch points

Replace `data` with `serializeDocument()` in every place the **whole file** is written or hashed:

| Function | Line (approx) | Change |
|---|---|---|
| `copyCurrentJson` | 1187 | `JSON.stringify(serializeDocument(), null, 2)` |
| `rawDiffersFromEdited` caller / `renderRawJson` | 1808 | `rawText = rawOverride ?? JSON.stringify(serializeDocument(), null, 2)` |
| `renderRawJson` → Apply Raw | 1824 | `fileRoot = parsed; docMode = detectDocMode(parsed); if (docMode === "predefinedQuote") { normalizeQuoteItems(fileRoot); setActiveQuoteItem(defaultQuoteItemIndex(fileRoot)); } else { data = fileRoot; } markDirty(); renderQuoteItemBar(); render();` — `normalizeQuoteItems` only coerces structure; it does **not** repair a missing/duplicate `isDefault`, so an invalid pasted document is applied as-is and surfaced by validation (criterion 13). |
| `buildDiffRows` | 1761–1762 | `flattenForDiff(originalData)` vs `flattenForDiff(serializeDocument())` (both already whole-doc now) |
| `writeJsonToDirectoryHandle` | 2661 | `JSON.stringify(serializeDocument(), null, 2)` |
| `saveVersion` fetch body | 2739 | `body: JSON.stringify({path: currentFilePath, data: serializeDocument()})` |
| `downloadJson` | 2761 | `new Blob([JSON.stringify(serializeDocument(), null, 2)], ...)` |
| `renderPreview` JSON tab | 2396 | show the whole doc: `JSON.stringify(serializeDocument(), null, 2)` |
| `discardChanges` | 2775 | `fileRoot = clone(originalData); docMode = detectDocMode(fileRoot); if (docMode === "predefinedQuote") { normalizeQuoteItems(fileRoot); setActiveQuoteItem(defaultQuoteItemIndex(fileRoot)); } else { data = fileRoot; } dirty = false; validationErrors = []; validationRan = false; renderQuoteItemBar(); render();` |
| `markSaved` | 1090 | `if (updateBaseline && fileRoot) originalData = clone(fileRoot);` |

**Leave untouched** every `JSON.stringify(data …)` that is intentionally per-item: `renderOptumPreview` internals do not stringify; there are none that need per-item JSON except the preview pane, handled above (choose whole-doc for the JSON tab so it matches what saves).

---

## Step 7 — Compare Versions path mapping

With `originalData`/current now whole-document, predefined-quote diff paths look like `quoteItems.0.item.packages.2.amount`. Make the grouping + jump logic strip that prefix.

In `compareSectionForPath`, `packageIndexFromDiffPath`, `packageModeFromDiffPath` — normalize first:

```javascript
function stripQuotePrefix(path) {
  const m = path.match(/^quoteItems\.(\d+)\.item\.(.*)$/);
  return m ? { qi: Number(m[1]), rest: m[2] } : { qi: null, rest: path };
}
```

- `compareSectionForPath(path)`: run `const { rest } = stripQuotePrefix(path);` then test `rest` against the existing `startsWith` checks. For `rest === ""` or a bare `quoteItems.N.subViewTemplate` / envelope key, return `{group: "Predefined Quote", section: "metadata"}`.
- `packageIndexFromDiffPath(path)`: match against `stripQuotePrefix(path).rest`.
- `packageModeFromDiffPath(path)`: same.
- In `buildDiffRows` `.map(...)`, add `quoteItemIndex: stripQuotePrefix(key).qi` to the row object, and in `jumpToDiff` call `setActiveQuoteItem(row.quoteItemIndex)` + `renderQuoteItemBar()` before `render()` when it is non-null.
- Prefix the group label with the sub-view name when `qi !== null` so diffs from different quote items are visually separated.

---

## Step 8 — Backend `/validate`

`main.py` `validate_json_structure` expects the flat Item shape and will emit false "Missing required top-level key: slug / contractTerms / packages" errors on the envelope.

Frontend fix only (no `main.py` change): in `validateData()` (line ~2604), send the **active item**, not the whole document:

```javascript
const res = await fetch("/validate", { method: "POST", headers: {"Content-Type": "application/json"},
  body: JSON.stringify({ data }) });   // data === active item, already correct
```

`data` is already the active item, so this line likely needs **no change** — just confirm it sends `data` and not `serializeDocument()`. Add a note in the Validation panel when `docMode === "predefinedQuote"`: *"Backend validation runs against the active quote item (`<subViewTemplate>`). Switch quote items and re-validate to check each."*

(Optional future: loop `fileRoot.quoteItems` and POST each. Out of scope for v2.0.29.)

---

## Step 9 — Frontend validation additions

In `runFrontendValidation` (line ~1884), after the existing item-level checks, add envelope checks guarded by mode:

```javascript
if (docMode === "predefinedQuote" && fileRoot) {
  const qs = fileRoot.quoteItems || [];
  if (isBlankValue(fileRoot.name)) addValidationIssue(issues, "error", "Predefined Quote", "metadata", "quoteName", "Predefined quote name is required.");
  if (!qs.length) addValidationIssue(issues, "error", "Predefined Quote", "metadata", "quoteItems", "Predefined quote has no quote items.");
  const defaults = qs.filter(q => q.isDefault === 1).length;
  if (qs.length && defaults !== 1) addValidationIssue(issues, "error", "Predefined Quote", "metadata", "quoteItems.isDefault", `Exactly one quote item must be the default (found ${defaults}).`);
  const svNames = qs.map(q => String(q.subViewTemplate || "").trim());
  svNames.forEach((n, i) => { if (!n) addValidationIssue(issues, "warning", "Predefined Quote", "metadata", `quoteItems.${i}.subViewTemplate`, `Quote item ${i + 1} has no sub view template label.`); });
  duplicateValues(svNames.filter(Boolean)).forEach(dup => addValidationIssue(issues, "warning", "Predefined Quote", "metadata", "quoteItems.subViewTemplate", `Duplicate sub view template label: ${dup}`));
}
```

These surface in the Metadata section status pill and Validation panel with no new nav item.

---

## Step 10 — New File modal: add Predefined Quote template

### 10a. HTML — add option (line ~858):

```html
<option value="Predefined-Quote">Predefined-Quote — multi-item quote (Monthly Minimum / Based on Usage)</option>
```

### 10b. `TEMPLATE_DESCRIPTIONS` (line ~2530):

```javascript
"Predefined-Quote": "<b>Predefined-Quote</b> — An envelope wrapping one or more quote items, each a full product item with its own sub view template label (e.g. \"Monthly Minimum\", \"Based on Usage\"). Starts with one API-Tiered quote item; add more from the Quote Item bar.",
```

### 10c. `blankTemplate` — add builder after it:

```javascript
function blankPredefinedQuote() {
  const item = blankTemplate("API-Tiered-Public");
  return {
    name: "New Predefined Quote",
    description: "New Predefined Quote",
    type: 0,
    catalogCode: "",
    paymentSchedule: "",
    quoteItems: [
      { subViewTemplate: "Monthly Minimum", isDefault: 1, sortOrder: 0, item }
    ]
  };
}
```

### 10d. `createNewFile` (line ~2555):

```javascript
function createNewFile() {
  const select = document.getElementById("newFileTemplateSelect");
  const value = select.value;
  closeNewFileModal();
  const template = value === "Predefined-Quote" ? blankPredefinedQuote() : blankTemplate(value);
  browserFileHandle = null;
  loadJson(JSON.stringify(template), value === "Predefined-Quote" ? "new-predefined-quote.json" : "new-product.json");
  currentFilePath = "";
  previewCheckedPackages.add(0);
  dirty = true;
  updateShell();
}
```

Also update the `writeJsonToDirectoryHandle` / `downloadJson` "ask for name" guard that currently special-cases `"new-product.json"` to also match `"new-predefined-quote.json"`.

---

## Step 11 — `updateShell` context

In `updateShell` (line ~2414) after setting `statusFile`:

```javascript
if (docMode === "predefinedQuote" && fileRoot?.quoteItems?.length) {
  const entry = fileRoot.quoteItems[activeQuoteItemIndex];
  const label = (entry?.subViewTemplate || "").trim() || `Quote Item ${activeQuoteItemIndex + 1}`;
  document.getElementById("statusFile").textContent =
    `file: ${currentFileName}  •  quote item ${activeQuoteItemIndex + 1}/${fileRoot.quoteItems.length} (${label})`;
}
```

Call `renderQuoteItemBar()` once at the end of `updateShell()` so the bar stays in sync after any render path.

`ensureLoaded()` — when `data` is null also hide the bar: `document.getElementById("quoteItemBar")?.classList.add("hidden");`

---

## Step 12 — Version strings + change log

- `<title>Pricing Editor v2.0.29</title>`
- `const APP_VERSION = "v2.0.29";`
- `const APP_VERSION_JS = "v2_0_29";`

Change log entry at the top of the in-file log:

```
v2.0.29
- Added Predefined Quote (multi-item) schema support alongside the legacy single-item schema
- Auto-detection on load: a top-level object with a quoteItems[] array whose entries
  carry an item object opens in predefined-quote mode; everything else stays legacy
- New fileRoot / docMode / activeQuoteItemIndex globals; data still references the
  active item so all existing sections, byPath/setByPath, preview, and validation are unchanged
- Quote Item bar under the top toolbar: switch active item, set default, add, duplicate,
  reorder, delete (min 1 enforced)
- Metadata section shows a "Predefined Quote — envelope" card (name, description, type,
  catalogCode, paymentSchedule) plus per-item subViewTemplate / sortOrder
- Save, Download, Copy JSON, Raw JSON, and Compare operate on the whole document;
  backend /validate runs against the active quote item
- Frontend validation: envelope name required, exactly one default quote item,
  sub view template labels present and unique
- New File modal: added "Predefined-Quote" template
- Legacy single-item files load, edit, validate, compare, and save byte-for-byte as before
```

---

## What NOT to change

- Do not modify `main.py`.
- Do not change `byPath`, `setByPath`, `getIndexPath`, `setIndexPath`, or any `render*` function that reads `data`, except the specific additions in Steps 5, 7, 11.
- Do not change `renderOptumPreview` logic (it already reads `data` = active item correctly).
- Do not alter legacy output: a legacy file opened and saved with no edits must produce identical JSON (aside from the existing 2-space reformat).
- Do not add a new nav section — the Quote Item bar and the envelope card cover it.
- Do not delete any existing CSS.

---

## Acceptance criteria

**Legacy regression (must all pass):**

1. Open `Sample JSONs/item_mn__08092024.json` → no Quote Item bar appears; Metadata shows no envelope card.
2. All sections (Metadata, Contract Terms, Packages, Option Items, Custom Attrs, Validation, Compare, Raw) behave exactly as v2.0.28.2.
3. Open then Download with no edits → output JSON is structurally identical to input (2-space formatted).
4. Open `rpa_04152025_latest.json` → preview and validation unchanged.

**Predefined Quote (new):**

5. Open `Sample JSONs/QuoteItem_Predefined_MN_Updated.json` → Quote Item bar shows a dropdown with `Monthly Minimum ★` and `Based on Usage`; "1 / 2" shown; status bar shows `quote item 1/2 (Monthly Minimum)`.
6. Metadata section shows "Predefined Quote — envelope" card with `name = "Predefined Quote for Medical Network"`, `catalogCode = "CHC-m0ck00008806"`, `type = 0`; plus `subViewTemplate = "Monthly Minimum"`, `sortOrder = 0`, Default = Yes.
7. Packages section lists the 5 packages (Eligibility, Institutional Claims, Professional Claims, Claim Status, ERA) of the active item; preview renders the API-Tiered layout; Claim Status still shows "Based on Usage*" (v2.0.28 isSummableAmount behavior intact).
8. Switch the dropdown to "Based on Usage" → package list + preview update to that item; editing a package amount there does not affect the "Monthly Minimum" item.
9. Edit envelope `name` → Compare Versions shows `quoteItems` / envelope change grouped under "Predefined Quote"; edit a package amount → diff path resolves to the correct quote item and clicking it switches the active item and jumps to Packages.
10. Raw JSON tab shows the **full envelope** (both quote items); Apply Raw with a hand-edited envelope re-detects mode and repoints the active item.
11. Download → output is the full envelope with both `quoteItems` intact, `sortOrder` 0/1, exactly one `isDefault: 1`, and every `item` sub-object preserved.
12. Quote Item bar: **+ Add** appends a **fresh blank API-Tiered item** (`subViewTemplate: "New Sub View"`, one default package) and selects it; **Duplicate** appends a full clone of the active item labelled `"… (copy)"`; **▲/▼** reorder and renumber `sortOrder`; **Set Default** moves the ★ and clears the other; **Delete** on the last remaining item is blocked with an alert.
13. Validation: remove all `isDefault` flags via Raw JSON + Apply → the invalid state is **preserved** (not auto-repaired) and frontend validation reports "Exactly one quote item must be the default (found 0)." Same for a pasted document with two defaults ("found 2").
14. New File → "Predefined-Quote" → creates a one-item envelope, bar visible, saves/round-trips as an envelope.

**General:**

15. Extract the `<script>` block, run `node --check` → passes.
16. No console errors on load, file open (both schemas), quote-item switching, add/delete/reorder, or Raw Apply.
17. `<title>` and download filename contain `v2_0_29`.

---

## Files to attach

- `index.html` (v2.0.28.2 — the file to edit)
- `Sample JSONs/QuoteItem_Predefined_MN_Updated.json` (new-schema test file)
- `Sample JSONs/item_mn__08092024.json` (legacy regression file)
- `rpa_04152025_latest.json` (legacy regression file)
