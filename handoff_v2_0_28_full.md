# Pricing Editor — ChatGPT Handoff
## v2.0.28: Preview Rendering Fixes + Dynamic Package Discount
*Prepared: 2026-05-11*

---

## Context

You are making targeted changes to `index_v2_0_26_filename_prompt.html`. The full file will be attached.

**Output:** A new file named `index_v2_0_28.html`.

Do not touch `main.py`. Do not change anything not listed here. All changes are inside `renderOptumPreview()` and two new helper functions added before it.

---

## Overview of changes

**Fix 1 — Remove two hardcoded partner notice lines** from the left column header. These lines are product-specific content already present in `headerDescription` for the products that need them. Hardcoding them causes them to appear incorrectly on every product.

**Fix 2 — Remove `packageMonthlySummaryDiscountToolTip` from the left column header.** It was rendering as a duplicate paragraph. It belongs in the Order Summary only.

**Fix 3 — Dynamic package discount in Order Summary.** Read `discountItems` from each package, detect active percentage discounts based on which packages are checked, show the discount line and calculated savings in the Order Summary, and show the tooltip on hover via `ⓘ`.

---

## New CSS to add

Add these rules inside the existing `<style>` tag, after all existing CSS:

```css
/* v2.0.28 — discount tooltip */
.op-tooltip-wrap {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.op-tooltip-icon {
  color: #00b050;
  font-size: 11px;
  cursor: default;
  user-select: none;
}
.op-tooltip-bubble {
  display: none;
  position: absolute;
  bottom: 120%;
  left: 0;
  background: #252b38;
  border: 1px solid #3a4255;
  border-radius: 5px;
  padding: 8px 10px;
  font-size: 10px;
  color: #8fa3bb;
  line-height: 1.5;
  width: 210px;
  z-index: 50;
  white-space: normal;
  pointer-events: none;
}
.op-tooltip-wrap:hover .op-tooltip-bubble { display: block; }

/* v2.0.28 — selected packages list in summary */
.op-sum-pkg-row {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  padding: 2px 0;
  color: #8fa3bb;
}
.op-sum-pkg-name { flex: 1; }
.op-sum-pkg-amt  { flex-shrink: 0; font-weight: 500; color: #f0f4ff; }
.op-sum-disc-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
  padding: 3px 0;
  border-top: 1px solid #2a3040;
  margin-top: 3px;
}
.op-sum-disc-lbl { color: #00b050; display: flex; align-items: center; gap: 4px; }
.op-sum-disc-amt { color: #00b050; font-weight: 600; }
.op-sum-costs-row {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  font-weight: 600;
  padding: 4px 0;
  border-top: 1px solid #2a3040;
  margin-top: 2px;
  color: #f0f4ff;
}
```

---

## New helper functions to add

Add both of these functions immediately before `function renderOptumPreview()`. Do not modify any existing functions.

### Function 1 — `collectPackageDiscounts(packages)`

Walks all packages and gathers unique percentage discount rules with which package indices carry them.

```javascript
function collectPackageDiscounts(packages) {
  // Returns a Map: key = "RuleName-pct", value = { pct, pkgIndices[] }
  const rules = new Map();
  packages.forEach((pkg, i) => {
    (pkg.discountItems || []).forEach(di => {
      (di.discounts || []).forEach(d => {
        if (!d.percentageOff) return;
        const key = `${di.ruleName || 'Discount'}-${d.percentageOff}`;
        if (!rules.has(key)) {
          rules.set(key, { pct: d.percentageOff, pkgIndices: [] });
        }
        rules.get(key).pkgIndices.push(i);
      });
    });
  });
  return rules;
}
```

### Function 2 — `activePackageDiscounts(packages, checkedSet)`

Evaluates which discount rules are active given the currently checked packages.
A discount is considered active when 2 or more of the packages that carry it are checked.
This approximates the real `customRules` logic without requiring a rules engine.

```javascript
function activePackageDiscounts(packages, checkedSet) {
  // Returns array of active { pct } objects
  const rules = collectPackageDiscounts(packages);
  const active = [];
  rules.forEach(rule => {
    const checkedCount = rule.pkgIndices.filter(i => checkedSet.has(i)).length;
    if (checkedCount >= 2) {
      active.push({ pct: rule.pct });
    }
  });
  return active;
}
```

---

## Changes inside `renderOptumPreview()`

### Change A — Replace the monthly total block with discount-aware calculation

