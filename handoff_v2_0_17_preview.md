# Pricing Editor — ChatGPT Handoff
## v2.0.17: Replace `renderPreview()` with Optum-Fidelity Preview
*Prepared: 2026-05-10*

---

## Context

You are making a targeted replacement to `index.html` (currently `index_v2_0_16_combined.html`). The full file will be attached.

**Output:** A new file named `index_v2_0_17.html`. Do not rename anything else. Do not touch `main.py`.

This is a self-contained change. You are replacing one function and adding CSS. You are not restructuring the editor, nav, panel resizing, validation, compare, save, or any other section.

---

## The problem

The current `renderPreview()` function (search for `function renderPreview()`) builds a generic card-based data inspector. It shows the product name, a truncated description, package cards with amber price badges, and a raw data table. It does not look like the actual Optum AI Marketplace pricing page.

The goal is to replace it with a high-fidelity replica of the real Optum page so the user sees exactly what the live page will look like as they edit.

A reference mockup has been built and tested. The CSS and JS from that mockup are provided below in full. Your job is to port them cleanly into the existing `index.html` without disturbing anything else.

---

## What the real Optum page looks like

The preview must render these elements in this order, reading from the real page:

**Left column:**
1. Category label (e.g. "Application Programming Interface") — derived from `viewTemplate`
2. H1 product name — from `data.name`
3. H2 "Build your package" — static label
4. Header description — from `data.headerDescription`, rendered as `innerHTML` (supports bold, links)
5. Two static notice lines (partner pricing, contact us)
6. Discount tooltip — from the `packageMonthlySummaryDiscountToolTip` custom attribute value, rendered as `innerHTML`
7. Package cards — one per package in `data.packages`, each showing:
   - Checkbox (toggleable, blue when checked)
   - Package name (bold)
   - Price description in green (from `amountDescription`)
   - Marketing title subtitle (from `marketingTitle`)
   - Dotted leader rows, one per volume band: `[range] ·····  [price]`
8. Implementation section — from the `Implementations` option group in top-level `data.optionItems`:
   - H2 "Implementation"
   - Header description as `innerHTML`
   - Waiver tooltip text (from `implementationSummaryDiscountToolTip` custom attr) — only shown when 2+ packages are checked
   - "Required with your package" label
   - Implementation card: name left, description center, price right
   - Price shows: if 2+ packages checked → strikethrough original + green $0.00; otherwise → full amount
9. Add-ons section — from the `Addons` option group in top-level `data.optionItems`:
   - H2 "Add-ons"
   - "Add-ons available with your package" label
   - Header description as `innerHTML`
   - Collapsed accordion showing line item count
10. Payment schedule notice — from `data.paymentSchedule`, rendered as `innerHTML`

**Right column (Order Summary):**
- "Order summary" heading
- "Monthly costs" dropdown header (static, decorative)
- Est. monthly payment — sum of `amount` for all checked packages
- Selected Add-Ons section with "Included Add-Ons: Based on Usage*"
- Monthly subtotal — same as monthly payment
- One-time fees accordion (collapsible):
  - Selected Implementation heading
  - Implementation line item name
  - List price
  - Discount line (100% off if 2+ packages checked, otherwise $0)
  - Your Implementations costs
  - One-time fees subtotal
- Promo code field (static, non-functional)
- Initial payment: $0.00 (static)
- "Continue to checkout" button (static, decorative)
- "Save changes" link (static)
- "Need help?" panel (static)

---

## Data mapping

The preview reads directly from the existing `data` object (already in scope as a global in `index.html`). No new global state needed except `previewCheckedPackages` (a `Set` of checked package indices) and `previewOtfOpen` (boolean for one-time fees accordion state).

```javascript
// Add these two at the top of the script block near other globals
const previewCheckedPackages = new Set();
let previewOtfOpen = true;
```

### Key data paths

