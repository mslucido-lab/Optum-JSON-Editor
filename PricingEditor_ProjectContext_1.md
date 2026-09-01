# Pricing Page JSON Editor — Project Context
*Created: 05/09/2026 — v1.0*

---

## Overview

The Pricing Page JSON Editor is a desktop utility for editing JSON files that drive product pricing pages on the Optum AI Marketplace. It is a standalone internal tool — not customer-facing, not connected to any database.

The tool replaces a manual JSON editing workflow (editing raw files in a text editor or similar) with a structured form-based UI that reduces errors and speeds up pricing page updates.

**Built with:**

| Layer | Technology |
|---|---|
| Frontend | Python / Streamlit |
| File I/O | Python standard library (json) |
| Hosting | Local — runs on developer's machine |
| Storage | JSON files on shared network drive |

---

## Background & Constraints

- Developer's work laptop is locked down — Reflex cannot be installed
- Streamlit installs cleanly via pip and is available
- This is a work tool, not a personal project — separate repo and project from Lucid Property Manager
- Zero budget — no paid tools or hosting
- No mobile support required
- No database — files are read from and written back to disk

---

## JSON Structure

The pricing page JSON has four meaningful layers:

### 1. Top-Level Metadata
Fields that describe the product globally:
- `name`, `description`, `slug` — product identity
- `catalogCode` — SKU-style identifier
- `viewTemplate` — controls page rendering template
- `maxQuantity` — purchase quantity cap
- `headerDescription` — HTML-supporting marketing copy shown at top of page
- `paymentSchedule` — notice text shown below pricing
- `toolTipText`, `toolTipDescription` — optional hover text
- `imageName` — product image reference
- `itemContact` — support email, subject line, email body content

### 2. Packages
Array of purchasable product tiers (5 in the sample file). Each package has:
- `internalName`, `name` — identity (internal vs. display)
- `marketingTitle`, `tagline`, `shortDescription`, `longDescription` — copy fields
- `toolTipDescription` — hover text
- `amount`, `amountDescription`, `unit` — base pricing
- `sortOrder` — display sequence
- `isDefault`, `isCountable`, `countableMin`, `countableMax` — behavior flags
- `includedModuleText` — supplemental copy
- `monthlyVolumes` — array of volume pricing bands (see below)
- `productItems` — array of catalog code references (read-through, not editable)
- `customAttributes` — package-level custom data (editable where present)
- `discountItems` — **not editable; preserved on save but never displayed**
- `optionItems` — package-level add-ons where present

### 3. Monthly Volume Bands (child of each Package)
Each package has 1–N volume bands defining tiered pricing:
- `internalName` — band identity
- `minimumValue`, `maximumValue` — transaction count range
- `amount`, `amountDescription` — flat amount for this band
- `transactionUnitAmount` — per-unit price
- `unit`, `subUnit`, `subUnitType`, `subUnitDescription` — unit labels
- `isDefault`, `sortOrder` — behavior and display order
- `discountItems` — **not editable; preserved on save**

### 4. Option Items (top-level)
Top-level array of supplemental line items grouped by type (e.g. Implementations, Addons). Each group has:
- `optionItemType` — group label (e.g. "Implementations", "Addons")
- `headerDescription`, `headerDescription2` — section copy
- `toolTipText`, `toolTipDescription` (and `2` variants) — hover text
- `optionLineItems` — array of individual line items, each with:
  - `internalName`, `marketingTitle`, `tagline`, `shortDescription`, `longDescription`
  - `amount`, `amountDescription`, `unit`, `subUnit`, `subUnitDescription`
  - `catalogCode`, `sortOrder`, `isDefault`, `isIncluded`, `isCountable`
  - `useTransactionUnitAmount` — flag
  - `eligiblePackages` — array of package references (read-through where present)
  - `discountItems` — **not editable; preserved on save**

