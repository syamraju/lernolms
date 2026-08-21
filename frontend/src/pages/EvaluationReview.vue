<template>
	<PageHeader :breadcrumbs="breadcrumbs">
		<template #actions>
			<Badge
				v-if="dirty"
				:label="__('Not saved')"
				variant="subtle"
				theme="orange"
			/>
			<HeaderButton
				:label="__('Save draft')"
				icon="lucide-save"
				:loading="saving === 'draft'"
				:disabled="isEvaluated || Boolean(validationError)"
				@click="submit(false)"
			/>
			<ShortcutTooltip :label="__('Release result')" combo="Mod+S">
				<HeaderButton
					:label="isEvaluated ? __('Update result') : __('Release result')"
					icon="lucide-check"
					variant="solid"
					:loading="saving === 'final'"
					:disabled="Boolean(validationError)"
					@click="submit(true)"
				/>
			</ShortcutTooltip>
		</template>
	</PageHeader>

	<PageBody>
		<SkeletonLoader
			v-if="evaluation.loading && !evaluation.data"
			variant="form"
			class="px-5 py-5"
		/>

		<div
			v-else-if="evaluation.data"
			class="mx-auto w-full pb-16 sm:w-2/3 sm:border-x"
		>
			<div class="space-y-3 border-b px-10 pb-5 pt-5">
				<div class="flex flex-wrap items-center gap-2">
					<h1 class="text-lg-semibold text-ink-gray-9">
						{{ evaluation.data.quiz_title }}
					</h1>
					<Badge
						:label="
							isEvaluated ? __('Evaluated') : __('Waiting on you')
						"
						variant="subtle"
						:theme="isEvaluated ? 'green' : 'orange'"
					/>
				</div>
				<p class="text-p-base text-ink-gray-7">
					{{
						__('{0} · submitted {1}').format(
							evaluation.data.member_name || evaluation.data.member,
							timeAgo(evaluation.data.submitted_on)
						)
					}}
					<template v-if="evaluation.data.course_title">
						· {{ evaluation.data.course_title }}
					</template>
				</p>
				<p
					v-if="evaluation.data.blocks_progress && !isEvaluated"
					class="text-p-sm text-ink-amber-3"
				>
					{{
						__(
							'This lesson is held open until you mark it — the learner cannot move on yet.'
						)
					}}
				</p>

				<!--
					The running total is the one number the evaluator is steering, so it
					stays visible while they work rather than appearing after the save.
				-->
				<div
					class="flex flex-wrap items-center gap-x-6 gap-y-1 rounded-md bg-surface-gray-1 px-4 py-3 text-p-sm"
				>
					<span class="text-ink-gray-7">
						<strong class="tabular-nums text-ink-gray-9">
							{{ awardedTotal }} / {{ evaluation.data.score_out_of }}
						</strong>
						{{ __('marks') }}
					</span>
					<span class="text-ink-gray-7">
						<strong class="tabular-nums text-ink-gray-9">
							{{ percentage }}%
						</strong>
						<span class="text-ink-gray-5">
							{{
								__('pass mark {0}%').format(
									evaluation.data.passing_percentage
								)
							}}
						</span>
					</span>
					<span :class="passes ? 'text-ink-green-3' : 'text-ink-gray-6'">
						{{ passes ? __('Passes') : __('Below the pass mark') }}
					</span>
				</div>
			</div>

			<ol class="divide-y">
				<li
					v-for="(answer, index) in draft"
					:key="answer.row"
					class="space-y-4 px-10 py-6"
				>
					<div class="text-ink-gray-9">
						<span class="text-p-sm text-ink-gray-5">
							{{ __('Task {0}').format(index + 1) }}
						</span>
						<div class="leading-5" v-safe-html:rich="answer.question" />
					</div>

					<div
						class="rounded-md border border-outline-gray-2 bg-surface-gray-1 p-4"
					>
						<div class="mb-1 text-p-sm text-ink-gray-5">
							{{ __('Answer') }}
						</div>
						<div
							v-if="stripHtml(answer.answer)"
							class="prose-sm max-w-none leading-5 text-ink-gray-9"
							v-safe-html:rich="answer.answer"
						/>
						<p v-else class="text-p-base italic text-ink-gray-5">
							{{ __('Left blank.') }}
						</p>
					</div>

					<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
						<FormControl
							type="number"
							min="0"
							:max="answer.marks_out_of"
							variant="outline"
							v-model="answer.marks"
							:label="
								__('Marks (out of {0})').format(answer.marks_out_of)
							"
						/>
						<FormControl
							type="textarea"
							rows="2"
							variant="outline"
							v-model="answer.evaluator_feedback"
							:label="__('Feedback (optional)')"
							:placeholder="__('What was right, what to fix next time.')"
						/>
					</div>
				</li>
			</ol>

			<div class="border-t px-10 py-6">
				<FormControl
					type="textarea"
					rows="3"
					variant="outline"
					v-model="comment"
					:label="__('Overall comment (optional)')"
					:placeholder="__('A note to the learner about the whole submission.')"
				/>
				<p
					v-if="validationError"
					class="mt-2 text-p-sm text-ink-red-3"
					role="alert"
				>
					{{ validationError }}
				</p>
				<p v-else class="mt-2 text-p-sm text-ink-gray-6">
					{{
						isEvaluated
							? __(
									'This result has been released. Saving again updates it and tells the learner.'
							  )
							: __(
									'Releasing the result notifies the learner and records their score.'
							  )
					}}
				</p>
			</div>
		</div>
	</PageBody>
