import { beforeEach, describe, expect, it } from 'vitest'
import {
	DEFAULT_DATE_FORMAT,
	blankTemplate,
	clampElement,
	elementStyle,
	missingRequirements,
	newElement,
	renderValue,
	scaleFor,
	templateFromSnapshot,
	toDayjsFormat,
} from '@/utils/certificate'
import type {
	CertificateElement,
	CertificateVariable,
} from '@/utils/certificate'
import { installTranslate } from './translateStub'

const VARIABLES: CertificateVariable[] = [
	{
		key: 'participant_name',
		label: 'Participant name',
		type: 'text',
		mandatory: true,
	},
	{ key: 'course_name', label: 'Course name', type: 'text', mandatory: true },
	{
		key: 'issue_date',
		label: 'Certificate issue date',
		type: 'date',
		mandatory: true,
	},
	{ key: 'batch_name', label: 'Batch name', type: 'text', mandatory: false },
]

function element(patch: Partial<CertificateElement> = {}): CertificateElement {
	return { ...newElement('Text', { width: 1000, height: 500 }), ...patch }
}

function variableElement(key: string): CertificateElement {
	return element({ element_type: 'Variable', variable: key, content: null })
}

describe('missingRequirements', () => {
	beforeEach(installTranslate)

	it('reports nothing once the background and every mandatory field are there', () => {
		const elements = VARIABLES.filter((entry) => entry.mandatory).map((entry) =>
			variableElement(entry.key)
		)
		expect(missingRequirements(VARIABLES, '/files/bg.png', elements)).toEqual([])
	})

	it('reports a missing background first', () => {
		const elements = VARIABLES.filter((entry) => entry.mandatory).map((entry) =>
			variableElement(entry.key)
		)
		const missing = missingRequirements(VARIABLES, null, elements)
		expect(missing.map((item) => item.code)).toEqual(['background'])
	})

	it('names every mandatory field that has not been placed', () => {
		const missing = missingRequirements(VARIABLES, '/files/bg.png', [
			variableElement('participant_name'),
		])
		expect(missing.map((item) => item.code)).toEqual([
			'course_name',
			'issue_date',
		])
	})

	// A field the moderator typed as free text carries one learner's name for
	// everybody, so it cannot stand in for the variable.
	it('does not accept free text in place of a variable', () => {
		const elements = [
			element({ content: 'Participant name' }),
			variableElement('course_name'),
			variableElement('issue_date'),
		]
		const missing = missingRequirements(VARIABLES, '/files/bg.png', elements)
		expect(missing.map((item) => item.code)).toEqual(['participant_name'])
	})

	it('never asks for an optional field', () => {
		const elements = VARIABLES.filter((entry) => entry.mandatory).map((entry) =>
			variableElement(entry.key)
		)
		const missing = missingRequirements(VARIABLES, '/files/bg.png', elements)
		expect(missing.map((item) => item.code)).not.toContain('batch_name')
	})
})

describe('clampElement', () => {
	it('leaves an element that already fits alone', () => {
		const clamped = clampElement(
			element({ x: 100, y: 50, width: 200, height: 60 }),
			1000,
			500
		)
		expect([clamped.x, clamped.y]).toEqual([100, 50])
	})

	it('pulls an element back from past the right edge', () => {
		const clamped = clampElement(
			element({ x: 950, y: 10, width: 200, height: 60 }),
			1000,
			500
		)
		expect(clamped.x).toBe(800)
	})

	it('pulls a negative position back to the edge', () => {
		const clamped = clampElement(
			element({ x: -40, y: -10, width: 200, height: 60 }),
			1000,
			500
		)
		expect([clamped.x, clamped.y]).toEqual([0, 0])
	})

	it('caps an element wider than the canvas at the canvas', () => {
		const clamped = clampElement(
			element({ x: 0, y: 0, width: 4000, height: 60 }),
			1000,
			500
		)
		expect(clamped.width).toBe(1000)
	})

	// A box dragged to nothing is invisible and unselectable, which reads as the
	// field having disappeared.
	it('gives a sizeless element a size', () => {
		const clamped = clampElement(
			element({ x: 0, y: 0, width: 0, height: 0 }),
			1000,
			500
		)
		expect([clamped.width, clamped.height]).toEqual([1, 1])
	})

	it('returns a new element rather than moving the one it was given', () => {
		const original = element({ x: -40, y: 0, width: 100, height: 20 })
		clampElement(original, 1000, 500)
		expect(original.x).toBe(-40)
	})
})

describe('newElement', () => {
	beforeEach(installTranslate)

	it('places a variable box inside the canvas', () => {
		const created = newElement(
			'Variable',
			{ width: 1000, height: 500 },
			0,
			VARIABLES[0]
		)
		expect(created.variable).toBe('participant_name')
		expect(created.x).toBeGreaterThanOrEqual(0)
		expect(created.x + created.width).toBeLessThanOrEqual(1000)
	})

	it('gives a date variable a date format and a text one none', () => {
		const date = newElement('Variable', { width: 1000, height: 500 }, 0, VARIABLES[2])
		const text = newElement('Variable', { width: 1000, height: 500 }, 0, VARIABLES[0])
		expect(date.date_format).toBe(DEFAULT_DATE_FORMAT)
		expect(text.date_format).toBeNull()
	})

	// Two fields added in a row landing on the same pixel makes the second look
	// like it was never added.
	it('offsets each new element from the last', () => {
		const first = newElement('Text', { width: 1000, height: 500 }, 0)
		const second = newElement('Text', { width: 1000, height: 500 }, 1)
		expect(second.y).toBeGreaterThan(first.y)
	})

	it('makes an image square rather than a text line', () => {
		const image = newElement('Image', { width: 1000, height: 500 }, 0)
		expect(image.width).toBe(image.height)
	})
})