### 5. Custom Attributes (top-level)
Array of key-value pairs used for tooltip content and display logic:
- `name` — attribute key
- `description` — label
- `value` — HTML-supporting content string
- `isRequired`, `displayFor`, `sortOrder` — behavior fields

---

## Discount Policy

**Discounts are not supported by this tool.**

`discountItems` arrays appear at multiple levels (packages, volume bands, option line items). They must be:
- Read from the source file on load
- Preserved exactly as-is in memory
- Written back to the output file unchanged on save

They are never displayed in the UI and never modified by the tool.

---

## UI Design

### Layout: Three-Panel

```
┌─────────────┬──────────────────────────┬────────────┐
│  Left Nav   │     Center Editor        │ JSON       │
│             │                          │ Preview    │
│  Metadata   │  Section-specific form   │            │
│  Packages   │  fields                  │  Live read-│
│  Option     │                          │  only view │
│  Items      │                          │  of output │
│  Custom     │                          │            │
│  Attrs      │                          │            │
│             │                          │            │
│  ─────────  │                          │            │
│  Validate   │                          │            │
└─────────────┴──────────────────────────┴────────────┘
```

### Navigation
- Left nav selects active section (Metadata / Packages / Option Items / Custom Attributes)
- Packages section uses horizontal tabs across the top of the editor panel — one tab per package

### Key UI Behaviors
- **Load file** — file picker that navigates to shared network drive path
- **Save file** — writes back to the same path; prompts for confirmation if overwriting
- **Unsaved changes indicator** — visible in header/status bar
- **JSON validity indicator** — always visible in status bar
- **JSON preview panel** — read-only, syntax-highlighted, updates as fields change
- **HTML field hint** — fields that support HTML tags (headerDescription, longDescription, etc.) are labeled as such
- **Add / remove volume bands** — inline within the package editor
- **Discard changes** — reloads from file, prompts for confirmation

### Fields That Are Read-Only (display only, not editable)
- `productItems` (catalogCode references within packages)
- `eligiblePackages` (within option line items)
- `discountItems` at all levels (hidden entirely)

---

## Workflow

1. Launch app (`streamlit run app.py`)
2. Click **Open File** → navigate to shared network drive → select JSON file
3. Edit fields across sections as needed
4. Review JSON preview panel before saving
5. Click **Save File** → file written back to original path
6. App confirms save; unsaved indicator clears

---

## File & Repo Conventions

- One Python file (`app.py`) — Streamlit app
- No database, no config file (file path selected at runtime via UI)
- Discount data preserved via a "passthrough" pattern: loaded into a separate dict, merged back at save time
- AI-managed versioning: new file per iteration with change log comment block at top of file

---

## Decisions Made

| Decision | Choice | Rationale |
|---|---|---|
| Framework | Streamlit | Reflex cannot install on locked-down work laptop; Streamlit installs via pip |
| Discount handling | Preserve, never display | Discounts not currently supported; hiding them prevents accidental edits |
| File storage | Shared network drive, path selected at runtime | No hardcoded paths — works across machines |
| JSON preview | Read-only right panel | Sanity check before save; reduces errors |
| Volume bands | Editable inline table with add/remove | Bands are the most numerically sensitive section; tabular layout reduces input errors |
| New file creation | Out of scope for v1 | Always starts from an existing file; new file creation deferred |
| Mobile support | Out of scope | Internal desktop tool only |

---

## Out of Scope (v1)

- Creating new JSON files from scratch
- Discount editing
- Version history / diff view
- CMS integration or API push
- Mobile layout
- Multi-file batch editing
- User authentication

---

## How to Work With Me

- I am a PM, not a developer. Lead with the "so what." Don't over-explain.
- I use a dual-AI workflow: Claude for architecture and review, ChatGPT for execution.
- When producing handoff docs for ChatGPT, be specific and implementation-ready.
- I will share the existing ChatGPT Streamlit prototype for reconciliation before any new code is written.
- Flag anything in the prototype that conflicts with the design decisions above.

---

*End of context.*
