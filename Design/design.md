# Design System: Microsoft Fluent

## 1. Visual Theme & Atmosphere

Microsoft's design language — the **Fluent Design System (Fluent 2)** — is an expression of calm productivity and human possibility. Microsoft's visual presence is inclusive and action-oriented: a window into a world where technology amplifies human capability. The register is accessible and deliberately welcoming — a workplace that invites rather than impresses.

The design philosophy rests on four core principles: **Light** (luminous surfaces that guide and delight), **Depth** (spatial layering that communicates hierarchy), **Motion** (purposeful animation that gives objects a sense of physics), and **Material** (translucent, layered surfaces that create immersive environments). These manifest as the Acrylic and Mica material effects, a systematic token-based elevation scale, and a neutral palette that adapts gracefully between light and dark modes.

Typography is carried by **Segoe UI Variable** — Microsoft's variable font with three optical size instances. The Display instance (36px+) uses wider proportions and higher stroke contrast optimised for large rendering; the Text instance (14–36px) strikes a balance for interface copy; the Small instance (below 14px) produces denser, sturdier forms for labels and captions. Segoe runs at **neutral letter-spacing throughout** — hierarchy is established through weight contrast and scale. On the web, the stack falls back to `Segoe UI` followed by system fonts.

The color story is built on **pure white and layered neutrals**. Section backgrounds step between white (`#ffffff`), off-white (`#fafafa`), and light gray (`#f3f2f1`), creating calm stratified paging. The sole branded accent — **Microsoft Blue** (`#0078d4`) — governs CTAs, links, and focus rings. Fluent also carries a full semantic palette: green for success, amber for warning, red for error — giving the system rich contextual expressiveness beyond the core neutral foundation.

**Key Characteristics:**
- Segoe UI Variable with three optical instances — Display, Text, and Small adapt letterform anatomy to size context
- Layered neutral foundation: white → `#fafafa` → `#f3f2f1` → `#ebebeb` as surfaces step up in elevation
- Microsoft Blue (`#0078d4`) as the primary interactive accent, supplemented by semantic status colors
- Acrylic and Mica materials for overlay depth — translucent + blurred surfaces with controlled tinting
- Generous line-heights (1.20–1.25 for headings, 1.60 for body) — prioritises readability over cinematic compression
- Systematic two-layer shadow scale: directional lift + ambient base across six elevation levels
- Rounded-rectangle geometry: 4px base radius for app components, 20–24px for marketing pill CTAs
- Content-forward, 12-column grid layout — product content alongside copy, not product-as-sole-hero

## 2. Color Palette & Roles

### Brand & Interactive
- **Microsoft Blue** (`#0078d4`): `--colorBrandBackground` — Primary CTA fills, links, active UI states. The only interactive accent.
- **Brand Hover** (`#106ebe`): `--colorBrandBackgroundHover` — Hover state on blue elements (darkened by ~8%).
- **Brand Pressed** (`#005a9e`): `--colorBrandBackgroundPressed` — Pressed/active confirmation state.
- **Brand Tint** (`#deecf9`): `--colorBrandBackground2` — Selection highlights, badge fills, low-emphasis tinted surfaces.

### Neutral Surfaces
- **White** (`#ffffff`): `--colorNeutralBackground1` — Primary page background, resting card surface.
- **Near White** (`#fafafa`): `--colorNeutralBackground2` — Subtle hover tint on transparent interactive elements; soft alternate sections.
- **Light Gray** (`#f5f5f5`): `--colorNeutralBackground3` — Alternate section backgrounds, disabled input fills.
- **Soft Gray** (`#ebebeb`): `--colorNeutralBackground4` — Pressed surface states, stronger section delineation.
- **Medium Gray** (`#e0e0e0`): `--colorNeutralBackground5` — Track fills, heavier dividers.
- **Dark Surface** (`#1f1f1f`): Primary dark-mode page background — notably **not** pure black; retains warmth.

