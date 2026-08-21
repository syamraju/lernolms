<template>
	<section class="space-y-5">
		<SkeletonLoader v-if="quiz.loading && !quiz.data" variant="form" />

		<template v-else>
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
							{{
								question.answers.length === 1
									? __('1 answer')
									: __('{0} answers').format(question.answers.length)
							}}
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
					__(
						'No questions yet. A quiz needs at least one before it can be published.'
					)
				}}
			</p>

			<!-- Question editor -->
			<div v-if="editing" class="space-y-4 rounded-md border p-4">
				<div class="space-y-1.5">
					<InputLabel :id="questionLabelId" :label="__('Question')" required />
					<RichTextEditor
						:key="editorKey"
						:content="draft.question"
						:editable="true"
						:fixedMenu="true"
						editorClass="prose-sm max-w-none border-b border-x border-outline-gray-2 rounded-b-md py-1 px-2 min-h-[5rem]"
						@change="(value: string) => (draft.question = value)"
					/>
				</div>

				<fieldset class="space-y-3">
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
							@change="setCorrect(index, ($event.target as HTMLInputElement).checked)"
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
						<label class="flex cursor-pointer items-center gap-2 text-p-sm text-ink-gray-7">
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
import { computed, reactive, ref, useId } from 'vue'
import { Button, call, createResource, toast } from 'frappe-ui'
import SkeletonLoader from '@/components/SkeletonLoader.vue'
import RichTextEditor from '@/components/RichTextEditor.vue'
import { InputLabel } from '@/components/Form/labeling'
import { errorMessage } from '@/utils/courseCreation'
import type { QuizAnswer, QuizDetail, QuizQuestion, Resource } from '@/types'

const MAX_ANSWERS = 10

// Held in script rather than inlined: the apostrophe would otherwise have to be
// escaped inside the attribute's own quoting.
const explanationPlaceholder = __("Explain why this is or isn't the best answer.")

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

const draft = reactive<{
	name: string
	question: string
	multiple: boolean
	answers: QuizAnswer[]
}>({ name: '', question: '', multiple: false, answers: [] })

const validationError = computed(() => {
	const filled = draft.answers.filter((answer) => answer.option.trim())
	if (!stripHtml(draft.question)) return __('Write the question.')
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
		// Two blanks up front: the minimum a valid question needs, so the shape
		// of the task is visible before the author starts typing.
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
			answers: draft.answers.filter((answer) => answer.option.trim()),
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