describe('toDayjsFormat', () => {
	it('translates every format the designer offers', () => {
		expect(toDayjsFormat('d MMMM yyyy')).toBe('D MMMM YYYY')
		expect(toDayjsFormat('MMMM d, yyyy')).toBe('MMMM D, YYYY')
		expect(toDayjsFormat('dd/MM/yyyy')).toBe('DD/MM/YYYY')
		expect(toDayjsFormat('yyyy-MM-dd')).toBe('YYYY-MM-DD')
	})

	it('falls back to the default when nothing is chosen', () => {
		expect(toDayjsFormat(null)).toBe(toDayjsFormat(DEFAULT_DATE_FORMAT))
	})
})

describe('renderValue', () => {
	beforeEach(installTranslate)

	const format = (value: string, pattern: string) => `${value}|${pattern}`

	it('renders a text element from its own content', () => {
		const value = renderValue(element({ content: 'Certificate' }), VARIABLES, {}, format)
		expect(value).toBe('Certificate')
	})

	it('renders a variable from the values it is given', () => {
		const value = renderValue(
			variableElement('participant_name'),
			VARIABLES,
			{ participant_name: 'Asha Rao' },
			format
		)
		expect(value).toBe('Asha Rao')
	})

	it('formats a date variable through the given formatter', () => {
		const value = renderValue(
			{ ...variableElement('issue_date'), date_format: 'dd/MM/yyyy' },
			VARIABLES,
			{ issue_date: '2026-08-21' },
			format
		)
		expect(value).toBe('2026-08-21|DD/MM/YYYY')
	})

	// Printing "undefined" where a learner has no batch is worse than printing
	// nothing at all.
	it('renders nothing for a value that is not there', () => {
		expect(
			renderValue(variableElement('batch_name'), VARIABLES, { batch_name: null }, format)
		).toBe('')
	})
})

describe('templateFromSnapshot', () => {
	it('rebuilds a drawable template from a frozen certificate', () => {
		const template = templateFromSnapshot({
			background_image: '/files/bg.png',
			canvas_width: 2000,
			canvas_height: 1400,
			elements: [
				{ element_type: 'Variable', variable: 'participant_name', value: 'Asha Rao', x: 10 },
			],
		})
		expect(template?.canvas_width).toBe(2000)
		expect(template?.elements[0].content).toBe('Asha Rao')
		expect(template?.elements[0].x).toBe(10)
	})

	// The whole point of freezing: the value travels with the certificate, so
	// nothing downstream may go looking the variable up again.
	it('turns every variable into plain text so nothing is re-resolved', () => {
		const template = templateFromSnapshot({
			background_image: '/files/bg.png',
			canvas_width: 100,
			canvas_height: 100,
			elements: [{ element_type: 'Variable', variable: 'course_name', value: 'Journaling' }],
		})
		expect(template?.elements[0].element_type).toBe('Text')
		expect(template?.elements[0].variable).toBeNull()
	})

	it('keeps an image an image', () => {
		const template = templateFromSnapshot({
			background_image: '/files/bg.png',
			canvas_width: 100,
			canvas_height: 100,
			elements: [{ element_type: 'Image', image: '/files/sign.png', value: '' }],
		})
		expect(template?.elements[0].element_type).toBe('Image')
		expect(template?.elements[0].image).toBe('/files/sign.png')
	})

	it('has nothing to draw without a background', () => {
		expect(templateFromSnapshot(null)).toBeNull()
		expect(
			templateFromSnapshot({
				background_image: null,
				canvas_width: 100,
				canvas_height: 100,
				elements: [],
			})
		).toBeNull()
	})
})

describe('scaleFor and elementStyle', () => {
	it('scales canvas pixels to screen pixels', () => {
		expect(scaleFor(1000, 500)).toBe(0.5)
	})

	// A canvas that has not been measured yet would otherwise scale every
	// element to infinity for a frame.
	it('reports no scale before the canvas has been measured', () => {
		expect(scaleFor(0, 500)).toBe(0)
		expect(scaleFor(1000, 0)).toBe(0)
	})

	it('places and sizes an element at the current scale', () => {
		const style = elementStyle(
			element({ x: 100, y: 50, width: 200, height: 40, font_size: 32 }),
			0.5
		)
		expect(style.left).toBe('50px')
		expect(style.top).toBe('25px')
		expect(style.width).toBe('100px')
		expect(style.fontSize).toBe('16px')
	})

	it('leaves an unrotated element without a transform', () => {
		expect(elementStyle(element({ rotation: 0 }), 1).transform).toBe('none')
		expect(elementStyle(element({ rotation: 15 }), 1).transform).toBe('rotate(15deg)')
	})
})

describe('blankTemplate', () => {
	it('starts empty, incomplete and pointed at its course', () => {
		const template = blankTemplate('LMS Course', 'journaling-101')
		expect(template.reference_name).toBe('journaling-101')
		expect(template.elements).toEqual([])
		expect(template.is_complete).toBe(0)
	})
})
