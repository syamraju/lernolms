import type { CurriculumItem, CurriculumItemType } from '@/types'
import { formatVideoLength } from '@/utils/courseCreation'

/** Per-type presentation: the icon in the row and the noun in the copy. */
export const ITEM_TYPE_META: Record<
	CurriculumItemType,
	{ icon: string; label: string; description: string }
> = {
	Lecture: {
		icon: 'lucide-monitor-play',
		label: 'Lecture',
		description: 'A video, article or slide deck learners watch or read.',
	},
	Quiz: {
		icon: 'lucide-circle-help',
		label: 'Quiz',
		description: 'Multiple-choice questions that check what stuck.',
	},
	Assignment: {
		icon: 'lucide-file-text',
		label: 'Assignment',
		description: 'A task learners complete and submit for feedback.',
	},
	'Coding Exercise': {
		icon: 'lucide-code',
		label: 'Coding Exercise',
		description: 'Hands-on practice checked automatically by test cases.',
	},
}

export const ITEM_TYPES = Object.keys(ITEM_TYPE_META) as CurriculumItemType[]

export function itemIcon(type: CurriculumItemType | undefined): string {
	return ITEM_TYPE_META[type ?? 'Lecture']?.icon ?? ITEM_TYPE_META.Lecture.icon
}

/**
 * The length badge on a curriculum row.
 *
 * A lecture reports the video it actually holds; everything else reports the
 * author's estimate, because there is no measurable duration to fall back on.
 * Returns an empty string rather than "0min" when neither is known — a blank
 * badge is honest, a zero reads like a measurement.
 */
export function itemDuration(item: CurriculumItem): string {
	if (item.video_duration) return formatVideoLength(item.video_duration)
	if (item.duration_minutes) return `${item.duration_minutes}min`
	return ''
}

/** Whether an item is finished enough to be shown to learners. */
export function canPublishItem(item: CurriculumItem): {
	ok: boolean
	reason: string
} {
	if (item.item_type === 'Lecture' && !item.has_video && !item.description) {
		return {
			ok: false,
			reason: __('Add a video or a description before publishing this lecture.'),
		}
	}
	return { ok: true, reason: '' }
}
