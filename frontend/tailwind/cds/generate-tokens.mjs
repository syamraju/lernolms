/*
 * Generates `src/styles/cds-tokens.css` — the Cloudscape (CDS) override layer.
 *
 * The app renders almost entirely through frappe-ui's semantic CSS custom
 * properties (`--surface-*`, `--ink-*`, `--outline-*`, `--radius-*`,
 * `--elevation-*`): 1143 token-class usages against 39 hardcoded colours. So
 * re-pointing those variables re-skins the whole product without touching the
 * 235 component files.
 *
 * frappe-ui emits its variables from a Tailwind plugin at `:root` and
 * `[data-theme="dark"]`. This file is imported after `frappe-ui/style.css`, so
 * an identical selector with the same specificity wins on source order.
 *
 * Run: node tailwind/cds/generate-tokens.mjs
 */
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const src = JSON.parse(readFileSync(resolve(here, 'cds-source.json'), 'utf8'))
const P = src.palette

/* ---------------------------------------------------------------- ramps --
 * frappe-ui indexes every hue 1..10 (ink and outline stop at 9 for gray).
 * These arrays say which CDS palette step each index takes, mirroring the
 * shape of frappe-ui's own light/dark mapping so component code that assumes
 * "higher index = stronger" keeps holding.
 */
const RAMP = {
	light: {
		surface: [
			'50',
			'100',
			'200',
			'300',
			'400',
			'500',
			'600',
			'700',
			'800',
			'900',
		],
		ink: [
			'#ffffff',
			'100',
			'200',
			'300',
			'400',
			'500',
			'600',
			'700',
			'800',
			'900',
		],
		outline: [
			'100',
			'200',
			'300',
			'400',
			'500',
			'600',
			'700',
			'800',
			'900',
			'950',
		],
	},
	dark: {
		surface: [
			'950',
			'900',
			'800',
			'700',
			'600',
			'500',
			'400',
			'300',
			'200',
			'100',
		],
		ink: [
			'#ffffff',
			'800',
			'700',
			'600',
			'500',
			'400',
			'300',
			'200',
			'100',
			'50',
		],
		outline: [
			'900',
			'800',
			'700',
			'600',
			'500',
			'400',
			'300',
			'200',
			'100',
			'50',
		],
	},
}

/* Gray is hand-mapped rather than generated. CDS ships a 19-step grey scale
 * (50…1000) built for a system that leans on borders instead of shadows, so a
 * naive 10-step slice skips the exact greys Cloudscape uses for dividers
 * (#dedee3, #c6c6cd) and body text (#0f141a, #424650). These anchor on the
 * real semantic values — see `semantic` in cds-source.json. */
const GRAY = {
	light: {
		surface: [
			'#f9f9fa',
			'#f3f3f7',
			'#ebebf0',
			'#dedee3',
			'#c6c6cd',
			'#b4b4bb',
			'#8c8c94',
			'#656871',
			'#424650',
			'#0f141a',
		],
		ink: [
			'#dedee3',
			'#c6c6cd',
			'#b4b4bb',
			'#8c8c94',
			'#656871',
			'#424650',
			'#333843',
			'#232b37',
			'#0f141a',
		],
		outline: [
			'#dedee3',
			'#c6c6cd',
			'#b4b4bb',
			'#8c8c94',
			'#656871',
			'#424650',
			'#333843',
			'#232b37',
			'#0f141a',
		],
	},
	dark: {
		surface: [
			'#1b232d',
			'#232b37',
			'#333843',
			'#424650',
			'#656871',
			'#8c8c94',
			'#a4a4ad',
			'#c6c6cd',
			'#dedee3',
			'#f9f9fa',
		],
		ink: [
			'#232b37',
			'#333843',
			'#424650',
			'#656871',
			'#8c8c94',
			'#a4a4ad',
			'#c6c6cd',
			'#dedee3',
			'#f9f9fa',
		],
		outline: [
			'#333843',
			'#424650',
			'#656871',
			'#8c8c94',
			'#a4a4ad',
			'#c6c6cd',
			'#dedee3',
			'#ebebf0',
			'#f9f9fa',
		],
	},
}

/* CDS has no alpha grey scale. These approximate the solid ramps as
 * translucency so overlay surfaces (which is all `*-alpha-*` is used for) still
 * composite over whatever sits behind them. */
const ALPHA = {
	light: [
		'#0f141a08',
		'#0f141a0d',
		'#0f141a17',
		'#0f141a24',
		'#0f141a3d',
		'#0f141a52',
		'#0f141a78',
		'#0f141aa1',
		'#0f141ac7',
		'#0f141a',
	],
	dark: [
		'#ffffff0a',
		'#ffffff14',
		'#ffffff1f',
		'#ffffff2e',
		'#ffffff42',
		'#ffffff5c',
		'#ffffff7a',
		'#ffffff99',
		'#ffffffc7',
		'#ffffff',
	],
}

