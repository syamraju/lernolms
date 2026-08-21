/**
 * One huddle, driven from the browser.
 *
 * The server owns the roster and forwards SDP/ICE; everything about the media
 * itself lives here. The topology is a full mesh -- one `RTCPeerConnection` per
 * other person -- which is why the server caps a call at eight: past that,
 * every additional joiner costs everyone else another upstream.
 *
 * Two decisions are worth knowing before reading:
 *
 *   * **Who offers is decided by comparing emails**, not by who arrived first.
 *     Both ends learn about each other from the same roster event, so a
 *     first-past-the-post rule makes them both offer and glare; a lexicographic
 *     compare makes exactly one of them offer, with no round trip to agree on
 *     it. Same trick the DM conversation id uses.
 *   * **Nothing renegotiates after the initial offer.** The offer always
 *     carries one audio and one video transceiver in `sendrecv`, whether or not
 *     a camera is on. Muting, unmuting, turning the camera on, and starting a
 *     screen share are all `replaceTrack` on a sender that already exists. A
 *     mesh that renegotiates on every toggle spends its life in glare.
 *
 * The roster's `muted` / `video` / `screensharing` flags -- not the presence of
 * a track -- are what the UI renders. A camera that is off is a sender with a
 * null track, which looks identical to a camera that is merely slow to start.
 */

import { computed, onScopeDispose, ref, shallowRef } from 'vue'
import { call } from 'frappe-ui'

export interface HuddleParticipant {
	user: string
	full_name: string
	avatar: string | null
	peer_id: string
	joined_at: number
	muted: boolean
	video: boolean
	screensharing: boolean
}

export interface HuddleRoster {
	id: string
	conversation: string
	started_by: string
	started_at: number
	participants: HuddleParticipant[]
}

/** `failed` means the call could not be entered at all -- a peer that fails to
 * connect leaves the huddle live and shows as reconnecting on its own tile. */
export type HuddleStatus = 'idle' | 'joining' | 'live' | 'failed'

interface SignalFrame {
	conversation: string
	kind: 'offer' | 'answer' | 'ice'
	from_user: string
	from_peer: string
	to_peer: string
	payload: any
}

/** One mesh edge. */
interface PeerLink {
	pc: RTCPeerConnection
	peerId: string
	/** ICE that arrived before the remote description did. Adding a candidate to
	 * a connection with no remote description throws, and the candidates that
	 * arrive in that window are usually the host ones -- the fast path. */
	pendingIce: RTCIceCandidateInit[]
	stream: MediaStream
	negotiating: boolean
}

const MIC_CONSTRAINTS: MediaTrackConstraints = {
	echoCancellation: true,
	noiseSuppression: true,
	autoGainControl: true,
}

const CAM_CONSTRAINTS: MediaTrackConstraints = {
	width: { ideal: 1280 },
	height: { ideal: 720 },
	frameRate: { ideal: 24, max: 30 },
}

const EVENT_SIGNAL = 'lms_huddle_signal'
const EVENT_ROSTER = 'lms_huddle_roster'

/** Lowercase compare so the tie-break is stable regardless of address casing. */
function offersTo(me: string, peer: string): boolean {
	return me.trim().toLowerCase() < peer.trim().toLowerCase()
}

function randomPeerId(): string {
	return `peer-${Math.random().toString(36).slice(2, 10)}${Date.now().toString(36)}`
}

export interface UseHuddleOptions {
	/** Frappe's socket.io client, injected as `$socket` by the app. */
	socket: any
	/** The signed-in user's email -- the identity the roster is keyed by. */
	currentUser: () => string
}