**Find this existing block** near the top of `renderOptumPreview()`:

```javascript
  const packages = data.packages || [];
  const multi = previewCheckedPackages.size > 1;

  // Monthly total from checked packages
  let monthly = 0;
  previewCheckedPackages.forEach(i => {
    const pkg = packages[i];
    if (pkg && pkg.amount) monthly += parseFloat(pkg.amount) || 0;
  });
```

**Replace with:**

```javascript
  const packages = data.packages || [];
  const multi = previewCheckedPackages.size > 1;

  // Monthly total from checked packages
  let monthly = 0;
  previewCheckedPackages.forEach(i => {
    const pkg = packages[i];
    if (pkg && pkg.amount) monthly += parseFloat(pkg.amount) || 0;
  });

  // Active package discounts
  const pkgDiscounts = activePackageDiscounts(packages, previewCheckedPackages);
  const activePct    = pkgDiscounts.length > 0 ? pkgDiscounts[0].pct : 0;
  const discountAmt  = activePct > 0 ? +(monthly * activePct / 100).toFixed(2) : 0;
  const monthlyAfterDiscount = +(monthly - discountAmt).toFixed(2);
```

---

### Change B — Remove the three lines from the left column header

**Find this block** in the `previewBody.innerHTML` template string:

```javascript
          <div class="op-body-text">${data.headerDescription || ''}</div>
          <div class="op-notice-text">Pricing shown is for partners only.</div>
          <div class="op-notice-text" style="margin-bottom:8px">If your volume levels are higher, OR you are a provider, <a href="#">contact us</a> to receive a private quote from our sales team.</div>
          ${discountTooltip ? `<div class="op-discount-text">${discountTooltip}</div>` : ''}
          <div id="opPkgCards">${pkgCardsHtml}</div>
```

**Replace with:**

```javascript
          <div class="op-body-text">${data.headerDescription || ''}</div>
          <div id="opPkgCards">${pkgCardsHtml}</div>
```

The two hardcoded notice lines and the `discountTooltip` paragraph are removed. `discountTooltip` is still used in the Order Summary below — do not remove the variable declaration.

---

### Change C — Replace the Order Summary monthly section with discount-aware version

**Find this block** in the `summaryHtml` template string:

```javascript
      <div class="op-sum-row"><span class="op-sum-lbl">Est. monthly payment:</span><span class="op-sum-val op-big">${previewFmt$(monthly)}</span></div>
      <div style="height:6px"></div>
      <div class="op-sum-row" style="padding-bottom:2px"><span class="op-sum-lbl" style="font-weight:700;color:#f0f4ff;font-size:11px">Selected Add-Ons</span></div>
      <div class="op-sum-row"><span class="op-sum-lbl">Included Add-Ons</span><span class="op-sum-val" style="font-size:10px">Based on Usage*</span></div>
      <div class="op-sum-row"><span class="op-sum-lbl">Your Add-on costs</span><span class="op-sum-val">&mdash;</span></div>
      <div class="op-sum-row"><span class="op-sum-lbl">Monthly subtotal:</span><span class="op-sum-val">${previewFmt$(monthly)}</span></div>
```

**Replace with:**

```javascript
      ${previewCheckedPackages.size > 0 ? `
      <div style="padding-bottom:4px">
        <div style="font-size:10px;font-weight:700;color:#f0f4ff;margin-bottom:3px">Selected package</div>
        ${[...previewCheckedPackages].map(i => {
          const pkg = packages[i];
          if (!pkg) return '';
          const label = esc(pkg.name || pkg.internalName || 'Package');
          const amt   = parseFloat(pkg.amount) || 0;
          const amtStr = amt > 0 ? previewFmt$(amt) : 'Based on Usage*';
          return `<div class="op-sum-pkg-row"><span class="op-sum-pkg-name">${label}</span><span class="op-sum-pkg-amt">${amtStr}</span></div>`;
        }).join('')}
        ${activePct > 0 ? `
        <div class="op-sum-disc-row">
          <span class="op-sum-disc-lbl">
            ${activePct}% off discount
            ${discountTooltip ? `
            <span class="op-tooltip-wrap">
              <span class="op-tooltip-icon">ⓘ</span>
              <span class="op-tooltip-bubble">${discountTooltip}</span>
            </span>` : ''}
          </span>
          <span class="op-sum-disc-amt">-${previewFmt$(discountAmt)}</span>
        </div>` : ''}
        <div class="op-sum-costs-row">
          <span>Your Package Costs</span>
          <span>${previewFmt$(monthlyAfterDiscount)}</span>
        </div>
      </div>` : ''}
      <div class="op-sum-row"><span class="op-sum-lbl">Est. monthly payment:</span><span class="op-sum-val op-big">${previewFmt$(monthlyAfterDiscount)}</span></div>
      <div style="height:6px"></div>
      <div class="op-sum-row" style="padding-bottom:2px"><span class="op-sum-lbl" style="font-weight:700;color:#f0f4ff;font-size:11px">Selected Add-Ons</span></div>
      <div class="op-sum-row"><span class="op-sum-lbl">Included Add-Ons</span><span class="op-sum-val" style="font-size:10px">Based on Usage*</span></div>
      <div class="op-sum-row"><span class="op-sum-lbl">Your Add-on costs</span><span class="op-sum-val">&mdash;</span></div>
      <div class="op-sum-row"><span class="op-sum-lbl">Monthly subtotal:</span><span class="op-sum-val">${previewFmt$(monthlyAfterDiscount)}</span></div>
```