| Preview element | Data path |
|---|---|
| Product name | `data.name` |
| Category label | derived from `data.viewTemplate` (see below) |
| Header description | `data.headerDescription` |
| Discount tooltip | `getCustomAttr(data, 'packageMonthlySummaryDiscountToolTip')` |
| Impl waiver tooltip | `getCustomAttr(data, 'implementationSummaryDiscountToolTip')` |
| Payment schedule | `data.paymentSchedule` |
| Packages | `data.packages` (array) |
| Package name | `pkg.name \|\| pkg.internalName` |
| Package price desc | `pkg.amountDescription` |
| Package subtitle | `pkg.marketingTitle` |
| Volume bands | `pkg.monthlyVolumes` (array) |
| Band min | `mv.minimumValue` |
| Band max | `mv.maximumValue` |
| Band price | `mv.transactionUnitAmount` |
| Band unit | `mv.unit` |
| Implementations group | top-level `data.optionItems` where `optionItemType === 'Implementations'` |
| Impl header desc | `group.headerDescription` |
| Impl line item name | `group.optionLineItems[0].internalName` |
| Impl line item amount | `group.optionLineItems[0].amount` |
| Impl line item unit | `group.optionLineItems[0].unit` |
| Impl line item desc | `group.optionLineItems[0].longDescription` |
| Addons group | top-level `data.optionItems` where `optionItemType === 'Addons'` |
| Addons header desc | `group.headerDescription` |
| Addons line item count | `group.optionLineItems.length` |

### Category label derivation

```javascript
function previewCategoryLabel(viewTemplate) {
  if (!viewTemplate) return '';
  const t = String(viewTemplate).toLowerCase();
  if (t.includes('api')) return 'Application Programming Interface';
  if (t.includes('software')) return 'Software';
  return viewTemplate;
}
```

### Custom attribute lookup

```javascript
function getCustomAttr(data, name) {
  const attrs = data.customAttributes || [];
  const attr = attrs.find(a => a && String(a.name || '').trim() === name);
  return attr ? (attr.value || '') : '';
}
```

### Money formatting

```javascript
function previewFmt$(n) {
  const v = parseFloat(n);
  if (isNaN(v)) return '$0.00';
  return v === 0 ? '$0.00' : '$' + v.toFixed(2);
}
```

### Volume band range and price formatting

```javascript
function previewFmtRange(mv) {
  const min = mv.minimumValue ?? 0;
  const max = mv.maximumValue;
  if (max === null || max === undefined || max === '' || Number(max) >= 999999999) {
    return `${Number(min).toLocaleString()}+ requests per month`;
  }
  return `${Number(min).toLocaleString()} – ${Number(max).toLocaleString()} requests per month`;
}

function previewFmtPrice(mv) {
  const price = parseFloat(mv.transactionUnitAmount ?? 0);
  const unit = mv.unit || '';
  if (price === 0) return unit || 'Included';
  return `${previewFmt$(price)}/${unit}`;
}
```

---

## CSS to add

Add this CSS block inside the existing `<style>` tag in `index.html`, after all existing CSS. Do not remove any existing CSS.

