/**
 * How a course deadline reads on a card.
 *
 * The server decides the facts — the due date, whether it has passed — in
 * `lms.lms.pacing`. This only turns them into the one line a student sees, and
 * is kept pure so the wording can be tested without a card or a session.
 */

export interface CoursePacingLike {
	due_date?: string | null
	days_left?: number | null
	is_overdue?: boolean
	status?: string
}

export type PacingTone = 'overdue' | 'warning' | 'neutral'

export interface PacingChip {
	text: string
	tone: PacingTone
}

/**
 * The deadline chip, or null when there is nothing worth saying.
 *
 * Nothing is said about a course with no deadline, one the student has already
 * finished, or one they are not enrolled in — a due date is only meaningful
 * against work in progress.
 */
export function pacingChip(
	pacing: CoursePacingLike | null | undefined
): PacingChip | null {
	if (!pacing?.due_date) return null
	if (pacing.status === 'Completed') return null

	const daysLeft = pacing.days_left

	if (pacing.is_overdue) {
		const late = typeof daysLeft === 'number' ? Math.abs(daysLeft) : 0
		return {
			text: late
				? __('Overdue by {0} day(s)').format(late)
				: __('Overdue'),
			tone: 'overdue',
		}
	}

	if (typeof daysLeft !== 'number') {
		return { text: __('Due {0}').format(pacing.due_date), tone: 'neutral' }
	}
	if (daysLeft === 0) return { text: __('Due today'), tone: 'warning' }
	if (daysLeft === 1) return { text: __('Due tomorrow'), tone: 'warning' }

	return {
		text: __('{0} days left').format(daysLeft),
		// "Due soon" is the server's judgement of when the date starts mattering;
		// re-deriving a threshold here is how the two would drift apart.
		tone: pacing.status === 'Due soon' ? 'warning' : 'neutral',
	}
}

/** Tailwind classes for a chip's tone, kept beside the wording that picks it. */
export const PACING_TONE_CLASS: Record<PacingTone, string> = {
	overdue: 'bg-[#ffe0e0] text-[#a11414]',
	warning: 'bg-[#fff0d4] text-[#8a5a00]',
	neutral: 'bg-[#e8e8e8] text-[#4a4a4a]',
}
