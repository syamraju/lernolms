<template>
	<div class="flex h-dvh flex-col bg-surface-gray-1">
		<header class="flex shrink-0 items-center gap-3 border-b bg-surface-base px-5 py-3">
			<button
				type="button"
				class="flex shrink-0 items-center gap-1.5 rounded px-1 py-1 text-p-sm text-ink-gray-7 transition-colors hover:text-ink-gray-9 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-outline-gray-4"
				@click="backToCurriculum"
			>
				<span class="lucide-chevron-left size-4" />
				{{ __('Back to curriculum') }}
			</button>
			<h1 class="min-w-0 truncate text-xl font-semibold text-ink-gray-9">
				{{ doc?.title || __('Assignment') }}
			</h1>
			<Badge
				:theme="doc?.is_published ? 'green' : 'orange'"
				:label="doc?.is_published ? __('Published') : __('Draft')"
			/>
			<div class="ms-auto flex shrink-0 items-center gap-2">
				<span v-if="isDirty" class="text-p-sm text-ink-amber-3" aria-live="polite">
					{{ __('Unsaved') }}
				</span>
				<Button
					:disabled="!isDirty"
					:loading="saving"
					:label="__('Save')"
					@click="save()"
				/>
				<Tooltip :text="publishTooltip">
					<Button
						variant="solid"
						:disabled="!doc?.is_published && !canPublish"
						:loading="publishing"
						:label="doc?.is_published ? __('Unpublish') : __('Publish')"
						@click="togglePublished"
					/>
				</Tooltip>
			</div>
		</header>

		<div class="flex min-h-0 flex-1 flex-col lg:flex-row">
			<nav
				class="shrink-0 border-b lg:w-56 lg:border-b-0 lg:border-e"
				:aria-label="__('Assignment sections')"
			>
				<ul class="flex gap-1 overflow-x-auto p-3 lg:block lg:space-y-1">
					<li v-for="tab in TABS" :key="tab.key">
						<button
							type="button"
							class="w-full whitespace-nowrap rounded-md px-3 py-1.5 text-start text-p-base transition-colors hover:bg-surface-gray-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-outline-gray-4"
							:class="
								tab.key === activeTab
									? 'bg-surface-gray-2 font-medium text-ink-gray-9'
									: 'text-ink-gray-7'
							"
							:aria-current="tab.key === activeTab ? 'page' : undefined"
							@click="activeTab = tab.key"
						>
							{{ __(tab.label) }}
						</button>
					</li>
				</ul>
			</nav>

			<main class="min-h-0 flex-1 overflow-y-auto p-4 lg:p-6">
				<SkeletonLoader v-if="!doc" variant="form" />
				<div v-else class="mx-auto max-w-3xl space-y-6">
					<!-- Basic info -->
					<section v-show="activeTab === 'basic'" class="space-y-5">
						<FormControl
							:modelValue="doc.title"
							variant="outline"
							:label="__('Title')"
							:maxlength="80"
							:required="true"
							@update:modelValue="set('title', $event)"
						/>
						<FormControl
							:modelValue="doc.description"
							type="textarea"
							:rows="3"
							variant="outline"
							:label="__('Description')"
							:placeholder="
								__('What this assignment is for, in a sentence or two.')
							"
							@update:modelValue="set('description', $event)"
						/>
						<FormControl
							type="number"
							min="1"
							class="max-w-xs"
							:modelValue="doc.estimated_duration ?? 0"
							variant="outline"
							:label="__('Estimated duration (minutes)')"
							:required="true"
							@update:modelValue="setDuration"
						/>
						<p
							v-if="!Number(doc.estimated_duration)"
							class="text-p-sm text-ink-amber-3"
						>
							{{ __('A minimum duration of 1 minute is required to publish.') }}
						</p>
						<FormControl
							type="select"
							class="max-w-xs"
							:modelValue="doc.type"
							:options="SUBMISSION_TYPES"
							variant="outline"
							:label="__('How learners submit')"
							@update:modelValue="set('type', $event)"
						/>
					</section>

					<!-- Instructions -->
					<section v-show="activeTab === 'instructions'" class="space-y-3">
						<p class="text-p-base text-ink-gray-6">
							{{
								__(
									'Tell learners what to do before they attempt the questions — what to read, gather or prepare.'
								)
							}}
						</p>
						<RichTextEditor
							:content="doc.instructions ?? ''"
							:editable="true"
							:fixedMenu="true"
							editorClass="prose-sm max-w-none border-b border-x border-outline-gray-2 rounded-b-md py-1 px-2 min-h-[12rem]"
							@change="(value: string) => set('instructions', value)"
						/>
					</section>

					<!-- Questions -->
					<section v-show="activeTab === 'questions'" class="space-y-3">
						<p class="text-p-base text-ink-gray-6">
							{{
								__(
									'The task itself. This is what learners answer and submit.'
								)
							}}
						</p>
						<RichTextEditor
							:content="doc.question ?? ''"
							:editable="true"
							:fixedMenu="true"
							editorClass="prose-sm max-w-none border-b border-x border-outline-gray-2 rounded-b-md py-1 px-2 min-h-[12rem]"
							@change="(value: string) => set('question', value)"
						/>
						<p v-if="!hasQuestion" class="text-p-sm text-ink-amber-3">
							{{ __('A question is required to publish.') }}
						</p>
					</section>

					<!-- Solutions -->
					<section v-show="activeTab === 'solutions'" class="space-y-4">
						<BooleanSwitch
							size="sm"
							:modelValue="Boolean(doc.show_answer)"
							:label="__('Show the solution to learners')"
							:description="
								__('Revealed after they submit, so they can check their work.')
							"
							@update:modelValue="setCheck('show_answer', $event)"
						/>
						<BooleanSwitch
							size="sm"
							:modelValue="Boolean(doc.grade_assignment)"
							:label="__('Grade this assignment')"
							:description="
								__('Submissions go to an evaluator instead of being auto-accepted.')
							"
							@update:modelValue="setCheck('grade_assignment', $event)"
						/>
						<RichTextEditor
							:content="doc.answer ?? ''"
							:editable="true"
							:fixedMenu="true"
							editorClass="prose-sm max-w-none border-b border-x border-outline-gray-2 rounded-b-md py-1 px-2 min-h-[10rem]"
							@change="(value: string) => set('answer', value)"
						/>
					</section>
				</div>
			</main>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useDebounceFn } from '@vueuse/core'
