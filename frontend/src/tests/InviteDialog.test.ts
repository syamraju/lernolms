import { beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

// Faithful to src/translation.js: a message with no {0} placeholder comes back
// as a plain string, and one with placeholders comes back as an object carrying
// only `format`. A stub that always returns a string makes every `.format(...)`
// call in the template throw.
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

const { callMock } = vi.hoisted(() => ({ callMock: vi.fn() }))

vi.mock('frappe-ui', () => ({
	call: callMock,
	toast: { success: vi.fn(), error: vi.fn() },
	Badge: {
		name: 'Badge',
		props: ['theme'],
		template: `<span class="badge" :data-theme="theme"><slot /></span>`,
	},
	// `v-bind="$attrs"` already carries the parent's `@click` through as onClick.
	// Emitting 'click' as well fires the handler a second time, which exhausts the
	// mocked reply and looked like the component clearing its own state.
	Button: {
		name: 'Button',
		inheritAttrs: false,
		props: ['variant', 'loading', 'disabled'],
		template: `<button v-bind="$attrs" :disabled="disabled"><slot /></button>`,
	},
	// The dialog renders its slots inline so the body and actions are queryable
	// without driving a teleport.
	Dialog: {
		name: 'Dialog',
		props: ['modelValue', 'options'],
		template: `<div class="dialog"><slot name="body-content" /><slot name="actions" /></div>`,
	},
}))

import InviteDialog from '@/pages/Batches/components/InviteDialog.vue'

// Templates resolve `__` through the app's globalProperties, not the window, so
// stubGlobal alone leaves `_ctx.__` undefined and every render throws.
const mountDialog = () =>
	mount(InviteDialog, {
		props: { modelValue: true, batch: 'march-cohort' },
		global: { config: { globalProperties: { __: translate } as any } },
	})

const typeAddresses = async (wrapper: any, value: string) => {
	await wrapper.find('textarea').setValue(value)
}

const clickLabelled = async (wrapper: any, label: string) => {
	const button = wrapper
		.findAll('button')
		.find((node: any) => node.text().includes(label))
	expect(button, `no button labelled ${label}`).toBeTruthy()
	await button!.trigger('click')
	await flushPromises()
}

const previewReply = (counts: Record<string, number>, rows: any[]) => ({
	batch: 'march-cohort',
	batch_title: 'March Cohort',
	rows,
	counts: {
		existing: 0,
		new: 0,
		already_enrolled: 0,
		invalid: 0,
		no_seats: 0,
		...counts,
	},
	seats_left: null,
	will_enqueue: false,
	mail_configured: true,
})

describe('InviteDialog', () => {
	beforeEach(() => {
		callMock.mockReset()
	})

	it('writes nothing before the moderator has seen what it would do', async () => {
		callMock.mockResolvedValueOnce(
			previewReply({ new: 2 }, [
				{ email: 'ada@example.com', verdict: 'new' },
				{ email: 'grace@example.com', verdict: 'new' },
			])
		)

		const wrapper = mountDialog()
		await typeAddresses(wrapper, 'ada@example.com\ngrace@example.com')
		await clickLabelled(wrapper, 'Continue')

		expect(callMock).toHaveBeenCalledTimes(1)
		expect(callMock).toHaveBeenCalledWith(
			'lms.lms.batch_invite.preview_invitations',
			{ batch: 'march-cohort', emails: ['ada@example.com', 'grace@example.com'] }
		)
	})

	it('says out loud how many accounts will be created', async () => {
		callMock.mockResolvedValueOnce(
			previewReply({ new: 2, existing: 3 }, [
				{ email: 'ada@example.com', verdict: 'new' },
			])
		)

		const wrapper = mountDialog()
		await typeAddresses(wrapper, 'ada@example.com')
		await clickLabelled(wrapper, 'Continue')

		const text = wrapper.text()
		expect(text).toContain('2 new accounts will be created')
		expect(text).toContain('3 existing users will be invited')
		// The confirm button restates it, so the count is visible at the moment of
		// the click and not only in a paragraph above it.
		expect(text).toContain('Create 2 accounts and invite')
	})

	it('refuses to confirm when nothing would happen', async () => {
		callMock.mockResolvedValueOnce(
			previewReply({ already_enrolled: 1 }, [
				{ email: 'ada@example.com', verdict: 'already_enrolled' },
			])
		)

		const wrapper = mountDialog()
		await typeAddresses(wrapper, 'ada@example.com')
		await clickLabelled(wrapper, 'Continue')

		const confirm = wrapper
			.findAll('button')
			.find((node) => node.text().includes('Send invitations'))
		expect(confirm!.attributes('disabled')).toBeDefined()
	})

	it('reports per address rather than a blanket success', async () => {
		callMock
			.mockResolvedValueOnce(
				previewReply({ new: 1, invalid: 1 }, [
					{ email: 'ada@example.com', verdict: 'new' },
					{ email: 'oops', verdict: 'invalid' },
				])
			)
			.mockResolvedValueOnce({
				queued: false,
				count: 2,
				results: [
					{ email: 'ada@example.com', status: 'created' },
					{ email: 'oops', status: 'invalid' },
				],
			})

		const wrapper = mountDialog()
		await typeAddresses(wrapper, 'ada@example.com\noops')
		await clickLabelled(wrapper, 'Continue')
		await clickLabelled(wrapper, 'Create 1 accounts and invite')

		const text = wrapper.text()
		expect(text).toContain('ada@example.com')
		expect(text).toContain('Account created')
		expect(text).toContain('oops')
		expect(text).toContain('Not an email')
	})

	it('forgets the previous run when it is reopened', async () => {
		callMock.mockResolvedValueOnce(
			previewReply({ new: 1 }, [{ email: 'ada@example.com', verdict: 'new' }])
		)

		const wrapper = mountDialog()
		await typeAddresses(wrapper, 'ada@example.com')
		await clickLabelled(wrapper, 'Continue')
		expect(wrapper.text()).toContain('1 new accounts will be created')

		await wrapper.setProps({ modelValue: false })
		await flushPromises()
		await wrapper.setProps({ modelValue: true })
		await flushPromises()

		expect(wrapper.text()).not.toContain('new accounts will be created')
		expect(wrapper.find('textarea').element.value).toBe('')
	})
})

describe('InviteDialog with no outgoing email account', () => {
	beforeEach(() => {
		callMock.mockReset()
	})

	it('says why, and refuses to send', async () => {
		callMock.mockResolvedValueOnce({
			...previewReply({ new: 2 }, [{ email: 'ada@example.com', verdict: 'new' }]),
			mail_configured: false,
		})

		const wrapper = mountDialog()
		await typeAddresses(wrapper, 'ada@example.com')
		await clickLabelled(wrapper, 'Continue')

		expect(wrapper.text()).toContain('no outgoing email account')
		const confirm = wrapper
			.findAll('button')
			.find((node) => node.text().includes('Create 2 accounts'))
		expect(confirm!.attributes('disabled')).toBeDefined()
	})
})
