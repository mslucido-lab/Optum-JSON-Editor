# Pricing Editor — ChatGPT Handoff
## v2.0.28: Preview Rendering Fixes + Dynamic Discount + isSummableAmount
*Prepared: 2026-05-11*

---

## Context

You are making targeted changes to `index_v2_0_26_filename_prompt.html`. The full file will be attached.

**Output:** A new file named `index_v2_0_28.html`.

Do not touch `main.py`. Do not change anything not listed here. All changes are inside `renderOptumPreview()` and three new helper functions added immediately before it.

---

## Overview — four problems being fixed

**Problem 1 — Two hardcoded partner notice lines** appear for every product. They are product-specific content already embedded in `headerDescription` for products that need them. Remove them entirely.

**Problem 2 — `packageMonthlySummaryDiscountToolTip` rendered as duplicate paragraph** in the left column header. It belongs in the Order Summary only. Remove it from the header. Add it as a hover tooltip `ⓘ` on the discount line in the Order Summary.

**Problem 3 — `isSummableAmount: "N"` packages incorrectly included in monthly total.** Claim Status has `customAttributes[].name === "isSummableAmount"` with `value === "N"`. This is the Optum platform flag meaning the package `amount` is a per-request rate, not a monthly minimum. It must be excluded from the monthly sum and shown as "Based on Usage*" in the Order Summary package list.

**Problem 4 — 7% package discount not implemented.** The Order Summary must show a dynamic discount line when the qualifying package combination is selected. The discount rule is stored in `discountItems` on individual packages. A discount fires when 2 or more packages carrying the same discount rule are checked.

---

## Step 1 — Add CSS

Add these rules inside the existing `<style>` tag after all existing CSS:

