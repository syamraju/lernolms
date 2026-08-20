<template>
	<div class="flex h-dvh flex-col bg-surface-gray-1">
		<!-- Dark command bar: identity, draft state, and the two global actions -->
		<header
			class="flex shrink-0 items-center gap-3 bg-gray-900 px-4 py-2.5 text-white"
		>
			<button
				type="button"
				class="flex shrink-0 items-center gap-1.5 rounded px-1 py-1 text-p-sm text-gray-300 transition-colors hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
				@click="backToCourses"
			>
				<span class="lucide-chevron-left size-4" />
				<span class="hidden sm:inline">{{ __('Back to courses') }}</span>
			</button>

			<h1 class="min-w-0 truncate text-p-base-semibold">
				{{ doc?.title || __('Untitled course') }}
			</h1>

			<span
				class="shrink-0 rounded-sm bg-gray-700 px-1.5 py-0.5 text-xs font-medium uppercase tracking-wide"
			>
				{{ statusLabel }}
			</span>

			<span
				v-if="status.data"
				class="hidden shrink-0 text-p-sm text-gray-300 lg:inline"
			>
				{{
					__('{0} of video content uploaded').format(
						formatVideoLength(status.data.video_seconds)
					)
				}}
			</span>

			<div class="ms-auto flex shrink-0 items-center gap-2">
				<span
					v-if="isDirty"
					class="hidden text-p-sm text-amber-300 sm:inline"
					aria-live="polite"
				>
					{{ __('Unsaved') }}
				</span>
				<button
					type="button"
					class="rounded bg-white/15 px-3 py-1.5 text-p-sm-medium transition-colors hover:bg-white/25 disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
					:disabled="!isDirty || saving"
					@click="save()"
				>
					{{ saving ? __('Saving…') : __('Save') }}
				</button>
				<button
					type="button"
					class="grid size-8 place-items-center rounded transition-colors hover:bg-white/15 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
					:class="showSettings && 'bg-white/20'"
					:aria-label="__('Course settings')"
					:aria-pressed="showSettings"
					@click="showSettings = !showSettings"
				>
					<span class="lucide-settings size-4" />
				</button>
			</div>
		</header>

		<div class="flex min-h-0 flex-1 flex-col lg:flex-row">
			<!-- Rail. On a phone it becomes a horizontal strip so the step list
			     never eats the viewport the step body needs. -->
			<nav
				class="shrink-0 border-b bg-surface-gray-1 lg:w-72 lg:overflow-y-auto lg:border-b-0 lg:border-e"
				:aria-label="__('Course creation steps')"
			>
				<div class="flex gap-2 overflow-x-auto p-3 lg:block lg:space-y-7 lg:p-6">
					<div
						v-for="group in STEP_GROUPS"
						:key="group.key"
						class="flex shrink-0 items-center gap-2 lg:block"
					>
						<h2
							class="hidden text-p-base-semibold text-ink-gray-9 lg:mb-3 lg:block"
						>
							{{ __(group.label) }}
						</h2>
						<ul class="flex gap-2 lg:block lg:space-y-1">
							<li v-for="step in stepsFor(group.key)" :key="step.key">
								<button
									type="button"
									class="flex w-full items-center gap-2.5 whitespace-nowrap rounded-md px-2 py-1.5 text-start text-p-base transition-colors hover:bg-surface-gray-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-outline-gray-4"
									:class="
										step.key === activeStep.key
											? 'bg-surface-gray-2 text-ink-gray-9 font-medium'
											: 'text-ink-gray-7'
									"
									:aria-current="step.key === activeStep.key ? 'step' : undefined"
									@click="goToStep(step.key)"
								>
									<span
										class="grid size-5 shrink-0 place-items-center rounded-full border"
										:class="
											isStepDone(step.key)
												? 'border-outline-gray-5 bg-surface-gray-7 text-white'
												: 'border-outline-gray-3'
										"
										aria-hidden="true"
									>
										<span
											v-if="isStepDone(step.key)"
											class="lucide-check size-3"
										/>
									</span>
									<span>
										{{ __(step.label) }}
										<span v-if="step.optional" class="text-ink-gray-5">
											{{ __('(optional)') }}
										</span>
									</span>
									<span class="sr-only">
										{{ isStepDone(step.key) ? __('Complete') : __('Incomplete') }}
									</span>
								</button>
							</li>
						</ul>
					</div>

					<div class="shrink-0 lg:pt-2">
						<Button
							v-if="status.data?.status === 'Under Review'"
							class="w-full"
							variant="outline"
							:loading="withdrawing"
							:label="__('Withdraw submission')"
							@click="withdrawSubmission"
						/>
						<Button
							v-else-if="status.data?.status === 'Approved'"
							class="w-full"
							variant="outline"
							:label="__('View course')"
							@click="viewCourse"
						/>
						<Button
							v-else
							class="w-full"
							variant="solid"
							:loading="submitting"
							:label="__('Submit for Review')"
							@click="attemptSubmit"
						/>
					</div>
				</div>
			</nav>

			<!-- Step body -->
			<main
				id="manageContent"
				tabindex="-1"
				class="min-h-0 flex-1 overflow-y-auto p-4 focus:outline-none lg:p-6"
			>
				<SkeletonLoader v-if="!resource.doc" variant="form" />
				<div
					v-else
					class="mx-auto max-w-4xl rounded-md border bg-surface-base shadow-sm"
				>
					<div class="border-b px-6 py-5">
						<h2 class="text-xl font-semibold text-ink-gray-9">
							{{ __(activeStep.label) }}
						</h2>
					</div>
					<div class="px-6 py-6">
						<component :is="activeStep.component" :key="activeStep.key" />
					</div>
				</div>
			</main>
		</div>

		<CourseManageSettings v-model="showSettings" />

		<SubmitBlockersModal
			v-model="showBlockers"
			:blockers="status.data?.blockers ?? []"
			@go="goToStep"
		/>
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, provide, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDebounceFn } from '@vueuse/core'
import {
	Button,
	call,
	createDocumentResource,
	createResource,
	toast,
	usePageMeta,
} from 'frappe-ui'
import SkeletonLoader from '@/components/SkeletonLoader.vue'
import CourseManageSettings from './CourseManageSettings.vue'
import SubmitBlockersModal from '@/components/Modals/SubmitBlockersModal.vue'
import { DEFAULT_STEP, MANAGE_STEPS, STEP_GROUPS, findStep } from './steps'
import type { ManageStep } from './steps'
import { errorMessage, formatVideoLength } from '@/utils/courseCreation'
import {
	saveShortcut,
	useKeyboardShortcuts,
} from '@/composables/useKeyboardShortcuts'
import { sessionStore } from '@/stores/session'
import type {
	CourseCreationStatus,
	CourseManageContext,
	Resource,
} from '@/types'
import type { LMSCourse } from '@/types/lms/LMSCourse'

