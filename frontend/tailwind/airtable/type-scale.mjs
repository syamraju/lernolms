/*
 * The Airtable type ramp, shared by the two places that need it.
 *
 * It has to be consumed twice because frappe-ui splits typography across two
 * Tailwind layers:
 *
 *   - `text-<size>` / `text-p-<size>` are *utilities*, generated from
 *     `theme.fontSize`. Utilities outrank components, so these can only be
 *     changed through the Tailwind config (see tailwind.config.js).
 *   - `text-<size>-<weight>` are *components*, registered by frappe-ui's plugin
 *     with `addComponents` and read from its own generated JSON rather than the
 *     resolved theme. Those can only be changed by re-declaring the classes
 *     (see generate-typography.mjs).
 *
 * Both paths must agree, so the numbers live here.
 */

/* frappe-ui size key -> [px, tight leading, paragraph leading, tracking px,
 *                        heading leading].
 *
 * Airtable's kit defines four body steps (11, 13, 15, 17) and six heading steps
 * (15, 17, 21, 23, 27, 35), each with px leading and its own paragraph leading.
 * The ramp is quantised onto those steps rather than interpolated.
 *
 * The consequential difference from the Cloudscape ramp this replaces is at the
 * bottom: Airtable's body text is **13px**, not 14px, and its small text is
 * 11px, not 12px. Airtable is a dense, data-first product and its whole scale
 * runs one step tighter than a general-purpose design system. `base` is the key
 * that most of this codebase's body copy resolves to, so that single number is
 * what makes the app read as Airtable rather than as a generic admin console.
 *
 * Above 35px the kit stops — those are marketing sizes with no Airtable
 * equivalent, so they continue the ratio.
 *
 * Three leadings per size:
 *   - tight     -> `text-<size>`, compact UI leading (the kit's Text/* line)
 *   - paragraph -> `text-p-<size>`, prose (the kit's Text/* - paragraph line)
 *   - heading   -> `text-<size>-<weight>`, which is how every heading in this
 *                  codebase is written. Where a size has a Heading/* equivalent
 *                  in the kit, that leading is used; otherwise it follows tight.
 *
 * Tracking is 0 across the whole kit — Airtable sets no optical tracking on
 * body or headings. The one exception is the three "caps" styles, which carry
 * 5% and are emitted separately as `.text-tiny-*` (frappe-ui's uppercase
 * eyebrow), not as a tracking value on every step.
 */
export const SCALE = {
  tiny: [11, 16, 16, 0.55],
  '2xs': [11, 14, 16, 0],
  xs: [11, 14, 16, 0],
  sm: [11, 14, 16, 0],
  base: [13, 16, 20, 0],
  md: [13, 16, 20, 0],
  lg: [15, 20, 22, 0, 22],
  xl: [15, 20, 22, 0, 22],
  '2xl': [17, 24, 26, 0, 24],
  '3xl': [21, 26, 28, 0, 26],
  '4xl': [23, 29, 32, 0, 29],
  '5xl': [27, 34, 36, 0, 34],
  '6xl': [35, 44, 46, 0, 44],
  '7xl': [40, 48, 52, 0, 48],
  '8xl': [46, 55, 59, 0, 55],
  '9xl': [52, 62, 66, 0, 62],
  '10xl': [58, 69, 73, 0, 69],
  '11xl': [64, 76, 80, 0, 76],
  '12xl': [72, 85, 89, 0, 85],
  '13xl': [80, 94, 98, 0, 94],
  '14xl': [88, 103, 107, 0, 103],
  '15xl': [96, 112, 116, 0, 112],
  '16xl': [104, 121, 125, 0, 121],
}

/** Tracking for a size, as a CSS value. */
export const trackingOf = (size) => {
  const t = SCALE[size][3]
  return t ? `${t}px` : 'normal'
}

/** Leading used by the weight variants (headings). */
export const headingLeadingOf = (size) => SCALE[size][4] ?? SCALE[size][1]

/* Airtable uses four weights, and — unlike Cloudscape — it uses them at
 * *different sizes*: Heading/xsmall (15px) is Bold 700, Heading/small (17px) is
 * Semibold 600, and everything 21px and up is Medium 500. Large type gets
 * lighter, not heavier, which is the single most characteristic thing about
 * Airtable's headings.
 *
 * frappe-ui's weight variants are keyed by name, not size, so that size-varying
 * rule cannot be expressed here — it is applied in generate-typography.mjs,
 * which knows both. This map is the floor: `semibold` (how every heading in this
 * codebase is written) resolves to 600, and the generator lightens it to 500 on
 * the display sizes. */
export const WEIGHTS = { medium: 500, semibold: 600, bold: 700, black: 700 }
export const REGULAR = 400

/* Sizes that take the display family rather than the text family. The kit
 * switches at Heading/default (21px). */
const DISPLAY_SIZES = new Set([
  '3xl', '4xl', '5xl', '6xl', '7xl', '8xl', '9xl',
  '10xl', '11xl', '12xl', '13xl', '14xl', '15xl', '16xl',
])

/* The weight the kit uses for headings at a given size — see the note above.
 * `medium` stays 500 everywhere because it marks label emphasis, not a
 * heading. */
export const weightFor = (size, name) => {
  if (name === 'medium') return 500
  if (DISPLAY_SIZES.has(size)) return 500 // Heading/default and up: Medium
  if (size === '2xl') return 600 // Heading/small: Semibold
  return 700 // Heading/xsmall and below: Bold
}

export const isDisplaySize = (size) => DISPLAY_SIZES.has(size)

/* frappe-ui's 0.02em is an Inter correction and is dropped: Airtable sets no
 * tracking anywhere except the caps styles. */
export const TRACKING = 'normal'

/* `tiny` is frappe-ui's uppercase eyebrow style, and it maps exactly onto the
 * kit's Heading/xsmall - caps: 11/16 Bold with 5% tracking. 5% of 11px is
 * 0.55px, which is the value carried in SCALE above. */
export const UPPERCASE = ['tiny']

/* The kit specifies SF Pro Text (UI, body, small headings) and SF Pro Display
 * (headings 21px and up). Both are Apple-licensed and cannot be bundled, so
 * Inter is shipped in their place: it is near metric-compatible with SF Pro at
 * UI sizes and renders identically on every platform, which the system stack
 * does not. `-apple-system` is deliberately NOT first — that would give macOS
 * real SF Pro and everyone else Inter, i.e. two different products.
 *
 * Airtable uses one family at every size in practice; the Text/Display split is
 * an optical-size distinction, which Inter's variable `opsz` axis handles on
 * its own via `font-optical-sizing: auto`. */
export const FONT_SANS = [
  'Inter Variable',
  'Inter',
  '-apple-system',
  'BlinkMacSystemFont',
  'Segoe UI',
  'Roboto',
  'Helvetica',
  'Arial',
  'sans-serif',
]

export const FONT_MONO = [
  'SF Mono',
  'Monaco',
  'Menlo',
  'Consolas',
  'Liberation Mono',
  'monospace',
]

/* Tailwind `theme.fontSize` entries for the regular utilities: `text-<size>`
 * (tight leading) and `text-p-<size>` (paragraph leading). */
export function fontSizeTheme() {
  const out = {}
  for (const [size, [px, tight, para]] of Object.entries(SCALE)) {
    const meta = { letterSpacing: trackingOf(size), fontWeight: String(REGULAR) }
    out[size] = [`${px}px`, { ...meta, lineHeight: `${tight}px` }]
    out[`p-${size}`] = [`${px}px`, { ...meta, lineHeight: `${para}px` }]
  }
  return out
}
