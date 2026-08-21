<template>
	<section class="space-y-5">
		<SkeletonLoader v-if="quiz.loading && !quiz.data" variant="form" />

		<template v-else>
			<!--
				The type decides what a question even is here, so it is stated before
				the rules rather than buried among them. It is only changeable while
				the quiz is empty: questions do not carry across.
			-->
			<div
				class="flex flex-wrap items-center gap-3 rounded-md border border-outline-gray-2 p-3"
			>
				<span
					class="size-5 shrink-0 text-ink-gray-6"
					:class="isSubjective ? 'lucide-user-pen' : 'lucide-list-checks'"
					aria-hidden="true"
				/>
				<div class="min-w-0 flex-1">
					<p class="text-p-base-medium text-ink-gray-9">
						{{
							isSubjective
								? __('Marked by an evaluator')
								: __('Marked automatically')
						}}
					</p>
					<p class="text-p-sm text-ink-gray-6">
						{{
							isSubjective
								? __(
										'Learners write their own answers. An evaluator assigned to this course reads and scores them.'
								  )
								: __(
										'Multiple choice. Scored against your answer key the moment a learner submits.'
								  )
						}}
					</p>
				</div>
				<Button
					v-if="!hasQuestions"
					variant="outline"
					:loading="switchingType"
					:label="
						isSubjective ? __('Switch to automatic') : __('Switch to evaluator')
					"
					@click="switchType"
				/>
			</div>

			<!--
				The pass mark is the whole point of a section-ending quiz: until a
				learner's best attempt reaches it, the item will not close and the
				next section stays locked. It belongs next to the questions that
				set it, not on a settings page the author has to go looking for.
			-->
			<fieldset class="space-y-3 rounded-md border bg-surface-gray-1 p-4">
				<legend class="sr-only">{{ __('Quiz rules') }}</legend>
				<div class="flex flex-wrap items-end gap-4">
					<FormControl
						type="number"
						min="0"
						max="100"
						class="w-36"
						variant="outline"
						:disabled="!hasQuestions"
						:modelValue="settings.passing_percentage"
						:label="__('Pass mark (%)')"
						@change="onSettingChange('passing_percentage', $event)"
					/>
					<FormControl
						type="number"
						min="0"
						class="w-36"
						variant="outline"
						:modelValue="settings.max_attempts"
						:label="__('Attempts allowed')"
						@change="onSettingChange('max_attempts', $event)"
					/>
					<!--
						A subjective quiz has no answer to reveal — the answer is
						whatever the evaluator decides — so the toggle is replaced by the
						one decision that type does have: whether the lesson waits.
					-->
					<label
						v-if="!isSubjective"
						class="flex cursor-pointer items-center gap-2 pb-2 text-p-sm text-ink-gray-7"
					>
						<input
							type="checkbox"
							class="size-4 rounded border-outline-gray-3 text-ink-gray-9 focus:ring-outline-gray-4"
							:checked="Boolean(settings.show_answers)"
							@change="
								onSettingChange(
									'show_answers',
									($event.target as HTMLInputElement).checked ? 1 : 0
								)
							"
						/>
						{{ __('Show answers after submitting') }}
					</label>
					<label
						v-else
						class="flex cursor-pointer items-center gap-2 pb-2 text-p-sm text-ink-gray-7"
					>
						<input
							type="checkbox"
							class="size-4 rounded border-outline-gray-3 text-ink-gray-9 focus:ring-outline-gray-4"
							:checked="Boolean(settings.block_progress_until_evaluated)"
							@change="
								onSettingChange(
									'block_progress_until_evaluated',
									($event.target as HTMLInputElement).checked ? 1 : 0
								)
							"
						/>
						{{ __('Wait for the mark before moving on') }}
					</label>
					<label
						class="flex cursor-pointer items-center gap-2 pb-2 text-p-sm text-ink-gray-7"
					>
						<input
							type="checkbox"
							class="size-4 rounded border-outline-gray-3 text-ink-gray-9 focus:ring-outline-gray-4"
							:checked="Boolean(settings.shuffle_questions)"
							@change="
								onSettingChange(
									'shuffle_questions',
									($event.target as HTMLInputElement).checked ? 1 : 0
								)
							"
						/>
						{{ __('Shuffle questions') }}
					</label>
				</div>
				<p class="text-p-sm text-ink-gray-6">
					{{ ruleSummary }}
				</p>
			</fieldset>

			<div class="flex flex-wrap items-center justify-between gap-3">
				<h4 class="text-p-base-medium text-ink-gray-9">
					{{ __('Questions') }}
					<span class="text-ink-gray-5">
						({{ quiz.data?.questions.length ?? 0 }})
					</span>
				</h4>
				<Button
					v-if="!editing"
					variant="outline"
					:label="__('Add question')"
					@click="startNew"
				>
					<template #prefix>
						<span class="lucide-plus size-4" />
					</template>
				</Button>
			</div>

			<ol v-if="quiz.data?.questions.length" class="space-y-2">
				<li
					v-for="(question, index) in quiz.data.questions"
					:key="question.name"
					class="rounded-md border px-3 py-2"
				>
					<div class="flex flex-wrap items-center gap-2">
						<span class="shrink-0 text-p-sm text-ink-gray-5">
							{{ __('Q{0}').format(index + 1) }}
						</span>
						<span
							class="min-w-0 flex-1 truncate text-p-base text-ink-gray-9"
							v-safe-html:rich="question.question"
						/>
						<span class="shrink-0 text-p-sm text-ink-gray-5">
							{{ questionSummary(question) }}
						</span>
						<Button
							variant="ghost"
							class="!size-8"
							:label="__('Edit question {0}').format(index + 1)"
							@click="startEdit(question)"
						>
							<template #icon>
								<span class="lucide-pencil size-4" />
							</template>
						</Button>
						<Button
							variant="ghost"
							theme="red"
							class="!size-8"
							:loading="deleting === question.name"
							:label="__('Delete question {0}').format(index + 1)"
							@click="remove(question)"
						>
							<template #icon>
								<span class="lucide-trash-2 size-4" />
							</template>
						</Button>
					</div>
				</li>
			</ol>

			<p v-else-if="!editing" class="text-p-base text-ink-gray-6">
				{{
					isSubjective
						? __(
								'No tasks yet. A quiz needs at least one before it can be published.'
						  )
						: __(
								'No questions yet. A quiz needs at least one before it can be published.'
						  )
				}}
			</p>

			<!-- Question editor -->
			<div v-if="editing" class="space-y-4 rounded-md border p-4">
				<div class="space-y-1.5">
					<InputLabel
						:id="questionLabelId"
						:label="isSubjective ? __('Task') : __('Question')"
						required
					/>
					<RichTextEditor
						:key="editorKey"
						:content="draft.question"
						:editable="true"
						:fixedMenu="true"
						editorClass="prose-sm max-w-none border-b border-x border-outline-gray-2 rounded-b-md py-1 px-2 min-h-[5rem]"
						@change="(value: string) => (draft.question = value)"
					/>
				</div>

				<!--
					A subjective question has no answer to write down — the learner
					supplies that, and an evaluator judges it. All that is left to
					decide is what it is worth.
				-->
				<div v-if="isSubjective" class="space-y-1.5">
					<FormControl
						type="number"
						min="1"
						:max="MAX_QUESTION_MARKS"
						class="w-36"
						variant="outline"
						v-model="draft.marks"
						:label="__('Marks')"
					/>
					<p class="text-p-sm text-ink-gray-6">
						{{
							__(
								'The evaluator awards up to this many marks for the answer they read.'
							)
						}}
					</p>
				</div>

				<fieldset v-else class="space-y-3">
					<legend class="text-p-base-medium text-ink-gray-9">
						{{ __('Answers') }}
					</legend>
					<p class="text-p-sm text-ink-gray-6">
						{{
							__(
								'Mark the correct answer. An explanation is shown to learners after they answer.'
							)
						}}
					</p>

					<div
						v-for="(answer, index) in draft.answers"
						:key="index"
						class="flex items-start gap-3"
					>
						<input
							:type="draft.multiple ? 'checkbox' : 'radio'"
							class="mt-2.5 size-4 shrink-0 border-outline-gray-3 text-ink-gray-9 focus:ring-outline-gray-4"
							:name="`correct-${editorKey}`"
							:checked="Boolean(answer.is_correct)"
							:aria-label="__('Answer {0} is correct').format(index + 1)"
							@change="
								setCorrect(index, ($event.target as HTMLInputElement).checked)
							"
						/>
						<div class="min-w-0 flex-1 space-y-1.5">
							<input
								v-model="answer.option"
								type="text"
								:placeholder="__('Add an answer.')"
								:aria-label="__('Answer {0}').format(index + 1)"
								class="w-full rounded-md border border-outline-gray-2 bg-surface-base px-3 py-1.5 text-p-base text-ink-gray-9 transition-colors hover:border-outline-gray-3 focus:border-outline-gray-4 focus:outline-none"
							/>
							<input
								v-model="answer.explanation"
								type="text"
								:maxlength="600"
								:placeholder="explanationPlaceholder"
								:aria-label="__('Explanation for answer {0}').format(index + 1)"
								class="w-full rounded-md border border-outline-gray-2 bg-surface-base px-3 py-1.5 text-p-sm text-ink-gray-8 transition-colors hover:border-outline-gray-3 focus:border-outline-gray-4 focus:outline-none"
							/>
						</div>
						<Button
							variant="ghost"
							theme="red"
							class="!mt-0.5 !size-8 shrink-0"
							:disabled="draft.answers.length <= 2"
							:label="__('Delete answer {0}').format(index + 1)"
							@click="draft.answers.splice(index, 1)"
						>
							<template #icon>
								<span class="lucide-trash-2 size-4" />
							</template>
						</Button>
					</div>

					<div class="flex flex-wrap items-center gap-3">
						<Button
							variant="ghost"
							class="!-ms-2"
							:disabled="draft.answers.length >= MAX_ANSWERS"
							:label="__('Add an answer')"
							@click="addAnswer"
						>
							<template #prefix>
								<span class="lucide-plus size-4" />
							</template>
						</Button>
						<label
							class="flex cursor-pointer items-center gap-2 text-p-sm text-ink-gray-7"
						>
							<input
								v-model="draft.multiple"
								type="checkbox"
								class="size-4 rounded border-outline-gray-3 text-ink-gray-9 focus:ring-outline-gray-4"
								@change="onMultipleChanged"
							/>
							{{ __('More than one answer can be correct') }}
						</label>
					</div>
				</fieldset>

				<p v-if="validationError" class="text-p-sm text-ink-red-3" role="alert">
					{{ validationError }}
				</p>

				<div class="flex items-center justify-end gap-2">
					<Button :label="__('Cancel')" @click="editing = false" />
					<Button
						variant="solid"
						:disabled="Boolean(validationError)"
						:loading="saving"
						:label="draft.name ? __('Save question') : __('Add question')"
						@click="save"
					/>
				</div>
			</div>
		</template>
	</section>
