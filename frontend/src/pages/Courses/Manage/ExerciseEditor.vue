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
				{{ doc?.title || __('Coding exercise') }}
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

		<div class="flex min-h-0 flex-1 flex-col">
			<nav
				class="shrink-0 border-b bg-surface-base px-5"
				:aria-label="__('Exercise stages')"
			>
				<ul class="flex gap-1 overflow-x-auto">
					<li v-for="tab in TABS" :key="tab.key">
						<button
							type="button"
							class="whitespace-nowrap border-b-2 px-4 py-3 text-p-base transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-outline-gray-4"
							:class="
								tab.key === activeTab
									? 'border-outline-gray-5 font-medium text-ink-gray-9'
									: 'border-transparent text-ink-gray-6 hover:text-ink-gray-8'
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
				<div v-else class="mx-auto max-w-4xl space-y-6">
					<!-- Plan -->
					<section v-show="activeTab === 'plan'" class="space-y-5">
						<p class="text-p-base text-ink-gray-6">
							{{
								__(
									'Describe the problem in the learner’s terms: what they are given, what they must produce, and how they will know they are right.'
								)
							}}
						</p>
						<FormControl
							:modelValue="doc.title"
							variant="outline"
							:label="__('Title')"
							:required="true"
							@update:modelValue="set('title', $event)"
						/>
						<FormControl
							type="select"
							class="max-w-xs"
							:modelValue="doc.language"
							:options="LANGUAGES"
							variant="outline"
							:label="__('Language')"
							@update:modelValue="set('language', $event)"
						/>
						<div class="space-y-1.5">
							<InputLabel
								:id="statementLabelId"
								:label="__('Problem statement')"
								:required="true"
							/>
							<RichTextEditor
								:content="doc.problem_statement ?? ''"
								:editable="true"
								:fixedMenu="true"
								editorClass="prose-sm max-w-none border-b border-x border-outline-gray-2 rounded-b-md py-1 px-2 min-h-[12rem]"
								@change="(value: string) => set('problem_statement', value)"
							/>
							<p v-if="!hasStatement" class="text-p-sm text-ink-amber-3">
								{{ __('A problem statement is required to publish.') }}
							</p>
						</div>
					</section>

					<!-- Author solution -->
					<section v-show="activeTab === 'solution'" class="space-y-5">
						<p class="text-p-base text-ink-gray-6">
							{{
								__(
									'Write a working solution and the test cases that check it. Learners never see the solution — it is how you prove the tests are right.'
								)
							}}
						</p>
						<div class="space-y-1.5">
							<InputLabel :id="starterLabelId" :label="__('Starter code')" />
							<textarea
								:value="doc.starter_code ?? ''"
								rows="8"
								spellcheck="false"
								:aria-label="__('Starter code')"
								class="w-full rounded-md border border-outline-gray-2 bg-surface-base px-3 py-2 font-mono text-p-sm text-ink-gray-9 transition-colors hover:border-outline-gray-3 focus:border-outline-gray-4 focus:outline-none"
								@change="onCodeChange('starter_code', $event)"
							/>
						</div>
						<div class="space-y-1.5">
							<InputLabel :id="solutionLabelId" :label="__('Solution code')" />
							<textarea
								:value="doc.solution_code ?? ''"
								rows="10"
								spellcheck="false"
								:aria-label="__('Solution code')"
								class="w-full rounded-md border border-outline-gray-2 bg-surface-base px-3 py-2 font-mono text-p-sm text-ink-gray-9 transition-colors hover:border-outline-gray-3 focus:border-outline-gray-4 focus:outline-none"
								@change="onCodeChange('solution_code', $event)"
							/>
						</div>

						<div class="space-y-3">
							<h3 class="text-p-base-medium text-ink-gray-9">
								{{ __('Test cases') }}
							</h3>
							<ul v-if="testCases.length" class="space-y-2">
								<li
									v-for="(testCase, index) in testCases"
									:key="index"
									class="grid gap-2 rounded-md border p-3 sm:grid-cols-[1fr,1fr,auto]"
								>
									<FormControl
										:modelValue="testCase.input"
										variant="outline"
										:label="index === 0 ? __('Input') : ''"
										@update:modelValue="updateTestCase(index, 'input', $event)"
									/>
									<FormControl
										:modelValue="testCase.expected_output"
										variant="outline"
										:label="index === 0 ? __('Expected output') : ''"
										@update:modelValue="
											updateTestCase(index, 'expected_output', $event)
										"
									/>
									<Button
										variant="ghost"
										theme="red"
										class="!size-8 self-end"
										:label="__('Delete test case {0}').format(index + 1)"
										@click="removeTestCase(index)"
									>
										<template #icon>
											<span class="lucide-trash-2 size-4" />
										</template>
									</Button>
								</li>
							</ul>
							<p v-else class="text-p-base text-ink-gray-6">
								{{
									__(
										'No test cases yet. At least one is required before you can publish.'
									)
								}}
							</p>
							<Button variant="outline" :label="__('Test case')" @click="addTestCase">
								<template #prefix>
									<span class="lucide-plus size-4" />
								</template>
							</Button>
						</div>
					</section>

					<!-- Guide learners -->
					<section v-show="activeTab === 'guide'" class="space-y-3">
						<p class="text-p-base text-ink-gray-6">
							{{
								__(
									'Hints are shown to a learner who is stuck. Nudge them towards the idea rather than giving the answer away.'
								)
							}}
						</p>
						<RichTextEditor
							:content="doc.hints ?? ''"
							:editable="true"
							:fixedMenu="true"
							editorClass="prose-sm max-w-none border-b border-x border-outline-gray-2 rounded-b-md py-1 px-2 min-h-[10rem]"
							@change="(value: string) => set('hints', value)"
						/>
					</section>
				</div>
			</main>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, useId, watch } from 'vue'
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
import RichTextEditor from '@/components/RichTextEditor.vue'
import SkeletonLoader from '@/components/SkeletonLoader.vue'
import { InputLabel } from '@/components/Form/labeling'
import { errorMessage } from '@/utils/courseCreation'
import type { Resource } from '@/types'