```css
/* v2.0.17 Optum-fidelity preview */
.op-preview-wrap { background: #15181e; font-family: var(--sans); color: #f0f4ff; padding: 18px 18px 40px; min-height: 100%; }
.op-preview-cols { display: grid; grid-template-columns: 1fr 210px; gap: 16px; align-items: flex-start; }
.op-preview-left { min-width: 0; }
.op-preview-right { position: sticky; top: 0; }
.op-cat-label { font-size: 10px; text-transform: uppercase; letter-spacing: .08em; color: #4a5870; margin-bottom: 8px; }
.op-h1 { font-size: 22px; font-weight: 700; color: #f0f4ff; margin-bottom: 12px; line-height: 1.2; }
.op-h2 { font-size: 15px; font-weight: 700; color: #f0f4ff; margin-bottom: 8px; margin-top: 2px; }
.op-body-text { font-size: 12px; line-height: 1.6; color: #8fa3bb; margin-bottom: 6px; }
.op-body-text b { color: #f0f4ff; font-weight: 700; }
.op-notice-text { font-size: 11px; color: #4a5870; margin-bottom: 4px; line-height: 1.5; }
.op-notice-text a { color: #1a8cff; }
.op-discount-text { font-size: 12px; color: #8fa3bb; margin-bottom: 14px; line-height: 1.55; }
.op-discount-text b { color: #f0f4ff; font-weight: 700; }
.op-pkg-card { border: 1px solid #2a3040; border-radius: 5px; background: #1e2330; padding: 11px 13px; margin-bottom: 6px; display: flex; align-items: flex-start; gap: 10px; cursor: pointer; transition: border-color .15s; }
.op-pkg-card:hover { border-color: #3a4255; }
.op-pkg-card.op-sel { border-color: #1a8cff; }
.op-pkg-cb { width: 15px; height: 15px; flex-shrink: 0; margin-top: 2px; border: 2px solid #3a4255; border-radius: 3px; display: flex; align-items: center; justify-content: center; background: transparent; transition: all .15s; }
.op-pkg-card.op-sel .op-pkg-cb { background: #1a8cff; border-color: #1a8cff; }
.op-pkg-ck { display: none; }
.op-pkg-card.op-sel .op-pkg-ck { display: block; }
.op-pkg-left { flex: 1; min-width: 0; }
.op-pkg-name { font-size: 12px; font-weight: 700; color: #f0f4ff; margin-bottom: 1px; }
.op-pkg-price { font-size: 12px; font-weight: 700; color: #00b050; }
.op-pkg-sub { font-size: 10px; color: #4a5870; margin-top: 1px; }
.op-pkg-right { flex-shrink: 0; min-width: 155px; }
.op-tier-row { display: flex; align-items: baseline; font-size: 10px; color: #8fa3bb; padding: 1px 0; gap: 3px; white-space: nowrap; }
.op-tier-range { flex-shrink: 0; min-width: 98px; }
.op-tier-dots { flex: 1; border-bottom: 1px dotted #3a4255; margin: 0 3px 2px; height: 1px; align-self: flex-end; min-width: 4px; }
.op-tier-price { flex-shrink: 0; text-align: right; }
.op-section-divider { height: 1px; background: #2a3040; margin: 14px 0; }
.op-section-sublabel { font-size: 10px; text-transform: uppercase; letter-spacing: .08em; color: #4a5870; margin-bottom: 6px; }
.op-impl-card { border: 1px solid #2a3040; border-radius: 5px; background: #1e2330; padding: 11px 13px; display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; margin-bottom: 6px; }
.op-impl-name { font-size: 11px; font-weight: 700; color: #f0f4ff; margin-bottom: 3px; }
.op-impl-desc { font-size: 10px; color: #8fa3bb; line-height: 1.5; max-width: 180px; }
.op-impl-desc a { color: #1a8cff; }
.op-impl-price-col { text-align: right; flex-shrink: 0; }
.op-impl-orig { font-size: 11px; color: #4a5870; text-decoration: line-through; }
.op-impl-new { font-size: 13px; font-weight: 700; color: #00b050; }
.op-impl-unit { font-size: 10px; color: #4a5870; }
.op-addon-row { border: 1px solid #2a3040; border-radius: 5px; background: #1e2330; padding: 9px 13px; display: flex; align-items: center; justify-content: space-between; cursor: default; }
.op-addon-row-label { font-size: 12px; font-weight: 600; color: #f0f4ff; }
.op-addon-expand-btn { width: 20px; height: 20px; border-radius: 50%; background: #1a8cff; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.op-payment-notice { font-size: 10px; color: #4a5870; border-top: 1px solid #2a3040; padding-top: 10px; margin-top: 12px; line-height: 1.5; }
.op-summary-box { background: #1e2330; border: 1px solid #2a3040; border-radius: 6px; padding: 12px; }
.op-summary-title { font-size: 12px; font-weight: 700; color: #f0f4ff; margin-bottom: 10px; }
.op-costs-head { display: flex; align-items: center; justify-content: space-between; background: #252b38; border: 1px solid #2a3040; border-radius: 4px; padding: 6px 9px; font-size: 11px; font-weight: 600; color: #f0f4ff; margin-bottom: 8px; }
.op-sum-row { display: flex; justify-content: space-between; font-size: 11px; padding: 3px 0; border-bottom: 1px solid #2a3040; }
.op-sum-row:last-child { border: none; }
.op-sum-lbl { color: #8fa3bb; }
.op-sum-val { font-weight: 600; color: #f0f4ff; }
.op-sum-val.op-big { font-size: 13px; }
.op-otf-head { display: flex; align-items: center; justify-content: space-between; cursor: pointer; padding: 6px 0; border-top: 1px solid #2a3040; margin-top: 6px; }
.op-otf-title { font-size: 11px; font-weight: 600; color: #8fa3bb; }
.op-otf-body { padding-top: 5px; display: flex; flex-direction: column; gap: 3px; }
.op-otf-row { display: flex; justify-content: space-between; font-size: 10px; padding: 2px 0; }
.op-otf-lbl { color: #8fa3bb; }
.op-otf-val { color: #f0f4ff; }
.op-otf-val.op-disc { color: #00b050; }
.op-sum-divider { height: 1px; background: #2a3040; margin: 8px 0; }
.op-promo-row { display: flex; gap: 5px; margin-bottom: 7px; }
.op-promo-row input { font-size: 10px; padding: 4px 7px; border-radius: 4px; flex: 1; }
.op-promo-row button { font-size: 10px; padding: 4px 8px; background: transparent; border: 1px solid #3a4255; color: #8fa3bb; border-radius: 4px; cursor: pointer; }
.op-checkout-btn { width: 100%; padding: 10px; background: #1a8cff; color: #fff; font-size: 12px; font-weight: 700; border: none; border-radius: 5px; cursor: default; margin-top: 10px; }
.op-save-link { display: block; text-align: center; color: #1a8cff; font-size: 11px; margin-top: 7px; text-decoration: underline; cursor: pointer; }
.op-help-box { border: 1px solid #2a3040; border-radius: 6px; padding: 12px; margin-top: 10px; text-align: center; }
.op-help-title { font-size: 13px; font-weight: 700; color: #f0f4ff; margin-bottom: 5px; }
.op-help-link { color: #1a8cff; font-size: 11px; text-decoration: underline; display: block; margin-bottom: 5px; }
.op-help-desc { font-size: 10px; color: #8fa3bb; line-height: 1.5; margin-bottom: 7px; }
.op-help-btn { width: 100%; padding: 6px; background: transparent; border: 1px solid #3a4255; color: #f0f4ff; font-size: 11px; border-radius: 4px; cursor: pointer; }
```

