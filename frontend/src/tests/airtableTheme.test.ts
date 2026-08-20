/**
 * Guards the Airtable theme layer.
 *
 * The theme is not written into the components — it re-points frappe-ui's own
 * CSS variables and re-declares a handful of its classes (see
 * src/styles/airtable-*.css and tailwind/airtable/). That keeps the diff small,
 * but it means the theme depends on two things staying true of the frappe-ui
 * package:
 *
 *   1. the set of themed CSS variables it declares, and
 *   2. the class list Button.vue emits, which is the only selector the
 *      component layer can anchor on.
 *
 * Neither is a public API. If a frappe-ui upgrade moves either, the app does
 * not crash — it quietly renders half-Espresso, half-Airtable, which is the
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

const tokensCss = read('src/styles/airtable-tokens.css')
const typographyCss = read('src/styles/airtable-typography.css')
const componentsCss = read('src/styles/airtable-components.css')
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

describe('Airtable token layer', () => {
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

	it('anchors the signature surfaces on Airtable values', () => {
		// background/app, text/default, border/default and the 3px button
		// radius — the four that set the product's character.
		expect(tokensCss).toContain('--surface-base: #FFFFFF')
		expect(tokensCss).toContain('--surface-base: #181818')
		expect(tokensCss).toContain('--ink-gray-9: #333333')
		expect(tokensCss).toContain('--outline-gray-1: #E0E0E0')
		expect(tokensCss).toContain('--ink-blue-link: #2D7FF9')
		// The single loudest difference from the Cloudscape theme this replaced,
		// where --radius-8 was a 20px pill.
		expect(tokensCss).toContain('--radius-8: 3px')
	})

	it('keeps resting surfaces flat — Airtable separates with hairlines', () => {
		// frappe-ui puts --elevation-base on cards and list rows. Giving those a
		// real shadow is the fastest way to stop looking like Airtable, so both
		// of the in-page steps are explicitly none and only floating things lift.
		expect(tokensCss).toContain('--elevation-sm: none')
		expect(tokensCss).toContain('--elevation-base: none')
		expect(tokensCss).toMatch(/--elevation-lg: 0px 4px 12px/)
	})

	it('declares the raw palette so var(--blue-400) style lookups resolve', () => {
		// CourseCard builds its gradient from these; frappe-ui never defined
		// them, so the whole gradient was invalid at computed-value time.
		// Airtable's own step names are published alongside the numeric ones the
		// stored `card_gradient` values use.
		expect(tokensCss).toContain('--blue-400:')
		expect(tokensCss).toContain('--gray-500:')
		expect(tokensCss).toContain('--blue-Bright: #2D7FF9')
	})

	it('leaves no Espresso oklch values in the override layer', () => {
		expect(tokensCss).not.toMatch(/oklch\(/)
	})

	// airtable-source.json carries `_note` documentation keys, and the palette
	// loop iterates the file's own structure. Iterating a `_note` *string* with
	// Object.entries yields one entry per character, which emitted
	// `--_note-45: '` — an apostrophe esbuild reads as an unterminated string
	// when it minifies the bundle. The build only warned; it did not fail.
	it('emits no variables from the source file documentation keys', () => {
		expect(tokensCss).not.toMatch(/--_/)
		expect(tokensCss).not.toMatch(/:\s*undefined/)
		// Every declared value is a colour, a length, a shadow or a keyword —
		// never a stray character from a prose string.
		const oneChar = [...tokensCss.matchAll(/(--[\w-]+):\s*(.)\s*;/g)].filter(
			([, , v]) => !/[a-z0-9)]/i.test(v),
		)
		expect(oneChar.map((m) => m[0])).toEqual([])
	})

	// Border widths are `--at-stroke-*` and border colours are `--at-border-*`.
	// They were one prefix at first, and `border/container` existed in both
	// sets: the colour overwrote the width, and a length property handed a hex
	// is dropped silently. Keep them disjoint.
	it('keeps border widths and border colours in separate namespaces', () => {
		const strokes = [
			...tokensCss.matchAll(/(--at-stroke-[\w-]+)\s*:\s*([^;]+)/g),
		]
		expect(strokes.length).toBeGreaterThan(4)
		for (const [, name, value] of strokes) {
			expect(`${name} = ${value}`).toMatch(/= \d+px$/)
		}
		expect(tokensCss).not.toMatch(/--at-border-[\w-]+:\s*\d+px/)
	})

	// The component layer names Airtable roles directly (`var(--at-text-label)`).
	// A typo or a token that was never extracted from Figma resolves to nothing
	// and the property is simply dropped — the element keeps frappe-ui's value
	// and nothing anywhere reports a problem.
	it('declares every --at-* token the component layer references', () => {
		const referenced = new Set(
			[...componentsCss.matchAll(/var\((--at-[\w-]+)/g)].map((m) => m[1]),
		)
		const declared = new Set([
			...[...tokensCss.matchAll(/(--at-[\w-]+)\s*:/g)].map((m) => m[1]),
			// The component layer also declares a few locals of its own (e.g.
			// --at-modal-pad, which carries the modal's responsive padding into
			// the header's bleed calculation).
			...[...componentsCss.matchAll(/^\s*(--at-[\w-]+)\s*:/gm)].map(
				(m) => m[1],
			),
		])

		expect(referenced.size).toBeGreaterThan(20)
		expect([...referenced].filter((t) => !declared.has(t)).sort()).toEqual([])
	})
})

describe('Airtable typography layer', () => {
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

	it('ships Inter and drops frappe-ui Inter-specific axis pins', () => {
		// The kit specifies SF Pro, which cannot be bundled. Inter is the
		// substitute — but frappe-ui pins `opsz` to 24 and `cv11` to 1, and both
		// have to be cleared: opsz 24 is a display size applied to 13px body.
		expect(typographyCss).toContain('Inter Variable')
		expect(typographyCss).toContain('font-variation-settings: normal')
		expect(typographyCss).toContain('font-optical-sizing: auto')
		expect(typographyCss).not.toContain('0.02em')
	})

	it('makes headings lighter as they get larger', () => {
		// The most characteristic thing about Airtable's headings, and the exact
		// inverse of Cloudscape's uniform 700. Heading/xsmall (15px) is Bold,
		// Heading/small (17px) Semibold, Heading/default (21px) and up Medium.
		const weightOf = (cls: string) => {
			const i = typographyCss.indexOf(`${cls} {`)
			expect(i, `${cls} missing`).toBeGreaterThan(-1)
			const block = typographyCss.slice(i, typographyCss.indexOf('\t}', i))
			return block.match(/font-weight:\s*(\d+)/)?.[1]
		}
		expect(weightOf('.text-base-semibold')).toBe('700') // 13px
		expect(weightOf('.text-lg-semibold')).toBe('700') // 15px
		expect(weightOf('.text-2xl-semibold')).toBe('600') // 17px
		expect(weightOf('.text-3xl-semibold')).toBe('500') // 21px
		expect(weightOf('.text-4xl-semibold')).toBe('500') // 23px
	})

	it('puts body text on Airtable 13px, not a general-purpose 14px', () => {
		// `base` is what most body copy in this codebase resolves to, and the
		// one number that most makes the app read as Airtable.
		const i = typographyCss.indexOf('.text-base-medium {')
		const block = typographyCss.slice(i, typographyCss.indexOf('\t}', i))
		expect(block).toContain('font-size: 13px')
	})
})

describe('frappe-ui Button contract', () => {
	// src/styles/airtable-components.css selects buttons by this exact class list.
	const BASE_CLASSES =
		"'inline-flex items-center justify-center gap-2 transition-colors shrink-0'"

	it('still emits the base class list the component layer selects on', () => {
		expect(buttonSource).toContain(BASE_CLASSES)
		expect(componentsCss).toContain(
			'.inline-flex.items-center.justify-center.transition-colors.shrink-0',
		)
	})

	it('still uses the variant utilities each Airtable button role is keyed to', () => {
		// gray-solid + blue-solid -> Airtable primary; blue-subtle + gray-outline
		// -> Airtable default (flat grey); bg-transparent -> ghost; red -> the
		// kit's real danger button. Losing any of these mappings leaves that
		// button role on frappe-ui's styling.
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

describe('Airtable component shape', () => {
	// These are the traits a reader would check a screenshot against. Each one
	// is the opposite of what the Cloudscape layer did, so a half-applied swap
	// shows up here rather than in review.
	it('fills inputs instead of outlining them', () => {
		const i = componentsCss.indexOf('input.bg-surface-gray-2,')
		const block = componentsCss.slice(i, componentsCss.indexOf('\n}', i))
		expect(block).toContain(
			'background-color: var(--at-background-input-default)',
		)
		expect(block).toContain('border-width: 0')
	})

	it('gives buttons no border and a medium label', () => {
		const i = componentsCss.indexOf(
			'.inline-flex.items-center.justify-center.transition-colors.shrink-0 {',
		)
		const block = componentsCss.slice(i, componentsCss.indexOf('\n}', i))
		expect(block).toContain('border-radius: var(--at-radius-button)')
		expect(block).toContain('border-width: 0')
		expect(block).toContain('font-weight: 500')
	})

	it('keeps placeholders upright — the italic was a Cloudscape trait', () => {
		expect(componentsCss).not.toContain('font-style: italic')
	})

	it('makes the active segment grey, reserving blue for the primary action', () => {
		expect(tokensCss).toContain('--at-background-segment-active: #666666')
	})
})
