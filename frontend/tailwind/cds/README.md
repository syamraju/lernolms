# Cloudscape (CDS) theme layer

The Learno UI is Cloudscape Design System applied over frappe-ui. Nothing in
`src/components` or `src/pages` knows about Cloudscape — the theme is three
generated/authored stylesheets that re-point frappe-ui's own design tokens.

**Figma source:** [CDS Component Library 2.0.2 (Community)][figma] —
file key `fZ2UxXNEQ9EAEgNtOT7yB1`.

[figma]: https://www.figma.com/design/fZ2UxXNEQ9EAEgNtOT7yB1/CDS-Component-Library-2.0.2--Community-

## Why a token layer instead of editing components

The app renders through frappe-ui's semantic tokens almost everywhere: 1143
uses of `bg-surface-*` / `text-ink-*` / `border-outline-*` against 39 hardcoded
colours (all since retokenised). Re-pointing the variables therefore re-skins
every screen at once, and the 235 component files stay untouched and
upgradeable.

## Files

| Path | Kind | What it does |
|---|---|---|
| `cds-source.json` | data | CDS tokens extracted from Figma: palette, semantic colours (light/dark), spacing, radii, border widths, shadows, typography |
| `type-scale.mjs` | data | The type ramp, shared by the Tailwind config and the typography generator |
| `generate-tokens.mjs` | generator | → `src/styles/cds-tokens.css` |
| `generate-typography.mjs` | generator | → `src/styles/cds-typography.css` |
| `render-logo.py` | generator | → the Learno mark as PNG (favicon, Apple touch icon, desk icon) |
| `../../src/styles/cds-components.css` | hand-written | Component *shape* — pill buttons, outlined inputs, container cards, tab underlines |

Regenerate everything:

```bash
node tailwind/cds/generate-tokens.mjs && node tailwind/cds/generate-typography.mjs && python3 tailwind/cds/render-logo.py
```

## How the three layers reach the UI

**Colour, radius, elevation** — `cds-tokens.css` re-declares all 406 themed
custom properties frappe-ui emits, plus the raw palette as `--<hue>-<step>`.
It is imported after `frappe-ui/style.css` in `src/index.css`, so it wins on
source order at equal specificity.

**Typography** — split, because frappe-ui splits it across two Tailwind layers:

- `text-<size>` / `text-p-<size>` are *utilities* built from `theme.fontSize`.
  Utilities outrank components, so these can only be changed from
  `tailwind.config.js` (which imports `type-scale.mjs`).
- `text-<size>-<weight>` are *components* registered with `addComponents` from
  frappe-ui's own generated JSON — unreachable from the theme, so
  `cds-typography.css` re-declares them.

**Shape** — `cds-components.css`. frappe-ui's Button renders Tailwind utilities
directly and exposes no stable hook, so the selectors anchor on the class list
`Button.vue` always emits and read the variant off the background utility it
picked. That is a deliberate coupling to frappe-ui internals; the alternative is
forking Button.vue and everything that wraps it.

## The upgrade risk, and what catches it

Both couplings are to things frappe-ui does not treat as public API:

1. the set of themed variables it declares, and
2. `Button.vue`'s emitted class list.

If either moves, the app doesn't break — it renders half-Espresso,
half-Cloudscape, which is easy to miss. `src/tests/cdsTheme.test.ts` pins both:
it enumerates frappe-ui's generated token data and asserts every variable is
overridden in *both* modes, and it asserts the button class contract against the
real `Button.vue` source. Run it after any frappe-ui bump.

## Mapping decisions worth knowing

- **Primary button.** frappe-ui's `solid` button is near-black; Cloudscape's
  primary is blue. Both `gray-solid` and `blue-solid` map onto CDS primary, so
  the main action on each screen reads as a CDS primary.
- **Ghost buttons stay neutral.** Cloudscape's *inline* icon button is blue, but
  frappe-ui uses `ghost` for toolbar and sidebar chrome too; recolouring all of
  it would turn every affordance into an accent.
- **`semibold` → 700.** Cloudscape uses two weights, 400 and 700. Every heading
  in this codebase is written `-semibold`, so semibold maps to CDS's 700 and
  those headings render as real CDS headings. `medium` keeps 500.
- **Grey is hand-mapped.** CDS ships a 19-step grey scale; a naive 10-step slice
  skips the exact greys Cloudscape uses for dividers and body text.
- **Type is quantised, not interpolated.** CDS defines eight sizes with px
  leading, so `xs`/`sm` both land on 12/16 and `md`/`lg` both on 16/20.
- **Destructive buttons keep red.** CDS has no red button, and a blue "Delete"
  would be worse.
