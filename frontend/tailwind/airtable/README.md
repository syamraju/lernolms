# Airtable theme layer

The Learno UI is the Airtable Apps UI Kit applied over frappe-ui. Nothing in
`src/components` or `src/pages` knows about Airtable — the theme is three
generated/authored stylesheets that re-point frappe-ui's own design tokens.

**Figma source:** [Airtable Apps UI Kit (Community)][figma] — file key
`StoTaUKJ4FiEzEoOr4kW3N`.

[figma]: https://www.figma.com/design/StoTaUKJ4FiEzEoOr4kW3N/Airtable-Apps-UI-Kit--Community-

> Replaces the Cloudscape (CDS) layer that previously lived in `tailwind/cds/`.
> The architecture is unchanged; only the values and the component shapes moved.
> The commit before this one is the Cloudscape state, so `git revert` restores
> it wholesale.

## Why a token layer instead of editing components

The app renders through frappe-ui's semantic tokens almost everywhere
(`bg-surface-*` / `text-ink-*` / `border-outline-*`). Re-pointing the variables
therefore re-skins every screen at once, and the 235 component files stay
untouched and upgradeable.

## Files

| Path | Kind | What it does |
|---|---|---|
| `airtable-source.json` | data | Airtable tokens extracted from Figma: palette, semantic colours (light/dark), spacing, radii, border widths, shadows, typography |
| `type-scale.mjs` | data | The type ramp, shared by the Tailwind config and the typography generator |
| `generate-tokens.mjs` | generator | → `src/styles/airtable-tokens.css` |
| `generate-typography.mjs` | generator | → `src/styles/airtable-typography.css` |
| `render-logo.py` | generator | → the Learno mark as PNG (favicon, Apple touch icon, desk icon) |
| `../../src/styles/airtable-components.css` | hand-written | Component *shape* — flat 3px buttons, filled inputs, hairline cards, grey segmented control |

Regenerate everything:

```bash
node tailwind/airtable/generate-tokens.mjs && node tailwind/airtable/generate-typography.mjs && python3 tailwind/airtable/render-logo.py
```

## How the three layers reach the UI

**Colour, radius, elevation** — `airtable-tokens.css` re-declares all 406 themed
custom properties frappe-ui emits, plus the raw palette as `--<hue>-<step>`. It
is imported after `frappe-ui/style.css` in `src/index.css`, so it wins on source
order at equal specificity.

**Typography** — split, because frappe-ui splits it across two Tailwind layers:

- `text-<size>` / `text-p-<size>` are *utilities* built from `theme.fontSize`.
  Utilities outrank components, so these can only be changed from
  `tailwind.config.js` (which imports `type-scale.mjs`).
- `text-<size>-<weight>` are *components* registered with `addComponents` from
  frappe-ui's own generated JSON — unreachable from the theme, so
  `airtable-typography.css` re-declares them.

**Shape** — `airtable-components.css`. frappe-ui's Button renders Tailwind
utilities directly and exposes no stable hook, so the selectors anchor on the
class list `Button.vue` always emits and read the variant off the background
utility it picked. That is a deliberate coupling to frappe-ui internals; the
alternative is forking Button.vue and everything that wraps it.

## The upgrade risk, and what catches it

Both couplings are to things frappe-ui does not treat as public API:

1. the set of themed variables it declares, and
2. `Button.vue`'s emitted class list.

If either moves, the app doesn't break — it renders half-Espresso,
half-Airtable, which is easy to miss. `src/tests/airtableTheme.test.ts` pins
both: it enumerates frappe-ui's generated token data and asserts every variable
is overridden in *both* modes, and it asserts the button class contract against
the real `Button.vue` source. Run it after any frappe-ui bump.

## Mapping decisions worth knowing

- **Everything is 3px.** Airtable's button, input, select, token and badge are
  all a 3px rectangle; cards and dialogs are 6px; only switches and avatars are
  pills. `--radius-8` — frappe-ui's button radius — goes from Cloudscape's 20px
  pill to **3px**, which is the single most visible change in the theme.

- **Inputs are filled, not outlined.** A grey `#F2F2F2` field with *no border*,
  turning white with a 2px blue border on focus. This is the most recognisable
  Airtable form detail and the exact inverse of the layer it replaced. The focus
  border is drawn as an inset `box-shadow` so the control does not change size
  and the text does not shift by 2px when focused.