const props = defineProps<{
	courseName: string
	step?: string
}>()

const route = useRoute()
const router = useRouter()
const { brand } = sessionStore() as { brand: { favicon?: string } }

const isDirty = ref(false)
const saving = ref(false)
const submitting = ref(false)
const withdrawing = ref(false)
const showSettings = ref(false)
const showBlockers = ref(false)

const resource = createDocumentResource({
	doctype: 'LMS Course',
	name: props.courseName,
	auto: true,
}) as Resource<LMSCourse | null>

const status = createResource({
	url: 'lms.lms.course_creation.get_course_creation_status',
	makeParams: () => ({ course: props.courseName }),
	auto: true,
}) as Resource<CourseCreationStatus | null>

const doc = computed(() => resource.doc)

// True while the freshly fetched doc is being normalised, so the checkbox
// coercion below doesn't register as an edit and arm an autosave the author
// never made.
let applyingServerData = false

watch(
	() => resource.doc,
	(loaded) => {
		if (!loaded) return
		applyingServerData = true
		normaliseCheckboxes(loaded)
		// Same tick would still be inside the reactive flush that the
		// normalisation triggers; release the guard after it settles.
		queueMicrotask(() => {
			applyingServerData = false
		})
	}
)

// Frappe sends checks as 0/1 and the switch controls bind to booleans. Left
// as-is, the first render of a switch writes `true` back over `1` and the doc
// looks dirty before the author touches anything.
const CHECKBOXES: (keyof LMSCourse)[] = [
	'published',
	'upcoming',
	'featured',
	'paid_course',
	'paid_certificate',
	'enable_certification',
	'captions_enabled',
	'daily_qa_digest',
	'lecture_ready_emails',
	'disable_self_learning',
	'enforce_lesson_completion',
]

function normaliseCheckboxes(target: LMSCourse) {
	const record = target as unknown as Record<string, unknown>
	for (const key of CHECKBOXES) {
		record[key] = target[key] ? true : false
	}
}

const autoSave = useDebounceFn(() => {
	if (isDirty.value) void save({ silent: true })
}, 1200)

function markDirty() {
	if (applyingServerData) return
	isDirty.value = true
	autoSave()
}

// Set when an edit arrives while a save is already in flight. Without it the
// second save is simply dropped: `isDirty` stays true so the header still says
// "Unsaved", but nothing ever retries, and the edit only lands if the author
// happens to type again or press Save.
let saveQueued = false