/* frappe-ui hue name -> CDS palette name. Everything maps 1:1 except gray. */
const HUES = {
	red: 'red',
	blue: 'blue',
	green: 'green',
	amber: 'amber',
	violet: 'violet',
	yellow: 'yellow',
	orange: 'orange',
	teal: 'teal',
	cyan: 'cyan',
	purple: 'purple',
	pink: 'pink',
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
	ALPHA[theme]
		.slice(0, 9)
		.forEach((v, i) => push(`--outline-alpha-gray-${i + 1}`, v))

	// colour hues
	for (const [fu, cds] of Object.entries(HUES)) {
		RAMP[theme].surface.forEach((s, i) =>
			push(`--surface-${fu}-${i + 1}`, step(cds, s))
		)
		RAMP[theme].ink.forEach((s, i) =>
			push(`--ink-${fu}-${i + 1}`, step(cds, s))
		)
		RAMP[theme].outline.forEach((s, i) =>
			push(`--outline-${fu}-${i + 1}`, step(cds, s))
		)
	}
	return out
}

/* Named anchors, taken straight from CDS semantic tokens rather than derived
 * from a ramp — these are the ones that set the product's character. */
const S = src.semantic
const pick = (key, theme) => S[key][theme === 'light' ? 0 : 1]

function anchors(theme) {
	const t = (k) => pick(k, theme)
	const dark = theme === 'dark'
	return [
		['--surface-base', t('background/layout/main')],
		['--surface-alpha-base', t('background/layout/main')],
		['--surface-sidebar', dark ? '#131920' : '#f9f9fa'],
		['--surface-alpha-sidebar', dark ? '#131920' : '#f9f9fa'],
		[
			'--surface-elevation-1',
			dark ? '#1b232d' : t('background/container/content'),
		],
		[
			'--surface-elevation-2',
			dark ? '#232b37' : t('background/container/content'),
		],
		[
			'--surface-elevation-3',
			dark ? '#333843' : t('background/container/content'),
		],
		[
			'--surface-alpha-elevation-1',
			dark ? '#1b232d' : t('background/container/content'),
		],
		[
			'--surface-alpha-elevation-2',
			dark ? '#232b37' : t('background/container/content'),
		],
		[
			'--surface-alpha-elevation-3',
			dark ? '#333843' : t('background/container/content'),
		],
		['--surface-alpha-gray-2-overlay', dark ? '#ffffff14' : '#0f141a0d'],

		['--ink-base', t('background/layout/main')],
		// CDS links are blue/600 light, blue/400 dark — not the ramp's blue-5.
		['--ink-blue-link', t('text/link/default')],

		['--outline-base', t('background/layout/main')],
		['--outline-alpha-base', t('background/layout/main')],
		['--outline-elevation-1', t('border/layout')],
		['--outline-elevation-2', t('border/divider/default')],
		['--outline-alpha-elevation-1', t('border/layout')],
		['--outline-alpha-elevation-2', t('border/divider/default')],

		['--surface-alert-button-default', dark ? '#424650' : '#ffffff'],
		['--surface-alert-button-info', dark ? '#004a9e' : '#ffffff'],
		['--surface-alert-button-success', dark ? '#007029' : '#ffffff'],
		['--surface-alert-button-warning', dark ? '#db9200' : '#ffffff'],
		['--surface-alert-button-error', dark ? '#c20000' : '#ffffff'],
		['--ink-alert-button-default', dark ? '#f9f9fa' : '#0f141a'],
		['--ink-alert-button-info', dark ? '#b8e7ff' : '#0f141a'],
		['--ink-alert-button-success', dark ? '#aeffa8' : '#0f141a'],
		['--ink-alert-button-warning', dark ? '#fef571' : '#0f141a'],
		['--ink-alert-button-error', dark ? '#ffc2c2' : '#0f141a'],

		// Shadow colour drives every --elevation-* below.
		['--cds-shadow', t('shadow/dropdown/color')],
	]
}

/* Cloudscape is a border-led system: shadows are few, tight and low-opacity.
 * `lg` reproduces the CDS dropdown shadow exactly (0 4 20 1 from the `borders`
 * collection); the rest interpolate around it. */
function elevations() {
	return [
		['--elevation-sm', '0px 1px 2px 0px var(--cds-shadow)'],
		['--elevation-base', '0px 1px 4px 1px var(--cds-shadow)'],
		['--elevation-md', '0px 2px 8px 1px var(--cds-shadow)'],
		['--elevation-lg', '0px 4px 20px 1px var(--cds-shadow)'],
		['--elevation-xl', '0px 6px 24px 2px var(--cds-shadow)'],
		['--elevation-2xl', '0px 12px 40px 4px var(--cds-shadow)'],
	]
}

/* frappe-ui's numeric radius scale rewritten to CDS's. The signature values are
 * the 20px pill button and the 16px container. */
