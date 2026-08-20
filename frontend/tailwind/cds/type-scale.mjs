/*
 * The Cloudscape type ramp, shared by the two places that need it.
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
 * Cloudscape defines only eight steps (12, 14, 16, 18, 20, 24, 42, plus the
 * 14px heading-5) and pins leading in px rather than as a ratio, so the ramp is
 * quantised onto those steps instead of interpolated: `xs`/`sm` land on CDS
 * paragraph-small (12/16), `base` on CDS paragraph (14/20), `md`/`lg` on
 * heading-4 (16/20), `xl`/`2xl` on heading-3 (18/22), `3xl` on heading-2
 * (20/24), `4xl` on heading-1 (24/30) and `8xl` on display-large (42/48).
 * Sizes above display-large continue the ratio — the app's marketing-scale
 * headings have no CDS equivalent.
 *
 * Three leadings per size:
 *   - tight     -> `text-<size>`, frappe-ui's compact UI leading
 *   - paragraph -> `text-p-<size>`, prose
 *   - heading   -> `text-<size>-<weight>`, which is how every heading in this
 *                  codebase is written. Only `base` differs from tight: CDS
 *                  heading-5 is 14/18 where body is 14/20.
 *
 * Tracking comes from the CDS text styles and is *negative* on every step above
 * 14px (H1 -0.48, H2 -0.30, H3 -0.18, H4 -0.08, display -1.26). Open Sans needs
 * no positive tracking, so 14px and below sit at 0 — but dropping the negative
 * values would leave large headings visibly loose against the spec.
 */
export const SCALE = {
  tiny: [12, 16, 16, 0],
  '2xs': [12, 16, 16, 0],
  xs: [12, 16, 18, 0],
  sm: [12, 16, 18, 0],
  base: [14, 20, 20, 0, 18],
  md: [16, 20, 22, -0.08],
  lg: [16, 20, 22, -0.08],
  xl: [18, 22, 24, -0.18],
  '2xl': [18, 22, 24, -0.18],
  '3xl': [20, 24, 28, -0.3],
  '4xl': [24, 30, 32, -0.48],
  '5xl': [28, 34, 38, -0.62],
  '6xl': [32, 38, 42, -0.8],
  '7xl': [36, 42, 46, -0.98],
  '8xl': [42, 48, 52, -1.26],
  '9xl': [46, 52, 56, -1.38],
  '10xl': [52, 58, 62, -1.56],
  '11xl': [58, 64, 68, -1.74],
  '12xl': [64, 70, 74, -1.92],
  '13xl': [72, 78, 82, -2.16],
  '14xl': [80, 86, 90, -2.4],
  '15xl': [88, 94, 98, -2.64],
  '16xl': [96, 102, 106, -2.88],
}

/** Tracking for a size, as a CSS value. */
export const trackingOf = (size) => {
  const t = SCALE[size][3]
  return t ? `${t}px` : 'normal'
}

/** Leading used by the weight variants (headings). */
export const headingLeadingOf = (size) => SCALE[size][4] ?? SCALE[size][1]

/* Cloudscape uses two weights: 400 body, 700 headings. The app's markup leans
 * on four, and every heading in this codebase is written with `-semibold`
 * (`text-lg-semibold`, `text-3xl-semibold`, `text-4xl-semibold`), so `semibold`
 * maps onto CDS's 700 and those headings render as real CDS headings. `medium`
 * keeps a lighter 500 for label emphasis. */
export const WEIGHTS = { medium: 500, semibold: 700, bold: 700, black: 800 }
export const REGULAR = 400

/* frappe-ui's 0.02em is an Inter correction and is dropped throughout; CDS
 * tracking is per-size and comes from `trackingOf` above. */
export const TRACKING = 'normal'

/* `tiny` is frappe-ui's uppercase eyebrow style. */
export const UPPERCASE = ['tiny']

export const FONT_SANS = [
  'Open Sans Variable',
  'Open Sans',
  '-apple-system',
  'BlinkMacSystemFont',
  'Segoe UI',
  'Roboto',
  'Helvetica',
  'Arial',
  'sans-serif',
]

export const FONT_MONO = [
  'Monaco',
  'SF Mono',
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
