<template>
	<div class="rounded-md border border-dashed p-3">
		<!-- Step 1: which kind of item -->
		<div v-if="!chosen" class="space-y-3">
			<div class="text-p-base-medium text-ink-gray-9">
				{{ __('What are you adding?') }}
			</div>
			<div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
				<button
					v-for="type in ITEM_TYPES"
					:key="type"
					type="button"
					class="flex items-start gap-3 rounded-md border border-outline-gray-2 p-3 text-start transition-colors hover:border-outline-gray-4 hover:bg-surface-gray-1 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-outline-gray-4"
					@click="choose(type)"
				>
					<span
						class="mt-0.5 size-5 shrink-0 text-ink-gray-6"
						:class="ITEM_TYPE_META[type].icon"
						aria-hidden="true"
					/>
					<span class="min-w-0">
						<span class="block text-p-base-medium text-ink-gray-9">
							{{ __(ITEM_TYPE_META[type].label) }}
						</span>
						<span class="block text-p-sm text-ink-gray-6">
							{{ __(ITEM_TYPE_META[type].description) }}
						</span>
					</span>
				</button>
			</div>
			<Button variant="ghost" :label="__('Cancel')" @click="$emit('cancel')" />
		</div>

		<!-- Step 2: name it -->
		<div v-else class="space-y-3">
			<div class="flex items-center gap-2">
				<span
					class="size-4 shrink-0 text-ink-gray-6"
					:class="ITEM_TYPE_META[chosen].icon"
					aria-hidden="true"
				/>
				<span class="text-p-base-medium text-ink-gray-9">
					{{ __('New {0}').format(__(ITEM_TYPE_META[chosen].label)) }}
				</span>
			</div>

			<!--
				A quiz can be written here or taken from the library. The choice
				comes before the title because it decides what the title means:
				a name for a new quiz, or a label for a placement of an existing
				one.
			-->
			<fieldset v-if="chosen === 'Quiz'" class="space-y-2">
				<legend class="sr-only">{{ __('Where the quiz comes from') }}</legend>
				<div class="flex flex-wrap gap-2">
					<button
						v-for="source in QUIZ_SOURCES"
						:key="source.value"
						type="button"
						class="rounded-md border px-3 py-1.5 text-p-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-outline-gray-4"
						:class="
							quizSource === source.value
								? 'border-outline-gray-4 bg-surface-gray-2 text-ink-gray-9'
								: 'border-outline-gray-2 text-ink-gray-7 hover:bg-surface-gray-1'
						"
						:aria-pressed="quizSource === source.value"
						@click="quizSource = source.value"
					>
						{{ __(source.label) }}
					</button>
				</div>

				<QuizPicker
					v-if="quizSource === 'library'"
					v-model="pickedQuiz"
					:courseName="courseName"
					:autofocus="true"
				/>
			</fieldset>

			<!--
				Asked here rather than in the builder because the two types take
				different questions: an objective one is written around an answer key,
				a subjective one around a prompt. An author who picks the wrong one has
				written the wrong quiz, not a quiz with the wrong setting.
			-->
			<fieldset v-if="chosen === 'Quiz' && !usingLibrary" class="space-y-2">
				<legend class="text-p-sm text-ink-gray-7">
					{{ __('How is it marked?') }}
				</legend>
				<div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
					<button
						v-for="option in QUIZ_TYPES"
						:key="option.value"
						type="button"
						class="rounded-md border p-3 text-start transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-outline-gray-4"
						:class="
							quizType === option.value
								? 'border-outline-gray-4 bg-surface-gray-2'
								: 'border-outline-gray-2 hover:bg-surface-gray-1'
						"
						:aria-pressed="quizType === option.value"
						@click="quizType = option.value"
					>
						<span class="block text-p-base-medium text-ink-gray-9">
							{{ __(option.label) }}
						</span>
						<span class="mt-0.5 block text-p-sm text-ink-gray-6">
							{{ __(option.description) }}
						</span>
					</button>
				</div>
			</fieldset>

			<div v-if="!usingLibrary" class="relative">
				<input
					ref="titleInput"
					v-model="title"
					type="text"
					:maxlength="TITLE_LIMIT"
					:placeholder="__('Enter a title')"
					:aria-label="__('Title')"
					class="w-full rounded-md border border-outline-gray-2 bg-surface-base py-1.5 pe-14 ps-3 text-p-base text-ink-gray-9 transition-colors hover:border-outline-gray-3 focus:border-outline-gray-4 focus:outline-none"
					@keydown.enter.prevent="submit"
					@keydown.esc="$emit('cancel')"
				/>
				<span
					class="pointer-events-none absolute end-3 top-1/2 -translate-y-1/2 text-p-sm tabular-nums text-ink-gray-4"
				>
					{{ TITLE_LIMIT - title.length }}
				</span>
			</div>

			<textarea
				v-if="!usingLibrary && (chosen === 'Quiz' || chosen === 'Assignment')"
				v-model="description"
				rows="2"
				:placeholder="
					__('{0} description (optional)').format(
						__(ITEM_TYPE_META[chosen].label)
					)
				"
				:aria-label="__('Description')"
				class="w-full rounded-md border border-outline-gray-2 bg-surface-base px-3 py-1.5 text-p-base text-ink-gray-9 transition-colors hover:border-outline-gray-3 focus:border-outline-gray-4 focus:outline-none"
			/>

			<div class="flex items-center justify-end gap-2">
				<Button :label="__('Cancel')" @click="$emit('cancel')" />
				<Button
					variant="solid"
					:disabled="!canSubmit"
					:loading="loading"
					:label="__('Add {0}').format(__(ITEM_TYPE_META[chosen].label))"
					@click="submit"
				/>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { Button } from 'frappe-ui'
