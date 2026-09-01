# Pricing Editor — ChatGPT Handoff
## v2.0.22: New File with Template Selector Modal
*Prepared: 2026-05-10*

---

## Context

You are adding one new feature to `index_v2_0_21_fixed.html`. The full file will be attached.

**Output:** A new file named `index_v2_0_22.html`.

Do not touch `main.py`. Do not change anything not listed here.

This replaces the earlier v2.0.22 handoff that used a `confirm()` dialog. That approach is discarded. Use this doc instead.

---

## What this adds

A **"New File"** button in the top bar. Clicking it opens a small modal dialog over the editor. The modal explains that the user should select a template type before proceeding, presents two options in a `<select>` dropdown, and has a **Create** button and a **Cancel** button.

Selecting a template and clicking Create loads a blank pricing JSON into the editor — exactly as if a file had been opened, but starting from a blank structure. The user then fills in all fields and uses Save Copy or Download JSON to write the file to disk.

---

## Change 1 — Add CSS for the modal

Add this CSS block inside the existing `<style>` tag, after all existing CSS (just before the closing `</style>` tag):

```css
/* v2.0.22 new file modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, .65);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal-overlay.hidden { display: none; }
.modal-box {
  background: var(--surface);
  border: 1px solid var(--border2);
  border-radius: 10px;
  padding: 26px 28px;
  width: 420px;
  max-width: calc(100vw - 40px);
  display: flex;
  flex-direction: column;
  gap: 16px;
  box-shadow: 0 8px 40px rgba(0, 0, 0, .6);
}
.modal-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
}
.modal-body {
  font-size: 13px;
  color: var(--text2);
  line-height: 1.55;
}
.modal-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.modal-label {
  font-family: var(--mono);
  font-size: 10px;
  font-weight: 600;
  color: var(--text2);
  letter-spacing: .07em;
  text-transform: uppercase;
}
.modal-select {
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text);
  font-size: 13px;
  padding: 8px 10px;
  outline: none;
  width: 100%;
  transition: border-color .15s;
}
.modal-select:focus { border-color: var(--amber); }
.modal-select option { background: var(--surface2); }
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 4px;
}
.modal-desc {
  background: var(--surface2);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 10px 12px;
  font-size: 11px;
  color: var(--text2);
  line-height: 1.6;
  min-height: 48px;
  transition: opacity .15s;
}
.modal-desc b { color: var(--text); font-weight: 600; }
```

---

## Change 2 — Add the modal HTML

Add this HTML immediately before the closing `</body>` tag, after the `<script>` block:

```html
<!-- v2.0.22 new file modal -->
<div id="newFileModal" class="modal-overlay hidden" role="dialog" aria-modal="true" aria-labelledby="newFileModalTitle">
  <div class="modal-box">
    <div class="modal-title" id="newFileModalTitle">New Pricing File</div>
    <div class="modal-body">Select a template type to start from. Each template pre-fills the correct structure for that product type. You can change any field after the file is created.</div>
    <div class="modal-field">
      <div class="modal-label">Template Type</div>
      <select id="newFileTemplateSelect" class="modal-select">
        <option value="API-Tiered-Public">API-Tiered-Public — e.g. Medical Network APIs</option>
        <option value="Software-MonthlyVolume-Public">Software-MonthlyVolume-Public — e.g. Revenue Performance Advisor</option>
      </select>
    </div>
    <div class="modal-desc" id="newFileTemplateDesc"></div>
    <div class="modal-actions">
      <button class="btn" id="newFileCancelBtn">Cancel</button>
      <button class="btn primary" id="newFileCreateBtn">Create</button>
    </div>
  </div>
</div>
```

---

## Change 3 — Add the "New File" button to the top bar

**Find this line** in the `<div class="topbar">` block:

```html
<button class="btn blue" id="openBtn">Open JSON</button>
```

**Replace with:**

```html
<button class="btn blue" id="openBtn">Open JSON</button>
<button class="btn" id="newFileBtn">New File</button>
```

---

## Change 4 — Add `blankTemplate()`, `newFile()`, and modal functions

Add all of the following functions immediately after the existing `defaultPackage()` function. Do not modify any existing function.

```javascript
// v2.0.22 new file template
function blankTemplate(viewTemplate) {
  const isApi = viewTemplate === "API-Tiered-Public";

  const pkg = defaultPackage();
  pkg.internalName = "New Package";
  pkg.name = "New Package";
  pkg.isDefault = 1;
  pkg.sortOrder = 0;
  if (isApi) {
    pkg.monthlyVolumes = [defaultMonthlyVolume(0)];
  }

  const implGroup = defaultOptionGroup();
  implGroup.optionItemType = "Implementations";
  implGroup.headerDescription = "";
  const implLine = defaultLineItem();
  implLine.internalName = "Implementation Fee";
  implLine.amount = 0;
  implLine.unit = "one-time fee";
  implLine.sortOrder = 0;
  implGroup.optionLineItems = [implLine];

  return {
    name: "New Product",
    description: "New Product",
    slug: "new-product",
    catalogCode: "",
    viewTemplate: viewTemplate,
    maxQuantity: 1,
    headerDescription: "",
    tooltipText: "",
    tooltipDescription: "",
    paymentSchedule: "",
    emailAddress: "",
    emailSubject: "",
    emailBody: "",
    contractTerms: {},
    packages: [pkg],
    optionItems: [implGroup],
    customAttributes: [],
    discountItems: [],
  };
}

const TEMPLATE_DESCRIPTIONS = {
  "API-Tiered-Public": "<b>API-Tiered-Public</b> — For API products with tiered monthly volume pricing. Pre-fills one package with one volume band and an Implementation option group. Use this for products like Medical Network APIs.",
  "Software-MonthlyVolume-Public": "<b>Software-MonthlyVolume-Public</b> — For software products with contract terms and monthly volume selection. Pre-fills one package and an Implementation option group. Use this for products like Revenue Performance Advisor.",
};

function openNewFileModal() {
  if (!confirmCanReplaceOpenFile()) return;
  const modal = document.getElementById("newFileModal");
  const select = document.getElementById("newFileTemplateSelect");
  // Reset to first option and update description
  select.selectedIndex = 0;
  updateNewFileModalDesc();
  modal.classList.remove("hidden");
  select.focus();
}

function closeNewFileModal() {
  document.getElementById("newFileModal").classList.add("hidden");
}

function updateNewFileModalDesc() {
  const select = document.getElementById("newFileTemplateSelect");
  const desc = document.getElementById("newFileTemplateDesc");
  desc.innerHTML = TEMPLATE_DESCRIPTIONS[select.value] || "";
}

function createNewFile() {
  const select = document.getElementById("newFileTemplateSelect");
  const viewTemplate = select.value;
  closeNewFileModal();
  const template = blankTemplate(viewTemplate);
  browserFileHandle = null;
  loadJson(JSON.stringify(template), "new-product.json");
  currentFilePath = "";
  dirty = true;
  updateShell();
}
```

