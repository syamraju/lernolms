import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const translate = (message: string): any => {
	if (!/{\d+}/.test(message)) return message
	return {
		format: (...args: unknown[]) =>
			message.replace(/{(\d+)}/g, (match, index) =>
				args[Number(index)] !== undefined ? String(args[Number(index)]) : match
			),
	}
}

vi.stubGlobal('__', translate)

const { callMock, resources } = vi.hoisted(() => {
	// `@/utils` (pulled in for timeAgo) touches matchMedia at import time, and the
	// hoisted factory runs before any top-level code, so the shim belongs here.
	window.matchMedia ??= (() => ({
		matches: false,
		addEventListener: () => {},
		removeEventListener: () => {},
	})) as unknown as typeof window.matchMedia
	return { callMock: vi.fn(), resources: [] as any[] }
})

// Async factory so `reactive` can be pulled in: the tests drive the component by
// assigning `.data` AFTER mount, and a plain object would never re-render.
vi.mock('frappe-ui', async () => {
	const { reactive } = await import('vue')
	return {
	call: callMock,
	// Each createResource stands in for one endpoint; the test drives them by
	// setting `.data` directly rather than round-tripping through fetch.
	createResource: (options: any) => {
		const resource: any = reactive({
			url: options.url,
			data: null,
			loading: false,
			makeParams: options.makeParams,
			reload: vi.fn(() => Promise.resolve()),
		})
		resources.push(resource)
		return resource
	},
	toast: { success: vi.fn(), error: vi.fn() },
	Avatar: { name: 'Avatar', props: ['label', 'image', 'size'], template: `<span />` },
	Badge: { name: 'Badge', props: ['theme', 'size'], template: `<span class="badge"><slot /></span>` },
	Button: {
		name: 'Button',
		inheritAttrs: false,
		props: ['variant', 'loading', 'disabled', 'label'],
		template: `<button v-bind="$attrs" :disabled="disabled"><slot name="prefix" /><slot name="icon" /><slot /></button>`,
	},
	Dialog: {
		name: 'Dialog',
		props: ['modelValue', 'options'],
		template: `<div><slot name="body-content" /><slot name="actions" /></div>`,
	},
	FormControl: {
		name: 'FormControl',
		props: ['modelValue', 'label', 'type', 'options', 'placeholder'],
		template: `<label>{{ label }}</label>`,
	},
	}
})

import BatchChats from '@/pages/Batches/components/BatchChats.vue'

const channel = (over: Record<string, unknown> = {}) => ({
	name: 'ch-general',
	title: 'general',
	description: '',
	channel_type: 'Discussion',
	audience: 'Everyone',
	post_permission: 'Everyone',
	course: null,
	is_archived: false,
	unread: 0,
	children: [],
	...over,
})

const mountChats = (batchData: Record<string, unknown> = {}) => {
	resources.length = 0
	const wrapper = mount(BatchChats, {
		props: {
			batch: { data: { name: 'march-cohort', ...batchData } },
		},
		global: {
			config: { globalProperties: { __: translate } as any },
			provide: { $user: { data: { name: 'ada@example.com' } } },
			directives: { 'safe-html': {} },
		},
	})
	return wrapper
}

const treeResource = () => resources.find((r) => r.url.endsWith('get_channel_tree'))
const messageResource = () => resources.find((r) => r.url.endsWith('get_messages'))

describe('BatchChats', () => {
	beforeEach(() => {
		callMock.mockReset()
		callMock.mockResolvedValue({})
	})

	it('renders sub-channels under their parent', async () => {
		const wrapper = mountChats()
		treeResource().data = [
			channel({
				children: [channel({ name: 'ch-python', title: 'python-basics' })],
			}),
		]
		await flushPromises()

		const rows = wrapper.findAll('button').map((node) => node.text())
		expect(rows.some((text) => text.includes('general'))).toBe(true)
		expect(rows.some((text) => text.includes('python-basics'))).toBe(true)
	})

	it('opens the first channel rather than leaving an empty pane', async () => {
		const wrapper = mountChats()
		treeResource().data = [channel()]
		await flushPromises()

		expect(messageResource().reload).toHaveBeenCalled()
		expect(callMock).toHaveBeenCalledWith('lms.lms.chat.mark_read', {
			channel: 'ch-general',
		})
	})

	it('hides the composer in a staff-only channel from a student', async () => {
		const wrapper = mountChats()
		treeResource().data = [channel({ post_permission: 'Staff' })]
		await flushPromises()

		expect(wrapper.find('textarea').exists()).toBe(false)
		expect(wrapper.text()).toContain('Only the people running this batch can post')
	})

	it('shows the composer in a staff-only channel to a moderator', async () => {
		const wrapper = mountChats({ is_moderator: 1 })
		treeResource().data = [channel({ post_permission: 'Staff' })]
		await flushPromises()

		expect(wrapper.find('textarea').exists()).toBe(true)
	})

	it('makes an archived channel read-only for a student', async () => {
		const wrapper = mountChats()
		treeResource().data = [channel({ is_archived: true })]
		await flushPromises()

		expect(wrapper.find('textarea').exists()).toBe(false)
		expect(wrapper.text()).toContain('This channel is archived')
	})

	it('still lets a moderator post in an archived channel', async () => {
		const wrapper = mountChats({ is_moderator: 1 })
		treeResource().data = [channel({ is_archived: true })]
		await flushPromises()

		expect(wrapper.find('textarea').exists()).toBe(true)
	})

	it('renders a deleted message as a tombstone, not as blank', async () => {
		const wrapper = mountChats()
		treeResource().data = [channel()]
		await flushPromises()
		messageResource().data = [
			{
				name: 'm1',
				sender: 'grace@example.com',
				sender_name: 'Grace',
				content: null,
				is_deleted: true,
				creation: '2026-08-01 10:00:00',
			},
		]
		await flushPromises()

		expect(wrapper.text()).toContain('This message was deleted')
	})

	it('offers the new-channel control only to a moderator', async () => {
		const student = mountChats()
		treeResource().data = [channel()]
		await flushPromises()
		expect(student.text()).not.toContain('New channel')

		const moderator = mountChats({ is_moderator: 1 })
		treeResource().data = [channel()]
		await flushPromises()
		expect(moderator.text()).toContain('New channel')
	})
})