### Stroke & Border
- **Default Stroke** (`#d1d1d1`): `--colorNeutralStroke1` — Borders on cards, inputs, table cells at rest.
- **Subtle Stroke** (`#ebebeb`): `--colorNeutralStroke2` — Hairline section dividers, grouped field separators.
- **Accessible Stroke** (`#616161`): `--colorNeutralStrokeAccessible` — Borders satisfying a 3:1 WCAG contrast ratio.

### Text
- **Primary Text** (`#242424`): `--colorNeutralForeground1` — Headlines and primary body copy. Near-black with warmth; not pure black.
- **Secondary Text** (`#616161`): `--colorNeutralForeground2` — Supporting copy, metadata, UI labels.
- **Tertiary Text** (`#8a8a8a`): `--colorNeutralForeground3` — Hints, placeholder text, helper descriptions.
- **Disabled Text** (`#bdbdbd`): `--colorNeutralForegroundDisabled` — Disabled and inactive states.
- **White** (`#ffffff`): Text on dark or filled-blue surfaces.
- **Brand Text** (`#0078d4`): Inline link color on white backgrounds — consistent with the brand accent.

### Semantic Status
- **Error** (`#bc2f32`): `--colorStatusDangerForeground1` — Inline error messages, destructive action labels.
- **Error Background** (`#fff0f0`): `--colorStatusDangerBackground1` — Error state fills, callout backgrounds.
- **Success** (`#107c10`): `--colorStatusSuccessForeground3` — Positive confirmations, completion indicators.
- **Success Background** (`#f1faf1`): `--colorStatusSuccessBackground1` — Success state fills.
- **Warning** (`#f7630c`): `--colorStatusWarningForeground1` — Caution indicators, expiry notices.
- **Warning Background** (`#fff8e1`): `--colorStatusWarningBackground1` — Warning state fills.
- **Info**: Falls back to brand blue (`#0078d4`) for informational status context.

### Shadows
- **Level 2** (`0px 1px 2px rgba(0,0,0,0.14), 0px 0px 2px rgba(0,0,0,0.12)`): Cards at rest, minimal elevation.
- **Level 4** (`0px 2px 4px rgba(0,0,0,0.14), 0px 0px 2px rgba(0,0,0,0.12)`): Hovered cards, open dropdowns.
- **Level 8** (`0px 4px 8px rgba(0,0,0,0.14), 0px 0px 2px rgba(0,0,0,0.12)`): Side panels, popovers.
- **Level 16** (`0px 8px 16px rgba(0,0,0,0.14), 0px 0px 2px rgba(0,0,0,0.12)`): Modals, toast notifications.
- **Level 28** (`0px 14px 28px rgba(0,0,0,0.12), 0px 0px 8px rgba(0,0,0,0.14)`): Teaching callouts, prominent global overlays.
- **Level 64** (`0px 32px 64px rgba(0,0,0,0.24), 0px 0px 8px rgba(0,0,0,0.10)`): Full-screen dialogs, maximum elevation.

## 3. Typography Rules

### Font Family
- **Primary**: `"Segoe UI Variable", "Segoe UI", system-ui, -apple-system, Helvetica Neue, Arial, sans-serif`
- **Display instance**: `"Segoe UI Variable Display"` — used at 36px+ for marketing headlines and product names
- **Text instance**: `"Segoe UI Variable Text"` — used at 14–36px for all interface and body copy
- **Small instance**: `"Segoe UI Variable Small"` — used below 14px for captions, labels, and legal text

### Hierarchy

