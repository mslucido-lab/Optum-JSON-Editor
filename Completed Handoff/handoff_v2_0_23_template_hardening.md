# Pricing Editor — ChatGPT Handoff
## v2.0.23: New File Template Hardening
*Prepared: 2026-05-10*

---

## Context

You are making four targeted changes to `index_v2_0_22_new_modal.html`. The full file will be attached.

**Output:** A new file named `index_v2_0_23.html`.

Do not touch `main.py`. Do not change anything not listed here. All four changes are inside or immediately adjacent to `blankTemplate()` and `createNewFile()`.

---

## Change 1 — Auto-select package 0 in preview on new file

**Why:** After creating a new file, the pricing preview shows $0 monthly subtotal and no checked package. A new file always starts with exactly one package, so it should default to selected — that's the obvious starting state.

**Find `createNewFile()`:**

```javascript
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

**Replace with:**

```javascript
function createNewFile() {
  const select = document.getElementById("newFileTemplateSelect");
  const viewTemplate = select.value;
  closeNewFileModal();
  const template = blankTemplate(viewTemplate);
  browserFileHandle = null;
  loadJson(JSON.stringify(template), "new-product.json");
  currentFilePath = "";
  previewCheckedPackages.add(0);
  dirty = true;
  updateShell();
}
```

The only change is adding `previewCheckedPackages.add(0);` after `loadJson()`. Everything else is identical.

---

## Change 2 — Add default contract term to Software template

**Why:** The Software-MonthlyVolume-Public template currently sets `contractTerms: {}`. The live Optum Software template expects contract terms structure, validation will flag missing defaults once the user adds terms, and the contract terms editor section will appear empty with no guidance. Adding one default initial term gives the user a correct starting point.

**Find `blankTemplate()`.** The function currently ends with this return statement:

```javascript
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
```

**Replace the return statement with:**

```javascript
  const contractTerms = isApi ? {} : {
    isAutoRenewalEnabled: 0,
    headerDescription: "",
    contractInitialTerm: [
      {
        termValue: 1,
        termUnit: "Y",
        description: "",
        isDefault: 1,
        sortOrder: 0,
        discountItems: [],
      }
    ],
    contractAutoRenewalTerm: [],
  };

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
    contractTerms: contractTerms,
    packages: [pkg],
    optionItems: [implGroup, addonGroup],
    customAttributes: customAttributes,
    discountItems: [],
  };
```

Note: this return references `addonGroup` and `customAttributes` which are defined in Changes 3 and 4 below. All four changes must be applied together — the template will not compile correctly if only some are applied.

---

## Change 3 — Add empty Addons group to both templates

**Why:** The Add-ons accordion in the preview only renders if an `Addons` optionItems group exists in the data. Without it, the Add-ons section is invisible in the preview for new files. Adding an empty group makes the section visible immediately so the user knows it exists and can add line items.

**Find `blankTemplate()`.** Locate the existing Implementation group setup block:

```javascript
  const implGroup = defaultOptionGroup();
  implGroup.optionItemType = "Implementations";
  implGroup.headerDescription = "";
  const implLine = defaultLineItem();
  implLine.internalName = "Implementation Fee";
  implLine.amount = 0;
  implLine.unit = "one-time fee";
  implLine.sortOrder = 0;
  implGroup.optionLineItems = [implLine];
```

**Replace with** (adds the Addons group immediately after):

```javascript
  const implGroup = defaultOptionGroup();
  implGroup.optionItemType = "Implementations";
  implGroup.headerDescription = "";
  const implLine = defaultLineItem();
  implLine.internalName = "Implementation Fee";
  implLine.amount = 0;
  implLine.unit = "one-time fee";
  implLine.sortOrder = 0;
  implGroup.optionLineItems = [implLine];

  const addonGroup = defaultOptionGroup();
  addonGroup.optionItemType = "Addons";
  addonGroup.headerDescription = "";
  addonGroup.optionLineItems = [];
```

---

## Change 4 — Add starter custom attributes to both templates

**Why:** The Optum preview reads `packageMonthlySummaryDiscountToolTip` and `implementationSummaryDiscountToolTip` from `customAttributes` via `getCustomAttr()`. Without these entries the discount tooltip and implementation waiver lines in the preview are permanently blank for new files. Adding them with empty values makes the fields immediately visible in the Custom Attrs editor section so the user knows to fill them in.

**Find `blankTemplate()`.** Locate this block anywhere in the function body before the return statement and add it as a new variable:

```javascript
  const customAttributes = [
    {
      name: "packageMonthlySummaryDiscountToolTip",
      value: "",
      description: "Tooltip shown on the pricing page for package monthly summary discount",
      displayFor: 1,
      sortOrder: 0,
    },
    {
      name: "implementationSummaryDiscountToolTip",
      value: "",
      description: "Tooltip shown when implementation fee is waived for multiple APIs",
      displayFor: 1,
      sortOrder: 1,
    },
  ];