</template>

<script setup lang="ts">
import { computed, reactive, ref, useId, watch } from 'vue'
import { Button, FormControl, call, createResource, toast } from 'frappe-ui'
import SkeletonLoader from '@/components/SkeletonLoader.vue'
import RichTextEditor from '@/components/RichTextEditor.vue'
import { InputLabel } from '@/components/Form/labeling'
import { errorMessage } from '@/utils/courseCreation'
import type { QuizAnswer, QuizDetail, QuizQuestion, Resource } from '@/types'

const MAX_ANSWERS = 10
// Mirrors MAX_QUESTION_MARKS in lms/lms/curriculum.py.
const MAX_QUESTION_MARKS = 100

// Held in script rather than inlined: the apostrophe would otherwise have to be
// escaped inside the attribute's own quoting.
const explanationPlaceholder = __(
	"Explain why this is or isn't the best answer."
)

const props = defineProps<{ quizName: string }>()
const emit = defineEmits<{ changed: [] }>()

const questionLabelId = useId()
const editing = ref(false)
const saving = ref(false)
const deleting = ref('')
// Bumped on every open so the rich-text editor remounts with the new content
// instead of keeping the previous question's body.
const editorKey = ref(0)

const quiz = createResource({
	url: 'lms.lms.curriculum.get_quiz',
	makeParams: () => ({ quiz: props.quizName }),
	auto: true,
}) as Resource<QuizDetail | null>

