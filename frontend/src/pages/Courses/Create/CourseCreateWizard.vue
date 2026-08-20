<template>
	<div class="flex h-dvh flex-col bg-surface-base">
		<header
			class="flex shrink-0 items-center justify-between gap-4 border-b ps-5 pe-5"
		>
			<div class="flex items-center gap-5">
				<span class="text-p-lg-semibold text-ink-gray-9">
					{{ brand.name || __('Learno') }}
				</span>
				<div
					class="border-s py-4 ps-5 text-p-base text-ink-gray-7"
					aria-live="polite"
				>
					{{ __('Step {0} of {1}').format(stepIndex + 1, STEPS.length) }}
				</div>
			</div>
			<Button variant="ghost" :label="__('Exit')" @click="exit" />
		</header>
		<div
			class="h-1 shrink-0 bg-surface-gray-2"
			role="progressbar"
			:aria-valuenow="stepIndex + 1"
			aria-valuemin="1"
			:aria-valuemax="STEPS.length"
			:aria-label="__('Course setup progress')"
		>
			<div
				class="h-full bg-surface-gray-7 transition-[width] duration-300 ease-out"
				:style="{ width: `${((stepIndex + 1) / STEPS.length) * 100}%` }"
			/>
		</div>

		<main
			class="flex-1 overflow-y-auto px-5 py-12"
			id="wizardContent"
			tabindex="-1"
		>
			<div class="mx-auto max-w-3xl">
				<h1
					class="text-center text-2xl font-semibold leading-tight text-ink-gray-9 md:text-3xl"
				>
					{{ current.heading }}
				</h1>
				<p
					v-if="current.subheading"
					class="mt-3 text-center text-p-base text-ink-gray-6"
				>
					{{ current.subheading }}
				</p>

				<!-- Step 1 — what kind of course -->
				<div
					v-if="current.key === 'type'"
					class="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2"
					role="radiogroup"
					:aria-label="__('Course type')"
				>
					<button
						v-for="option in COURSE_TYPES"
						:key="option.value"
						type="button"
						role="radio"
						:aria-checked="draft.course_type === option.value"
						class="rounded-md border-2 p-6 text-center transition-colors hover:border-outline-gray-4"
						:class="
							draft.course_type === option.value
								? 'border-outline-gray-5 bg-surface-gray-1'
								: 'border-outline-gray-2'
						"
						@click="draft.course_type = option.value"
					>
						<span
							class="mx-auto mb-3 block size-6 text-ink-gray-8"
							:class="option.icon"
						/>
						<span class="block text-p-base-semibold text-ink-gray-9">
							{{ option.label }}
						</span>
						<span class="mt-2 block text-p-sm text-ink-gray-6">
							{{ option.description }}
						</span>
					</button>
				</div>

				<!-- Step 2 — working title -->
				<div v-else-if="current.key === 'title'" class="mx-auto mt-10 max-w-xl">
					<FormControl
						ref="titleInput"
						v-model="draft.title"
						variant="outline"
						:label="__('Course title')"
						:placeholder="__('e.g. Learn Journaling for Beginners')"
						:maxlength="TITLE_LIMIT"
						autocomplete="off"
						@keyup.enter="next()"
					/>
					<div class="mt-1.5 text-end text-p-sm tabular-nums text-ink-gray-5">
						{{ TITLE_LIMIT - draft.title.length }}
					</div>
				</div>

				<!-- Step 3 — category -->
				<div
					v-else-if="current.key === 'category'"
					class="mx-auto mt-10 max-w-xl"
				>
					<Link
						v-model="draft.category"
						doctype="LMS Category"
						:label="__('Category')"
						:placeholder="__('Choose a category')"
						:inlineCreate="true"
						inlineCreatePlaceholder="Category name"
						:onCreate="onCreateCategory"
						variant="outline"
					/>
				</div>

				<!-- Step 4 — how much time -->
				<div
					v-else-if="current.key === 'time'"
					class="mx-auto mt-10 max-w-xl space-y-3"
					role="radiogroup"
					:aria-label="__('Time commitment')"
				>
					<button
						v-for="option in TIME_COMMITMENTS"
						:key="option"
						type="button"
						role="radio"
						:aria-checked="draft.time_commitment === option"
						class="flex w-full items-center gap-3 rounded-md border p-4 text-start transition-colors hover:border-outline-gray-4"
						:class="
							draft.time_commitment === option
								? 'border-outline-gray-5 bg-surface-gray-1'
								: 'border-outline-gray-2'
						"
						@click="draft.time_commitment = option"
					>
						<span
							class="grid size-5 shrink-0 place-items-center rounded-full border-2"
							:class="
								draft.time_commitment === option
									? 'border-outline-gray-5'
									: 'border-outline-gray-3'
							"
						>
							<span
								v-if="draft.time_commitment === option"
								class="size-2.5 rounded-full bg-surface-gray-7"
							/>
						</span>
						<span class="text-p-base-medium text-ink-gray-9">
							{{ __(option) }}
						</span>
					</button>
				</div>
			</div>
		</main>

		<footer
			class="flex shrink-0 items-center justify-between gap-3 border-t px-5 py-4"
		>
			<Button
				v-if="stepIndex > 0"
				variant="outline"
				:label="__('Previous')"
				@click="previous"
			/>
			<span v-else />
			<Button
				variant="solid"
				:disabled="!canContinue"
				:loading="creating"
				:label="isLastStep ? __('Create course') : __('Continue')"
				@click="next"
			/>
		</footer>
	</div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Button, FormControl, call, toast, usePageMeta } from 'frappe-ui'
