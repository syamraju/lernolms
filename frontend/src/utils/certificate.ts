/**
 * Certificate design, on the client side.
 *
 * The moderator uploads a background image and places things on top of it. Every
 * coordinate here is in that image's own pixels, never in screen pixels: the
 * editor renders at whatever width the viewport allows, the public verification
 * page renders at another, and both have to produce the same certificate. One
 * `scale` factor converts at the last moment, in `elementStyle`.
 *
 * `missingRequirements` deliberately re-implements the server's check of the
 * same name. The server's answer is the one that gates the instructor handoff;
 * this one exists so the checklist ticks as the moderator drags a field onto the
 * canvas rather than a round-trip later. They are kept honest by taking the
 * mandatory list from the server rather than hard-coding it here.
 */

export type ElementType = 'Variable' | 'Text' | 'Image'
export type TextAlign = 'left' | 'center' | 'right'

export interface CertificateVariable {
	key: string
	label: string
	type: 'text' | 'date'
	mandatory: boolean
	hint?: string
}

export interface CertificateElement {
	element_type: ElementType
	variable?: string | null
	content?: string | null
	image?: string | null
	date_format?: string | null
	x: number
	y: number
	width: number
	height: number
	rotation: number
	font_family: string
	font_size: number
	font_weight: string
	italic: 0 | 1
	letter_spacing: number
	color: string
	align: TextAlign
	opacity: number
}

export interface CertificateTemplate {
	name?: string | null
	reference_doctype: string
	reference_name: string
	background_image: string | null
	canvas_width: number
	canvas_height: number
	issue_date_source: 'Completion Date' | 'Custom Date'
	custom_issue_date: string | null
	is_complete: 0 | 1
	elements: CertificateElement[]
}

export interface MissingRequirement {
	code: string
	message: string
}

/** An A4 landscape sheet at 150dpi — what certificate artwork is usually exported as. */
export const DEFAULT_CANVAS = { width: 1754, height: 1240 }

export const DATE_FORMATS = [
	'd MMMM yyyy',
	'MMMM d, yyyy',
	'dd/MM/yyyy',
	'dd-MM-yyyy',
	'yyyy-MM-dd',
]

export const DEFAULT_DATE_FORMAT = 'd MMMM yyyy'

export function blankTemplate(
	referenceDoctype: string,
	referenceName: string,
): CertificateTemplate {
	return {
		name: null,
		reference_doctype: referenceDoctype,
		reference_name: referenceName,
		background_image: null,
		canvas_width: DEFAULT_CANVAS.width,
		canvas_height: DEFAULT_CANVAS.height,
		issue_date_source: 'Completion Date',
		custom_issue_date: null,
		is_complete: 0,
		elements: [],
	}
}

/**
 * Pull one element back inside the canvas, returning a new element.
 *
 * Mirrors the server's clamp so a box dragged past the edge snaps back under
 * the pointer instead of snapping back only after a save.
 */
export function clampElement(
	element: CertificateElement,
	canvasWidth: number,
	canvasHeight: number,
): CertificateElement {
	const width = Math.min(Math.max(element.width || 0, 1), canvasWidth)
	const height = Math.min(Math.max(element.height || 0, 1), canvasHeight)
	return {
		...element,
		width,
		height,
		x: Math.min(Math.max(element.x || 0, 0), canvasWidth - width),
		y: Math.min(Math.max(element.y || 0, 0), canvasHeight - height),
	}
}

/** Everything standing between this design and a certificate that can be issued. */
export function missingRequirements(
	variables: CertificateVariable[],
	background: string | null | undefined,
	elements: CertificateElement[],
): MissingRequirement[] {
	const missing: MissingRequirement[] = []

	if (!background) {
		missing.push({
			code: 'background',
			message: __('Upload a certificate background (PNG or JPG)'),
		})
	}

	const placed = new Set(
		(elements || [])
			.filter((element) => element.element_type === 'Variable')
			.map((element) => element.variable || ''),
	)
	for (const variable of variables) {
		if (variable.mandatory && !placed.has(variable.key)) {
			missing.push({
				code: variable.key,
				message: __('Place {0} on the certificate').format(variable.label),
			})
		}
	}

	return missing
}

/**
 * A new box, sized and placed so it lands somewhere useful.
 *
 * Each one is dropped a little lower than the last. Stacking every new element
 * on the exact same spot makes the second one look like it was never added.
 */
export function newElement(
	kind: ElementType,
	canvas: { width: number; height: number },
	index = 0,
	variable?: CertificateVariable,
): CertificateElement {
	const width = Math.round(canvas.width * 0.6)
	const fontSize = Math.round(canvas.height * 0.035)
	const height = Math.round(fontSize * 1.6)
	const offset = (index % 8) * Math.round(height * 1.25)

	return {
		element_type: kind,
		variable: kind === 'Variable' ? (variable?.key ?? null) : null,
		content: kind === 'Text' ? __('Double click to edit') : null,
		image: null,
		date_format:
			kind === 'Variable' && variable?.type === 'date'
				? DEFAULT_DATE_FORMAT
				: null,
		x: Math.round((canvas.width - width) / 2),
		y: Math.round(canvas.height * 0.35) + offset,
		width: kind === 'Image' ? Math.round(canvas.width * 0.15) : width,
		height: kind === 'Image' ? Math.round(canvas.width * 0.15) : height,
		rotation: 0,
		font_family: 'Inter',
		font_size: fontSize,
		font_weight: '400',
		italic: 0,
		letter_spacing: 0,
		color: '#111827',
		align: 'center',
		opacity: 1,
	}
}