// Mirrored locally so a field the author is editing does not snap back while
// the write is in flight; the server's answer replaces it when it lands.
const settings = reactive({
	passing_percentage: 0,
	max_attempts: 0,
	show_answers: 0 as 0 | 1,
	shuffle_questions: 0 as 0 | 1,
	block_progress_until_evaluated: 0 as 0 | 1,
})

watch(
	() => quiz.data,
	(data) => {
		if (!data) return
		settings.passing_percentage = data.passing_percentage ?? 0
		settings.max_attempts = data.max_attempts ?? 0
		settings.show_answers = data.show_answers ? 1 : 0
		settings.shuffle_questions = data.shuffle_questions ? 1 : 0
		settings.block_progress_until_evaluated =
			data.block_progress_until_evaluated ? 1 : 0
	},
	{ immediate: true }
)

const hasQuestions = computed(() => Boolean(quiz.data?.questions.length))
const isSubjective = computed(() => quiz.data?.quiz_type === 'Subjective')

function questionSummary(question: QuizQuestion): string {
	if (isSubjective.value) {
		return question.marks === 1
			? __('1 mark')
			: __('{0} marks').format(question.marks)
	}
	return question.answers.length === 1
		? __('1 answer')
		: __('{0} answers').format(question.answers.length)
}