import {
	Badge,
	Button,
	FormControl,
	Tooltip,
	createDocumentResource,
	toast,
	usePageMeta,
} from 'frappe-ui'
import BooleanSwitch from '@/components/Controls/BooleanSwitch.vue'
import RichTextEditor from '@/components/RichTextEditor.vue'
import SkeletonLoader from '@/components/SkeletonLoader.vue'
import { errorMessage } from '@/utils/courseCreation'
import type { Resource } from '@/types'

const TABS = [
	{ key: 'basic', label: 'Basic Info' },
	{ key: 'instructions', label: 'Instructions' },
	{ key: 'questions', label: 'Questions' },
	{ key: 'solutions', label: 'Solutions' },
] as const

const SUBMISSION_TYPES = ['Text', 'Document', 'PDF', 'URL', 'Image']

interface Assignment {
	name: string
	title: string
	description?: string
	estimated_duration?: number
	type: string
	instructions?: string
	question?: string
	answer?: string
	show_answer?: 0 | 1 | boolean
	grade_assignment?: 0 | 1 | boolean
	is_published?: 0 | 1 | boolean
	modified?: string
}

const props = defineProps<{ courseName: string; assignmentName: string }>()

const router = useRouter()
const activeTab = ref<(typeof TABS)[number]['key']>('basic')
const isDirty = ref(false)
const saving = ref(false)
const publishing = ref(false)

const resource = createDocumentResource({
	doctype: 'LMS Assignment',
	name: props.assignmentName,
	auto: true,
}) as Resource<Assignment | null>

const doc = computed(() => resource.doc)

const hasQuestion = computed(() =>
	Boolean((doc.value?.question ?? '').replace(/<[^>]*>/g, '').trim())
)

// The server enforces both of these through `mandatory_depends_on`; naming
// them here turns a save error into a disabled button with a reason.
const canPublish = computed(
	() => hasQuestion.value && Number(doc.value?.estimated_duration) > 0
)

const publishTooltip = computed(() => {
	if (doc.value?.is_published) return __('Hide this assignment from learners')
	if (!hasQuestion.value) return __('Write a question before publishing.')
	if (!Number(doc.value?.estimated_duration)) {
		return __('Set an estimated duration of at least 1 minute.')
	}
	return __('Show this assignment to learners')
})

const autoSave = useDebounceFn(() => {
	if (isDirty.value) void save({ silent: true })
}, 1200)

function markDirty() {
	isDirty.value = true
	autoSave()
}

function set(field: keyof Assignment, value: unknown) {
	if (!resource.doc) return
	;(resource.doc as Record<string, unknown>)[field] = value
	markDirty()
}

function setCheck(field: keyof Assignment, value: boolean) {
	set(field, value ? 1 : 0)
}

function setDuration(value: string | number) {
	set('estimated_duration', Math.max(Number(value) || 0, 0))
}

// Same reason as the course shell: this is a whole-doc last-write-wins save,
// and a stale `modified` trips Frappe's conflict guard when the curriculum
// renamed the assignment while this page was open.
let saveQueued = false
async function save(opts: { silent?: boolean } = {}): Promise<void> {
	if (!resource.doc) return
	if (saving.value) {
		saveQueued = true
		return
	}
	saving.value = true
	const payload: Record<string, unknown> = { ...resource.doc }
	delete payload.modified
	try {
		await resource.setValue.submit(payload)
		isDirty.value = false
		if (!opts.silent) toast.success(__('Assignment saved'))
	} catch (error) {
		if (!opts.silent) {
			toast.error(errorMessage(error, __('Could not save the assignment')))
		}
	} finally {
		saving.value = false
	}
	if (saveQueued) {
		saveQueued = false
		await save({ silent: true })
	}
}

async function togglePublished() {
	if (!resource.doc) return
	publishing.value = true
	const next = resource.doc.is_published ? 0 : 1
	resource.doc.is_published = next
	try {
		// Through the normal save so the server's publish-time validation runs
		// and a missing question or duration is refused with its own message.
		await save({ silent: true })
		toast.success(next ? __('Assignment published') : __('Assignment unpublished'))
	} finally {
		publishing.value = false
	}
}

function backToCurriculum() {
	router.push({
		name: 'CourseDetail',
		params: { courseName: props.courseName },
		hash: '#editor',
		query: { view: 'curriculum' },
	})
}

onBeforeUnmount(() => {
	if (isDirty.value) void save({ silent: true })
})

watch(
	() => props.assignmentName,
	() => {
		isDirty.value = false
		resource.reload()
	}
)

usePageMeta(() => ({ title: doc.value?.title || __('Assignment') }))
</script>
