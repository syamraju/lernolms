import { cleanError } from '@/utils'

interface FrappeError {
	messages?: string[]
	message?: string
	exc_type?: string
}

/**
 * Pull a readable sentence out of whatever `call()` rejected with.
 *
 * Frappe throws come back as `{ messages: [html] }`, network failures as a
 * plain Error, and a few paths reject with a bare string. Every step of the
 * creation flow surfaces failures through a toast, so they all need the same
 * three-way unwrap — hence one helper rather than a ternary per call site.
 */
export function errorMessage(error: unknown, fallback: string): string {
	if (!error) return fallback
	if (typeof error === 'string') return cleanError(error)
	const err = error as FrappeError
	const raw = err.messages?.[0] ?? err.message
	return raw ? cleanError(raw) : fallback
}

/** "0min", "8min", "1h 12min" — the header's video-content readout. */
export function formatVideoLength(seconds: number | undefined): string {
	const total = Math.max(Math.floor(Number(seconds) || 0), 0)
	const minutes = Math.floor(total / 60)
	if (minutes < 60) return `${minutes}min`
	const hours = Math.floor(minutes / 60)
	const rest = minutes % 60
	return rest ? `${hours}h ${rest}min` : `${hours}h`
}

/** Words in a rich-text value, counted the way the server counts them. */
export function countWords(html: string | undefined | null): number {
	if (!html) return 0
	const text = html
		.replace(/<[^>]*>/g, ' ')
		.replace(/&nbsp;/g, ' ')
		.trim()
	if (!text) return 0
	return text.split(/\s+/).filter(Boolean).length
}

/**
 * Read a video file's duration in seconds without uploading it twice.
 *
 * Resolves to 0 rather than rejecting when the browser cannot decode the
 * metadata: a missing length degrades the "N min uploaded" readout, which is
 * not worth failing an otherwise good upload over.
 */
export function readVideoDuration(url: string): Promise<number> {
	return new Promise((resolve) => {
		const video = document.createElement('video')
		video.preload = 'metadata'
		const done = (value: number) => {
			video.removeAttribute('src')
			resolve(Number.isFinite(value) && value > 0 ? value : 0)
		}
		video.onloadedmetadata = () => done(video.duration)
		video.onerror = () => done(0)
		video.src = url
	})
}