---

## JS to add

Add these functions to the script block in `index.html`. Place them immediately before the existing `renderPreview()` function.

```javascript
// v2.0.17 Optum-fidelity preview helpers
const previewCheckedPackages = new Set();
let previewOtfOpen = true;

function getCustomAttr(d, name) {
  const attrs = (d && d.customAttributes) || [];
  const attr = attrs.find(a => a && String(a.name || '').trim() === name);
  return attr ? (attr.value || '') : '';
}

function previewCategoryLabel(viewTemplate) {
  if (!viewTemplate) return '';
  const t = String(viewTemplate).toLowerCase();
  if (t.includes('api')) return 'Application Programming Interface';
  if (t.includes('software')) return 'Software';
  return viewTemplate;
}

function previewFmt$(n) {
  const v = parseFloat(n);
  if (isNaN(v)) return '$0.00';
  return v === 0 ? '$0.00' : '$' + v.toFixed(2);
}

function previewFmtRange(mv) {
  const min = mv.minimumValue ?? 0;
  const max = mv.maximumValue;
  if (max === null || max === undefined || max === '' || Number(max) >= 999999999) {
    return `${Number(min).toLocaleString()}+ requests per month`;
  }
  return `${Number(min).toLocaleString()} \u2013 ${Number(max).toLocaleString()} requests per month`;
}

function previewFmtPrice(mv) {
  const price = parseFloat(mv.transactionUnitAmount ?? 0);
  const unit = mv.unit || '';
  if (price === 0) return unit || 'Included';
  return `${previewFmt$(price)}/${unit}`;
}

function getTopLevelOptionGroup(d, type) {
  const groups = (d && d.optionItems) || [];
  return groups.find(g => g && String(g.optionItemType || '').trim() === type) || null;
}

function renderOptumPreview() {
  if (!data) {
    previewBody.innerHTML = `<div class="empty">No JSON loaded.</div>`;
    return;
  }

  const packages = data.packages || [];
  const multi = previewCheckedPackages.size > 1;

  // Monthly total from checked packages
  let monthly = 0;
  previewCheckedPackages.forEach(i => {
    const pkg = packages[i];
    if (pkg && pkg.amount) monthly += parseFloat(pkg.amount) || 0;
  });

  // Option groups
  const implGroup  = getTopLevelOptionGroup(data, 'Implementations');
  const addonGroup = getTopLevelOptionGroup(data, 'Addons');
  const implItem   = implGroup  && implGroup.optionLineItems  && implGroup.optionLineItems[0]  ? implGroup.optionLineItems[0]  : null;
  const implAmt    = implItem   ? (parseFloat(implItem.amount) || 0) : 0;
  const implDisc   = multi ? implAmt : 0;
  const implNet    = implAmt - implDisc;
  const addonCount = addonGroup && addonGroup.optionLineItems ? addonGroup.optionLineItems.length : 0;

  // Discount tooltips from customAttributes
  const discountTooltip = getCustomAttr(data, 'packageMonthlySummaryDiscountToolTip');
  const implWaiverTooltip = getCustomAttr(data, 'implementationSummaryDiscountToolTip');

  // Package cards HTML
  const pkgCardsHtml = packages.map((pkg, i) => {
    const sel = previewCheckedPackages.has(i);
    const name = esc(pkg.name || pkg.internalName || 'Package');
    const priceDesc = esc(pkg.amountDescription || '');
    const subtitle = esc(pkg.marketingTitle || '');
    const bands = (pkg.monthlyVolumes || []).map(mv =>
      `<div class="op-tier-row">
        <span class="op-tier-range">${esc(previewFmtRange(mv))}</span>
        <span class="op-tier-dots"></span>
        <span class="op-tier-price">${esc(previewFmtPrice(mv))}</span>
      </div>`
    ).join('');
    return `<div class="op-pkg-card${sel ? ' op-sel' : ''}" data-pkgidx="${i}">
      <div class="op-pkg-cb">
        <svg class="op-pkg-ck" width="9" height="9" viewBox="0 0 10 10" fill="none">
          <path d="M1.5 5l2.5 2.5 4.5-4.5" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </div>
      <div class="op-pkg-left">
        <div class="op-pkg-name">${name}</div>
        <div class="op-pkg-price">${priceDesc}</div>
        <div class="op-pkg-sub">${subtitle}</div>
      </div>
      <div class="op-pkg-right">${bands}</div>
    </div>`;
  }).join('');

  // Implementation section HTML
  const implHtml = implGroup ? `
    <div class="op-section-divider"></div>
    <div class="op-h2">Implementation</div>
    <div class="op-body-text">${implGroup.headerDescription || ''}</div>
    ${multi && implWaiverTooltip ? `<div class="op-body-text">${implWaiverTooltip}</div>` : ''}
    <div class="op-section-sublabel" style="margin-bottom:6px">Required with your package</div>
    <div class="op-impl-card">
      <div>
        <div class="op-impl-name">${esc(implItem ? (implItem.internalName || '') : '')}</div>
        <div class="op-impl-desc">${implItem ? (implItem.longDescription || implItem.shortDescription || '') : ''}</div>
      </div>
      <div class="op-impl-price-col">
        ${multi ? `<div class="op-impl-orig">${previewFmt$(implAmt)}</div>` : ''}
        <div class="op-impl-new">${multi ? '$0.00' : previewFmt$(implAmt)}</div>
        <div class="op-impl-unit">${esc(implItem ? (implItem.unit || 'one-time fee') : 'one-time fee')}</div>
      </div>
    </div>` : '';

  // Add-ons section HTML
  const addonHtml = addonGroup ? `
    <div class="op-section-divider"></div>
    <div class="op-h2">Add-ons</div>
    <div class="op-section-sublabel">Add-ons available with your package</div>
    <div class="op-body-text">${addonGroup.headerDescription || ''}</div>
    <div class="op-addon-row">
      <div class="op-addon-row-label">${addonCount} Add-on option${addonCount !== 1 ? 's' : ''}</div>
      <div class="op-addon-expand-btn">
        <svg width="9" height="9" viewBox="0 0 10 10" fill="none">
          <path d="M2 4l3 3 3-3" stroke="white" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
      </div>
    </div>` : '';

  // Order Summary HTML
  const otfBodyStyle = previewOtfOpen ? 'display:flex;flex-direction:column;gap:3px' : 'display:none';
  const otfArrowStyle = previewOtfOpen ? 'transform:rotate(180deg)' : '';
  const summaryHtml = `
    <div class="op-summary-box">
      <div class="op-summary-title">Order summary</div>
      <div class="op-costs-head">
        <span>Monthly costs</span>
        <svg width="11" height="11" viewBox="0 0 11 11" fill="none"><path d="M2 4l3 3 3-3" stroke="#8fa3bb" stroke-width="1.4" stroke-linecap="round"/></svg>
      </div>
      <div class="op-sum-row"><span class="op-sum-lbl">Est. monthly payment:</span><span class="op-sum-val op-big">${previewFmt$(monthly)}</span></div>
      <div style="height:6px"></div>
      <div class="op-sum-row" style="padding-bottom:2px"><span class="op-sum-lbl" style="font-weight:700;color:#f0f4ff;font-size:11px">Selected Add-Ons</span></div>
      <div class="op-sum-row"><span class="op-sum-lbl">Included Add-Ons</span><span class="op-sum-val" style="font-size:10px">Based on Usage*</span></div>
      <div class="op-sum-row"><span class="op-sum-lbl">Your Add-on costs</span><span class="op-sum-val">&mdash;</span></div>
      <div class="op-sum-row"><span class="op-sum-lbl">Monthly subtotal:</span><span class="op-sum-val">${previewFmt$(monthly)}</span></div>
      <div class="op-otf-head" id="opOtfHead">
        <span class="op-otf-title">One-time fees</span>
        <svg id="opOtfArrow" width="11" height="11" viewBox="0 0 11 11" fill="none" style="${otfArrowStyle};transition:transform .2s"><path d="M2 4l3 3 3-3" stroke="#8fa3bb" stroke-width="1.4" stroke-linecap="round"/></svg>
      </div>
      <div id="opOtfBody" style="${otfBodyStyle}">
        <div style="font-size:10px;font-weight:700;color:#8fa3bb;margin-bottom:2px">Selected Implementation</div>
        <div class="op-otf-row"><span class="op-otf-lbl" style="font-size:10px">${esc(implItem ? (implItem.internalName || '') : 'Implementation Fee')}</span></div>
        <div class="op-otf-row"><span class="op-otf-lbl">List price</span><span class="op-otf-val">${previewFmt$(implAmt)}</span></div>
        ${multi ? `<div class="op-otf-row"><span class="op-otf-lbl" style="color:#00b050">100% off discount</span><span class="op-otf-val op-disc">-${previewFmt$(implDisc)}</span></div>` : ''}
        <div class="op-otf-row" style="border-top:1px solid #2a3040;margin-top:3px;padding-top:3px"><span class="op-otf-lbl">Your Implementations costs</span><span class="op-otf-val">${previewFmt$(implNet)}</span></div>
        <div class="op-otf-row"><span class="op-otf-lbl">One-time fees subtotal</span><span class="op-otf-val">$0.00</span></div>
      </div>
      <div class="op-sum-divider"></div>
      <div class="op-promo-row">
        <input placeholder="Enter Promo Code" style="font-size:10px;padding:4px 7px;border-radius:4px;flex:1">
        <button>Apply</button>
      </div>
      <div class="op-sum-row"><span class="op-sum-lbl">Initial payment:</span><span class="op-sum-val op-big">$0.00</span></div>
      <button class="op-checkout-btn">Continue to checkout</button>
      <div class="op-save-link">Save changes</div>
    </div>
    <div class="op-help-box">
      <div class="op-help-title">Need help?</div>
      <a class="op-help-link">You may find what you need in our FAQs</a>
      <div class="op-help-desc">Or contact us for questions about quotes, implementation, or for other help.</div>
      <button class="op-help-btn">Contact us</button>
    </div>`;

  // Build full preview HTML
  previewBody.innerHTML = `
    <div class="op-preview-wrap">
      <div class="op-preview-cols">
        <div class="op-preview-left">
          <div class="op-cat-label">${esc(previewCategoryLabel(data.viewTemplate))}</div>
          <div class="op-h1">${esc(data.name || 'Unnamed Product')}</div>
          <div class="op-h2">Build your package</div>
          <div class="op-body-text">${data.headerDescription || ''}</div>
          <div class="op-notice-text">Pricing shown is for partners only.</div>
          <div class="op-notice-text" style="margin-bottom:8px">If your volume levels are higher, OR you are a provider, <a href="#">contact us</a> to receive a private quote from our sales team.</div>
          ${discountTooltip ? `<div class="op-discount-text">${discountTooltip}</div>` : ''}
          <div id="opPkgCards">${pkgCardsHtml}</div>
          ${implHtml}
          ${addonHtml}
          ${data.paymentSchedule ? `<div class="op-payment-notice">${data.paymentSchedule}</div>` : ''}
        </div>
        <div class="op-preview-right">${summaryHtml}</div>
      </div>
    </div>`;

  // Bind package card click handlers
  previewBody.querySelectorAll('.op-pkg-card').forEach(card => {
    card.addEventListener('click', () => {
      const idx = parseInt(card.dataset.pkgidx, 10);
      if (previewCheckedPackages.has(idx)) {
        previewCheckedPackages.delete(idx);
      } else {
        previewCheckedPackages.add(idx);
      }
      renderOptumPreview();
    });
  });

  // Bind OTF accordion
  const otfHead = document.getElementById('opOtfHead');
  if (otfHead) {
    otfHead.addEventListener('click', () => {
      previewOtfOpen = !previewOtfOpen;
      renderOptumPreview();
    });
  }
}
```