export function useHuddle({ socket, currentUser }: UseHuddleOptions) {
	const status = ref<HuddleStatus>('idle')
	const conversation = ref('')
	const roster = ref<HuddleParticipant[]>([])
	const error = ref('')

	const muted = ref(false)
	const cameraOn = ref(false)
	const screensharing = ref(false)

	// shallowRef + replace-the-Map: a deeply reactive Map would hand out Proxy
	// wrappers around MediaStream, and a proxied stream assigned to
	// `video.srcObject` plays nothing.
	const remoteStreams = shallowRef(new Map<string, MediaStream>())
	const localStream = shallowRef<MediaStream | null>(null)

	const links = new Map<string, PeerLink>()
	let peerId = ''
	let iceServers: RTCIceServer[] = []
	let heartbeatTimer: number | undefined
	let micTrack: MediaStreamTrack | null = null
	let camTrack: MediaStreamTrack | null = null
	let screenTrack: MediaStreamTrack | null = null
	let unbind: (() => void) | null = null

	const me = () => currentUser()

	const others = computed(() => roster.value.filter((p) => p.user !== me()))
	const self = computed(() => roster.value.find((p) => p.user === me()) || null)
	const active = computed(() => status.value === 'live' || status.value === 'joining')

	// --- local media ----------------------------------------------------------

	/** The track other people should see from me: the screen when I'm sharing
	 * it, the camera otherwise. One video sender covers both, so starting a
	 * share never renegotiates. */
	function outboundVideo(): MediaStreamTrack | null {
		return screenTrack || camTrack
	}

	function refreshLocalStream() {
		const stream = new MediaStream()
		if (micTrack) stream.addTrack(micTrack)
		const video = outboundVideo()
		if (video) stream.addTrack(video)
		localStream.value = stream
	}

	async function acquireMic(): Promise<void> {
		if (micTrack) return
		const stream = await navigator.mediaDevices.getUserMedia({ audio: MIC_CONSTRAINTS })
		micTrack = stream.getAudioTracks()[0] || null
		if (micTrack) micTrack.enabled = !muted.value
		refreshLocalStream()
	}

	async function acquireCamera(): Promise<void> {
		if (camTrack) return
		const stream = await navigator.mediaDevices.getUserMedia({ video: CAM_CONSTRAINTS })
		camTrack = stream.getVideoTracks()[0] || null
		refreshLocalStream()
	}

	function stopCamera() {
		camTrack?.stop()
		camTrack = null
		refreshLocalStream()
	}

	function stopScreen() {
		screenTrack?.stop()
		screenTrack = null
		refreshLocalStream()
	}

	/** Push whatever I'm currently sending onto every existing sender. Called
	 * after any local media change; never renegotiates. */
	function pushLocalTracks() {
		const video = outboundVideo()
		for (const link of links.values()) applyTracks(link.pc, video)
	}

	function applyTracks(pc: RTCPeerConnection, video: MediaStreamTrack | null) {
		const transceivers = pc.getTransceivers()
		const audioT = transceivers.find((t) => t.receiver.track?.kind === 'audio' || t.sender.track?.kind === 'audio')
		const videoT = transceivers.find((t) => t.receiver.track?.kind === 'video' || t.sender.track?.kind === 'video')

		// Fall back to positional lookup: before the first negotiation completes
		// a transceiver has neither a sender nor a receiver track to identify it
		// by, but the offer always puts audio first.
		const [first, second] = transceivers
		void (audioT || first)?.sender.replaceTrack(micTrack).catch(() => {})
		void (videoT || second)?.sender.replaceTrack(video).catch(() => {})
	}

	// --- mesh ------------------------------------------------------------------

	function bumpStreams() {
		remoteStreams.value = new Map(remoteStreams.value)
	}

	function ensureRemoteStream(user: string): MediaStream {
		let stream = remoteStreams.value.get(user)
		if (!stream) {
			stream = new MediaStream()
			remoteStreams.value.set(user, stream)
			bumpStreams()
		}
		return stream
	}

	function send(toUser: string, toPeer: string, kind: string, payload: any) {
		return call('lms.lms.huddle.signal', {
			conversation: conversation.value,
			to_user: toUser,
			to_peer: toPeer,
			kind,
			payload,
		}).catch(() => {
			// A dropped frame is not fatal: the peer either reloaded (its roster
			// event will rebuild the link) or the call ended under us.
		})
	}

	function linkFor(user: string, remotePeerId: string): PeerLink {
		const existing = links.get(user)
		if (existing && existing.peerId === remotePeerId) return existing
		// A peer that reloaded is a different connection wearing the same name.
		if (existing) dropLink(user)

		const pc = new RTCPeerConnection({ iceServers })
		const link: PeerLink = {
			pc,
			peerId: remotePeerId,
			pendingIce: [],
			stream: ensureRemoteStream(user),
			negotiating: false,
		}
		links.set(user, link)

		pc.onicecandidate = (event) => {
			if (event.candidate) send(user, remotePeerId, 'ice', { candidate: event.candidate.toJSON() })
		}

		pc.ontrack = (event) => {
			// Tracks are attached without a stream id (addTransceiver, not
			// addTrack), so the per-peer stream is assembled here rather than
			// taken from event.streams.
			const stream = ensureRemoteStream(user)
			if (!stream.getTracks().includes(event.track)) {
				stream.addTrack(event.track)
				bumpStreams()
			}
			event.track.addEventListener('ended', () => {
				stream.removeTrack(event.track)
				bumpStreams()
			})
		}

		pc.onconnectionstatechange = () => {
			if (pc.connectionState === 'failed') {
				// One dead edge is not a dead call. Rebuild it from the offering
				// side; the other side will accept a fresh offer for the same peer.
				if (offersTo(me(), user)) void openOffer(user, remotePeerId, true)
			}
		}

		return link
	}

	function dropLink(user: string) {
		const link = links.get(user)
		if (!link) return

		link.pc.onicecandidate = null
		link.pc.ontrack = null
		link.pc.onconnectionstatechange = null
		try {
			link.pc.close()
		} catch {
			// Already closed by a failed state transition.
		}
		links.delete(user)
		remoteStreams.value.delete(user)
		bumpStreams()
	}

	async function openOffer(user: string, remotePeerId: string, rebuild = false) {
		if (rebuild) dropLink(user)
		const link = linkFor(user, remotePeerId)
		if (link.negotiating) return
		link.negotiating = true

		try {
			// The offering side declares the shape of the call once: audio and
			// video, both ways, camera or no camera. Everything after this is
			// replaceTrack.
			if (!link.pc.getTransceivers().length) {
				link.pc.addTransceiver('audio', { direction: 'sendrecv' })
				link.pc.addTransceiver('video', { direction: 'sendrecv' })
			}
			applyTracks(link.pc, outboundVideo())

			const offer = await link.pc.createOffer()
			await link.pc.setLocalDescription(offer)
			await send(user, remotePeerId, 'offer', { sdp: offer.sdp })
		} catch (e) {
			link.negotiating = false
			throw e
		}
	}

	async function onOffer(frame: SignalFrame) {
		const link = linkFor(frame.from_user, frame.from_peer)
		await link.pc.setRemoteDescription({ type: 'offer', sdp: frame.payload.sdp })
		applyTracks(link.pc, outboundVideo())

		const answer = await link.pc.createAnswer()
		await link.pc.setLocalDescription(answer)
		await drainIce(link)
		await send(frame.from_user, frame.from_peer, 'answer', { sdp: answer.sdp })
	}

	async function onAnswer(frame: SignalFrame) {
		const link = links.get(frame.from_user)
		if (!link || link.peerId !== frame.from_peer) return
		if (link.pc.signalingState !== 'have-local-offer') return

		await link.pc.setRemoteDescription({ type: 'answer', sdp: frame.payload.sdp })
		link.negotiating = false
		await drainIce(link)
	}

	async function onIce(frame: SignalFrame) {
		const link = links.get(frame.from_user)
		if (!link || link.peerId !== frame.from_peer) return

		const candidate = frame.payload?.candidate
		if (!candidate) return

		if (!link.pc.remoteDescription) {
			link.pendingIce.push(candidate)
			return
		}
		await link.pc.addIceCandidate(candidate).catch(() => {})
	}

	async function drainIce(link: PeerLink) {
		const queued = link.pendingIce.splice(0)
		for (const candidate of queued) await link.pc.addIceCandidate(candidate).catch(() => {})
	}

	// --- roster ----------------------------------------------------------------

	function reconcile(next: HuddleRoster | null) {
		if (!next) {
			roster.value = []
			for (const user of [...links.keys()]) dropLink(user)
			return
		}

		roster.value = next.participants

		const present = new Map(next.participants.filter((p) => p.user !== me()).map((p) => [p.user, p.peer_id]))

		// Gone, or back under a new peer id: either way the old edge is dead.
		for (const [user, link] of [...links.entries()]) {
			if (!present.has(user) || present.get(user) !== link.peerId) dropLink(user)
		}

		if (status.value !== 'live') return

		for (const [user, remotePeerId] of present) {
			if (links.has(user)) continue
			if (offersTo(me(), user)) {
				void openOffer(user, remotePeerId)
			} else {
				// Wait to be offered to, but stand the connection up now so an
				// offer that beats the roster event has somewhere to land.
				linkFor(user, remotePeerId)
			}
		}
	}

	// --- realtime ---------------------------------------------------------------

	function bindSocket() {
		if (unbind) return

		const onSignal = (frame: SignalFrame) => {
			if (frame.conversation !== conversation.value) return
			if (frame.to_peer !== peerId) return

			const handler =
				frame.kind === 'offer' ? onOffer : frame.kind === 'answer' ? onAnswer : frame.kind === 'ice' ? onIce : null
			void handler?.(frame).catch(() => {
				// A failed negotiation shows up as a peer tile that never
				// connects; the connectionstatechange rebuild is the recovery.
			})
		}

		const onRoster = (payload: HuddleRoster) => {
			if (payload.conversation !== conversation.value) return
			reconcile(payload)
		}

		socket.on(EVENT_SIGNAL, onSignal)
		socket.on(EVENT_ROSTER, onRoster)
		unbind = () => {
			socket.off(EVENT_SIGNAL, onSignal)
			socket.off(EVENT_ROSTER, onRoster)
			unbind = null
		}
	}

	// --- public api ---------------------------------------------------------------

	async function join(target: string, options: { video?: boolean } = {}) {
		if (active.value && conversation.value === target) return
		if (active.value) await leave()

		conversation.value = target
		status.value = 'joining'
		error.value = ''
		peerId = randomPeerId()

		try {
			const config = await call('lms.lms.huddle.get_config')
			iceServers = config.ice_servers || []

			// Mic first: a call you can't be heard in is not a call, and asking
			// for the camera at the same time turns one permission prompt into a
			// single all-or-nothing one.
			await acquireMic()
			if (options.video) {
				try {
					await acquireCamera()
					cameraOn.value = true
				} catch {
					// No camera, or refused. Audio-only is a fine call.
					cameraOn.value = false
				}
			}

			bindSocket()
			const result = await call('lms.lms.huddle.join', {
				conversation: target,
				peer_id: peerId,
				video: cameraOn.value ? 1 : 0,
			})

			status.value = 'live'
			reconcile(result.huddle)
			startHeartbeat()
		} catch (e: any) {
			status.value = 'failed'
			error.value = e?.messages?.[0] || e?.message || 'Could not join the call.'
			await teardown()
			throw e
		}
	}

	async function leave() {
		if (!conversation.value) return
		const target = conversation.value

		await teardown()
		await call('lms.lms.huddle.leave', { conversation: target, peer_id: peerId }).catch(() => {})
	}

	async function teardown() {
		stopHeartbeat()
		for (const user of [...links.keys()]) dropLink(user)

		micTrack?.stop()
		micTrack = null
		stopCamera()
		stopScreen()
		localStream.value = null

		roster.value = []
		muted.value = false
		cameraOn.value = false
		screensharing.value = false
		status.value = 'idle'
		conversation.value = ''
		unbind?.()
	}

	function flags(patch: Record<string, number>) {
		return call('lms.lms.huddle.set_flags', {
			conversation: conversation.value,
			peer_id: peerId,
			...patch,
		}).catch(() => {})
	}

	function toggleMute() {
		muted.value = !muted.value
		// Disabling the track keeps the sender alive, so unmuting is instant and
		// silent -- no renegotiation, no dropped first syllable.
		if (micTrack) micTrack.enabled = !muted.value
		void flags({ muted: muted.value ? 1 : 0 })
	}

	async function toggleCamera() {
		if (cameraOn.value) {
			stopCamera()
			cameraOn.value = false
		} else {
			try {
				await acquireCamera()
				cameraOn.value = true
			} catch {
				error.value = 'No camera available.'
				return
			}
		}
		pushLocalTracks()
		void flags({ video: cameraOn.value ? 1 : 0 })
	}

	async function toggleScreenshare() {
		if (screensharing.value) {
			stopScreen()
			screensharing.value = false
			pushLocalTracks()
			void flags({ screensharing: 0 })
			return
		}

		try {
			const stream = await navigator.mediaDevices.getDisplayMedia({ video: true })
			screenTrack = stream.getVideoTracks()[0] || null
			// The browser's own "Stop sharing" bar is the control most people
			// reach for; honour it rather than leaving the UI claiming to share.
			screenTrack?.addEventListener('ended', () => {
				screensharing.value = false
				stopScreen()
				pushLocalTracks()
				void flags({ screensharing: 0 })
			})
			screensharing.value = true
			refreshLocalStream()
			pushLocalTracks()
			void flags({ screensharing: 1 })
		} catch {
			// The picker was dismissed. Not an error worth showing.
		}
	}

	function startHeartbeat() {
		stopHeartbeat()
		heartbeatTimer = window.setInterval(async () => {
			try {
				const result = await call('lms.lms.huddle.heartbeat', {
					conversation: conversation.value,
					peer_id: peerId,
				})
				if (!result.huddle) return void teardown()
				// The reconciliation path: a client that missed a realtime frame
				// while backgrounded is corrected here rather than drifting.
				if (result.evicted) return void teardown()
				reconcile(result.huddle)
			} catch {
				// A blip in the API is not a reason to hang up; the media is
				// peer-to-peer and keeps flowing.
			}
		}, 20000)
	}

	function stopHeartbeat() {
		if (heartbeatTimer) window.clearInterval(heartbeatTimer)
		heartbeatTimer = undefined
	}

	/** Closing the tab sends no `leave`, so the seat would sit there until the
	 * server's prune notices. `keepalive` buys us the request on the way out. */
	function releaseOnUnload() {
		if (!conversation.value) return
		const body = JSON.stringify({ conversation: conversation.value, peer_id: peerId })
		navigator.sendBeacon?.(
			'/api/method/lms.lms.huddle.leave',
			new Blob([body], { type: 'application/json' })
		)
	}

	if (typeof window !== 'undefined') {
		window.addEventListener('pagehide', releaseOnUnload)
		onScopeDispose(() => window.removeEventListener('pagehide', releaseOnUnload))
	}

	onScopeDispose(() => {
		releaseOnUnload()
		void teardown()
	})

	return {
		status,
		conversation,
		roster,
		others,
		self,
		error,
		muted,
		cameraOn,
		screensharing,
		localStream,
		remoteStreams,
		active,
		join,
		leave,
		toggleMute,
		toggleCamera,
		toggleScreenshare,
	}
}