const TABS = [
	{ key: 'plan', label: 'Plan exercise' },
	{ key: 'solution', label: 'Author solution' },
	{ key: 'guide', label: 'Guide learners' },
] as const

const LANGUAGES = ['Python', 'JavaScript', 'Rust', 'Go']

interface TestCase {
	name?: string
	input?: string
	expected_output?: string
}
interface Exercise {
	name: string
	title: string
	language: string
	problem_statement?: string
	starter_code?: string
	solution_code?: string
	hints?: string
	is_published?: 0 | 1 | boolean
	test_cases?: TestCase[]
	modified?: string
}

const props = defineProps<{ courseName: string; exerciseName: string }>()

const router = useRouter()
const activeTab = ref<(typeof TABS)[number]['key']>('plan')
const isDirty = ref(false)
const saving = ref(false)
const publishing = ref(false)

const statementLabelId = useId()
const starterLabelId = useId()
const solutionLabelId = useId()

const resource = createDocumentResource({
	doctype: 'LMS Programming Exercise',
	name: props.exerciseName,
	auto: true,
}) as Resource<Exercise | null>

const doc = computed(() => resource.doc)
const testCases = computed<TestCase[]>(() => doc.value?.test_cases ?? [])

const hasStatement = computed(() =>
	Boolean((doc.value?.problem_statement ?? '').replace(/<[^>]*>/g, '').trim())
)

// Both are enforced server-side — the statement through
// `mandatory_depends_on`, the test cases in the controller's validate. Naming
// them here turns a failed save into a disabled button with a reason.
const canPublish = computed(() => hasStatement.value && testCases.value.length > 0)

const publishTooltip = computed(() => {
	if (doc.value?.is_published) return __('Hide this exercise from learners')
	if (!hasStatement.value) return __('Write a problem statement before publishing.')
	if (!testCases.value.length) return __('Add at least one test case.')
	return __('Show this exercise to learners')
})

const autoSave = useDebounceFn(() => {
	if (isDirty.value) void save({ silent: true })
}, 1200)

function markDirty() {
	isDirty.value = true
	autoSave()
}

function set(field: keyof Exercise, value: unknown) {
	if (!resource.doc) return
	;(resource.doc as Record<string, unknown>)[field] = value
	markDirty()
}

function onCodeChange(field: 'starter_code' | 'solution_code', event: Event) {
	set(field, (event.target as HTMLTextAreaElement).value)
}

function addTestCase() {
	if (!resource.doc) return
	resource.doc.test_cases = [...testCases.value, { input: '', expected_output: '' }]
	markDirty()
}

function updateTestCase(index: number, field: keyof TestCase, value: string) {
	if (!resource.doc) return
	resource.doc.test_cases = testCases.value.map((testCase, i) =>
		i === index ? { ...testCase, [field]: value } : testCase
	)
	markDirty()
}

function removeTestCase(index: number) {
	if (!resource.doc) return
	resource.doc.test_cases = testCases.value.filter((_, i) => i !== index)
	markDirty()
}

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
		if (!opts.silent) toast.success(__('Exercise saved'))
	} catch (error) {
		if (!opts.silent) {
			toast.error(errorMessage(error, __('Could not save the exercise')))
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
		await save({ silent: true })
		toast.success(next ? __('Exercise published') : __('Exercise unpublished'))
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
	() => props.exerciseName,
	() => {
		isDirty.value = false
		resource.reload()
	}
)

usePageMeta(() => ({ title: doc.value?.title || __('Coding exercise') }))
</script>
