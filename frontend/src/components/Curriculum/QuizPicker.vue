<!--
	Pick a quiz that already exists instead of writing a new one.

	The Quizzes section is where a teacher builds their question bank, and until
	now the curriculum builder could not reach it: adding a quiz item always
	minted an empty quiz, so a quiz reused across three courses had to be typed
	three times. This lists what the author may place — their own standalone
	quizzes first, then quizzes already sitting in a course they can edit.
-->
<template>
	<div class="space-y-3">
		<div class="relative">
			<input
				ref="searchInput"
				v-model="search"
				type="text"
				:placeholder="__('Search quizzes')"
				:aria-label="__('Search quizzes')"
				class="w-full rounded-md border border-outline-gray-2 bg-surface-base py-1.5 pe-3 ps-9 text-p-base text-ink-gray-9 transition-colors hover:border-outline-gray-3 focus:border-outline-gray-4 focus:outline-none"
			/>
			<span
				class="lucide-search pointer-events-none absolute start-3 top-1/2 size-4 -translate-y-1/2 text-ink-gray-5"
				aria-hidden="true"
			/>
		</div>

		<SkeletonLoader v-if="library.loading && !library.data" variant="list" />

		<p v-else-if="!options.length" class="text-p-sm text-ink-gray-6">
			{{
				search
					? __('No quiz matches "{0}".').format(search)
					: __(
							'You have no quizzes yet. Create one here, or build a question bank in the Quizzes section first.'
					  )
			}}
		</p>

		<ul v-else class="max-h-72 space-y-1 overflow-y-auto" role="listbox">
			<li v-for="quiz in options" :key="quiz.name">
				<button
					type="button"
					role="option"
					:aria-selected="quiz.name === modelValue"
					class="flex w-full items-start gap-3 rounded-md border p-3 text-start transition-colors hover:bg-surface-gray-1 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-outline-gray-4"
					:class="
						quiz.name === modelValue
							? 'border-outline-gray-4 bg-surface-gray-1'
							: 'border-outline-gray-2'
					"
					@click="$emit('update:modelValue', quiz.name)"
				>
					<span
						class="lucide-circle-help mt-0.5 size-4 shrink-0 text-ink-gray-6"
						aria-hidden="true"
					/>
					<span class="min-w-0 flex-1">
						<span class="block truncate text-p-base-medium text-ink-gray-9">
							{{ quiz.title || quiz.name }}
						</span>
						<span class="block text-p-sm text-ink-gray-6">
							{{ describe(quiz) }}
						</span>
					</span>
					<span
						v-if="quiz.name === modelValue"
						class="lucide-check mt-0.5 size-4 shrink-0 text-ink-gray-8"
						aria-hidden="true"
					/>
				</button>
			</li>
		</ul>
	</div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useDebounceFn } from '@vueuse/core'
import { createResource } from 'frappe-ui'
import SkeletonLoader from '@/components/SkeletonLoader.vue'
import type { QuizSummary, Resource } from '@/types'

const props = defineProps<{
	/** The quiz currently chosen, if any. */
	modelValue?: string | null
	/** Scopes the listing to what this course's author may place. */
	courseName: string
	/** Kept out of the list — the item already uses it. */
	excludeQuiz?: string | null
	autofocus?: boolean
}>()

defineEmits<{ 'update:modelValue': [string] }>()

const search = ref('')
const searchInput = ref<HTMLInputElement | null>(null)

const library = createResource({
	url: 'lms.lms.curriculum.list_quiz_library',
	makeParams: () => ({ course: props.courseName, search: search.value }),
	auto: true,
}) as Resource<QuizSummary[] | null>

// Debounced: the picker opens on a keystroke and the author keeps typing, so
// firing a listing per character would race its own results into the list.
const reload = useDebounceFn(() => void library.reload(), 300)
watch(search, reload)

const options = computed<QuizSummary[]>(() =>
	(library.data ?? []).filter((quiz) => quiz.name !== props.excludeQuiz)
)

/** The one line under a quiz's title: its size, its bar, and where it lives. */
function describe(quiz: QuizSummary): string {
	const parts = [
		quiz.question_count === 1
			? __('1 question')
			: __('{0} questions').format(quiz.question_count),
		__('{0}% to pass').format(quiz.passing_percentage ?? 0),
	]
	parts.push(
		quiz.course_title
			? __('Used in {0}').format(quiz.course_title)
			: __('Quiz library')
	)
	return parts.join(' · ')
}

onMounted(async () => {
	if (!props.autofocus) return
	await nextTick()
	searchInput.value?.focus()
})
</script>