---

## Replace `renderPreview()`

Find the existing `function renderPreview()` in the script block and replace it entirely with:

```javascript
function renderPreview() {
  if (currentPreview === "json" && !document.body.classList.contains("preview-mode")) {
    previewBody.innerHTML = `<pre class="code">${esc(JSON.stringify(data, null, 2))}</pre>`;
    return;
  }
  renderOptumPreview();
}
```

That's the entire replacement. The JSON tab behavior stays the same. All Optum preview rendering is delegated to `renderOptumPreview()`.

---

## Additional fixes in this version

While making the above changes, also fix these three small issues found during code review:

**1. HTML title version** — find `<title>Pricing Editor v2.0.15</title>` and change to `<title>Pricing Editor v2.0.17</title>`

**2. Hardcoded download filename** — find `downloadJson()`. The line that builds the filename currently has `_v2_0_16_` hardcoded. Replace the hardcoded version string with a JS constant. Add this near the top of the script block near other constants:
```javascript
const APP_VERSION_JS = "v2_0_17";
```
Then replace the hardcoded `_v2_0_16_` in the download filename with `_${APP_VERSION_JS}_`.

**3. Misleading save warning alert** — find `shouldWarnBeforeSave()`. The alert text says "Use Download JSON only if you need an emergency local copy." Replace that sentence with: "Fix validation errors before saving."

