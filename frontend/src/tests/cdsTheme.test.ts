/**
 * Guards the Cloudscape (CDS) theme layer.
 *
 * The theme is not written into the components — it re-points frappe-ui's own
 * CSS variables and re-declares a handful of its classes (see
 * src/styles/cds-*.css and tailwind/cds/). That keeps the diff small, but it
 * means the theme depends on two things staying true of the frappe-ui package:
 *
 *   1. the set of themed CSS variables it declares, and
 *   2. the class list Button.vue emits, which is the only selector the
 *      component layer can anchor on.
 *
 * Neither is a public API. If a frappe-ui upgrade moves either, the app does
 * not crash — it quietly renders half-Espresso, half-Cloudscape, which is the
 * kind of regression nobody notices until a screenshot. These tests turn that
 * into a failure.
 *
 * They read the real files rather than mounting anything: frappe-ui's internal
 * module resolution doesn't work under vitest (see PersonaCard.test.ts), so a
 * mounted Button would be a stub and would prove nothing about the real one.
 */
import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const read = (p: string) => readFileSync(resolve(process.cwd(), p), 'utf8')

const tokensCss = read('src/styles/cds-tokens.css')
const typographyCss = read('src/styles/cds-typography.css')
const componentsCss = read('src/styles/cds-components.css')
const buttonSource = read(
	'node_modules/frappe-ui/src/components/Button/Button.vue',
)
const frappeColors = JSON.parse(
	read('node_modules/frappe-ui/tailwind/generated/colors.json'),
)

/** Variable names declared inside a given selector block of a CSS string. */
function declaredIn(css: string, selector: string): Set<string> {
	const start = css.indexOf(`${selector} {`)
	if (start === -1) return new Set()
	const end = css.indexOf('\n}', start)
	const body = css.slice(start, end)
	return new Set([...body.matchAll(/(--[\w-]+)\s*:/g)].map((m) => m[1]))
}

describe('CDS token layer', () => {
	// The heart of the theme: every themed variable frappe-ui declares must be
	// re-declared here, or that slice of the UI silently keeps Espresso's
	// palette. Enumerated from frappe-ui's own generated token data, so a
	// version that adds variables fails this until they are mapped.
	it('overrides every themed variable frappe-ui declares, in both modes', () => {
		const expected = Object.entries(frappeColors.themedVariables.light).flatMap(
			([category, entries]) =>
				Object.keys(entries as Record<string, unknown>).map(
					(name) => `--${category}-${name}`,
				),
		)

		const light = declaredIn(tokensCss, ':root')
		const dark = declaredIn(tokensCss, '[data-theme="dark"]')

		expect(expected.length).toBeGreaterThan(400)
		expect(expected.filter((v) => !light.has(v))).toEqual([])
		expect(expected.filter((v) => !dark.has(v))).toEqual([])
	})

	it('anchors the signature surfaces on Cloudscape values', () => {
		// background/layout/main, text/body/default, border/layout, and the
		// 20px pill button radius — the four that set the product's character.
		expect(tokensCss).toContain('--surface-base: #ffffff')
		expect(tokensCss).toContain('--surface-base: #161d26')
		expect(tokensCss).toContain('--ink-gray-9: #0f141a')
		expect(tokensCss).toContain('--outline-gray-1: #dedee3')
		expect(tokensCss).toContain('--radius-8: 20px')
	})

	it('declares the raw palette so var(--blue-400) style lookups resolve', () => {
		// CourseCard builds its gradient from these; frappe-ui never defined
		// them, so the whole gradient was invalid at computed-value time.
		expect(tokensCss).toContain('--blue-400:')
		expect(tokensCss).toContain('--gray-500:')
	})

	it('leaves no Espresso oklch values in the override layer', () => {
		expect(tokensCss).not.toMatch(/oklch\(/)
	})

	// The component layer names CDS roles directly (`var(--cds-text-form-label)`).
	// A typo or a token that was never extracted from Figma resolves to nothing
	// and the property is simply dropped — the element keeps frappe-ui's value
	// and nothing anywhere reports a problem. This is the cheapest way to catch
	// that, and it scales as more components are built out.
	it('declares every --cds-* token the component layer references', () => {
		const referenced = new Set(
			[...componentsCss.matchAll(/var\((--cds-[\w-]+)/g)].map((m) => m[1]),
		)
		const declared = new Set([
			...[...tokensCss.matchAll(/(--cds-[\w-]+)\s*:/g)].map((m) => m[1]),
			// The component layer also declares a few locals of its own (e.g.
			// --cds-modal-pad, which carries the modal's responsive padding into
			// the header's bleed calculation).
			...[...componentsCss.matchAll(/^\s*(--cds-[\w-]+)\s*:/gm)].map(
				(m) => m[1],
			),
		])

		expect(referenced.size).toBeGreaterThan(20)
		expect([...referenced].filter((t) => !declared.has(t)).sort()).toEqual([])
	})
})

describe('CDS typography layer', () => {
	it('re-declares the weight variants frappe-ui registers as components', () => {
		// These are addComponents output, unreachable from theme.fontSize — the
		// only way to move them is to re-declare the class.
		for (const cls of [
			'.text-lg-semibold',
			'.text-p-base-medium',
			'.text-4xl-semibold',
			'.text-base-semibold',
		]) {
			expect(typographyCss).toContain(cls)
		}
	})

	it('uses Cloudscape headings weight and drops Inter tracking', () => {
		expect(typographyCss).toContain('font-weight: 700')
		expect(typographyCss).not.toContain('0.02em')
		expect(typographyCss).toContain('Open Sans Variable')
	})
})

describe('frappe-ui Button contract', () => {
	// src/styles/cds-components.css selects buttons by this exact class list.
	const BASE_CLASSES =
		"'inline-flex items-center justify-center gap-2 transition-colors shrink-0'"

	it('still emits the base class list the component layer selects on', () => {
		expect(buttonSource).toContain(BASE_CLASSES)
		expect(componentsCss).toContain(
			'.inline-flex.items-center.justify-center.transition-colors.shrink-0',
		)
	})

	it('still uses the variant utilities each CDS button role is keyed to', () => {
		// gray-solid + blue-solid -> CDS primary; blue-subtle + gray-outline ->
		// CDS normal; bg-transparent -> ghost. Losing any of these mappings
		// leaves that button role on frappe-ui's styling.
		for (const utility of [
			'bg-surface-gray-10', // gray solid
			'bg-surface-blue-6', // blue solid
			'bg-surface-blue-2', // blue subtle
			'border-outline-gray-2', // gray outline
			'bg-transparent', // ghost
		]) {
			expect(buttonSource).toContain(utility)
			expect(componentsCss).toContain(utility)
		}
	})

	it('still emits the height utilities the padding scale is keyed to', () => {
		// Padding has to scale with size or dense toolbars overflow.
		for (const h of ['h-6', 'h-7', 'h-8', 'h-10']) {
			expect(buttonSource).toContain(h)
			expect(componentsCss).toContain(`.${h} {`)
		}
	})
})