| Role | Font Instance | Size | Weight | Line Height | Letter Spacing | Notes |
|------|---------------|------|--------|-------------|----------------|-------|
| Display Hero | Segoe UI Variable Display | 68px (4.25rem) | 600 | 1.20 | 0px | Flagship campaign headlines |
| Hero | Segoe UI Variable Display | 52px (3.25rem) | 600 | 1.20 | 0px | Standard marketing hero |
| H1 | Segoe UI Variable Display | 40px (2.50rem) | 600 | 1.25 | 0px | Page-level headings |
| H2 | Segoe UI Variable Display | 32px (2.00rem) | 600 | 1.25 | 0px | Section headings |
| H3 | Segoe UI Variable Text | 24px (1.50rem) | 600 | 1.33 | 0px | Sub-section headings |
| H4 | Segoe UI Variable Text | 20px (1.25rem) | 600 | 1.40 | 0px | Card titles, panel headings |
| H5 | Segoe UI Variable Text | 16px (1.00rem) | 600 | 1.50 | 0px | Small section labels, grouped UI |
| Body Large | Segoe UI Variable Text | 18px (1.125rem) | 400 | 1.60 | 0px | Hero supporting copy, intro paragraphs |
| Body | Segoe UI Variable Text | 16px (1.00rem) | 400 | 1.60 | 0px | Standard reading text |
| Body Strong | Segoe UI Variable Text | 16px (1.00rem) | 600 | 1.60 | 0px | Emphasised inline body text |
| Body Small | Segoe UI Variable Text | 14px (0.875rem) | 400 | 1.57 | 0px | Secondary content, metadata |
| Button Large | Segoe UI Variable Text | 16px (1.00rem) | 600 | 1.00 | 0px | Marketing pill CTA labels |
| Button | Segoe UI Variable Text | 14px (0.875rem) | 600 | 1.00 | 0px | App button labels — always semibold |
| Link | Segoe UI Variable Text | 16px (1.00rem) | 400 | 1.60 | 0px | Inline links, underlined on hover |
| Caption | Segoe UI Variable Small | 12px (0.75rem) | 400 | 1.67 | 0px | Labels, tags, timestamps |
| Caption Strong | Segoe UI Variable Small | 12px (0.75rem) | 600 | 1.67 | 0px | Emphasised captions, badge text |
| Overline | Segoe UI Variable Small | 12px (0.75rem) | 600 | 1.33 | 1.5px | All-caps section labels — the only context using positive tracked spacing |

### Principles
- **Optical sizing as engineering**: Segoe UI Variable shifts its internal glyph proportions across three instances — Display (higher stroke contrast, optimised for 36px+), Text (balanced, 14–36px), and Small (denser forms, below 14px). Always use the appropriate instance for the rendered size context.
- **Weight contrast as hierarchy**: Fluent Design uses weight contrast (400 vs 600) as the primary hierarchy signal. Regular at 400 reads cleanly; semibold at 600 creates unambiguous section breaks without aggression.
- **Neutral tracking always**: Segoe UI is engineered to run at 0px letter-spacing. Its proportions assume default spacing — do not apply negative tracking. The sole exception is the Overline role (+1.5px) for all-caps labels.
- **Generous line-heights**: Body at 1.60 creates substantial inter-line breathing room, prioritising sustained readability. Headlines sit at 1.20–1.25 — tight enough to read as a unit, open enough to remain comfortable at every size.
- **No weight extremes**: The effective range is 400 (regular) and 600 (semibold). Weight 700 (bold) appears only for select marketing display moments. Weights 800–900 do not exist in the system.

## 4. Component Stylings

### Buttons

**Primary (Microsoft Blue)**
- Background: `#0078d4`
- Text: `#ffffff`, 14–16px, weight 600
- Padding: 8px 20px (app) / 12px 28px (marketing)
- Radius: 4px (app) / 20–24px (marketing pill)
- Border: none
- Hover: `#106ebe`
- Pressed: `#005a9e`
- Focus: `2px solid #0078d4`, 2px offset
- Use: Primary CTA — "Get started", "Sign in", "Download"

**Secondary (Outline)**
- Background: transparent
- Text: `#0078d4`, weight 600
- Padding: 8px 20px
- Radius: 4px (app) / 20–24px (marketing pill)
- Border: 1px solid `#0078d4`
- Hover: background `#deecf9`
- Use: Alternate CTA, lower-emphasis parallel action

**Ghost / Subtle**
- Background: transparent
- Text: `#242424`, weight 600
- Hover: background `#f5f5f5`
- Use: Tertiary actions — "Cancel", contextual navigation links

**Danger**
- Background: `#bc2f32`
- Text: `#ffffff`
- Hover: `#a4262c`
- Use: Destructive confirmations — "Delete", "Remove"

