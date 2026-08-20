/*
 * Generates `src/styles/airtable-tokens.css` — the Airtable override layer.
 *
 * The app renders almost entirely through frappe-ui's semantic CSS custom
 * properties (`--surface-*`, `--ink-*`, `--outline-*`, `--radius-*`,
 * `--elevation-*`). Re-pointing those variables at Airtable values re-skins the
 * whole product without touching the component files.
 *
 * frappe-ui emits its variables from a Tailwind plugin at `:root` and
 * `[data-theme="dark"]`. This file is imported after `frappe-ui/style.css`, so
 * an identical selector with the same specificity wins on source order.
 *
 * Run: node tailwind/airtable/generate-tokens.mjs
 */
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const src = JSON.parse(readFileSync(resolve(here, 'airtable-source.json'), 'utf8'))
const P = src.palette

/* ---------------------------------------------------------------- ramps --
 * frappe-ui indexes every hue 1..10 (gray's ink and outline stop at 9).
 *
 * Airtable ships only five steps per hue — Light2, Light1, base, Bright, Dark1
 * — where a frappe-ui ramp wants ten. The five are not evenly spaced either:
 * Bright and base are near-neighbours (#2D7FF9 / #1283DA), because Airtable
 * uses Bright for interactive fills and base for muted ones rather than as two
 * rungs of a lightness ladder.
 *
 * So the ten indices are built by repeating steps rather than by interpolating
 * new colours: every value below is a real Airtable colour, and "higher index =
 * stronger" still holds, which is the only property component code relies on.
 * The alternative — generating intermediate hexes — would put colours on screen
 * that are not in the design system.
 */
const RAMP = {
  light: {
    // 1..10, lightest to strongest. Index 5/6 are the interactive pair.
    surface: ['Light2', 'Light2', 'Light1', 'Light1', 'Bright', 'Bright', 'base', 'base', 'Dark1', 'Dark1'],
    // ink-1 is white (text on a strong fill); the rest darken.
    ink: ['#ffffff', 'Light2', 'Light1', 'Light1', 'Bright', 'Bright', 'base', 'base', 'Dark1', 'Dark1'],
    outline: ['Light2', 'Light2', 'Light1', 'Light1', 'Bright', 'Bright', 'base', 'base', 'Dark1', 'Dark1'],
  },
  dark: {
    surface: ['Dark1', 'Dark1', 'base', 'base', 'Bright', 'Bright', 'Light1', 'Light1', 'Light2', 'Light2'],
    ink: ['#ffffff', 'Dark1', 'Dark1', 'base', 'base', 'Bright', 'Bright', 'Light1', 'Light2', 'Light2'],
    outline: ['Dark1', 'Dark1', 'base', 'base', 'Bright', 'Bright', 'Light1', 'Light1', 'Light2', 'Light2'],
  },
}

/* Grey is hand-mapped, not sliced.
 *
 * The kit publishes nine neutrals — white, four light greys (#FAFAFA, #F2F2F2,
 * #E8E8E8, #E0E0E0) and four darks (#757575, #666666, #424242, #333333) — and
 * they are deliberately lopsided: Airtable's UI is built almost entirely from
 * the light end (fills, dividers, input backgrounds) and uses the dark end only
 * for text and the active segment. There is a real gap in the middle of the
 * published set, which `airtable-source.json` fills with three steps (#CFCFCF,
 * #A8A8A8, #8C8C8C) so that disabled text and placeholder text have somewhere
 * to land. Those three are the only greys here that are not in the kit.
 *
 * These anchor on the exact values the kit uses: `outline-gray-1` must be
 * #E0E0E0 (every divider and container border in the App frame board) and
 * `ink-gray-9` must be #333333 (Text/default). Those two carry most of the
 * theme's character.
 */
const G = P.grey
const GRAY = {
  light: {
    surface: [G['50'], G['100'], G['150'], G['200'], G['300'], G['400'], G['600'], G['700'], G['850'], G['950']],
    ink: [G['200'], G['300'], G['400'], G['600'], G['700'], G['800'], G['850'], G['900'], G['950']],
    outline: [G['200'], G['300'], G['400'], G['500'], G['600'], G['700'], G['800'], G['850'], G['950']],
  },
  dark: {
    surface: [G['1000'], G['950'], G['900'], G['850'], G['800'], G['700'], G['500'], G['400'], G['200'], G['50']],
    ink: [G['950'], G['900'], G['850'], G['700'], G['600'], G['400'], G['300'], G['200'], G['50']],
    outline: [G['900'], G['850'], G['800'], G['700'], G['600'], G['500'], G['300'], G['200'], G['50']],
  },
}