import QuizPicker from '@/components/Curriculum/QuizPicker.vue'
import { ITEM_TYPES, ITEM_TYPE_META } from '@/utils/curriculum'
import type { CurriculumItemType, QuizType } from '@/types'

const TITLE_LIMIT = 80

type QuizSource = 'new' | 'library'

const QUIZ_SOURCES: { value: QuizSource; label: string }[] = [
	{ value: 'new', label: 'Write a new quiz' },
	{ value: 'library', label: 'Use an existing quiz' },
]

const QUIZ_TYPES: { value: QuizType; label: string; description: string }[] = [
	{
		value: 'Objective',
		label: 'Marked automatically',
		description: 'Multiple choice. Scored the moment a learner submits it.',
	},
	{
		value: 'Subjective',
		label: 'Marked by an evaluator',
		description: 'Written or coded answers, read and scored by a person.',
	},
]

defineProps<{ courseName: string; loading?: boolean }>()

const emit = defineEmits<{
	add: [
		{
			itemType: CurriculumItemType
			title: string
			description: string
			quiz: string | null
			quizType: QuizType
		}
	]
	cancel: []
}>()

const chosen = ref<CurriculumItemType | null>(null)
const title = ref('')
const description = ref('')
const quizSource = ref<QuizSource>('new')
const quizType = ref<QuizType>('Objective')
const pickedQuiz = ref<string | null>(null)
const titleInput = ref<HTMLInputElement | null>(null)

// A library quiz already has a name, a description and questions. Asking the
// author to retype any of that would only create a second name for one quiz.
const usingLibrary = computed(
	() => chosen.value === 'Quiz' && quizSource.value === 'library'
)

const canSubmit = computed(() =>
	usingLibrary.value ? Boolean(pickedQuiz.value) : Boolean(title.value.trim())
)

async function choose(type: CurriculumItemType) {
	chosen.value = type
	quizSource.value = 'new'
	quizType.value = 'Objective'
	pickedQuiz.value = null
	// Picking a type is a commitment to naming one, so put the cursor where the
	// author is about to type instead of making them aim for the field.
	await nextTick()
	titleInput.value?.focus()
}

function submit() {
	if (!chosen.value || !canSubmit.value) return
	emit('add', {
		itemType: chosen.value,
		title: title.value.trim(),
		description: description.value.trim(),
		quiz: usingLibrary.value ? pickedQuiz.value : null,
		quizType: quizType.value,
	})
}
</script>