---

## Change log entry

Add this at the top of the existing change log comment block:

```
v2.0.17
- Replaced generic card-based preview with Optum-fidelity pricing page replica
- Preview now shows: category label, product name, header description (HTML),
  discount tooltip, package cards with dotted leader tier rows, implementation
  section with conditional 2+ package waiver logic, add-ons accordion,
  order summary with live monthly subtotal, one-time fees accordion
- Package checkboxes toggle and update order summary live
- headerDescription, optionGroup headers, discount tooltips render as innerHTML
- Fixed HTML title still showing v2.0.15
- Fixed hardcoded _v2_0_16_ in download filename
- Fixed misleading save warning alert text
```

---

## What NOT to change

- Do not touch any editor sections (Metadata, Packages, Contract Terms, Option Items, Custom Attrs, Validation, Compare, Raw JSON, Save)
- Do not touch panel resizing, splitter logic, or collapse behavior
- Do not touch the nav, topbar, or statusbar
- Do not touch `main.py`
- Do not touch `saveVersion()`, `downloadJson()` logic (other than the version string fix above), `validateData()`, `discardChanges()`, or `loadJson()`
- Do not add new npm dependencies or external JS libraries
- Do not split into multiple files

---

## Acceptance criteria

1. Loading a JSON file shows the Optum-fidelity preview in the preview panel
2. Product name in preview matches `data.name`
3. Header description renders as HTML (bold tags display as bold, not as literal `<b>`)
4. Discount tooltip appears below the partner pricing notices
5. Each package in `data.packages` renders as a card with checkbox, green price description, subtitle, and dotted tier rows
6. Clicking a package card toggles its checkbox and updates the Order Summary monthly subtotal
7. When 2 or more packages are checked: the impl waiver tooltip appears, the impl price shows strikethrough + $0.00, and the Order Summary one-time fees show 100% off discount
8. When fewer than 2 packages are checked: no waiver text, impl shows full amount
9. One-time fees accordion opens and closes on click
10. JSON tab still shows raw JSON
11. HTML title shows `v2.0.17`
12. Download filename contains `v2_0_17` not `v2_0_16`
13. Python syntax check on `main.py` still passes (unchanged)
14. No console errors on page load or during editing

---

## Files

Attach `index_v2_0_16_combined.html` when sending this to ChatGPT. `main.py` does not need to be attached.
