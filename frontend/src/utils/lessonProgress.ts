/**
 * Pure helpers for lesson-progress logic. Kept side-effect-free so they can
 * be unit-tested without mounting Lesson.vue or stubbing the Pinia store.
 */

export function resolveDwellSeconds(
	raw: unknown,
	fallback = 30,
): number | null {
	const n = Number(raw ?? fallback)
	if (!Number.isFinite(n) || n <= 0) return null
	return n
}

export function isVideoComplete(
	currentTime: number,
	duration: number,
): boolean {
	if (!Number.isFinite(currentTime) || !Number.isFinite(duration)) return false
	if (duration <= 0) return false
	return currentTime >= duration - 1
}

export function shouldStartDwellTimer(opts: {
	hasVideo: boolean
	enforceVideo: boolean | 0 | 1
}): boolean {
	return !(opts.hasVideo && !!opts.enforceVideo)
}

export function shouldAttachVideoFallback(opts: {
	hasVideo: boolean
	enforceVideo: boolean | 0 | 1
}): boolean {
	return opts.hasVideo && !!opts.enforceVideo
}

/** What `get_lesson` reports as still gating completion of a lesson. */
export type CompletionBlocker = 'quiz' | 'assignment'

/**
 * The sentence shown under a disabled "Mark as Complete".
 *
 * `save_progress` refuses to record completion while a lesson's quiz is unpassed
 * or its assignment unsubmitted, and it refuses silently — it returns the course
 * percentage either way. The server reports what it is waiting on so the student
 * reads a reason instead of pressing a button that does nothing.
 *
 * Returns '' when nothing is outstanding, which is also the caller's "not
 * blocked" signal.
 */
export function completionBlockerMessage(
	blockers: readonly string[] | undefined | null,
	pendingQuizzes?: readonly PendingQuizLike[] | null,
): string {
	const quiz = blockers?.includes('quiz') ?? false
	const assignment = blockers?.includes('assignment') ?? false
	// The detail is an upgrade on the generic wording, not a replacement for it:
	// when the server sends no pass mark — an older backend, a quiz whose
	// requirement could not be read — the plain sentences still have to work.
	const detail = quiz ? quizRequirementSentence(pendingQuizzes) : ''

	if (quiz && assignment) {
		return detail
			? __('{0} You also need to submit the assignment.').format(detail)
			: __('Pass the quiz and submit the assignment to complete this session.')
	}
	if (quiz) return detail || __('Pass the quiz to complete this session.')
	if (assignment) return __('Submit the assignment to complete this session.')
	return ''
}

/** The quiz half of the message, from `get_lesson`'s `pending_quizzes`. */
export interface PendingQuizLike {
	title?: string
	passing_percentage?: number
	best_percentage?: number | null
	attempts?: number
}

/**
 * "Pass the quiz" with the number in it.
 *
 * A student blocked by a pass mark needs the two things the bare sentence
 * leaves out: what the bar is, and how close they got. Returns '' when the
 * server sent nothing to be specific about, which is the caller's signal to use
 * the generic wording instead.
 */
export function quizRequirementSentence(
	pendingQuizzes?: readonly PendingQuizLike[] | null,
): string {
	const pending = pendingQuizzes?.[0]
	if (!pending) return ''

	const target = Number(pending.passing_percentage) || 0
	if (target <= 0) return __('Submit the quiz to complete this session.')

	if (!pending.attempts || pending.best_percentage == null) {
		return __(
			'Score at least {0}% on the quiz to complete this session.',
		).format(target)
	}
	return __(
		'Your best score is {0}%. You need {1}% to complete this session.',
	).format(pending.best_percentage, target)
}