const switchingType = ref(false)

/**
 * Flip the quiz between the two types.
 *
 * Only offered while the quiz is empty — the server refuses the switch once
 * questions exist, because an objective question's answer key has no meaning on
 * a subjective quiz and a subjective prompt has no key to give an objective one.
 */
async function switchType() {
	if (switchingType.value) return
	switchingType.value = true
	try {
		quiz.data = (await call('lms.lms.curriculum.update_quiz_settings', {
			quiz: props.quizName,
			quiz_type: isSubjective.value ? 'Objective' : 'Subjective',
		})) as QuizDetail
		emit('changed')
	} catch (error) {
		toast.error(errorMessage(error, __('Could not change the quiz type')))
	} finally {
		switchingType.value = false
	}
}

/**
 * The sentence under the rules.
 *
 * An empty quiz is called out rather than showing its pass mark: LMS Quiz pins
 * `passing_percentage` to 100 while there are no questions, so any number typed
 * here would come straight back as 100 and read as the field being broken.
 */
const ruleSummary = computed(() => {
	if (!hasQuestions.value) {
		return __(
			'Add a question before setting the pass mark — an empty quiz cannot be passed.'
		)
	}
	if (isSubjective.value && !settings.block_progress_until_evaluated) {
		return __(
			'Handing the work in completes this item; the mark arrives later and never takes it back.'
		)
	}
	const bar =
		settings.passing_percentage > 0
			? __(
					'Learners must score at least {0}% before this item counts as complete and the course moves on.'
			  ).format(settings.passing_percentage)
			: __(
					'With a pass mark of 0, submitting the quiz is enough — it will not hold anyone back.'
			  )
	if (isSubjective.value) {
		return __('{0} The lesson stays open until an evaluator marks it.').format(
			bar
		)
	}
	const attempts =
		settings.max_attempts > 0
			? __('They get {0} attempt(s).').format(settings.max_attempts)
			: __('Attempts are unlimited.')
	return `${bar} ${attempts}`
})

async function onSettingChange(field: keyof typeof settings, value: unknown) {
	const raw =
		value instanceof Event ? (value.target as HTMLInputElement).value : value
	let next = Number(raw) || 0
	// Clamp here as well as on the server: a number input still accepts a typed
	// 500, and sending it only to be refused loses the author's other edits.
	if (field === 'passing_percentage') next = Math.min(Math.max(next, 0), 100)
	if (field === 'max_attempts') next = Math.max(next, 0)
	if (settings[field] === next) return

	const previous = settings[field]
	settings[field] = next as never
	try {
		quiz.data = (await call('lms.lms.curriculum.update_quiz_settings', {
			quiz: props.quizName,
			[field]: next,
		})) as QuizDetail
		emit('changed')
	} catch (error) {
		settings[field] = previous as never
		toast.error(errorMessage(error, __('Could not save the quiz settings')))
	}
}