</template>

<script setup lang="ts">
/**
 * Marking one subjective quiz submission.
 *
 * Only the marks and the feedback are the evaluator's to set. The score, the
 * percentage and the pass/fail are all recomputed by the server from those
 * marks, so the totals shown here are a preview of the server's arithmetic and
 * never a second source of it.
 */
import { computed, inject, onMounted, ref, watch } from 'vue'
import {
	Badge,
	FormControl,
	call,
	createResource,
	toast,
	usePageMeta,
} from 'frappe-ui'
import { useRouter } from 'vue-router'
import PageHeader from '@/components/Layouts/PageHeader.vue'
import PageBody from '@/components/Layouts/PageBody.vue'
import HeaderButton from '@/components/HeaderButton.vue'
import ShortcutTooltip from '@/components/ShortcutTooltip.vue'
import SkeletonLoader from '@/components/SkeletonLoader.vue'
import {
	useKeyboardShortcuts,
	saveShortcut,
} from '@/composables/useKeyboardShortcuts'
import { sessionStore } from '@/stores/session'
import { errorMessage } from '@/utils/courseCreation'
import { timeAgo } from '@/utils'
import type { EvaluationAnswer, EvaluationDetail, Resource } from '@/types'

const props = defineProps<{ submission: string }>()

const { brand } = sessionStore()
const router = useRouter()
const user = inject('$user') as { data?: Record<string, boolean> }

onMounted(() => {
	if (
		!user.data?.is_evaluator &&
		!user.data?.is_moderator &&
		!user.data?.is_instructor
	) {
		router.push({ name: 'Courses' })
	}
})

const evaluation = createResource({
	url: 'lms.lms.evaluation.get_evaluation',
	makeParams: () => ({ submission: props.submission }),
	auto: true,
}) as Resource<EvaluationDetail | null>

const draft = ref<EvaluationAnswer[]>([])
const comment = ref('')
const saving = ref<'' | 'draft' | 'final'>('')
const dirty = ref(false)

watch(
	() => evaluation.data,
	(data) => {
		if (!data) return
		// Copied rather than bound: the resource is replaced wholesale by every
		// save, and editing its rows in place would fight that replacement.
		draft.value = data.answers.map((answer) => ({ ...answer }))
		comment.value = data.evaluator_comment ?? ''
		dirty.value = false
	},
	{ immediate: true }
)

watch(
	[draft, comment],
	() => {
		if (evaluation.data) dirty.value = true
	},
	{ deep: true }
)

const isEvaluated = computed(
	() => evaluation.data?.evaluation_status === 'Evaluated'
)

const awardedTotal = computed(() =>
	draft.value.reduce((total, answer) => total + (Number(answer.marks) || 0), 0)
)

const percentage = computed(() => {
	const outOf = evaluation.data?.score_out_of ?? 0
	if (!outOf) return 0
	return Math.round((awardedTotal.value / outOf) * 100)
})

const passes = computed(
	() => percentage.value >= (evaluation.data?.passing_percentage ?? 0)
)

const validationError = computed(() => {
	for (const [index, answer] of draft.value.entries()) {
		const marks = Number(answer.marks)
		if (!Number.isInteger(marks) || marks < 0) {
			return __('Task {0}: marks have to be a whole number, 0 or more.').format(
				index + 1
			)
		}
		if (marks > answer.marks_out_of) {
			return __('Task {0} is out of {1} marks.').format(
				index + 1,
				answer.marks_out_of
			)
		}
	}
	return ''
})

function stripHtml(value: string | null | undefined): string {
	return (value ?? '').replace(/<[^>]*>/g, '').trim()
}

async function submit(finalize: boolean) {
	if (saving.value || validationError.value) return
	saving.value = finalize ? 'final' : 'draft'
	try {
		evaluation.data = (await call('lms.lms.evaluation.save_evaluation', {
			submission: props.submission,
			marks: draft.value.map((answer) => ({
				row: answer.row,
				marks: Number(answer.marks) || 0,
				evaluator_feedback: answer.evaluator_feedback ?? '',
			})),
			comment: comment.value,
			finalize: finalize ? 1 : 0,
		})) as EvaluationDetail
		toast.success(
			finalize ? __('Result released') : __('Marks saved as a draft')
		)
	} catch (error) {
		toast.error(errorMessage(error, __('Could not save the evaluation')))
	} finally {
		saving.value = ''
	}
}

useKeyboardShortcuts({
	ignoreTyping: false,
	shortcuts: [
		{
			...saveShortcut(() => submit(true)),
			guard: (e: KeyboardEvent) =>
				!(e.target as HTMLElement)?.classList?.contains('ProseMirror'),
		},
	],
})

const breadcrumbs = computed(() => [
	{ label: __('Evaluations'), route: { name: 'Evaluations' } },
	{ label: evaluation.data?.member_name || __('Submission') },
])

usePageMeta(() => ({
	title: evaluation.data?.quiz_title || __('Evaluation'),
	icon: brand.favicon,
}))
</script>
