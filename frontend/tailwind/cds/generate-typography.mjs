/*
 * Generates `src/styles/cds-typography.css` — the weight-variant half of the
 * Cloudscape type ramp, plus the font-family reset.
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
 * Run: node tailwind/cds/generate-typography.mjs
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
} from './type-scale.mjs'

const here = dirname(fileURLToPath(import.meta.url))

const rules = []
const rule = (sel, decls) =>
	rules.push(`\t${sel} {\n${decls.map((d) => `\t\t${d};`).join('\n')}\n\t}`)

for (const [size, [px, , para]] of Object.entries(SCALE)) {
	const upper = UPPERCASE.includes(size) ? ['text-transform: uppercase'] : []
	const tracking = trackingOf(size)
	// Weight variants are how every heading in this codebase is written, so they
	// take the CDS heading leading rather than the compact UI one.
	const heading = headingLeadingOf(size)
	for (const [name, weight] of Object.entries(WEIGHTS)) {
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
 * Cloudscape (CDS) typography — GENERATED, do not edit by hand.
 *
 * Source:    CDS Component Library 2.0.2 (Community), Figma file fZ2UxXNEQ9EAEgNtOT7yB1
 * Generator: tailwind/cds/generate-typography.mjs
 * Scale:     tailwind/cds/type-scale.mjs (shared with tailwind.config.js)
 * Regenerate: node tailwind/cds/generate-typography.mjs
 *
 * Only weight variants live here. The regular \`text-<size>\` utilities come
 * from \`theme.fontSize\` — see the note at the top of the generator.
 */

/* frappe-ui's plugin sets \`html { font-family: InterVar, … }\` plus Inter-only
 * \`font-variation-settings\` ('opsz' 24, 'cv11' 1) on html/body/button/p/span/div.
 * Open Sans has no \`cv11\` axis and a different \`opsz\` range, so the settings
 * have to be cleared as well as the family replaced — otherwise the browser is
 * handed an unsupported axis and falls back unpredictably.
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
	--cds-font-sans: ${quote(FONT_SANS)};
	--cds-font-mono: ${quote(FONT_MONO)};
}

html {
	font-family: var(--cds-font-sans);
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
	font-family: var(--cds-font-mono);
}

@layer components {
${rules.join('\n\n')}
}
`

const outPath = resolve(here, '../../src/styles/cds-typography.css')
writeFileSync(outPath, css)
console.log(`wrote ${outPath}`)
console.log(`  weight-variant classes: ${rules.length}`)