**Text Link**
- Color: `#0078d4`
- No background, no border
- Underline: appears on hover
- Use: Inline "Learn more" links, navigation text links

### Cards & Containers
- Background: `#ffffff`
- Border: 1px solid `#d1d1d1` — Fluent uses visible containment strokes as structural signals
- Radius: 8px
- Shadow: Level 2 at rest (`0px 1px 2px rgba(0,0,0,0.14), 0px 0px 2px rgba(0,0,0,0.12)`)
- Hover: shadow lifts to Level 4 (`0px 2px 4px...`), optional `#fafafa` background tint
- Padding: 16–24px
- Content density: structured title / body / action-link hierarchy

### Navigation
- Background: `#ffffff` (solid opaque white — the navigation is grounded, not floating or blurred)
- Height: 48–56px
- Border-bottom: 1px solid `#ebebeb`
- Logo: Microsoft four-square logo + Segoe wordmark, left-aligned
- Text: `#242424`, Segoe UI Variable Text, 14px, weight 400
- Active state: `#0078d4` text color + 2px solid `#0078d4` bottom border
- Hover: `#f5f5f5` background on individual nav item
- Mobile: collapses to hamburger with a slide-in side drawer

### Acrylic Material (Overlay Depth)
- Background: `rgba(255, 255, 255, 0.7)` (light Acrylic) or `rgba(32, 32, 32, 0.7)` (dark Acrylic)
- Backdrop-filter: `blur(40px) saturate(180%)`
- Used for: panel overlays, dialog backdrops, flyout menus
- Not used for the main navigation bar (which is opaque white)

### Image Treatment
- Product screenshots rendered with Level 4–8 shadows, suggesting a floating interface layer
- Hero imagery favours inclusive, diverse people in collaborative or productive settings
- Content images use 8–12px rounded corners matching the component border-radius language
- Gradient hero backgrounds (blue-to-purple, blue-to-teal) are acceptable in marketing hero sections
- Product imagery on white cards uses the standard 1px `#d1d1d1` border and 8px radius
- No solid-black full-bleed photography backgrounds — the aesthetic is open, not cinematic

### Distinctive Components

**Product Hero Module**
- Background: white or a soft brand gradient (e.g. `linear-gradient(135deg, #0067b8 0%, #6264a7 100%)`)
- Headline: 52–68px, Segoe UI Variable Display, weight 600
- Supporting copy: 18px, weight 400, line-height 1.60, color `#616161` (or white on gradient bg)
- Two CTAs: filled blue pill primary + outline secondary
- Optional: product screenshot or illustration in the right column of a two-column layout

**Product Feature Card (3-up or 4-up Grid)**
- White card, 8px radius, 1px `#d1d1d1` border, Level 2 shadow
- Icon (48–64px, Microsoft-brand icon style) at top
- H4 heading: 20px, weight 600, `#242424`
- Body: 16px, weight 400, line-height 1.60, `#616161`
- "Learn more" link in `#0078d4` at bottom with hover underline
- Hover: shadow lifts to Level 4

**Feature Strip (Microsoft 365 / Copilot Style)**
- Full-width section with `#f3f2f1` alternate background
- Left column: headline + body + CTA block
- Right column: product screenshot or animation
- Alternating mirror layout on consecutive strips for visual rhythm

**Pricing / Comparison Table**
- White background with `#ebebeb` cell borders
- Highlighted recommended column: light blue fill (`#deecf9`) with `#0078d4` header
- Green checkmarks (`#107c10`) / red X marks (`#bc2f32`) for feature availability
- Used extensively on product and subscription pages

## 5. Layout Principles

### Spacing System
- **Base unit**: 4px (the Fluent grid unit)
- **Scale**: 2, 4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96, 128px
- The scale is composed exclusively of multiples of 4 — predictable, systematic, and free of fractional or arbitrary step values.
- Section padding: 64–80px vertical, 24–48px horizontal
- Component internal padding: 12–24px

