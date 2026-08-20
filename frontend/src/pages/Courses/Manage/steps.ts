import { defineAsyncComponent } from 'vue'
import type { Component } from 'vue'

/** One entry in the course-creation rail. */
export interface ManageStep {
	/** URL segment and the key the server's status map is keyed by. */
	key: string
	label: string
	/** Rail heading this step sits under. */
	group: 'plan' | 'content' | 'publish'
	/** Optional steps never block submission and read as "(optional)". */
	optional?: boolean
	component: Component
}

export const STEP_GROUPS: { key: ManageStep['group']; label: string }[] = [
	{ key: 'plan', label: 'Plan your course' },
	{ key: 'content', label: 'Create your content' },
	{ key: 'publish', label: 'Publish your course' },
]

// Async so the twelve step bodies stay out of the shell's chunk; only the one
// being viewed is fetched. The registry is the single source of truth for the
// rail's order, the URL segments and the keys `get_course_creation_status`
// returns, so the three can't drift apart.
export const MANAGE_STEPS: ManageStep[] = [
	{
		key: 'intended-learners',
		label: 'Intended learners',
		group: 'plan',
		component: defineAsyncComponent(() => import('./StepIntendedLearners.vue')),
	},
	{
		key: 'structure',
		label: 'Course structure',
		group: 'plan',
		component: defineAsyncComponent(() => import('./StepStructure.vue')),
	},
	{
		key: 'test-video',
		label: 'Setup & test video',
		group: 'plan',
		component: defineAsyncComponent(() => import('./StepTestVideo.vue')),
	},
	{
		key: 'film-edit',
		label: 'Film & edit',
		group: 'content',
		component: defineAsyncComponent(() => import('./StepFilmEdit.vue')),
	},
	{
		key: 'curriculum',
		label: 'Curriculum',
		group: 'content',
		component: defineAsyncComponent(() => import('./StepCurriculum.vue')),
	},
	{
		key: 'captions',
		label: 'Captions',
		group: 'content',
		optional: true,
		component: defineAsyncComponent(() => import('./StepCaptions.vue')),
	},
	{
		key: 'accessibility',
		label: 'Accessibility',
		group: 'content',
		optional: true,
		component: defineAsyncComponent(() => import('./StepAccessibility.vue')),
	},
	{
		key: 'landing-page',
		label: 'Course landing page',
		group: 'publish',
		component: defineAsyncComponent(() => import('./StepLandingPage.vue')),
	},
	{
		key: 'pricing',
		label: 'Pricing',
		group: 'publish',
		component: defineAsyncComponent(() => import('./StepPricing.vue')),
	},
	{
		key: 'promotions',
		label: 'Promotions',
		group: 'publish',
		component: defineAsyncComponent(() => import('./StepPromotions.vue')),
	},
	{
		key: 'messages',
		label: 'Course messages',
		group: 'publish',
		component: defineAsyncComponent(() => import('./StepMessages.vue')),
	},
]

export const DEFAULT_STEP = MANAGE_STEPS[0].key

export function findStep(key: string | undefined): ManageStep | undefined {
	return MANAGE_STEPS.find((step) => step.key === key)
}