- **Body text is 13px, not 14.** Airtable is a dense, data-first product and its
  whole ramp runs a step tighter than a general-purpose system: 11 / 13 / 15 /
  17 rather than 12 / 14 / 16 / 18. `base` is what most body copy in this
  codebase resolves to, so that one number does most of the work of making the
  app read as Airtable.

- **Headings get lighter as they grow.** Heading/xsmall (15px) is Bold 700,
  Heading/small (17px) Semibold 600, and Heading/default (21px) and up are
  Medium 500. frappe-ui's weight variants are keyed by name, not size, so this
  size-varying rule cannot live in the `WEIGHTS` map — `weightFor()` in
  `type-scale.mjs` applies it and the typography generator calls it per size.

- **Nothing at rest carries a shadow.** Airtable separates surfaces with a 1px
  `#E0E0E0` hairline. frappe-ui puts `--elevation-base` on cards and list rows,
  so `--elevation-sm` and `--elevation-base` are explicitly `none`; only
  dropdowns, popovers and dialogs lift.

- **The active segment is grey, not blue.** The kit's "Select buttons" mark the
  chosen segment with dark grey `#666666` and white text. Blue is reserved for
  the primary action, and a blue segment would compete with it.

- **Buttons carry no border at all.** Including `gray-outline`, which loses its
  hairline and becomes the same flat grey field as `blue-subtle`. Airtable has
  one secondary button, not two.

- **Danger keeps its own red.** Unlike Cloudscape, the kit ships a real red
  button (`redBright` `#F82B60`), so destructive actions get the system's own
  treatment rather than an exception.

- **Links are never underlined at rest**, including in prose — underline is the
  hover cue. The previous layer underlined body links at rest.

- **Grey is hand-mapped.** The kit publishes nine neutrals and they are
  deliberately lopsided toward the light end. Three steps (`#CFCFCF`, `#A8A8A8`,
  `#8C8C8C`) are interpolated to fill the middle so disabled and placeholder
  text have somewhere to land; they are the only greys here not in the kit.

- **Colour ramps repeat steps rather than interpolate.** Airtable ships five
  steps per hue where a frappe-ui ramp wants ten, and `Bright`/`base` are
  near-neighbours rather than two rungs of a ladder. Every value emitted is a
  real Airtable colour; the alternative would put colours on screen that are not
  in the design system.

- **`amber` and `violet` borrow.** frappe-ui wants eleven hues, the kit has
  nine. Both alias onto their nearest neighbour (yellow, purple), which is what
  the kit itself would use.

- **Border widths are `--at-stroke-*`, colours are `--at-border-*`.** They were
  one prefix at first, and `border/container` exists in both sets — the colour
  silently overwrote the width, and a length property handed a hex is simply
  dropped. The test asserts the two namespaces stay disjoint.

- **`_note` keys are skipped by key, not by value.** `airtable-source.json`
  carries prose `_note` fields for documentation. Iterating one with
  `Object.entries` yields a pair per *character*, which emitted `--_note-45: '`
  — an apostrophe esbuild reads as an unterminated string when it minifies. The
  build only warned; the test now fails on it.

## Substitutions

- **Type: SF Pro → Inter.** The kit specifies SF Pro Text (UI, body, small
  headings) and SF Pro Display (21px and up). Both are Apple-licensed and cannot
  be bundled, so Inter ships in their place via `@fontsource-variable/inter`:
  near metric-compatible at UI sizes and identical on every platform.
  `-apple-system` is deliberately *not* first in the stack — that would give
  macOS real SF Pro and everyone else Inter, i.e. two different products. The
  kit's Text/Display split is an optical-size distinction, which Inter's
  variable `opsz` axis handles via `font-optical-sizing: auto`; frappe-ui's pin
  of `opsz` to 24 (a display size, applied to 13px body) is cleared, along with
  its `cv11` stylistic set.

- **Dark mode is synthesised.** The kit is light-only. The second entry of every
  pair in `airtable-source.json`'s `semantic` block is derived — the neutral
  ramp inverted around `#181818`, with the accent hues held at their published
  values because they read correctly on both grounds. It is an honest
  extrapolation, not extracted data; frappe-ui requires both modes, and
  `[data-theme="dark"]` has to resolve to something coherent.

- **The Learno mark.** `public/learning.svg`, `Icons/LMSLogo.vue` and
  `render-logo.py` all carry the tile colour and radius; they moved from
  Cloudscape's `#006ce0` at radius 21 to Airtable's `#2d7ff9` at radius 10 (the
  app-frame radius, the largest the kit uses). Keep the three in step.
