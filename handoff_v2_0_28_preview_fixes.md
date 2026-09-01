# Pricing Editor — ChatGPT Handoff
## v2.0.28: Preview Rendering Fixes
*Prepared: 2026-05-11*

---

## Context

You are making three targeted changes to `index_v2_0_26_filename_prompt.html`. The full file will be attached.

**Output:** A new file named `index_v2_0_28.html`.

Do not touch `main.py`. Do not change anything not listed here. All three changes are inside `renderOptumPreview()` only.

---

## Background

Two rendering bugs were found in the Optum-fidelity pricing preview:

**Bug 1 — Duplicate discount text.**
The `packageMonthlySummaryDiscountToolTip` custom attribute value is being rendered as a standalone paragraph in the left column header area. This causes the 7% discount text to appear twice on the Medical Network APIs preview — once from `headerDescription` (correct) and once from the custom attribute tooltip (wrong location). The tooltip belongs in the Order Summary right column, not the header.

**Bug 2 — Hardcoded partner notice lines.**
Two lines are hardcoded in the preview for every product:
- "Pricing shown is for partners only."
- "If your volume levels are higher, OR you are a provider, contact us..."

These lines are product-specific — they only apply to Medical Network APIs and are already embedded in that product's `headerDescription` field. They do not belong in the preview renderer at all. Hardcoding them causes them to appear on every product, which is incorrect. They should be removed entirely — products that need this language include it in `headerDescription`.

---

## Change 1 — Remove the two hardcoded notice lines

**Find this block** inside `renderOptumPreview()` (lines 2154–2155):

```javascript
          <div class="op-notice-text">Pricing shown is for partners only.</div>
          <div class="op-notice-text" style="margin-bottom:8px">If your volume levels are higher, OR you are a provider, <a href="#">contact us</a> to receive a private quote from our sales team.</div>
```

**Delete both lines entirely.** The surrounding lines stay unchanged:

```javascript
          <div class="op-body-text">${data.headerDescription || ''}</div>
          ${discountTooltip ? `<div class="op-discount-text">${discountTooltip}</div>` : ''}
```

becomes:

```javascript
          <div class="op-body-text">${data.headerDescription || ''}</div>
          ${discountTooltip ? `<div class="op-discount-text">${discountTooltip}</div>` : ''}
```

Wait — that still leaves the `discountTooltip` paragraph in the wrong place. Change 2 handles that. Apply both changes together.

---

## Change 2 — Remove `discountTooltip` from the left column header

The `discountTooltip` variable holds the `packageMonthlySummaryDiscountToolTip` custom attribute value. It is currently rendered as a paragraph in the left column between the header description and the package cards. This is wrong — it belongs in the Order Summary as a tooltip, not as body copy.

**Find this line** immediately after the two notice lines you deleted in Change 1:

```javascript
          ${discountTooltip ? `<div class="op-discount-text">${discountTooltip}</div>` : ''}
```

**Delete this line entirely.**

After both Change 1 and Change 2, the left column header block should read:

```javascript
          <div class="op-cat-label">${esc(previewCategoryLabel(data.viewTemplate))}</div>
          <div class="op-h1">${esc(data.name || 'Unnamed Product')}</div>
          <div class="op-h2">Build your package</div>
          <div class="op-body-text">${data.headerDescription || ''}</div>
          <div id="opPkgCards">${pkgCardsHtml}</div>
          ${implHtml}
          ${addonHtml}
          ${data.paymentSchedule ? `<div class="op-payment-notice">${String(data.paymentSchedule || '')}</div>` : ''}
```

Nothing else in the left column changes.

---

## Change 3 — Add `discountTooltip` as a ⓘ in the Order Summary

The `packageMonthlySummaryDiscountToolTip` value should appear in the Order Summary right column as a tooltip indicator next to the "Selected package" heading — visible when the value is non-empty, always shown (not conditioned on package selection state, since evaluating the discount eligibility rules from `discountItems.customRules` is out of scope for the preview).

**Find this block** in the `summaryHtml` template string (the Selected Add-Ons section, around line 2113):