async function save(opts: { silent?: boolean } = {}): Promise<void> {
	if (!resource.doc) return
	if (saving.value) {
		saveQueued = true
		return
	}
	saving.value = true
	// `modified` is dropped deliberately: this shell does whole-doc
	// last-write-wins saves, and a stale timestamp trips Frappe's conflict
	// guard whenever another surface (the lesson editor, a publish toggle)
	// touched the course since the shell loaded.
	const payload: Record<string, unknown> = { ...resource.doc }
	delete payload.modified
	try {
		await resource.setValue.submit(payload)
		isDirty.value = false
		if (!opts.silent) toast.success(__('Changes saved'))
		void status.reload()
	} catch (error) {
		// Autosave failures stay quiet, but `isDirty` is left set so the header
		// keeps showing "Unsaved" and the work isn't silently dropped.
		if (!opts.silent) {
			toast.error(errorMessage(error, __('Could not save the course')))
		}
	} finally {
		saving.value = false
	}
	// Flush anything that arrived mid-flight. Runs after `saving` is cleared so
	// the recursive call takes the normal path, and stays silent because the
	// author already got (or will get) feedback from the call they triggered.
	if (saveQueued) {
		saveQueued = false
		await save({ silent: true })
	}
}

const activeStep = computed<ManageStep>(
	() => findStep(props.step) ?? MANAGE_STEPS[0]
)

function stepsFor(group: ManageStep['group']) {
	return MANAGE_STEPS.filter((step) => step.group === group)
}

function isStepDone(key: string): boolean {
	return Boolean(status.data?.steps?.[key])
}

function goToStep(key: string) {
	if (key === activeStep.value.key) return
	router.push({
		name: 'CourseManage',
		params: { courseName: props.courseName, step: key },
	})
}

function backToCourses() {
	router.push({ name: 'Courses', query: { tab: 'created' } })
}

function viewCourse() {
	router.push({
		name: 'CourseDetail',
		params: { courseName: props.courseName },
	})
}

async function attemptSubmit() {
	if (submitting.value) return
	// Flush pending edits first: submitting against a stale server copy would
	// report blockers the author has already cleared on screen.
	if (isDirty.value) await save({ silent: true })
	await status.reload()
	if (!status.data?.can_submit) {
		showBlockers.value = true
		return
	}
	submitting.value = true
	try {
		await call('lms.lms.course_creation.submit_course_for_review', {
			course: props.courseName,
		})
		toast.success(__('Course submitted for review'))
		void status.reload()
	} catch (error) {
		toast.error(errorMessage(error, __('Could not submit the course')))
	} finally {
		submitting.value = false
	}
}

async function withdrawSubmission() {
	withdrawing.value = true
	try {
		await call('lms.lms.course_creation.withdraw_course_submission', {
			course: props.courseName,
		})
		toast.success(__('Submission withdrawn'))
		void status.reload()
	} catch (error) {
		toast.error(errorMessage(error, __('Could not withdraw the submission')))
	} finally {
		withdrawing.value = false
	}
}

const statusLabel = computed(() => {
	if (doc.value?.published) return __('Live')
	switch (status.data?.status) {
		case 'Under Review':
			return __('In review')
		case 'Approved':
			return __('Approved')
		default:
			return __('Draft')
	}
})

// An unknown or absent :step lands on the first one rather than a blank body,
// and normalising it into the URL keeps refreshes and shared links stable.
watch(
	() => props.step,
	(step) => {
		if (!step || findStep(step)) return
		router.replace({
			name: 'CourseManage',
			params: { courseName: props.courseName, step: DEFAULT_STEP },
		})
	},
	{ immediate: true }
)

watch(
	() => props.courseName,
	(name) => {
		if (!name) return
		isDirty.value = false
		resource.reload()
		void status.reload()
	}
)

useKeyboardShortcuts({ shortcuts: [saveShortcut(() => save())] })

// Leaving with edits in flight would drop them; the debounce may not have
// fired yet. A synchronous flag check plus a fire-and-forget save is enough
// because the shell only unmounts on an in-app navigation.
onBeforeUnmount(() => {
	if (isDirty.value) void save({ silent: true })
})

// A plain object, not `reactive()`: the resources are already reactive and the
// only other member is a ref, which stays a ref for consumers this way.
provide<CourseManageContext>('courseManage', {
	resource,
	status,
	isDirty,
	markDirty,
	save: () => save(),
	goToStep,
})

usePageMeta(() => ({
	title: doc.value?.title
		? `${doc.value.title} — ${__('Course setup')}`
		: __('Course setup'),
	icon: brand.favicon,
}))

// Keep the deep-linked hash out of the way: this shell owns its own chrome and
// has no tab strip for a hash to select.
watch(
	() => route.hash,
	(hash) => {
		if (hash) router.replace({ ...route, hash: '' })
	},
	{ immediate: true }
)
</script>
