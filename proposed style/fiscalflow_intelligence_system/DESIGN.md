---
name: FiscalFlow Intelligence System
colors:
  surface: '#f8f9ff'
  surface-dim: '#cbdbf5'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d3e4fe'
  on-surface: '#0b1c30'
  on-surface-variant: '#45474c'
  inverse-surface: '#213145'
  inverse-on-surface: '#eaf1ff'
  outline: '#75777d'
  outline-variant: '#c5c6cd'
  surface-tint: '#545f73'
  primary: '#091426'
  on-primary: '#ffffff'
  primary-container: '#1e293b'
  on-primary-container: '#8590a6'
  inverse-primary: '#bcc7de'
  secondary: '#006c49'
  on-secondary: '#ffffff'
  secondary-container: '#6cf8bb'
  on-secondary-container: '#00714d'
  tertiary: '#001815'
  on-tertiary: '#ffffff'
  tertiary-container: '#002f29'
  on-tertiary-container: '#00a292'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d8e3fb'
  primary-fixed-dim: '#bcc7de'
  on-primary-fixed: '#111c2d'
  on-primary-fixed-variant: '#3c475a'
  secondary-fixed: '#6ffbbe'
  secondary-fixed-dim: '#4edea3'
  on-secondary-fixed: '#002113'
  on-secondary-fixed-variant: '#005236'
  tertiary-fixed: '#71f8e4'
  tertiary-fixed-dim: '#4fdbc8'
  on-tertiary-fixed: '#00201c'
  on-tertiary-fixed-variant: '#005048'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.02em
  display-lg-mobile:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 34px
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  title-sm:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  data-mono:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
  label-caps:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '700'
    lineHeight: 16px
    letterSpacing: 0.05em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  container-max: 1440px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 32px
  density-high: 8px
  density-medium: 16px
---

## Brand & Style
The design system is engineered for "Financial Trust," targeting the sophisticated Indian investor and high-net-worth individuals who require high-density data clarity. The brand personality is authoritative, precise, and secure, moving away from consumer "fintech-lite" aesthetics toward a professional-grade intelligence platform.

The visual style is **Corporate / Modern** with a focus on **Minimalism**. It utilizes a structured hierarchy, ample but controlled whitespace to manage cognitive load, and a rigorous adherence to grid systems. Every pixel serves a functional purpose, evoking the reliability of a high-end banking terminal combined with the sleekness of modern SaaS.

## Colors
The palette is rooted in Deep Indigo and Navy to establish a foundation of security and institutional stability. 

- **Primary & Foundation:** Deep Indigo (#1E293B) is used for primary navigation and text, while Navy (#0F172A) provides structural contrast for sidebars or dark-mode surfaces.
- **Semantic Indicators:**
    - **Success (Income/Growth):** Emerald Green (#10B981) for positive cash flow and savings targets.
    - **Investment:** Teal (#14B8A6) distinguishes market-linked assets from standard liquid cash.
    - **Alerts (Expense/Debt):** Rose (#E11D48) signals immediate attention for leaks; Amber (#F59E0B) indicates pending debts or warnings.
- **Neutrals:** A range of Slate grays (#64748B) and soft off-whites (#F8FAFC) are used to create "data surfaces" that minimize eye strain during long sessions of financial analysis.

## Typography
This design system utilizes **Inter** exclusively for its exceptional legibility and support for tabular figures (`tnum`). In a data-rich environment, the ability to align Indian Rupee (₹) amounts vertically is critical for scanning speed.

- **Numerical Precision:** All currency displays must use the `data-mono` role to ensure characters occupy equal horizontal space, preventing "jumping" during real-time data updates.
- **Scale:** The scale is tight and efficient. Large display sizes are reserved for "Net Worth" or "Total Balance" overviews, while the majority of the interface operates on `body-sm` and `label-caps` to maximize information density.
- **Weights:** Heavy weights (700) are used sparingly for section headers; medium weights (500-600) are preferred for interactive labels.

## Layout & Spacing
The layout follows a **Fixed Grid** philosophy for desktop (12-column) to maintain predictable data visualization widths, transitioning to a fluid model for mobile.

- **Rhythm:** A 4px baseline grid ensures vertical consistency. 
- **Density:** High-density views (tables, transaction lists) use an 8px spacing unit. Lower-density views (onboarding, settings) use 16px or 24px units.
- **Responsive Strategy:** 
    - **Desktop (>1024px):** 12 columns, 24px gutters. Side navigation is persistent.
    - **Tablet (768px - 1023px):** 8 columns, 16px gutters. Side navigation collapses to icons.
    - **Mobile (<767px):** 4 columns, 16px margins. Content stacks vertically; charts switch to simplified sparklines.

## Elevation & Depth
To maintain a professional, "flat" aesthetic that emphasizes data over decoration, this design system uses **Low-contrast outlines** and **Tonal layers** rather than heavy shadows.

- **Surface Levels:** 
    - **Level 0 (Background):** Slate-50 (#F8FAFC) – The base canvas.
    - **Level 1 (Cards/Containers):** White (#FFFFFF) with a 1px border in Slate-200 (#E2E8F0).
    - **Level 2 (Modals/Popovers):** White (#FFFFFF) with a subtle ambient shadow (0px 4px 20px rgba(0, 0, 0, 0.05)) to provide focus without breaking the minimalist aesthetic.
- **Interactive States:** Hovering over a clickable card should trigger a transition to a Slate-100 background or a slightly darker border color, never a "lift" effect.

## Shapes
The shape language is **Soft (0.25rem)**. This subtle rounding provides a modern touch while maintaining a disciplined, architectural feel. 

- **Standard Elements:** Buttons, input fields, and checkboxes use the base 4px radius.
- **Large Elements:** Dashboard cards and modal containers may use `rounded-lg` (8px) to soften the large surface areas.
- **Pill Tags:** Status badges (e.g., "Verified", "Pending") are the only elements permitted to be fully rounded to distinguish them from actionable buttons.

## Components
- **Data Tables:** High-contrast borders. Header row in Slate-100 with `label-caps` text. Cell text uses `data-mono` for currency. Every second row uses a faint zebra stripe (#F1F5F9).
- **Cards:** White background, 1px Slate-200 border. No shadows. Card headers include an icon slot (20px) and a "more options" menu.
- **Status Badges:** 
    - **Transfer:** Indigo background/white text. 
    - **Investment:** Teal background/white text. 
    - **Expense:** Rose background/white text.
- **Input Fields:** 1px border (#CBD5E1). Focus state uses a 1px solid Navy (#0F172A) border with no outer glow. Support for Rupee prefix (₹) is mandatory in all amount fields.
- **Buttons:** 
    - **Primary:** Deep Indigo background, white text, no gradient.
    - **Secondary:** Transparent background, 1px Slate-300 border, Navy text.
- **Charts:** Use thin stroke widths (2px) for line charts. Area charts use a 10% opacity fill of the stroke color. Grid lines must be Slate-100 and dotted.