### Grid & Container
- **Columns**: 12-column grid — supports a wide range of layout patterns from single-column editorial to complex multi-column product pages
- **Max content width**: ~1400px — a wide canvas that accommodates richer, denser content layouts while maintaining comfortable reading widths
- **Gutter**: 24px default
- **Layout patterns**: 2-up, 3-up, 4-up product card grids; alternating text+image feature strips; pricing and comparison tables
- Sections present a portfolio of features rather than a singular product moment. Full-viewport single-product immersion is not a Fluent layout pattern.

### Whitespace Philosophy
- **Productive breathing room**: Microsoft gives generous vertical space (64–80px section padding) but never commits an entire viewport to a single isolated product. The gesture is "here is everything you need" rather than "behold this one thing."
- **Tonal section alternation**: Sections step between white (`#ffffff`) and light gray (`#f3f2f1`) — calm, low-contrast transitions that guide the eye without disrupting reading flow.
- **Content density is a feature**: Fluent accepts more information per section. A marketing card can carry a title, two sentences of body copy, and a "Learn more" link without feeling overloaded. Density is organised, not compressed.

### Border Radius Scale
- **Micro (2px)**: Form field corners, tags, small inline indicators
- **Default (4px)**: All app-level buttons, inputs, and component containers
- **Medium (8px)**: Content cards, image containers, dashboard widgets
- **Large (12px)**: Modal dialogs, significant container panels
- **Marketing Pill (20–24px)**: Primary CTA buttons on marketing pages
- **Full Pill (9999px)**: Status badges, pill-shaped labels
- **Circle (50%)**: Avatars, circular icon buttons, media controls

## 6. Depth & Elevation

| Level | Token | Shadow | Use |
|-------|-------|--------|-----|
| Flat (0) | `--shadow0` | None | Standard page content, text blocks |
| Subtle (2) | `--shadow2` | `0px 1px 2px rgba(0,0,0,0.14), 0px 0px 2px rgba(0,0,0,0.12)` | Resting cards, grouped form inputs |
| Medium (4) | `--shadow4` | `0px 2px 4px rgba(0,0,0,0.14), 0px 0px 2px rgba(0,0,0,0.12)` | Hovered cards, open dropdown menus |
| Elevated (8) | `--shadow8` | `0px 4px 8px rgba(0,0,0,0.14), 0px 0px 2px rgba(0,0,0,0.12)` | Side panels, popovers, command bars |
| High (16) | `--shadow16` | `0px 8px 16px rgba(0,0,0,0.14), 0px 0px 2px rgba(0,0,0,0.12)` | Modals, toast notifications |
| Maximum (28) | `--shadow28` | `0px 14px 28px rgba(0,0,0,0.12), 0px 0px 8px rgba(0,0,0,0.14)` | Teaching callouts, prominent overlays |
| Global (64) | `--shadow64` | `0px 32px 64px rgba(0,0,0,0.24), 0px 0px 8px rgba(0,0,0,0.10)` | Full-screen dialogs, maximum layer |
| Acrylic | — | `rgba(255,255,255,0.7)` + `backdrop-filter: blur(40px) saturate(180%)` | Panel overlays, menu flyouts |
| Focus Ring | — | `2px solid #0078d4`, 2px offset | Keyboard focus on all interactive elements |

**Shadow Philosophy**: Fluent uses a systematic six-level shadow scale. Every shadow follows the same two-layer formula: a directional lift (y-offset increases with level) plus a fixed ambient base (2px blur at 12–14% opacity). Depth communicates function — an element's shadow level tells the user where it sits in the spatial hierarchy. Each element claims the elevation token appropriate to its layer.

### Decorative Depth
- **Navigation border**: The nav's 1px `#ebebeb` bottom border is its depth signal — the page ground plane. The nav is anchored, not floating.
- **Card hover animation**: Cards animate from Level 2 to Level 4 on hover, giving kinetic confirmation that the element is interactive before a click.
- **Acrylic overlays**: Overlapping panels use the Acrylic blur material to communicate layering without obscuring the underlying content — a metaphor for working in parallel.
- **Background stepping**: The neutral scale (`#ffffff` → `#fafafa` → `#f5f5f5` → `#ebebeb`) creates perceived depth through surface lightness differences, used for alternating sections and raised containers.

