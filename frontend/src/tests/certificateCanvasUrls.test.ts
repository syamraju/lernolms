import { beforeAll, describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import CertificateCanvas from '@/components/Certificates/CertificateCanvas.vue'
import type {
	CertificateElement,
	CertificateTemplate,
} from '@/utils/certificate'
import { installTranslate, translate } from './translateStub'

// The canvas measures itself on mount; jsdom has no ResizeObserver.
class StubResizeObserver {
	observe() {}
	unobserve() {}
	disconnect() {}
}

const template = (over: Partial<CertificateTemplate> = {}): CertificateTemplate => ({
	reference_doctype: 'LMS Course',
	reference_name: 'course-1',
	background_image: null,
	canvas_width: 1754,
	canvas_height: 1240,
	issue_date_source: 'Completion Date',
	custom_issue_date: null,
	is_complete: 1,
	elements: [],
	...over,
})

const imageElement = (image: string): CertificateElement =>
	({
		element_type: 'Image',
		image,
		x: 0,
		y: 0,
		width: 100,
		height: 100,
		align: 'Left',
	}) as unknown as CertificateElement

// Templates resolve `__` through the app's globalProperties, not the window, so
// installTranslate alone leaves `_ctx.__` undefined and the placeholder branch
// throws instead of rendering.
const render = (doc: CertificateTemplate) =>
	mount(CertificateCanvas, {
		props: { template: doc, variables: [] },
		global: { config: { globalProperties: { __: translate } as any } },
	})

describe('CertificateCanvas URL handling', () => {
	beforeAll(() => {
		installTranslate()
		;(globalThis as any).ResizeObserver = StubResizeObserver
	})

	it('renders a legitimate background and image', () => {
		const wrapper = render(
			template({
				background_image: '/files/bg.png',
				elements: [imageElement('/files/seal.png')],
			})
		)
		const sources = wrapper.findAll('img').map((img) => img.attributes('src'))

		expect(sources).toContain('/files/bg.png')
		expect(sources).toContain('/files/seal.png')
	})

	// A certificate template is author-supplied and this canvas is what the
	// PUBLIC verification page renders, so a hostile URL stored on the template
	// would reach a stranger's browser.
	it.each([
		['javascript:alert(1)'],
		['JaVaScRiPt:alert(1)'],
		['data:text/html,<script>alert(1)</script>'],
		['//evil.example.com/bg.png'],
		['/\\evil.example.com/bg.png'],
	])('refuses %s as a background', (hostile) => {
		const wrapper = render(template({ background_image: hostile }))

		expect(wrapper.find('img').exists()).toBe(false)
		// Not merely src-less: the placeholder is the honest failure, and an
		// <img> with no src renders as a broken-image icon.
		expect(wrapper.text()).toContain('No background uploaded yet')
	})

	it.each([['javascript:alert(1)'], ['data:text/html,x'], ['//evil.example.com/s.png']])(
		'refuses %s as an element image',
		(hostile) => {
			const wrapper = render(
				template({ background_image: '/files/bg.png', elements: [imageElement(hostile)] })
			)
			const sources = wrapper.findAll('img').map((img) => img.attributes('src'))

			expect(sources).not.toContain(hostile)
			expect(wrapper.text()).toContain('No image')
		}
	)

	it('never emits an empty src, which would re-request the page', () => {
		const wrapper = render(
			template({ background_image: 'javascript:alert(1)', elements: [imageElement('data:x')] })
		)
		for (const img of wrapper.findAll('img')) {
			expect(img.attributes('src')).not.toBe('')
		}
	})
})