/* Airtable has no alpha grey scale. These approximate the solid ramps as
 * translucency so overlay surfaces (which is all `*-alpha-*` is used for) still
 * composite over whatever sits behind them. Based on #333333, the kit's Dark. */
const ALPHA = {
  light: ['#33333308', '#3333330d', '#33333317', '#33333324', '#3333333d', '#33333352', '#33333378', '#333333a1', '#333333c7', '#333333'],
  dark: ['#ffffff0a', '#ffffff14', '#ffffff1f', '#ffffff2e', '#ffffff42', '#ffffff5c', '#ffffff7a', '#ffffff99', '#ffffffc7', '#ffffff'],
}

/* frappe-ui hue name -> Airtable palette name.
 *
 * Airtable ships nine hues; frappe-ui wants eleven. `amber` and `violet` have no
 * Airtable equivalent and borrow their nearest neighbour (yellow and purple),
 * which is what the kit itself would use — it has one yellow and one purple. */
const HUES = {
  red: 'red', blue: 'blue', green: 'green', yellow: 'yellow', orange: 'orange',
  teal: 'teal', cyan: 'cyan', purple: 'purple', pink: 'pink',
  amber: 'yellow', violet: 'purple',
}

const step = (hue, s) => (s.startsWith('#') ? s : P[hue][s])

function ramps(theme) {
  const out = []
  const push = (name, value) => out.push([name, value])

  // gray
  GRAY[theme].surface.forEach((v, i) => push(`--surface-gray-${i + 1}`, v))
  GRAY[theme].ink.forEach((v, i) => push(`--ink-gray-${i + 1}`, v))
  GRAY[theme].outline.forEach((v, i) => push(`--outline-gray-${i + 1}`, v))
  ALPHA[theme].forEach((v, i) => push(`--surface-alpha-gray-${i + 1}`, v))
  ALPHA[theme].slice(0, 9).forEach((v, i) => push(`--outline-alpha-gray-${i + 1}`, v))

  // colour hues
  for (const [fu, at] of Object.entries(HUES)) {
    RAMP[theme].surface.forEach((s, i) => push(`--surface-${fu}-${i + 1}`, step(at, s)))
    RAMP[theme].ink.forEach((s, i) => push(`--ink-${fu}-${i + 1}`, step(at, s)))
    RAMP[theme].outline.forEach((s, i) => push(`--outline-${fu}-${i + 1}`, step(at, s)))
  }
  return out
}

/* Named anchors, taken straight from the Airtable semantic tokens rather than
 * derived from a ramp — these are the ones that set the product's character. */
const S = src.semantic
const pick = (key, theme) => S[key][theme === 'light' ? 0 : 1]

function anchors(theme) {
  const t = (k) => pick(k, theme)
  return [
    ['--surface-base', t('background/app')],
    ['--surface-alpha-base', t('background/app')],
    ['--surface-sidebar', t('background/sidebar')],
    ['--surface-alpha-sidebar', t('background/sidebar')],
    // Airtable is flat: a raised surface is the same white as the page, told
    // apart by a hairline, not by a tint. Only genuinely floating things
    // (dropdowns, dialogs) lift, and they lift with shadow — see elevations().
    ['--surface-elevation-1', t('background/container')],
    ['--surface-elevation-2', t('background/raised')],
    ['--surface-elevation-3', t('background/raised')],
    ['--surface-alpha-elevation-1', t('background/container')],
    ['--surface-alpha-elevation-2', t('background/raised')],
    ['--surface-alpha-elevation-3', t('background/raised')],
    ['--surface-alpha-gray-2-overlay', theme === 'dark' ? '#ffffff14' : '#3333330d'],

    ['--ink-base', t('background/app')],
    ['--ink-blue-link', t('text/link')],

    ['--outline-base', t('background/app')],
    ['--outline-alpha-base', t('background/app')],
    ['--outline-elevation-1', t('border/container')],
    ['--outline-elevation-2', t('border/divider')],
    ['--outline-alpha-elevation-1', t('border/container')],
    ['--outline-alpha-elevation-2', t('border/divider')],

    ['--surface-alert-button-default', t('background/button/default')],
    ['--surface-alert-button-info', t('background/status/info')],
    ['--surface-alert-button-success', t('background/status/success')],
    ['--surface-alert-button-warning', t('background/status/warning')],
    ['--surface-alert-button-error', t('background/status/error')],
    ['--ink-alert-button-default', t('text/default')],
    ['--ink-alert-button-info', t('text/status/info')],
    ['--ink-alert-button-success', t('text/status/success')],
    ['--ink-alert-button-warning', t('text/status/warning')],
    ['--ink-alert-button-error', t('text/status/error')],

    // Shadow colour drives every --elevation-* below.
    ['--at-shadow', t('shadow/color')],
    ['--at-shadow-strong', t('shadow/color-strong')],
  ]
}