## 7. Do's and Don'ts

### Do
- Use Segoe UI Variable Display at 36px+ and Segoe UI Variable Text below — respect the optical size boundary
- Keep letter-spacing at 0px for all display and body text — Segoe is engineered to run at neutral spacing
- Use Microsoft Blue (`#0078d4`) for all primary interactive elements — links, CTAs, focus rings
- Apply the two-layer shadow formula at every elevation level — directional lift + fixed ambient base
- Use 1px `#d1d1d1` borders on cards — Fluent embraces visible containment and structure
- Alternate section backgrounds between `#ffffff` and `#f3f2f1` — subtle tonal steps, never stark contrast swings
- Use 4px radius as the default for app-level components; 20–24px for marketing pill CTAs
- Include semantic colors (green / amber / red) in status-relevant UI contexts — they are first-class citizens
- Use weight 600 (semibold) for headings and button labels — it is the primary hierarchy signal
- Apply hover shadow lift (Level 2 → Level 4) on interactive cards — interactivity must be communicated before a click

### Don't
- Don't apply negative letter-spacing to Segoe UI — it will look cramped and defeat the typeface's design intent
- Don't compress headline line-heights below 1.20 — Fluent text is airy and legible, never cinematic and squeezed
- Don't use `#000000` pure black as a page or section background — dark surfaces use `#1f1f1f` for warmth
- Don't blur or ghost the navigation bar — Microsoft's navigation is opaque white, grounded in the page plane
- Don't use only one shadow level for all components — apply the correct elevation token based on spatial role
- Don't skip card borders — the Fluent Design System uses visible containment strokes (`#d1d1d1`) as structural signals
- Don't apply gradients to text — gradients are reserved for decorative section backgrounds and illustration
- Don't use weight 800 or 900 — the effective range is 400 to 700; semibold (600) handles most hierarchy work
- Don't omit semantic colors in status contexts — using only neutral tones for errors/success removes critical meaning
- Don't create full-viewport single-product immersion sections — Fluent presents a portfolio of capabilities, not solitary product theatre

## 8. Responsive Behavior

### Breakpoints
| Name | Width | Key Changes |
|------|-------|-------------|
| Small Mobile | <320px | Minimum supported; single column, 16px minimum font |
| Mobile | 320–480px | Single column, full-width CTAs, stacked hero |
| Mobile Large | 480–640px | Wider single column, condensed 2-column cards |
| Tablet Small | 640–768px | 2-column grid begins, side-by-side hero layout |
| Tablet | 768–1024px | Full tablet layout, horizontal navigation visible |
| Desktop Small | 1024–1280px | Standard 12-column layout, standard spacing |
| Desktop | 1280–1440px | Full layout, comfortable reading width |
| Wide | >1440px | Centered with increased margins, max-width enforced at 1400px |

### Touch Targets
- Primary CTAs: minimum 44px touch height (padding ensures compliance)
- Navigation links: 44–48px active area
- Icon buttons: 40×40px minimum
- All interactive elements: compliant with WCAG 2.1 AA touch target requirements

### Collapsing Strategy
- Hero headlines: 68px Display → 52px → 40px → 32px on mobile, maintaining 1.20 line-height throughout
- Product grids: 4-column → 3-column → 2-column → single column
- Navigation: full horizontal nav → hamburger with side-drawer slide-in
- Feature strips: side-by-side text+image layout → stacked (image above text) on mobile
- Section backgrounds: maintain full-width alternating tones at all breakpoints
- CTAs: maintain pill shape at all sizes; may go full-width below 480px for thumb-friendly tapping

### Image Behavior
- Product screenshots maintain aspect ratio, scale down proportionally within their grid column
- Hero lifestyle images may use `object-fit: cover` for cropped contexts on mobile
- All images maintain the 8px rounded-corner language at every breakpoint
- Icons switch to text labels below critical breakpoints if container space is insufficient
- Lazy loading applied to all below-fold images

## 9. Agent Prompt Guide