```

Place this block immediately after the `addonGroup` block from Change 3, before the return statement.

---

## Final shape of `blankTemplate()` after all four changes

For clarity, here is the complete replacement for the entire `blankTemplate()` function. Use this as the authoritative version — it incorporates all four changes correctly:

```javascript
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

  const addonGroup = defaultOptionGroup();
  addonGroup.optionItemType = "Addons";
  addonGroup.headerDescription = "";
  addonGroup.optionLineItems = [];

  const customAttributes = [
    {
      name: "packageMonthlySummaryDiscountToolTip",
      value: "",
      description: "Tooltip shown on the pricing page for package monthly summary discount",
      displayFor: 1,
      sortOrder: 0,
    },
    {
      name: "implementationSummaryDiscountToolTip",
      value: "",
      description: "Tooltip shown when implementation fee is waived for multiple APIs",
      displayFor: 1,
      sortOrder: 1,
    },
  ];

  const contractTerms = isApi ? {} : {
    isAutoRenewalEnabled: 0,
    headerDescription: "",
    contractInitialTerm: [
      {
        termValue: 1,
        termUnit: "Y",
        description: "",
        isDefault: 1,
        sortOrder: 0,
        discountItems: [],
      }
    ],
    contractAutoRenewalTerm: [],
  };

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
    contractTerms: contractTerms,
    packages: [pkg],
    optionItems: [implGroup, addonGroup],
    customAttributes: customAttributes,
    discountItems: [],
  };
}
```

---

## Change 5 — Version strings and change log

**HTML title** — find:
```html
<title>Pricing Editor v2.0.22</title>
```
Replace with:
```html
<title>Pricing Editor v2.0.23</title>
```

**APP_VERSION constants** — find:
```javascript
const APP_VERSION = "v2.0.22";
const APP_VERSION_JS = "v2_0_22";
```
Replace with:
```javascript
const APP_VERSION = "v2.0.23";
const APP_VERSION_JS = "v2_0_23";
```

**Change log** — add this at the very top of the existing change log comment block, above the `v2.0.22` entry:

```
v2.0.23
- createNewFile: auto-selects package 0 in preview so monthly subtotal shows immediately
- blankTemplate: Software-MonthlyVolume-Public now includes one default contract
  initial term (1 Year, isDefault 1) so contract terms editor starts populated
- blankTemplate: both templates now include an empty Addons option group so the
  Add-ons accordion appears in the preview immediately
- blankTemplate: both templates now include packageMonthlySummaryDiscountToolTip
  and implementationSummaryDiscountToolTip custom attributes with empty values
  so they appear in the Custom Attrs editor immediately
```

---

## What NOT to change

- Do not modify `loadJson()`, `openFile()`, `openNewFileModal()`, `closeNewFileModal()`, `updateNewFileModalDesc()`, `defaultPackage()`, `defaultOptionGroup()`, `defaultLineItem()`, `defaultMonthlyVolume()`, or `defaultContractTerm()`
- Do not touch `main.py`
- Do not touch any editor sections, nav, validation, compare, save, preview, or panel layout logic
- Do not add new functions, CSS, globals, or external libraries

---

## Acceptance criteria

1. Creating an API-Tiered-Public new file: preview shows the New Package card with checkbox pre-checked and a $0 monthly subtotal (since base amount is 0 until user edits it)
2. Creating a Software-MonthlyVolume-Public new file: same preview behavior
3. Creating an API-Tiered-Public new file: Contract Terms editor section shows empty `{}` — no terms
4. Creating a Software-MonthlyVolume-Public new file: Contract Terms editor section shows one initial term (1 Year, default)
5. Creating either template: Option Items editor section shows both an Implementations group and an empty Addons group
6. Creating either template: Custom Attrs editor section shows two attributes: `packageMonthlySummaryDiscountToolTip` and `implementationSummaryDiscountToolTip` with empty values
7. Creating either template: Optum preview shows the Add-ons accordion (empty, "0 Add-on options")
8. Validation on a freshly created API file shows no contract term errors
9. Validation on a freshly created Software file shows no contract term default errors (one default term is set)
10. Opening a real JSON file after creating a new file still works correctly — no stale state
11. HTML title shows `v2.0.23`
12. Download filename contains `v2_0_23`
13. JavaScript syntax check passes: extract script block and run `node --check`
14. No console errors on page load, new file creation, or subsequent edits

---

## Files

Attach `index_v2_0_22_new_modal.html`. No other files needed.