```css
/* v2.0.28 */
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
.op-sum-pkg-row {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  padding: 2px 0;
  color: #8fa3bb;
}
.op-sum-pkg-name { flex: 1; }
.op-sum-pkg-amt  { flex-shrink: 0; font-weight: 500; color: #f0f4ff; }
.op-sum-pkg-amt.op-usage { color: #8fa3bb; font-style: italic; }
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

## Step 2 — Add three helper functions

Add all three of these functions immediately before `function renderOptumPreview()`. Do not modify any existing functions.

### Helper 1 — `isPkgSummable(pkg)`

Returns `false` when a package has `isSummableAmount: "N"`, meaning its `amount` is a per-request rate and must be excluded from the monthly minimum total.

```javascript
function isPkgSummable(pkg) {
  const attrs = pkg.customAttributes || [];
  const flag = attrs.find(a => String(a.name || '').trim() === 'isSummableAmount');
  return !flag || String(flag.value || '').trim().toUpperCase() !== 'N';
}
```

### Helper 2 — `collectPackageDiscounts(packages)`

Walks all packages and gathers unique percentage discount rules. Returns a Map: key = `"RuleName-pct"`, value = `{ pct, pkgIndices[] }` listing which package indices carry that rule.

```javascript
function collectPackageDiscounts(packages) {
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

### Helper 3 — `activePackageDiscounts(packages, checkedSet)`

Evaluates which discount rules are active. A discount fires when 2 or more packages carrying that rule are checked. Returns an array of active `{ pct }` objects.

```javascript
function activePackageDiscounts(packages, checkedSet) {
  const rules = collectPackageDiscounts(packages);
  const active = [];
  rules.forEach(rule => {
    const checkedCount = rule.pkgIndices.filter(i => checkedSet.has(i)).length;
    if (checkedCount >= 2) active.push({ pct: rule.pct });
  });
  return active;
}
```

---

## Step 3 — Replace the variable declarations block at the top of `renderOptumPreview()`

**Find this exact block** (lines 2004–2012):

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

  // Monthly total — only summable packages (excludes isSummableAmount: "N")
  let monthly = 0;
  previewCheckedPackages.forEach(i => {
    const pkg = packages[i];
    if (pkg && isPkgSummable(pkg) && pkg.amount) {
      monthly += parseFloat(pkg.amount) || 0;
    }
  });

  // Active package discounts
  const pkgDiscounts      = activePackageDiscounts(packages, previewCheckedPackages);
  const activePct         = pkgDiscounts.length > 0 ? pkgDiscounts[0].pct : 0;
  const discountAmt       = activePct > 0 ? +(monthly * activePct / 100).toFixed(2) : 0;
  const monthlyAfterDiscount = +(monthly - discountAmt).toFixed(2);
```

---

## Step 4 — Remove three lines from the left column header

**Find this block** in the `previewBody.innerHTML` template string (lines 2153–2156):

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

The two hardcoded notice lines and the `discountTooltip` left-column paragraph are removed. Do not remove the `discountTooltip` variable declaration earlier in the function — it is still used in Step 5.

---

## Step 5 — Replace the Order Summary monthly costs section

**Find this exact block** inside `summaryHtml` (lines 2111–2116):

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
      <div style="padding-bottom:6px">
        <div style="font-size:10px;font-weight:700;color:#f0f4ff;margin-bottom:4px">Selected package</div>
        ${[...previewCheckedPackages].sort((a,b)=>a-b).map(i => {
          const pkg = packages[i];
          if (!pkg) return '';
          const label  = esc(pkg.name || pkg.internalName || 'Package');
          const summable = isPkgSummable(pkg);
          const amtStr = summable
            ? (parseFloat(pkg.amount) > 0 ? previewFmt$(parseFloat(pkg.amount)) : '$0.00')
            : 'Based on Usage*';
          return `<div class="op-sum-pkg-row">
            <span class="op-sum-pkg-name">${label}</span>
            <span class="op-sum-pkg-amt${summable ? '' : ' op-usage'}">${amtStr}</span>
          </div>`;
        }).join('')}
        ${activePct > 0 ? `
        <div class="op-sum-disc-row">
          <span class="op-sum-disc-lbl">
            ${activePct}% off discount
            ${discountTooltip ? `<span class="op-tooltip-wrap">
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

**HTML title:**
```html
<title>Pricing Editor v2.0.28</title>
```

**APP_VERSION constants:**
```javascript
const APP_VERSION = "v2.0.26";
const APP_VERSION_JS = "v2_0_26";
```
Replace with:
```javascript
const APP_VERSION = "v2.0.28";
const APP_VERSION_JS = "v2_0_28";
```

**Change log entry** — add at the very top:

```
v2.0.28
- Removed two hardcoded partner notice lines from preview left column header
  (product-specific content already present in headerDescription where needed)
- Removed packageMonthlySummaryDiscountToolTip from left column header
  (was causing duplicate 7% discount text on Medical Network APIs)
- Added isPkgSummable() helper: reads isSummableAmount customAttribute;
  packages with value "N" are excluded from monthly total and shown as
  "Based on Usage*" in the Order Summary package list
- Added collectPackageDiscounts() helper: walks package discountItems to build
  a map of percentage discount rules and which packages carry them
- Added activePackageDiscounts() helper: fires a discount when 2+ packages
  carrying the same rule are checked
- Order Summary now shows selected package list with individual names and amounts
- Claim Status correctly shows "Based on Usage*" instead of $0.20 in package list
- Monthly total correctly excludes non-summable packages
- 7% off discount line appears dynamically when qualifying package combination
  is selected, with correct savings calculation
- packageMonthlySummaryDiscountToolTip shown as ⓘ hover tooltip on discount line
- Est. monthly payment, Monthly subtotal, and Your Package Costs all reflect
  post-discount amount
```

---

## What NOT to change

- Do not remove the `discountTooltip` or `implWaiverTooltip` variable declarations
- Do not modify the implementation discount logic (`multi`, `implDisc`, `implNet`)
- Do not touch any editor sections, nav, validation, compare, save, or panel logic
- Do not touch `main.py`
- Do not delete any existing CSS rules

---

## Acceptance criteria

**Medical Network APIs (`item_mn__08092024.json`):**

1. Left column header shows no hardcoded notice lines and no standalone discount tooltip paragraph
2. Check Eligibility only → Order Summary: one package row `Eligibility $200.00`, no discount line, Est. payment `$200.00`
3. Check Eligibility + Claim Status → Order Summary: Eligibility `$200.00`, Claim Status `Based on Usage*` (italic), no discount line, Est. payment `$200.00`
4. Check Eligibility + ERA → Order Summary: both package rows, `7% off discount ⓘ -$22.40`, Your Package Costs `$297.60`, Est. payment `$297.60`
5. Hovering `ⓘ` on the discount line shows the tooltip bubble with the `packageMonthlySummaryDiscountToolTip` value
6. Check all 5 packages → Claim Status shows `Based on Usage*`, four summable packages sum to `$820.00`, `7% off discount -$57.40`, Your Package Costs `$762.60` — matches real Optum page exactly
7. Uncheck packages below 2 qualifying → discount line disappears, totals revert
8. Implementation 2+ package waiver still works independently and correctly

**Revenue Performance Advisor (`rpa_04152025_latest.json`):**

9. No hardcoded notice lines appear
10. No discount line appears (RPA packages have no `percentageOff` discountItems)
11. No `isSummableAmount` issues (RPA packages are all summable)
12. Preview renders correctly with no regressions

**General:**

13. HTML title shows `v2.0.28`
14. Download filename contains `v2_0_28`
15. JavaScript syntax check passes: extract script block and run `node --check`
16. No console errors on page load, file load, or package checkbox interaction

---

## Files

Attach `index_v2_0_26_filename_prompt.html`. No other files needed.