---

## Version strings and change log

**HTML title** — find:
```html
<title>Pricing Editor v2.0.26</title>
```
Replace with:
```html
<title>Pricing Editor v2.0.28</title>
```

**APP_VERSION constants** — find:
```javascript
const APP_VERSION = "v2.0.26";
const APP_VERSION_JS = "v2_0_26";
```
Replace with:
```javascript
const APP_VERSION = "v2.0.28";
const APP_VERSION_JS = "v2_0_28";
```

**Change log** — add at the very top of the existing change log:

```
v2.0.28
- Removed two hardcoded partner notice lines from preview left column header
  ("Pricing shown is for partners only" and "If your volume levels are higher...")
  These are product-specific; products that need them include them in headerDescription
- Removed packageMonthlySummaryDiscountToolTip from left column header where it
  caused duplicate discount text on Medical Network APIs
- Added collectPackageDiscounts() helper: walks package discountItems to gather
  unique percentage discount rules and the package indices that carry them
- Added activePackageDiscounts() helper: fires a discount when 2+ packages carrying
  that rule are checked — approximates customRules logic without a rules engine
- Order Summary now shows selected package list with names and amounts
- Order Summary now shows dynamic percentage discount line with calculated savings
  when qualifying package combination is selected
- packageMonthlySummaryDiscountToolTip shown as ⓘ hover tooltip on discount line
- Est. monthly payment and Monthly subtotal now reflect post-discount amount
```

---

## What NOT to change

- Do not remove the `discountTooltip` or `implWaiverTooltip` variable declarations — both are still used
- Do not modify the implementation discount logic (`multi`, `implDisc`, `implNet`) — unchanged
- Do not touch any editor sections, nav, validation, compare, save, or panel logic
- Do not touch `main.py`
- Do not delete any existing CSS rules

---

## Acceptance criteria

**Medical Network APIs (`item_mn__08092024.json`):**
1. Left column header shows `headerDescription` HTML once — no duplicate 7% text paragraph
2. "Pricing shown is for partners only" does not appear as a standalone line
3. "If your volume levels are higher…" does not appear as a standalone line
4. Check Eligibility only — Order Summary shows one package row, no discount line
5. Check Eligibility + ERA — Order Summary shows two package rows, 7% off discount line appears with `-$XX.XX`, and `ⓘ` tooltip shows on hover
6. Check Eligibility + ERA + Institutional Claims — discount fires, savings calculated correctly
7. Uncheck packages below 2 qualifying — discount line disappears, subtotal reverts
8. Est. monthly payment and Monthly subtotal reflect post-discount amount when discount is active
9. Implementation 2+ package waiver logic still works independently and correctly

**Revenue Performance Advisor (`rpa_04152025_latest.json`):**
10. No hardcoded notice lines appear
11. No discount tooltip or discount line appears (RPA has no package-level `discountItems` with `percentageOff`)
12. Order Summary shows selected package rows and correct monthly total with no discount line
13. Preview renders correctly with no regressions

**General:**
14. HTML title shows `v2.0.28`
15. Download filename contains `v2_0_28`
16. JavaScript syntax check passes: extract script block and run `node --check`
17. No console errors on page load, file load, or package checkbox interaction

---

## Files

Attach `index_v2_0_26_filename_prompt.html`. No other files needed.
