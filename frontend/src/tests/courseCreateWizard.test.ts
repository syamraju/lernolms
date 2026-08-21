import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { installTranslate, translate } from './translateStub'

installTranslate()

// Templates resolve `__` through the app's globalProperties, not the window
// global that script blocks reach, so both have to be provided.
const mocks = { __: translate }

// A moderator starts a course they will not write; the instructors step is what
// hands it over. If those emails stop reaching create_course_draft the wizard
// still looks right — it just silently creates a course nobody is told about,
// which is exactly the failure this pins.
const H = vi.hoisted(() => ({ call: vi.fn(), push: vi.fn(), replace: vi.fn() }))

vi.mock('frappe-ui', async () => {
	const passthrough = (name: string) => ({
		name,
		inheritAttrs: false,
		template: `<div v-bind="$attrs"><slot /></div>`,
	})
	const { reactive } = await import('vue')
	return {
		call: H.call,
		// The wizard fetches reference data (certificate variables and the like);
		// an inert resource keeps this test about the steps, not about those.
		createResource: (options: any) =>
			reactive({ options, data: null, loading: false, reload: vi.fn(), submit: vi.fn() }),
		usePageMeta: () => {},
		toast: { success: vi.fn(), error: vi.fn() },
		Avatar: passthrough('Avatar'),
		Button: {
			props: ['label', 'disabled', 'loading'],
			inheritAttrs: false,
			template: `<button v-bind="$attrs" :disabled="disabled">{{ label }}</button>`,
		},
		FormControl: {
			props: ['modelValue'],
			emits: ['update:modelValue'],
			template: `<input :value="modelValue" @input="$emit('update:modelValue', $event.target.value)" />`,
		},
	}
})

vi.mock('vue-router', () => ({
	useRouter: () => ({ push: H.push, replace: H.replace }),
}))

vi.mock('@/utils', () => ({
	canCreateCourse: () => true,
	createLMSCategory: vi.fn(),
}))

vi.mock('@/stores/session', () => ({
	sessionStore: () => ({ brand: { name: 'Learno' } }),
}))

vi.mock('@/components/Controls/Link.vue', () => ({
	default: { template: '<div class="link-stub" />' },
}))

vi.mock('@/components/Controls/MultiLink.vue', () => ({
	default: {
		props: ['modelValue'],
		emits: ['update:modelValue'],
		template: '<div class="multilink-stub" />',
	},
}))

import CourseCreateWizard from '@/pages/Courses/Create/CourseCreateWizard.vue'

async function mountWizard() {
	const wrapper = mount(CourseCreateWizard, { global: { mocks } })
	await flushPromises()
	return wrapper
}

/** Click the footer's primary button, whatever it currently says. */
async function advance(wrapper: any) {
	const buttons = wrapper.findAll('button')
	await buttons[buttons.length - 1].trigger('click')
	await flushPromises()
}

/**
 * Walk to the instructors step, filling in whatever the earlier ones require.
 *
 * Deliberately not "click Continue N times": the wizard grows steps, and a test
 * that pins the count fails on every addition without saying anything about the
 * step it is actually here to check.
 */
async function walkToInstructors(wrapper: any) {
	const vm = wrapper.vm as any
	vm.draft.title = 'Journaling'
	vm.draft.time_commitment = '2-4 hours per week'
	await flushPromises()

	for (let guard = 0; guard < 20; guard += 1) {
		if (vm.current.key === 'instructors') return vm
		await advance(wrapper)
	}
	throw new Error(`never reached the instructors step (stuck on ${vm.current.key})`)
}

describe('CourseCreateWizard', () => {
	beforeEach(() => {
		installTranslate()
		H.call.mockReset()
		H.call.mockResolvedValue('course-1')
		H.push.mockReset()
		H.replace.mockReset()
	})

	// The instructors step is last, because it is the handoff: everything the
	// moderator decides comes before naming the people who take it from here.
	it('ends on the instructors step', async () => {
		const wrapper = await mountWizard()
		expect(wrapper.text()).toContain('Step 1 of')

		const vm = await walkToInstructors(wrapper)

		expect(wrapper.text()).toContain('Who will build this course?')
		expect(vm.STEPS[vm.STEPS.length - 1].key).toBe('instructors')
	})

	it('sends the chosen instructors to the server', async () => {
		const wrapper = await mountWizard()
		const vm = await walkToInstructors(wrapper)
		vm.draft.instructors = ['ada@example.com', 'grace@example.com']
		await flushPromises()
		await advance(wrapper)

		expect(H.call).toHaveBeenCalledWith(
			'lms.lms.course_creation.create_course_draft',
			expect.objectContaining({
				title: 'Journaling',
				instructors: ['ada@example.com', 'grace@example.com'],
			}),
		)
	})

	// The step is skippable on purpose: a course creator building their own
	// course has nobody to invite, and the copy on the step says so.
	it('creates the course with no instructors chosen', async () => {
		const wrapper = await mountWizard()
		await walkToInstructors(wrapper)
		await advance(wrapper)

		expect(H.call).toHaveBeenCalledWith(
			'lms.lms.course_creation.create_course_draft',
			expect.objectContaining({ instructors: [] }),
		)
	})
})
