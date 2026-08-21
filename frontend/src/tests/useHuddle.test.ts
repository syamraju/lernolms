/**
 * useHuddle: the mesh's decisions, with the browser's WebRTC stack faked out.
 *
 * What is worth guarding here is not that an offer is well-formed -- that is
 * the browser's job -- but the three things a mesh gets wrong on its own:
 * exactly one side of a pair offers, a peer that reloads is rebuilt rather than
 * talked past, and a peer that leaves takes its connection with it.
 */
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { effectScope } from 'vue'

const calls: { method: string; args: any }[] = []
let joinResponse: any = null

vi.mock('frappe-ui', () => ({
	call: vi.fn((method: string, args: any) => {
		calls.push({ method, args })
		if (method === 'lms.lms.huddle.get_config') {
			return Promise.resolve({ ice_servers: [], heartbeat_interval: 20 })
		}
		if (method === 'lms.lms.huddle.join') return Promise.resolve(joinResponse)
		return Promise.resolve({})
	}),
}))

import { useHuddle } from '@/composables/useHuddle'

class FakePeerConnection {
	static instances: FakePeerConnection[] = []
	transceivers: any[] = []
	localDescription: any = null
	remoteDescription: any = null
	signalingState = 'stable'
	connectionState = 'new'
	onicecandidate: any = null
	ontrack: any = null
	onconnectionstatechange: any = null
	closed = false

	constructor() {
		FakePeerConnection.instances.push(this)
	}

	addTransceiver(kind: string, init?: any) {
		const transceiver = {
			direction: init?.direction ?? 'sendrecv',
			sender: { replaceTrack: vi.fn(() => Promise.resolve()) },
			receiver: { track: { kind } },
		}
		this.transceivers.push(transceiver)
		return transceiver
	}

	/** What a browser does on setRemoteDescription(offer): it derives
	 *  transceivers from the offer, and they start `recvonly`. */
	receiveOfferTransceivers() {
		for (const kind of ['audio', 'video']) {
			this.transceivers.push({
				direction: 'recvonly',
				sender: { replaceTrack: vi.fn(() => Promise.resolve()) },
				receiver: { track: { kind } },
			})
		}
	}

	getTransceivers() {
		return this.transceivers
	}

	createOffer() {
		return Promise.resolve({ type: 'offer', sdp: 'fake-offer' })
	}

	createAnswer() {
		return Promise.resolve({ type: 'answer', sdp: 'fake-answer' })
	}

	setLocalDescription(description: any) {
		this.localDescription = description
		this.signalingState = description.type === 'offer' ? 'have-local-offer' : 'stable'
		return Promise.resolve()
	}

	setRemoteDescription(description: any) {
		this.remoteDescription = description
		if (description.type === 'offer' && !this.transceivers.length) this.receiveOfferTransceivers()
		return Promise.resolve()
	}

	addIceCandidate() {
		return Promise.resolve()
	}

	close() {
		this.closed = true
	}
}

function fakeTrack(kind: string) {
	return { kind, enabled: true, stop: vi.fn(), addEventListener: vi.fn() }
}

class FakeMediaStream {
	tracks: any[] = []
	constructor(tracks: any[] = []) {
		this.tracks = [...tracks]
	}
	addTrack(track: any) {
		this.tracks.push(track)
	}
	removeTrack(track: any) {
		this.tracks = this.tracks.filter((t) => t !== track)
	}
	getTracks() {
		return this.tracks
	}
	getAudioTracks() {
		return this.tracks.filter((t) => t.kind === 'audio')
	}
	getVideoTracks() {
		return this.tracks.filter((t) => t.kind === 'video')
	}
}

function fakeSocket() {
	const handlers: Record<string, Function[]> = {}
	return {
		handlers,
		on: (event: string, fn: Function) => {
			;(handlers[event] ||= []).push(fn)
		},
		off: (event: string, fn: Function) => {
			handlers[event] = (handlers[event] || []).filter((h) => h !== fn)
		},
		emit: (event: string, payload: any) => {
			for (const fn of handlers[event] || []) fn(payload)
		},
	}
}

function roster(participants: { user: string; peer_id: string }[]) {
	return {
		id: 'H1',
		conversation: 'batch:B1',
		started_by: participants[0]?.user,
		started_at: 0,
		participants: participants.map((p) => ({
			...p,
			full_name: p.user,
			avatar: null,
			joined_at: 0,
			muted: false,
			video: false,
			screensharing: false,
		})),
	}
}

/** The peer id the client generated for itself -- the server echoes it back, so
 * frames addressed to this tab carry it and frames for a stale tab do not. */
const myPeerId = () =>
	calls.find((c) => c.method === 'lms.lms.huddle.join')?.args.peer_id as string

const signalsTo = (user: string, kind: string) =>
	calls.filter(
		(c) => c.method === 'lms.lms.huddle.signal' && c.args.to_user === user && c.args.kind === kind
	)