/* Airtable is a flat, hairline-led system. Nothing that sits *in* the page
 * carries a shadow — containers are told apart by a 1px #E0E0E0 border. Shadow
 * is reserved for things that genuinely float above it, and there are only
 * three of those in the kit: the dropdown, the dialog and a dragged record.
 *
 * So `sm` and `base` are deliberately none: frappe-ui puts `--elevation-base`
 * on cards and list rows, and giving those a real shadow is the single fastest
 * way to stop looking like Airtable. The three real steps come from `shadow` in
 * airtable-source.json. */
function elevations() {
  const H = src.shadow
  const s = (k, colour = 'var(--at-shadow)') =>
    `${H[k].x}px ${H[k].y}px ${H[k].blur}px ${H[k].spread}px ${colour}`
  return [
    ['--elevation-sm', 'none'],
    ['--elevation-base', 'none'],
    ['--elevation-md', s('raised')],
    ['--elevation-lg', s('dropdown')],
    ['--elevation-xl', s('dropdown')],
    ['--elevation-2xl', s('dialog', 'var(--at-shadow-strong)')],
  ]
}

/* frappe-ui's numeric radius scale rewritten to Airtable's.
 *
 * This is the most visible single change in the theme. Cloudscape's button was a
 * 20px pill and its container 16px; Airtable's button is **3px** and its card
 * 6px. Every rounded thing in the app tightens at once. `--radius-9` and
 * `--radius-full` stay circular because avatars and switches need them. */
function radii() {
  const R = src.radius
  return [
    ['--radius-0', '0px'],
    ['--radius-1', `${R.badge}px`],
    ['--radius-2', `${R.button}px`],
    ['--radius-3', `${R.input}px`],
    ['--radius-4', `${R.swatch}px`],
    ['--radius-5', `${R.card}px`],
    ['--radius-6', `${R.dialog}px`],
    ['--radius-7', `${R.container}px`],
    ['--radius-8', `${R.button}px`],
    ['--radius-9', '999px'],
    ['--radius-none', '0px'],
    ['--radius-sm', `${R.badge}px`],
    ['--radius-md', `${R.button}px`],
    ['--radius-lg', `${R.card}px`],
    ['--radius-xl', `${R.container}px`],
    ['--radius-2xl', `${R['app-frame']}px`],
    ['--radius-full', '9999px'],
  ]
}

/* The raw palette as `--<hue>-<step>` custom properties.
 *
 * frappe-ui exposes its palette to Tailwind as *colours* (class names), never
 * as CSS variables — only the themed variables become custom properties.
 * Hand-written CSS that reaches for `var(--blue-400)` therefore resolves to
 * nothing: CourseCard.vue builds its gradient as
 * `linear-gradient(to top right, black, var(--blue-400))`, and with the var
 * undefined the whole gradient value is invalid at computed-value time and the
 * card falls back to no gradient at all.
 *
 * Airtable's step names (Bright/base/Dark1/Light1/Light2) are not the numeric
 * ones that markup asks for, so each hue is also published under the numeric
 * names frappe-ui's own palette used — 50..900 — mapped onto the nearest
 * Airtable step. That is what keeps `card_gradient` values already stored in
 * the database rendering after the theme swap.
 */
const NUMERIC = {
  50: 'Light2', 100: 'Light2', 200: 'Light1', 300: 'Light1', 400: 'Bright',
  500: 'Bright', 600: 'base', 700: 'base', 800: 'Dark1', 900: 'Dark1',
}