const draft = reactive<{
	name: string
	question: string
	multiple: boolean
	marks: number
	answers: QuizAnswer[]
}>({ name: '', question: '', multiple: false, marks: 1, answers: [] })

const validationError = computed(() => {
	if (!stripHtml(draft.question)) {
		return isSubjective.value
			? __('Write the task.')
			: __('Write the question.')
	}
	if (isSubjective.value) {
		const marks = Number(draft.marks)
		if (!Number.isInteger(marks) || marks < 1 || marks > MAX_QUESTION_MARKS) {
			return __('Marks have to be between 1 and {0}.').format(
				MAX_QUESTION_MARKS
			)
		}
		return ''
	}
	const filled = draft.answers.filter((answer) => answer.option.trim())
	if (filled.length < 2) return __('A question needs at least two answers.')
	if (!filled.some((answer) => answer.is_correct)) {
		return __('Mark at least one answer as correct.')
	}
	return ''
})

function stripHtml(value: string): string {
	return value.replace(/<[^>]*>/g, '').trim()
}

function blankAnswer(): QuizAnswer {
	return { option: '', is_correct: 0, explanation: '' }
}

function startNew() {
	Object.assign(draft, {
		name: '',
		question: '',
		multiple: false,
		marks: 1,
		// Two blanks up front: the minimum a valid question needs, so the shape
		// of the task is visible before the author starts typing. A subjective
		// quiz never reads these.
		answers: [blankAnswer(), blankAnswer()],
	})
	editorKey.value += 1
	editing.value = true
}

function startEdit(question: QuizQuestion) {
	Object.assign(draft, {
		name: question.name,
		question: question.question,
		multiple: Boolean(question.multiple),
		marks: question.marks ?? 1,
		answers: question.answers.map((answer) => ({
			option: answer.option,
			is_correct: answer.is_correct ? 1 : 0,
			explanation: answer.explanation ?? '',
		})),
	})
	editorKey.value += 1
	editing.value = true
}

function addAnswer() {
	if (draft.answers.length >= MAX_ANSWERS) return
	draft.answers.push(blankAnswer())
}

function setCorrect(index: number, checked: boolean) {
	if (draft.multiple) {
		draft.answers[index].is_correct = checked ? 1 : 0
		return
	}
	// Single-answer mode: selecting one clears the rest, so the data can never
	// disagree with what the radio group shows.
	draft.answers.forEach((answer, i) => {
		answer.is_correct = i === index && checked ? 1 : 0
	})
}

function onMultipleChanged() {
	if (draft.multiple) return
	// Switching back to single-answer: keep the first correct one and drop the
	// others, rather than leaving a radio group with several filled dots.
	let seen = false
	for (const answer of draft.answers) {
		if (answer.is_correct && !seen) {
			seen = true
			continue
		}
		answer.is_correct = 0
	}
}

async function save() {
	if (validationError.value || saving.value) return
	saving.value = true
	try {
		quiz.data = (await call('lms.lms.curriculum.save_quiz_question', {
			quiz: props.quizName,
			name: draft.name || null,
			question: draft.question,
			multiple: draft.multiple ? 1 : 0,
			marks: isSubjective.value ? Number(draft.marks) || 1 : 1,
			// A subjective quiz has no answer key; the server clears any the
			// question carried from a previous life as an objective one.
			answers: isSubjective.value
				? []
				: draft.answers.filter((answer) => answer.option.trim()),
		})) as QuizDetail
		editing.value = false
		emit('changed')
	} catch (error) {
		toast.error(errorMessage(error, __('Could not save the question')))
	} finally {
		saving.value = false
	}
}

async function remove(question: QuizQuestion) {
	deleting.value = question.name
	try {
		quiz.data = (await call('lms.lms.curriculum.delete_quiz_question', {
			quiz: props.quizName,
			name: question.name,
		})) as QuizDetail
		emit('changed')
	} catch (error) {
		toast.error(errorMessage(error, __('Could not delete the question')))
	} finally {
		deleting.value = ''
	}
}
</script>