/**
 * Translate a Frappe date format into the dayjs one.
 *
 * The server formats dates with Frappe's tokens and the live preview formats
 * them with dayjs. Storing one format string and converting here is what keeps
 * the preview showing the same date the issued certificate will carry.
 */
export function toDayjsFormat(format?: string | null): string {
	const tokens: Record<string, string> = {
		yyyy: 'YYYY',
		yy: 'YY',
		MMMM: 'MMMM',
		MMM: 'MMM',
		MM: 'MM',
		dd: 'DD',
		d: 'D',
	}
	return (format || DEFAULT_DATE_FORMAT).replace(
		/yyyy|yy|MMMM|MMM|MM|dd|d/g,
		(token) => tokens[token] ?? token,
	)
}

/**
 * The literal text one element draws.
 *
 * A variable with no value renders empty rather than "undefined": a learner who
 * took a course on their own has no batch, and a certificate must not say so in
 * placeholder text.
 */
export function renderValue(
	element: CertificateElement,
	variables: CertificateVariable[],
	values: Record<string, unknown>,
	formatDate: (value: string, format: string) => string,
): string {
	if (element.element_type === 'Text') return element.content || ''
	if (element.element_type !== 'Variable') return ''

	const key = element.variable || ''
	const value = values?.[key]
	if (value === null || value === undefined || value === '') return ''

	const variable = variables.find((entry) => entry.key === key)
	if (variable?.type !== 'date') return String(value)
	return formatDate(String(value), toDayjsFormat(element.date_format))
}

export interface CertificateSnapshot {
	background_image: string | null
	canvas_width: number
	canvas_height: number
	elements: (Partial<CertificateElement> & { value?: string })[]
}

/**
 * Turn a frozen certificate back into something the canvas can draw.
 *
 * A snapshot's elements already carry their finished text — resolved on the
 * server the day the certificate was issued. Rewriting them as plain text
 * elements is what lets the public page reuse the designer's renderer without
 * looking up a single course, learner or template, and is why a certificate
 * still shows what was awarded after the course has been renamed.
 */
export function templateFromSnapshot(
	snapshot: CertificateSnapshot | null | undefined,
): CertificateTemplate | null {
	if (!snapshot?.background_image) return null
	const base = blankTemplate('LMS Course', '')
	return {
		...base,
		background_image: snapshot.background_image,
		canvas_width: snapshot.canvas_width || DEFAULT_CANVAS.width,
		canvas_height: snapshot.canvas_height || DEFAULT_CANVAS.height,
		is_complete: 1,
		elements: (snapshot.elements || []).map((element) => ({
			...blankElement(),
			...element,
			element_type: element.element_type === 'Image' ? 'Image' : 'Text',
			variable: null,
			content: element.value ?? '',
		})),
	}
}

function blankElement(): CertificateElement {
	return {
		element_type: 'Text',
		variable: null,
		content: '',
		image: null,
		date_format: null,
		x: 0,
		y: 0,
		width: 1,
		height: 1,
		rotation: 0,
		font_family: 'Inter',
		font_size: 32,
		font_weight: '400',
		italic: 0,
		letter_spacing: 0,
		color: '#111827',
		align: 'center',
		opacity: 1,
	}
}

/**
 * How many screen pixels one canvas pixel is worth right now.
 *
 * Guarded against a zero canvas: a background whose measured width has not
 * arrived yet would otherwise scale every element to infinity for one frame.
 */
export function scaleFor(canvasWidth: number, renderedWidth: number): number {
	if (!canvasWidth || !renderedWidth) return 0
	return renderedWidth / canvasWidth
}

/** The CSS that places one element over the background at the current scale. */
export function elementStyle(
	element: CertificateElement,
	scale: number,
): Record<string, string> {
	return {
		position: 'absolute',
		left: `${element.x * scale}px`,
		top: `${element.y * scale}px`,
		width: `${element.width * scale}px`,
		height: `${element.height * scale}px`,
		transform: element.rotation ? `rotate(${element.rotation}deg)` : 'none',
		opacity: String(element.opacity ?? 1),
		fontFamily: element.font_family || 'Inter',
		fontSize: `${element.font_size * scale}px`,
		fontWeight: element.font_weight || '400',
		fontStyle: element.italic ? 'italic' : 'normal',
		letterSpacing: `${(element.letter_spacing || 0) * scale}px`,
		color: element.color || '#111827',
		textAlign: element.align || 'center',
		lineHeight: '1.2',
	}
}