import Link from '@/components/Controls/Link.vue'
import { canCreateCourse, createLMSCategory } from '@/utils'
import { errorMessage } from '@/utils/courseCreation'
import { createHandler } from '@/utils/createHandler'
import { sessionStore } from '@/stores/session'

const TITLE_LIMIT = 60

const COURSE_TYPES = [
	{
		value: 'Course' as const,
		label: __('Course'),
		icon: 'lucide-monitor-play',
		description: __(
			'Create rich learning experiences with video lessons, quizzes and exercises.'
		),
	},
	{
		value: 'Practice Test' as const,
		label: __('Practice Test'),
		icon: 'lucide-list-checks',
		description: __(
			'Help learners prepare for certification exams with practice questions.'
		),
	},
]

const TIME_COMMITMENTS = [
	'0-2 hours per week',
	'2-4 hours per week',
	'5+ hours per week',
	'Not decided yet',
] as const

interface WizardStep {
	key: 'type' | 'title' | 'category' | 'time'
	heading: string
	subheading?: string
}

const STEPS: WizardStep[] = [
	{
		key: 'type',
		heading: __("First, let's find out what type of course you're making."),
	},
	{
		key: 'title',
		heading: __('How about a working title?'),
		subheading: __(
			"It's ok if you can't think of a good title now. You can change it later."
		),
	},
	{
		key: 'category',
		heading: __("What category best fits the knowledge you'll share?"),
		subheading: __(
			"If you're not sure about the right category, you can change it later."
		),
	},
	{
		key: 'time',
		heading: __('How much time can you spend creating your course per week?'),
		subheading: __(
			"There's no wrong answer. We can help you reach your goal even if you don't have much time."
		),
	},
]

const router = useRouter()
const { brand } = sessionStore() as {
	brand: { name?: string; favicon?: string }
}

const draft = reactive({
	course_type: 'Course' as 'Course' | 'Practice Test',
	title: '',
	category: '',
	time_commitment: '' as string,
})

const stepIndex = ref(0)
const creating = ref(false)
const titleInput = ref<{ $el?: HTMLElement } | null>(null)

const current = computed<WizardStep>(() => STEPS[stepIndex.value])
const isLastStep = computed(() => stepIndex.value === STEPS.length - 1)

// Every step but the category gate has a required answer. Category is
// deliberately skippable: the copy tells the author they can change it later,
// so blocking on it would contradict the page.
const canContinue = computed(() => {
	switch (current.value.key) {
		case 'type':
			return Boolean(draft.course_type)
		case 'title':
			return draft.title.trim().length > 0
		case 'category':
			return true
		case 'time':
			return Boolean(draft.time_commitment)
		default:
			return false
	}
})

onMounted(() => {
	if (!canCreateCourse()) {
		toast.error(__('You are not permitted to create a course.'))
		router.replace({ name: 'Courses' })
	}
})

function previous() {
	if (stepIndex.value > 0) stepIndex.value -= 1
}

async function next() {
	if (!canContinue.value || creating.value) return
	if (!isLastStep.value) {
		stepIndex.value += 1
		// The title step is the only one with a text field; focusing it saves a
		// click and keeps keyboard-only progress through the wizard unbroken.
		if (current.value.key === 'title') {
			await nextTick()
			titleInput.value?.$el?.querySelector('input')?.focus()
		}
		return
	}
	await createCourse()
}

async function createCourse() {
	creating.value = true
	try {
		const courseName = await call('lms.lms.course_creation.create_course_draft', {
			title: draft.title.trim(),
			course_type: draft.course_type,
			category: draft.category || null,
			time_commitment: draft.time_commitment || null,
		})
		toast.success(__('Course created'))
		router.replace({
			name: 'CourseManage',
			params: { courseName, step: 'intended-learners' },
		})
	} catch (error) {
		toast.error(errorMessage(error, __('Could not create the course')))
	} finally {
		creating.value = false
	}
}

function createCategory(name: string, done?: () => void) {
	if (!name) return
	createLMSCategory(name).then((categoryName?: string) => {
		if (!categoryName) return
		draft.category = categoryName
		done?.()
	})
}

function onCreateCategory(value: string | null, done?: () => void) {
	createHandler(value, done, (name) => createCategory(name, done))
}

function exit() {
	router.push({ name: 'Courses' })
}

usePageMeta(() => ({
	title: __('Create a course'),
	icon: brand.favicon,
}))
</script>