```javascript
      <div class="op-sum-row" style="padding-bottom:2px"><span class="op-sum-lbl" style="font-weight:700;color:#f0f4ff;font-size:11px">Selected Add-Ons</span></div>
```

**Replace the entire Order Summary selected package block** — find this section at the top of `summaryHtml`:

```javascript
      <div class="op-sum-row"><span class="op-sum-lbl">Est. monthly payment:</span><span class="op-sum-val op-big">${previewFmt$(monthly)}</span></div>
      <div style="height:6px"></div>
      <div class="op-sum-row" style="padding-bottom:2px"><span class="op-sum-lbl" style="font-weight:700;color:#f0f4ff;font-size:11px">Selected Add-Ons</span></div>
```

**Replace with:**

```javascript
      <div class="op-sum-row"><span class="op-sum-lbl">Est. monthly payment:</span><span class="op-sum-val op-big">${previewFmt$(monthly)}</span></div>
      <div style="height:6px"></div>
      ${discountTooltip ? `<div class="op-sum-row" style="padding-bottom:4px">
        <span style="font-size:10px;color:#8fa3bb;line-height:1.5">${discountTooltip}</span>
      </div>` : ''}
      <div class="op-sum-row" style="padding-bottom:2px"><span class="op-sum-lbl" style="font-weight:700;color:#f0f4ff;font-size:11px">Selected Add-Ons</span></div>
```

This renders the tooltip value as small body text in the Order Summary, between the monthly payment line and the Selected Add-Ons section — which matches where the real Optum page shows the 7% discount tooltip content. It only renders when `discountTooltip` is non-empty, so products without this custom attribute are unaffected.

---

## CSS to add

Add this one new CSS rule inside the existing `<style>` tag, after the existing `.op-discount-text` rule. If `.op-discount-text` no longer has any usages after these changes you may leave it in place — do not delete existing CSS rules.

```css
.op-sum-discount-tip {
  font-size: 10px;
  color: #8fa3bb;
  line-height: 1.5;
  padding: 3px 0 6px;
}
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

**Change log** — add this at the very top of the existing change log comment block:

```
v2.0.28
- Removed two hardcoded partner notice lines from preview left column
  ("Pricing shown is for partners only" and "If your volume levels are higher...")
  These are product-specific and already present in headerDescription where needed
- Removed packageMonthlySummaryDiscountToolTip from preview left column header area
  where it was causing duplicate discount text on Medical Network APIs
- Added packageMonthlySummaryDiscountToolTip to Order Summary right column
  as tooltip body text between Est. monthly payment and Selected Add-Ons
```

---

## What NOT to change

- Do not modify any other part of `renderOptumPreview()` beyond the three changes above
- Do not remove the `discountTooltip` variable declaration or the `getCustomAttr()` call that populates it — it is still used in Change 3
- Do not touch `main.py`
- Do not touch any editor sections, nav, validation, compare, save, or panel logic
- Do not delete any existing CSS rules

---

## Acceptance criteria

1. Loading `item_mn__08092024.json` — the 7% discount text appears **once only** in the preview, inside `headerDescription` rendering, not as a separate paragraph below it
2. Loading `item_mn__08092024.json` — "Pricing shown is for partners only" does **not** appear as a standalone line in the preview
3. Loading `item_mn__08092024.json` — the hardcoded "If your volume levels are higher…" line does **not** appear as a standalone line
4. Loading `item_mn__08092024.json` — the Order Summary shows the `packageMonthlySummaryDiscountToolTip` value as small text between Est. monthly payment and Selected Add-Ons
5. Loading `rpa_04152025_latest.json` — none of the removed lines appear (RPA has no `packageMonthlySummaryDiscountToolTip` custom attribute, so the Order Summary tooltip block is absent)
6. Loading `rpa_04152025_latest.json` — preview renders correctly with no regressions
7. Package card checkbox behavior still works
8. Implementation 2+ package waiver logic still works
9. HTML title shows `v2.0.28`
10. Download filename contains `v2_0_28`
11. JavaScript syntax check passes: extract script block and run `node --check`
12. No console errors on page load or file load

---

## Files

Attach `index_v2_0_26_filename_prompt.html`. No other files needed.
