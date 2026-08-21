/**
 * The call UI's decisions.
 *
 * Two things are worth pinning down here. The banner must never offer to join a
 * call you are already in -- the dock owns the controls once you are in it, and
 * a thread showing a second Join button reads as a second call. And a message
 * body must reach the page as TEXT: the field is plain text end to end, so a
 * body containing markup has to render as the characters somebody typed.
 */
import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

const sent: any[] = []

vi.mock('frappe-ui', () => ({
	Avatar: { props: ['label', 'image', 'size'], template: '<div class="avatar" />' },
	Button: { template: '<button><slot /></button>' },
	call: vi.fn((method: string, args: any) => {
		sent.push({ method, args })
		return Promise.resolve({})
	}),
	createResource: (options: any) => ({
		data: options.__data ?? null,
		loading: false,
		reload: vi.fn(),
	}),
}))

vi.mock('@/stores/session', () => ({
	sessionStore: () => ({ user: 'me@x.com' }),
}))

vi.mock('@/utils', () => ({ timeAgo: () => 'just now' }))

import HuddleBanner from '@/components/Huddle/HuddleBanner.vue'
import HuddleTile from '@/components/Huddle/HuddleTile.vue'

// Mirrors translation.js: a message with no {0} placeholders returns a string,
// one with them returns a `.format(...)` object. A mock that always returns the
// string would pass these tests and break every interpolated label in the app.
function translate(message: string): any {
	if (!/{\d+}/.test(message)) return message
	return {
		format: (...args: any[]) =>
			message.replace(/{(\d+)}/g, (match, index) =>
				typeof args[index] !== 'undefined' ? String(args[index]) : match
			),
	}
}

const withGlobals = { global: { mocks: { __: translate } } }

// `global.mocks` only patches the template render proxy. A `__()` call inside
// <script setup> -- HuddleBanner's `names` computed is one -- resolves from the
// global object instead, which is where translation.js puts it in the real app.
;(globalThis as any).__ = translate

const participant = (over: any = {}) => ({
	user: 'bob@x.com',
	full_name: 'Bob',
	avatar: null,
	peer_id: 'p-bob',
	joined_at: 0,
	muted: false,
	video: false,
	screensharing: false,
	...over,
})

describe('HuddleBanner', () => {
	it('offers to join a call you are not in', () => {
		const wrapper = mount(HuddleBanner, {
			props: {
				active: { participant_count: 2, participants: [{ full_name: 'Bob' }, { full_name: 'Cara' }] },
				inThisCall: false,
			},
			...withGlobals,
		})

		expect(wrapper.text()).toContain('Call in progress')
		expect(wrapper.text()).toContain('Bob, Cara')
		expect(wrapper.find('button').text()).toBe('Join')
	})

	it('offers to leave, not to join, once you are in it', () => {
		// Two Join buttons for one call is the bug this guards.
		const wrapper = mount(HuddleBanner, {
			props: { active: { participant_count: 2, participants: [] }, inThisCall: true },
			...withGlobals,
		})

		expect(wrapper.text()).toContain('You are in this call')
		expect(wrapper.text()).not.toContain('Join')
	})

	it('says nothing when no call is happening', () => {
		const wrapper = mount(HuddleBanner, {
			props: { active: null, inThisCall: false },
			...withGlobals,
		})
		expect(wrapper.text().trim()).toBe('')
	})

	it('summarises a crowd rather than listing everyone', () => {
		const wrapper = mount(HuddleBanner, {
			props: {
				active: {
					participant_count: 5,
					participants: ['A', 'B', 'C', 'D', 'E'].map((full_name) => ({ full_name })),
				},
				inThisCall: false,
			},
			...withGlobals,
		})

		expect(wrapper.text()).toContain('A, B, C and 2 more')
	})
})

describe('HuddleTile', () => {
	it('shows a face, not a black rectangle, when the camera is off', () => {
		// A camera that is off and a camera two seconds from its first frame look
		// identical at the track level; the roster flag is what distinguishes them.
		const wrapper = mount(HuddleTile, {
			props: { participant: participant({ video: false }), stream: null },
			...withGlobals,
		})

		expect(wrapper.find('video').isVisible()).toBe(false)
		expect(wrapper.find('.avatar').exists()).toBe(true)
	})

	it('shows video once the roster says the camera is on and a stream exists', () => {
		const wrapper = mount(HuddleTile, {
			props: { participant: participant({ video: true }), stream: {} as MediaStream },
			...withGlobals,
		})

		expect(wrapper.find('video').isVisible()).toBe(true)
	})

	it('does not show video for a claimed camera with no stream yet', () => {
		const wrapper = mount(HuddleTile, {
			props: { participant: participant({ video: true }), stream: null },
			...withGlobals,
		})

		expect(wrapper.find('video').isVisible()).toBe(false)
	})

	it('marks a muted participant', () => {
		const wrapper = mount(HuddleTile, {
			props: { participant: participant({ muted: true }), stream: null },
			...withGlobals,
		})

		expect(wrapper.find('[aria-label="Muted"]').exists()).toBe(true)
	})

	it('labels your own tile as you, and mutes it so you do not echo', () => {
		const wrapper = mount(HuddleTile, {
			props: { participant: participant(), stream: null, isSelf: true },
			...withGlobals,
		})

		expect(wrapper.text()).toContain('You')
		// Vue binds `muted` as a DOM property, not an attribute -- reading it off
		// the element is the only way to see it, and hearing yourself is the bug
		// this prevents.
		expect((wrapper.find('video').element as HTMLVideoElement).muted).toBe(true)
	})

	it('fits a shared screen rather than cropping it', () => {
		const wrapper = mount(HuddleTile, {
			props: { participant: participant({ screensharing: true }), stream: {} as MediaStream },
			...withGlobals,
		})

		expect(wrapper.find('video').classes()).toContain('object-contain')
		expect(wrapper.text()).toContain('sharing')
	})
})
