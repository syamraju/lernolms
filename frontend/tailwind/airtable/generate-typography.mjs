/*
 * Generates `src/styles/airtable-typography.css` — the weight-variant half of
 * the Airtable type ramp, plus the font-family reset.
 *
 * The regular `text-<size>` / `text-p-<size>` utilities are NOT emitted here:
 * they are utilities, they outrank anything in the components layer, and they
 * are driven from `theme.fontSize` in tailwind.config.js instead. This file
 * covers `text-<size>-<weight>`, which frappe-ui's plugin registers with
 * `addComponents` from its own generated JSON — unreachable from the theme, so
 * the classes have to be re-declared.
 *
 * Everything lands in `@layer components`, the same layer frappe-ui's plugin
 * uses. Tailwind emits plugin components before CSS-authored ones, so these win
 * on source order without escalating specificity — utilities still override
 * them, exactly as before.
 *
 * Run: node tailwind/airtable/generate-typography.mjs
 */
import { writeFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import {
  SCALE,
  WEIGHTS,
  UPPERCASE,
  FONT_SANS,
  FONT_MONO,
  trackingOf,
  headingLeadingOf,
  weightFor,
} from './type-scale.mjs'

const here = dirname(fileURLToPath(import.meta.url))

const rules = []
const rule = (sel, decls) =>
  rules.push(`\t${sel} {\n${decls.map((d) => `\t\t${d};`).join('\n')}\n\t}`)

for (const [size, [px, , para]] of Object.entries(SCALE)) {
  const upper = UPPERCASE.includes(size) ? ['text-transform: uppercase'] : []
  const tracking = trackingOf(size)
  // Weight variants are how every heading in this codebase is written, so they
  // take the Airtable heading leading rather than the compact UI one.
  const heading = headingLeadingOf(size)
  for (const name of Object.keys(WEIGHTS)) {
    // Airtable's headings get *lighter* as they get larger — Bold at 15px,
    // Semibold at 17px, Medium at 21px and up. `weightFor` encodes that;
    // `WEIGHTS` is only the floor. See type-scale.mjs.
    const weight = weightFor(size, name)
    rule(`.text-${size}-${name}`, [
      `font-size: ${px}px`,
      `line-height: ${heading}px`,
      `letter-spacing: ${tracking}`,
      `font-weight: ${weight}`,
      ...upper,
    ])
    rule(`.text-p-${size}-${name}`, [
      `font-size: ${px}px`,
      `line-height: ${para}px`,
      `letter-spacing: ${tracking}`,
      `font-weight: ${weight}`,
      ...upper,
    ])
  }
}

const quote = (list) =>
  list.map((f) => (/[^a-zA-Z-]/.test(f) ? `'${f}'` : f)).join(', ')

const css = `/*
 * Airtable typography — GENERATED, do not edit by hand.
 *
 * Source:    Airtable Apps UI Kit (Community), Figma file StoTaUKJ4FiEzEoOr4kW3N
 * Generator: tailwind/airtable/generate-typography.mjs
 * Scale:     tailwind/airtable/type-scale.mjs (shared with tailwind.config.js)
 * Regenerate: node tailwind/airtable/generate-typography.mjs
 *
 * Only weight variants live here. The regular \`text-<size>\` utilities come
 * from \`theme.fontSize\` — see the note at the top of the generator.
 */

/* frappe-ui's plugin sets \`html { font-family: InterVar, … }\` plus
 * \`font-variation-settings: 'opsz' 24, 'cv11' 1\` on html/body/button/p/span/div.
 *
 * This theme also ships Inter, so unlike the Cloudscape layer it replaced, the
 * axes are real here — but the values are not the ones wanted. \`opsz\` is pinned
 * to 24, which is a display optical size applied to *everything* including 13px
 * body text; Airtable's Text/Display split is exactly what the optical axis is
 * for, so it is handed back to the browser with \`font-optical-sizing: auto\` and
 * the pin is cleared. \`cv11\` (single-storey a) is an Inter stylistic set that
 * SF Pro does not have and Airtable does not use.
 *
 * The family is set on \`html\` ONLY, and everything below inherits it. It is
 * tempting to repeat it on html/body/button/p/span/div to mirror frappe-ui's
 * own list, but that quietly breaks any subtree that sets its own font: the
 * student shell (src/styles/learno.css) puts DM Sans on \`.learno\` and relies on
 * inheritance, and an element selector like \`div\` — specificity (0,0,1) —
 * outranks an inherited value no matter how specific its source. Tailwind's
 * preflight already gives form controls \`font-family: inherit\`, so they follow
 * \`html\` without being named here.
 *
 * \`font-variation-settings\` is different: it has to be cleared wherever
 * frappe-ui set it, and \`normal\` is the right value for any font, so the broad
 * list is kept for that property alone. */
:root {
	--at-font-sans: ${quote(FONT_SANS)};
	--at-font-mono: ${quote(FONT_MONO)};
}

html {
	font-family: var(--at-font-sans);
	font-optical-sizing: auto;
}

html,
body,
button,
input,
select,
textarea,
p,
span,
div {
	font-variation-settings: normal;
}

code,
kbd,
pre,
samp {
	font-family: var(--at-font-mono);
}

@layer components {
${rules.join('\n\n')}
}
`

const outPath = resolve(here, '../../src/styles/airtable-typography.css')
writeFileSync(outPath, css)
console.log(`wrote ${outPath}`)
console.log(`  weight-variant classes: ${rules.length}`)