### Quick Color Reference
- Primary CTA fill: Microsoft Blue (`#0078d4`)
- CTA hover: `#106ebe`
- CTA pressed: `#005a9e`
- CTA tint / selection: `#deecf9`
- Page background: `#ffffff`
- Alternate section: `#f3f2f1`
- Primary text: `#242424`
- Secondary text: `#616161`
- Link color: `#0078d4`
- Card border: `1px solid #d1d1d1`
- Card shadow (rest): `0px 1px 2px rgba(0,0,0,0.14), 0px 0px 2px rgba(0,0,0,0.12)`
- Card shadow (hover): `0px 2px 4px rgba(0,0,0,0.14), 0px 0px 2px rgba(0,0,0,0.12)`
- Focus ring: `2px solid #0078d4`, 2px offset
- Success: `#107c10` / Error: `#bc2f32` / Warning: `#f7630c`

### Example Component Prompts
- "Create a hero section on white background. Headline at 68px Segoe UI Variable Display weight 600, line-height 1.20, letter-spacing 0px, color #242424. Supporting copy at 18px Segoe UI Variable Text weight 400, line-height 1.60, color #616161. Two CTAs side-by-side: primary pill ('Get started', background #0078d4, white text, 20px radius, 12px 28px padding, 16px semibold) + secondary outline pill ('Learn more', transparent background, #0078d4 text, 1px solid #0078d4, same radius)."
- "Design a product feature card: white background, 8px border-radius, 1px solid #d1d1d1 border, shadow 0px 1px 2px rgba(0,0,0,0.14) 0px 0px 2px rgba(0,0,0,0.12). Icon 48px at top. Title at 20px Segoe UI Variable Text weight 600, color #242424. Body at 16px weight 400, line-height 1.60, color #616161, 16px padding. 'Learn more' link in #0078d4 at the bottom. Hover: shadow lifts to 0px 2px 4px rgba(0,0,0,0.14) 0px 0px 2px rgba(0,0,0,0.12)."
- "Build the Microsoft navigation: solid white background (#ffffff), 56px height, 1px solid #ebebeb bottom border. Microsoft four-square logo + Segoe wordmark left-aligned. Nav links at 14px Segoe UI Variable Text weight 400, #242424. Active link: color #0078d4 + 2px solid #0078d4 bottom border. Hover state: #f5f5f5 background on individual link."
- "Create an alternating feature strip layout: first section white (#ffffff) background, two-column grid — left column has 32px H2 (weight 600, #242424), 16px body copy (#616161, line-height 1.60), and a blue pill CTA; right column has product screenshot with 8px radius and Level 4 shadow. Second section #f3f2f1 background with mirrored layout. Each section 80px vertical padding, 1400px max-width."
- "Design a 3-up product card grid: each card is white, 8px radius, 1px solid #d1d1d1, shadow Level 2. Top: 48px icon. Below: H4 at 20px semibold #242424. Body at 16px regular #616161, 1.60 line-height. Footer: 'Learn more' text link in #0078d4 with underline on hover. 24px gutter between cards. Full-width section background #f3f2f1 with 64px vertical padding."

### Iteration Guide
1. Every interactive element gets Microsoft Blue (`#0078d4`) — CTAs, links, active states, and focus rings all share this single accent
2. Section backgrounds alternate between `#ffffff` and `#f3f2f1` — gentle tonal shift, never stark black-to-white contrast swings
3. Typography optical sizing: Segoe UI Variable Display at 36px+, Text instance for everything below — letter-spacing stays at zero always
4. Apply the two-layer shadow formula at the correct token level — directional lift + ambient base; never a single-blur shortcut
5. Cards carry both a 1px `#d1d1d1` border AND a Level 2 shadow at rest — the border defines containment, the shadow communicates elevation
6. Semantic colors (green / amber / red) are first-class citizens — deploy them in every status context without hesitation
7. Line-heights breathe: 1.20 minimum for headings, 1.60 for body — never compress below this floor
8. Focus rings on every interactive element: `2px solid #0078d4` with 2px offset — accessibility is architected in, not deferred