### Why `dirty = true` after `loadJson()`

`loadJson()` sets `dirty = false` because it treats every load as a clean baseline. A brand new file that has never been saved anywhere should immediately show as unsaved. Setting `dirty = true` and calling `updateShell()` after `loadJson()` achieves this without modifying `loadJson()`.

### Why `currentFilePath = ""`

`loadJson()` calls `recallPathForFile("new-product.json")` which may find a previously remembered path for that filename from a prior session. Clearing it ensures Save Copy prompts for a real path rather than silently using a stale one.

### Why `browserFileHandle = null`

Clears any stored File System Access API handle from a previously opened file so Save Copy cannot accidentally overwrite it using the stored handle.

---

## Change 5 — Wire up event listeners

Find the block of event bindings near the bottom of the script:

```javascript
document.getElementById("openBtn").onclick = openFile;
document.getElementById("discardBtn").onclick = discardChanges;
```

Add these lines immediately after `openBtn`:

```javascript
document.getElementById("newFileBtn").onclick = openNewFileModal;
document.getElementById("newFileCancelBtn").onclick = closeNewFileModal;
document.getElementById("newFileCreateBtn").onclick = createNewFile;
document.getElementById("newFileTemplateSelect").addEventListener("change", updateNewFileModalDesc);
document.getElementById("newFileModal").addEventListener("click", function(e) {
  if (e.target === this) closeNewFileModal();
});
document.getElementById("newFileModal").addEventListener("keydown", function(e) {
  if (e.key === "Escape") closeNewFileModal();
});
```

The last two bindings implement two standard modal UX behaviors: clicking the dark overlay outside the modal box closes it, and pressing Escape closes it.

---

## Change 6 — Version strings and change log

**HTML title** — find:
```html
<title>Pricing Editor v2.0.21</title>
```
Replace with:
```html
<title>Pricing Editor v2.0.22</title>
```

**APP_VERSION constants** — find:
```javascript
const APP_VERSION = "v2.0.21";
const APP_VERSION_JS = "v2_0_21";
```
Replace with:
```javascript
const APP_VERSION = "v2.0.22";
const APP_VERSION_JS = "v2_0_22";
```

**Change log** — add this at the very top of the existing change log comment block, above the `v2.0.21` entry:

```
v2.0.22
- Added New File button to top bar
- Added template selector modal with dropdown and description panel
- Two templates: API-Tiered-Public and Software-MonthlyVolume-Public
- Modal closes on Cancel, Escape key, or clicking outside the modal box
- blankTemplate() builds a valid blank JSON with one default package and
  one Implementation option group, pre-structured for the chosen template type
- browserFileHandle cleared on new file to prevent accidental overwrite
- dirty flag set immediately on new file load before any edits
```

---

## What NOT to change

- Do not modify `loadJson()`, `openFile()`, `confirmCanReplaceOpenFile()`, `defaultPackage()`, `defaultOptionGroup()`, `defaultLineItem()`, or `defaultMonthlyVolume()`
- Do not touch `main.py`
- Do not touch any editor sections, nav, validation, compare, save, or panel layout logic
- Do not add external libraries

---

## Acceptance criteria

1. "New File" button appears in the top bar immediately after "Open JSON"
2. Clicking "New File" when dirty data is loaded prompts "You have unsaved changes…" before opening the modal
3. The modal appears centered over the editor with a dark overlay
4. The modal shows the title "New Pricing File", an explanatory sentence, a labeled dropdown, a description panel, and Cancel / Create buttons
5. The dropdown defaults to `API-Tiered-Public` with its description visible immediately when the modal opens
6. Selecting `Software-MonthlyVolume-Public` in the dropdown updates the description panel
7. Clicking Cancel closes the modal and does nothing else
8. Clicking outside the modal box (on the dark overlay) closes it
9. Pressing Escape closes the modal
10. Clicking Create loads the blank template, closes the modal, shows `new-product.json` in the file pill, and shows the amber dirty dot immediately
11. The editor shows all sections with blank/default values for the chosen template
12. The preview shows "New Product" as the H1 and a blank package card
13. Opening a real JSON file after creating a new file works correctly — no stale handle or path
14. HTML title shows `v2.0.22`
15. Download filename contains `v2_0_22`
16. JavaScript syntax check passes: extract the script block and run `node --check`
17. No console errors on page load, modal open/close, or file creation

---

## Files

Attach `index_v2_0_21_fixed.html`. No other files needed.