function paletteVars() {
  const out = []
  for (const [hue, steps] of Object.entries(P)) {
    // `palette._note` is documentation, not a hue. Skipping it by key is not
    // optional: `Object.entries` on its *string* value yields one entry per
    // character, so it emitted `--_note-45: '` — an apostrophe, which esbuild
    // reads as an unterminated string token when it minifies the bundle.
    if (hue.startsWith('_') || hue === 'grey') continue
    for (const [name, value] of Object.entries(steps)) {
      if (name.startsWith('_')) continue
      out.push([`--${hue}-${name}`, value])
    }
    for (const [n, s] of Object.entries(NUMERIC)) out.push([`--${hue}-${n}`, steps[s]])
  }
  // frappe-ui's `amber` and `violet` spellings, for markup that uses them.
  for (const [alias, real] of [['amber', 'yellow'], ['violet', 'purple']]) {
    for (const [n, s] of Object.entries(NUMERIC)) out.push([`--${alias}-${n}`, P[real][s]])
  }
  // Grey, under both spellings CourseCard's stored `card_gradient` values use.
  for (const [name, value] of Object.entries(P.grey)) {
    if (name.startsWith('_')) continue
    out.push([`--grey-${name}`, value], [`--gray-${name}`, value])
  }
  out.push(['--white', '#ffffff'], ['--black', '#000000'])
  return out
}

/* Raw Airtable scales, exposed so component-level CSS can reach them directly.
 *
 * Border *widths* are published as `--at-stroke-*`, not `--at-border-*`: the
 * semantic block below already owns `--at-border-*` for border *colours*, and
 * `border/container` and `border/divider` exist in both sets. Emitting both
 * under one prefix let the colour silently overwrite the width — a length
 * property handed a hex is simply dropped, so the rule using it would lose its
 * border with nothing anywhere reporting a problem. */
function airtableScales() {
  const out = []
  const skip = (k) => k.startsWith('_')
  for (const [k, v] of Object.entries(src.spacing)) if (!skip(k)) out.push([`--at-space-${k}`, `${v}px`])
  for (const [k, v] of Object.entries(src.radius)) if (!skip(k)) out.push([`--at-radius-${k.replace(/\//g, '-')}`, `${v}px`])
  for (const [k, v] of Object.entries(src.borderWidth)) if (!skip(k)) out.push([`--at-stroke-${k.replace(/\//g, '-')}`, `${v}px`])
  for (const [k, v] of Object.entries(src.sizes)) if (!skip(k)) out.push([`--at-size-${k.replace(/\//g, '-')}`, `${v}px`])
  return out
}

/* Airtable semantic tokens kept under their own namespace. The ramp overrides
 * above cover component code that already uses frappe-ui classes; these give
 * hand-written CSS a way to name an Airtable role exactly. */
function airtableSemantic(theme) {
  return Object.entries(S)
    .filter(([k]) => !k.startsWith('_'))
    .map(([k, v]) => [`--at-${k.replace(/\//g, '-')}`, v[theme === 'light' ? 0 : 1]])
}

const block = (selector, pairs, indent = '\t') =>
  `${selector} {\n${pairs.map(([k, v]) => `${indent}${k}: ${v};`).join('\n')}\n}`

const header = `/*
 * Airtable token layer — GENERATED, do not edit by hand.
 *
 * Source:    Airtable Apps UI Kit (Community), Figma file StoTaUKJ4FiEzEoOr4kW3N
 * Generator: tailwind/airtable/generate-tokens.mjs
 * Data:      tailwind/airtable/airtable-source.json
 * Regenerate: node tailwind/airtable/generate-tokens.mjs
 *
 * Imported after frappe-ui/style.css in src/index.css, so these declarations
 * override frappe-ui's defaults on source order at equal specificity.
 */`

const css = [
  header,
  '',
  '/* ---------------------------------------------------------------- light */',
  block(':root', [...paletteVars(), ...ramps('light'), ...anchors('light'), ...elevations(), ...radii(), ...airtableScales(), ...airtableSemantic('light')]),
  '',
  '/* ----------------------------------------------------------------- dark */',
  block('[data-theme="dark"]', [...ramps('dark'), ...anchors('dark'), ...airtableSemantic('dark')]),
  '',
].join('\n')

const outPath = resolve(here, '../../src/styles/airtable-tokens.css')
mkdirSync(dirname(outPath), { recursive: true })
writeFileSync(outPath, css)

const count = (s) => (css.match(new RegExp(s, 'g')) || []).length
console.log(`wrote ${outPath}`)
console.log(`  declarations: ${count(';')}`)
console.log(`  --surface-*:  ${count('--surface-')}`)
console.log(`  --ink-*:      ${count('--ink-')}`)
console.log(`  --outline-*:  ${count('--outline-')}`)
console.log(`  --at-*:       ${count('--at-')}`)
