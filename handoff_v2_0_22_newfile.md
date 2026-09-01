# Pricing Editor — ChatGPT Handoff
## v2.0.22: New File from Template
*Prepared: 2026-05-10*

---

## Context

You are adding one new feature to `index_v2_0_21_fixed.html`. The full file will be attached.

**Output:** A new file named `index_v2_0_22.html`.

Do not touch `main.py`. Do not change anything not listed here.

---

## What this adds

A **"New File"** button in the top bar that creates a blank pricing JSON from a template and loads it into the editor — exactly like opening a file, but starting from scratch instead of from disk. The user fills in all fields, then uses Save Copy or Download JSON to write it out.

Two template options are presented in a simple `confirm()` flow:
- **API product** — `viewTemplate: "API-Tiered-Public"` (like Medical Network APIs)
- **Software product** — `viewTemplate: "Software-MonthlyVolume-Public"` (like Revenue Performance Advisor)

---

## Change 1 — Add the "New File" button to the top bar

**Find this line** in the `<div class="topbar">` block:

```html
<button class="btn blue" id="openBtn">Open JSON</button>
```

**Replace with:**

```html
<button class="btn blue" id="openBtn">Open JSON</button>
<button class="btn" id="newFileBtn">New File</button>
```

The new button sits immediately after Open JSON, before Discard.

---

## Change 2 — Add `blankTemplate()` function

Add this function immediately after the existing `defaultPackage()` function (line ~2100). Do not modify `defaultPackage()` or any other existing default function.

```javascript
function blankTemplate(viewTemplate) {
  const isApi = viewTemplate === "API-Tiered-Public";
  const pkg = defaultPackage();
  pkg.internalName = "New Package";
  pkg.name = "New Package";
  pkg.isDefault = 1;
  pkg.sortOrder = 0;
  if (isApi) {
    pkg.monthlyVolumes = [
      defaultMonthlyVolume(0),
    ];
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
```

---

## Change 3 — Add `newFile()` function

Add this function immediately after `blankTemplate()`:

```javascript
function newFile() {
  if (!confirmCanReplaceOpenFile()) return;
  const useApi = confirm(
    "Choose a template:\n\nOK → API-Tiered-Public (e.g. Medical Network APIs)\nCancel → Software-MonthlyVolume-Public (e.g. Revenue Performance Advisor)"
  );
  const viewTemplate = useApi ? "API-Tiered-Public" : "Software-MonthlyVolume-Public";
  const template = blankTemplate(viewTemplate);
  browserFileHandle = null;
  loadJson(JSON.stringify(template), "new-product.json");
  currentFilePath = "";
  dirty = true;
  updateShell();
}
```

### Why `dirty = true` after `loadJson()`

`loadJson()` sets `dirty = false` because it treats every load as a clean baseline. For a new file, we immediately want the dirty indicator active — the user hasn't saved anything yet and should be prompted before accidentally discarding. Setting `dirty = true` and calling `updateShell()` after `loadJson()` achieves this without touching `loadJson()` itself.

### Why `currentFilePath = ""`

`loadJson()` calls `recallPathForFile("new-product.json")` which may find a previously remembered path for that filename. Clearing it after load ensures the Save Copy path prompt is not pre-filled with a stale path from a previous session.

### Why `browserFileHandle = null`

Clears any stored File System Access API handle from a previously opened file. Without this, Save Copy could silently overwrite the previously opened file using the stored handle instead of prompting for a new location.

---

## Change 4 — Wire up the event listener

Find the block of event bindings at the bottom of the script (near line 2225):

```javascript
document.getElementById("openBtn").onclick = openFile;
document.getElementById("discardBtn").onclick = discardChanges;
```

Add this line immediately after `openBtn`:

```javascript
document.getElementById("newFileBtn").onclick = newFile;
```

---

## Change 5 — Version strings and change log

**HTML title** — find:
```html
<title>Pricing Editor v2.0.21</title>
```
Replace with:
```html
<title>Pricing Editor v2.0.22</title>
```

**APP_VERSION** — find:
```javascript
const APP_VERSION = "v2.0.21";
const APP_VERSION_JS = "v2_0_21";
```
Replace with:
```javascript
const APP_VERSION = "v2.0.22";
const APP_VERSION_JS = "v2_0_22";
```

**Change log** — add this at the very top of the existing change log, above the `v2.0.21` entry:

```
v2.0.22
- Added New File button to top bar
- Added blankTemplate() function: builds a valid blank JSON for API-Tiered-Public
  or Software-MonthlyVolume-Public, with one default package and one Implementation
  option group
- Added newFile() function: prompts for template type, loads blank template into
  editor, sets dirty flag so unsaved state is clear from the start
- browserFileHandle cleared on new file to prevent accidental overwrite of
  previously opened file
```

---

## What NOT to change

- Do not modify `loadJson()`, `openFile()`, `confirmCanReplaceOpenFile()`, `defaultPackage()`, `defaultOptionGroup()`, `defaultLineItem()`, or `defaultMonthlyVolume()`
- Do not touch `main.py`
- Do not touch any editor sections, nav, validation, compare, save, or panel logic
- Do not add external libraries or new CSS classes
- Do not change the `confirm()` dialog wording — exact text matters for usability

---

## Acceptance criteria

1. "New File" button appears in the top bar immediately after "Open JSON"
2. Clicking "New File" when dirty data is loaded prompts "You have unsaved changes..." before proceeding — same guard as Open JSON
3. Clicking OK in the template prompt loads an `API-Tiered-Public` blank template
4. Clicking Cancel in the template prompt loads a `Software-MonthlyVolume-Public` blank template
5. After loading, the editor shows all sections populated with blank/default values
6. The file pill shows `new-product.json`
7. The dirty indicator (amber dot) is active immediately after new file loads — before any edits
8. The preview panel shows the blank product name ("New Product") and an empty package card
9. Save Copy and Download JSON both work correctly after creating a new file
10. Opening a real JSON file after creating a new file works correctly — no stale handle or path
11. HTML title shows `v2.0.22`
12. Download filename contains `v2_0_22`
13. JavaScript syntax check passes: extract the script block and run `node --check`
14. No console errors on page load, new file creation, or subsequent open/save

---

## Files

Attach `index_v2_0_21_fixed.html`. No other files needed.