describe('useHuddle', () => {
	let scope: ReturnType<typeof effectScope>

	beforeEach(() => {
		calls.length = 0
		FakePeerConnection.instances = []
		joinResponse = null

		vi.stubGlobal('RTCPeerConnection', FakePeerConnection)
		vi.stubGlobal('MediaStream', FakeMediaStream)
		vi.stubGlobal('navigator', {
			mediaDevices: {
				getUserMedia: vi.fn(() => Promise.resolve(new FakeMediaStream([fakeTrack('audio')]))),
				getDisplayMedia: vi.fn(),
			},
			sendBeacon: vi.fn(),
		})
	})

	function build(me: string) {
		const socket = fakeSocket()
		scope = effectScope()
		const huddle = scope.run(() => useHuddle({ socket, currentUser: () => me }))!
		return { socket, huddle }
	}

	it('offers to a peer whose email sorts after mine', async () => {
		joinResponse = {
			huddle: roster([
				{ user: 'alice@x.com', peer_id: 'p-alice' },
				{ user: 'bob@x.com', peer_id: 'p-bob' },
			]),
			self: { user: 'alice@x.com', peer_id: 'p-alice' },
		}
		const { huddle } = build('alice@x.com')

		await huddle.join('batch:B1')
		await vi.waitFor(() => expect(signalsTo('bob@x.com', 'offer')).toHaveLength(1))
	})

	it('waits to be offered to when my email sorts after the peer', async () => {
		// Both ends see the same roster event. If both offered, they would glare.
		joinResponse = {
			huddle: roster([
				{ user: 'alice@x.com', peer_id: 'p-alice' },
				{ user: 'bob@x.com', peer_id: 'p-bob' },
			]),
			self: { user: 'bob@x.com', peer_id: 'p-bob' },
		}
		const { huddle } = build('bob@x.com')

		await huddle.join('batch:B1')
		await new Promise((resolve) => setTimeout(resolve, 10))
		expect(signalsTo('alice@x.com', 'offer')).toHaveLength(0)
	})

	it('answers an offer it receives', async () => {
		joinResponse = {
			huddle: roster([{ user: 'bob@x.com', peer_id: 'p-bob' }]),
			self: { user: 'bob@x.com', peer_id: 'p-bob' },
		}
		const { socket, huddle } = build('bob@x.com')
		await huddle.join('batch:B1')

		socket.emit('lms_huddle_signal', {
			conversation: 'batch:B1',
			kind: 'offer',
			from_user: 'alice@x.com',
			from_peer: 'p-alice',
			to_peer: myPeerId(),
			payload: { sdp: 'their-offer' },
		})

		await vi.waitFor(() => expect(signalsTo('alice@x.com', 'answer')).toHaveLength(1))
	})

	it('turns the answering side sendrecv, so its microphone actually transmits', async () => {
		// A transceiver derived from a remote offer starts `recvonly`, and
		// replaceTrack does not change that. Without the fix the call connects,
		// ICE succeeds, and audio flows one way only — with no error anywhere.
		// Found by running a real call between two browsers; no fake could have
		// surfaced it, so this test encodes what the browser actually does.
		joinResponse = {
			huddle: roster([{ user: 'bob@x.com', peer_id: 'p-bob' }]),
			self: { user: 'bob@x.com', peer_id: 'p-bob' },
		}
		const { socket, huddle } = build('bob@x.com')
		await huddle.join('batch:B1')

		socket.emit('lms_huddle_signal', {
			conversation: 'batch:B1',
			kind: 'offer',
			from_user: 'alice@x.com',
			from_peer: 'p-alice',
			to_peer: myPeerId(),
			payload: { sdp: 'their-offer' },
		})

		await vi.waitFor(() => expect(signalsTo('alice@x.com', 'answer')).toHaveLength(1))
		const pc = FakePeerConnection.instances[0]
		expect(pc.getTransceivers().map((t: any) => t.direction)).toEqual(['sendrecv', 'sendrecv'])
	})

	it('ignores a frame addressed to a different tab of mine', async () => {
		joinResponse = {
			huddle: roster([{ user: 'bob@x.com', peer_id: 'p-bob' }]),
			self: { user: 'bob@x.com', peer_id: 'p-bob' },
		}
		const { socket, huddle } = build('bob@x.com')
		await huddle.join('batch:B1')

		socket.emit('lms_huddle_signal', {
			conversation: 'batch:B1',
			kind: 'offer',
			from_user: 'alice@x.com',
			from_peer: 'p-alice',
			to_peer: 'some-other-tab',
			payload: { sdp: 'their-offer' },
		})

		await new Promise((resolve) => setTimeout(resolve, 10))
		expect(signalsTo('alice@x.com', 'answer')).toHaveLength(0)
	})

	it('ignores a frame for a different conversation', async () => {
		joinResponse = {
			huddle: roster([{ user: 'alice@x.com', peer_id: 'p-alice' }]),
			self: { user: 'alice@x.com', peer_id: 'p-alice' },
		}
		const { socket, huddle } = build('alice@x.com')
		await huddle.join('batch:B1')
		const before = FakePeerConnection.instances.length

		socket.emit('lms_huddle_roster', roster([
			{ user: 'alice@x.com', peer_id: 'p-alice' },
			{ user: 'zoe@x.com', peer_id: 'p-zoe' },
		]) as any)
		// Same payload, wrong conversation.
		socket.emit('lms_huddle_roster', {
			...roster([
				{ user: 'alice@x.com', peer_id: 'p-alice' },
				{ user: 'other@x.com', peer_id: 'p-other' },
			]),
			conversation: 'batch:SOMEWHERE-ELSE',
		})

		await vi.waitFor(() => expect(FakePeerConnection.instances.length).toBe(before + 1))
	})

	it('rebuilds the connection when a peer reloads under a new peer id', async () => {
		joinResponse = {
			huddle: roster([
				{ user: 'alice@x.com', peer_id: 'p-alice' },
				{ user: 'bob@x.com', peer_id: 'p-bob' },
			]),
			self: { user: 'alice@x.com', peer_id: 'p-alice' },
		}
		const { socket, huddle } = build('alice@x.com')
		await huddle.join('batch:B1')
		await vi.waitFor(() => expect(FakePeerConnection.instances).toHaveLength(1))
		const first = FakePeerConnection.instances[0]

		socket.emit('lms_huddle_roster', roster([
			{ user: 'alice@x.com', peer_id: 'p-alice' },
			{ user: 'bob@x.com', peer_id: 'p-bob-reloaded' },
		]) as any)

		await vi.waitFor(() => expect(first.closed).toBe(true))
		await vi.waitFor(() => expect(signalsTo('bob@x.com', 'offer')).toHaveLength(2))
		expect(signalsTo('bob@x.com', 'offer')[1].args.to_peer).toBe('p-bob-reloaded')
	})

	it('closes the connection to a peer who leaves', async () => {
		joinResponse = {
			huddle: roster([
				{ user: 'alice@x.com', peer_id: 'p-alice' },
				{ user: 'bob@x.com', peer_id: 'p-bob' },
			]),
			self: { user: 'alice@x.com', peer_id: 'p-alice' },
		}
		const { socket, huddle } = build('alice@x.com')
		await huddle.join('batch:B1')
		await vi.waitFor(() => expect(FakePeerConnection.instances).toHaveLength(1))

		socket.emit('lms_huddle_roster', roster([{ user: 'alice@x.com', peer_id: 'p-alice' }]) as any)

		await vi.waitFor(() => expect(FakePeerConnection.instances[0].closed).toBe(true))
		expect(huddle.remoteStreams.value.has('bob@x.com')).toBe(false)
	})

	it('mutes by disabling the track rather than dropping the sender', async () => {
		// Renegotiating on every mute is how a mesh ends up in permanent glare;
		// disabling also means unmuting has no first-syllable gap.
		joinResponse = {
			huddle: roster([{ user: 'alice@x.com', peer_id: 'p-alice' }]),
			self: { user: 'alice@x.com', peer_id: 'p-alice' },
		}
		const { huddle } = build('alice@x.com')
		await huddle.join('batch:B1')

		const track = huddle.localStream.value!.getAudioTracks()[0]
		huddle.toggleMute()

		expect(huddle.muted.value).toBe(true)
		expect(track.enabled).toBe(false)
		expect(calls.some((c) => c.method === 'lms.lms.huddle.set_flags' && c.args.muted === 1)).toBe(true)
	})

	it('carries on audio-only when the camera is refused', async () => {
		joinResponse = {
			huddle: roster([{ user: 'alice@x.com', peer_id: 'p-alice' }]),
			self: { user: 'alice@x.com', peer_id: 'p-alice' },
		}
		;(navigator.mediaDevices.getUserMedia as any) = vi.fn((constraints: any) =>
			constraints.video
				? Promise.reject(new Error('NotAllowedError'))
				: Promise.resolve(new FakeMediaStream([fakeTrack('audio')]))
		)
		const { huddle } = build('alice@x.com')

		await huddle.join('batch:B1', { video: true })

		expect(huddle.status.value).toBe('live')
		expect(huddle.cameraOn.value).toBe(false)
	})

	it('reports a join it could not complete instead of sitting in connecting', async () => {
		;(navigator.mediaDevices.getUserMedia as any) = vi.fn(() =>
			Promise.reject(new Error('No microphone'))
		)
		const { huddle } = build('alice@x.com')

		await expect(huddle.join('batch:B1')).rejects.toThrow()
		expect(huddle.status.value).toBe('idle')
	})
})