function radii() {
	const R = src.radius
	return [
		['--radius-0', '0px'],
		['--radius-1', `${R.badge}px`],
		['--radius-2', '6px'],
		['--radius-3', `${R.input}px`],
		['--radius-4', `${R.item}px`],
		['--radius-5', `${R.dropdown}px`],
		['--radius-6', `${R.alert}px`],
		['--radius-7', `${R.container}px`],
		['--radius-8', `${R.button}px`],
		['--radius-9', '999px'],
		['--radius-none', '0px'],
		['--radius-sm', `${R.badge}px`],
		['--radius-md', `${R.dropdown}px`],
		['--radius-lg', `${R.alert}px`],
		['--radius-xl', `${R.container}px`],
		['--radius-2xl', `${R.button}px`],
		['--radius-full', '9999px'],
	]
}

/* The raw palette as `--<hue>-<step>` custom properties.
 *
 * frappe-ui exposes its palette to Tailwind as *colours* (class names), never
 * as CSS variables — only the 406 themed variables become custom properties.
 * Hand-written CSS that reaches for `var(--blue-400)` therefore resolves to
 * nothing: CourseCard.vue builds its gradient as
 * `linear-gradient(to top right, black, var(--blue-400))`, and with the var
 * undefined the whole gradient value is invalid at computed-value time and the
 * card falls back to no gradient at all. Declaring the palette fixes that and
 * puts those gradients on CDS colours.
 */
function paletteVars() {
	const out = []
	for (const [hue, steps] of Object.entries(P)) {
		for (const [s, value] of Object.entries(steps))
			out.push([`--${hue}-${s}`, value])
	}
	// CourseCard's `card_gradient` values use frappe-ui's `gray` spelling.
	for (const [s, value] of Object.entries(P.grey))
		out.push([`--gray-${s}`, value])
	out.push(['--white', '#ffffff'], ['--black', '#000000'])
	return out
}

/* Raw CDS scales, exposed so component-level CSS can reach them directly. */
function cdsScales() {
	const out = []
	for (const [k, v] of Object.entries(src.spacing))
		out.push([`--cds-space-${k}`, `${v}px`])
	for (const [k, v] of Object.entries(src.radius))
		out.push([`--cds-radius-${k.replace(/\//g, '-')}`, `${v}px`])
	for (const [k, v] of Object.entries(src.borderWidth))
		out.push([`--cds-border-${k.replace(/\//g, '-')}`, `${v}px`])
	for (const [k, v] of Object.entries(src.sizes))
		out.push([`--cds-size-${k.replace(/\//g, '-')}`, `${v}px`])
	return out
}

/* CDS semantic tokens kept under their own namespace. The ramp overrides above
 * cover component code that already uses frappe-ui classes; these give
 * hand-written CSS a way to name a Cloudscape role exactly. */
function cdsSemantic(theme) {
	return Object.entries(S)
		.filter(([k]) => !k.startsWith('_'))
		.map(([k, v]) => [
			`--cds-${k.replace(/\//g, '-')}`,
			v[theme === 'light' ? 0 : 1],
		])
}

const block = (selector, pairs, indent = '\t') =>
	`${selector} {\n${pairs
		.map(([k, v]) => `${indent}${k}: ${v};`)
		.join('\n')}\n}`

const header = `/*
 * Cloudscape (CDS) token layer — GENERATED, do not edit by hand.
 *
 * Source:    CDS Component Library 2.0.2 (Community), Figma file fZ2UxXNEQ9EAEgNtOT7yB1
 * Generator: tailwind/cds/generate-tokens.mjs
 * Data:      tailwind/cds/cds-source.json
 * Regenerate: node tailwind/cds/generate-tokens.mjs
 *
 * Imported after frappe-ui/style.css in src/index.css, so these declarations
 * override frappe-ui's defaults on source order at equal specificity.
 */`

const css = [
	header,
	'',
	'/* ---------------------------------------------------------------- light */',
	block(':root', [
		...paletteVars(),
		...ramps('light'),
		...anchors('light'),
		...elevations(),
		...radii(),
		...cdsScales(),
		...cdsSemantic('light'),
	]),
	'',
	'/* ----------------------------------------------------------------- dark */',
	block('[data-theme="dark"]', [
		...ramps('dark'),
		...anchors('dark'),
		...cdsSemantic('dark'),
	]),
	'',
].join('\n')

const outPath = resolve(here, '../../src/styles/cds-tokens.css')
mkdirSync(dirname(outPath), { recursive: true })
writeFileSync(outPath, css)

const count = (s) => (css.match(new RegExp(s, 'g')) || []).length
console.log(`wrote ${outPath}`)
console.log(`  declarations: ${count(';')}`)
console.log(`  --surface-*:  ${count('--surface-')}`)
console.log(`  --ink-*:      ${count('--ink-')}`)
console.log(`  --outline-*:  ${count('--outline-')}`)
console.log(`  --cds-*:      ${count('--cds-')}`)
