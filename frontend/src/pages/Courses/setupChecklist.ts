import {
	accessibilityGuidance,
	filmEditGuidance,
	intendedLearnersGuidance,
	promotionsGuidance,
	structureGuidance,
} from './setupGuidance'
import type { GuidanceBlock } from './setupGuidance'

/**
 * Where a checklist item is actually done.
 *
 * Every item points at a tab of the course detail page rather than owning a
 * form of its own. That is the whole point of the checklist: it reports on
 * state and hands off, so there is exactly one place to edit each field.
 * `focus` is passed through as a query param and matched against a section's
 * `id` by the receiving tab, which scrolls it into view.
 */
export interface SetupTarget {
	tab: 'overview' | 'editor' | 'settings'
	/** Query params the receiving tab reads, e.g. `{ focus: 'audience' }`. */
	query?: Record<string, string>
	label: string
}

export interface SetupItem {
	/**
	 * Matches a key in `get_course_creation_status().steps` and in the `step`
	 * field of its blockers, so the server stays the single source of truth for
	 * what counts as done.
	 */
	key: string
	label: string
	group: 'plan' | 'content' | 'publish'
	/** Optional items are shown as such and never gate submission. */
	optional?: boolean
	/** One line saying what "done" means, shown under the label. */
	hint: string
	target?: SetupTarget
	/** Advisory copy, revealed when the item is expanded. */
	guidance?: () => GuidanceBlock[]
}

export const SETUP_GROUPS: { key: SetupItem['group']; label: string }[] = [
	{ key: 'plan', label: 'Plan your course' },
	{ key: 'content', label: 'Create your content' },
	{ key: 'publish', label: 'Publish your course' },
]

export const SETUP_ITEMS: SetupItem[] = [
	{
		key: 'intended-learners',
		label: 'Intended learners',
		group: 'plan',
		hint: 'Four learning objectives, plus requirements and who the course is for.',
		target: {
			tab: 'settings',
			query: { focus: 'audience' },
			label: 'Edit in Settings',
		},
		guidance: intendedLearnersGuidance,
	},
	{
		key: 'structure',
		label: 'Course structure',
		group: 'plan',
		hint: 'Name the single skill at the centre of the course.',
		target: {
			tab: 'settings',
			query: { focus: 'details' },
			label: 'Edit in Settings',
		},
		guidance: structureGuidance,
	},
	{
		key: 'test-video',
		label: 'Setup & test video',
		group: 'plan',
		hint: 'Upload a minute of footage to check lighting, sound and framing.',
		target: {
			tab: 'settings',
			query: { focus: 'production' },
			label: 'Edit in Settings',
		},
	},
	{
		key: 'film-edit',
		label: 'Film & edit',
		group: 'content',
		hint: 'Production guidance for recording your lectures.',
		guidance: filmEditGuidance,
	},
	{
		key: 'curriculum',
		label: 'Curriculum',
		group: 'content',
		hint: 'At least five lectures and thirty minutes of video.',
		target: {
			tab: 'editor',
			query: { view: 'curriculum' },
			label: 'Open the curriculum',
		},
	},
	{
		key: 'captions',
		label: 'Captions',
		group: 'content',
		optional: true,
		hint: 'Automatic captions for every lecture with a video.',
		target: {
			tab: 'settings',
			query: { focus: 'captions' },
			label: 'Edit in Settings',
		},
	},
	{
		key: 'accessibility',
		label: 'Accessibility',
		group: 'content',
		optional: true,
		hint: 'Reach learners who cannot see or hear your lectures.',
		guidance: accessibilityGuidance,
	},
	{
		key: 'landing-page',
		label: 'Course landing page',
		group: 'publish',
		hint: 'Title, short introduction, image and a description of 200 words.',
		target: {
			tab: 'settings',
			query: { focus: 'details' },
			label: 'Edit in Settings',
		},
	},
	{
		key: 'pricing',
		label: 'Pricing',
		group: 'publish',
		hint: 'Free, or a price the course is actually sold at.',
		target: {
			tab: 'settings',
			query: { focus: 'publish' },
			label: 'Edit in Settings',
		},
	},
	{
		key: 'promotions',
		label: 'Promotions',
		group: 'publish',
		optional: true,
		hint: 'Coupons that discount this course for a limited time.',
		target: {
			tab: 'settings',
			query: { focus: 'promotions' },
			label: 'Edit in Settings',
		},
		guidance: promotionsGuidance,
	},
	{
		key: 'messages',
		label: 'Course messages',
		group: 'publish',
		hint: 'What learners read when they start and when they finish.',
		target: {
			tab: 'settings',
			query: { focus: 'messages' },
			label: 'Edit in Settings',
		},
	},
]

export function itemsFor(group: SetupItem['group']): SetupItem[] {
	return SETUP_ITEMS.filter((item) => item.group === group)
}

export function findItem(key: string | undefined): SetupItem | undefined {
	return SETUP_ITEMS.find((item) => item.key === key)
}
