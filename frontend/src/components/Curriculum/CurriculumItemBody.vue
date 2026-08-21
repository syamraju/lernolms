<template>
	<div class="space-y-6">
		<!-- Description: every item type has one -->
		<div class="space-y-1.5">
			<InputLabel :id="descriptionLabelId" :label="__('Description')" />
			<RichTextEditor
				:key="item.name"
				:content="item.description ?? ''"
				:editable="true"
				:fixedMenu="true"
				editorClass="prose-sm max-w-none border-b border-x border-outline-gray-2 rounded-b-md py-1 px-2 min-h-[5rem]"
				@change="onDescriptionChange"
			/>
			<p class="text-p-sm text-ink-gray-5">
				{{ __('Shown under the title before learners open the item.') }}
			</p>
		</div>

		<!-- Lecture: the video itself -->
		<section v-if="item.item_type === 'Lecture'" class="space-y-3">
			<h4 class="text-p-base-medium text-ink-gray-9">{{ __('Content') }}</h4>
			<div class="flex flex-wrap items-center gap-3">
				<span
					class="rounded-sm px-2 py-1 text-p-sm"
					:class="
						item.has_video
							? 'bg-surface-green-2 text-ink-green-3'
							: 'bg-surface-gray-2 text-ink-gray-6'
					"
				>
					{{
						item.video_duration
							? __('Video · {0}').format(formatVideoLength(item.video_duration))
							: item.has_video
							? __('Video attached')
							: __('No video yet')
					}}
				</span>
				<FileUploader
					:fileTypes="['video/*']"
					:uploadArgs="{
						private: true,
						doctype: 'Course Lesson',
						docname: item.name,
						fieldname: 'content',
					}"
					@success="onVideoUploaded"
					@failure="onVideoFailed"
				>
					<template #default="{ uploading, progress, openFileSelector }">
						<Button
							variant="subtle"
							:loading="uploading || attaching"
							:label="
								uploading
									? `${__('Uploading')} ${progress}%`
									: item.has_video
									? __('Replace video')
									: __('Add video')
							"
							@click="openFileSelector"
						/>
					</template>
				</FileUploader>
				<Button
					variant="outline"
					:label="__('Open in lesson editor')"
					@click="$emit('edit-content', item)"
				>
					<template #prefix>
						<span class="lucide-pencil size-4" />
					</template>
				</Button>
			</div>
			<p class="text-p-sm text-ink-gray-5">
				{{
					__(
						'The lesson editor is where you write articles, embed slides and add quizzes inside the video.'
					)
				}}
			</p>
		</section>

		<!-- Quiz -->
		<section v-else-if="item.item_type === 'Quiz'" class="space-y-4">
			<div class="flex flex-wrap items-center justify-between gap-3">
				<div class="min-w-0">
					<h4 class="text-p-base-medium text-ink-gray-9">
						{{ isSharedQuiz ? __('Linked quiz') : __('Quiz') }}
					</h4>
					<p class="text-p-sm text-ink-gray-6">
						{{
							isSharedQuiz
								? __(
										'This quiz comes from your library and may be used by other courses, so it is edited in the Quizzes section.'
								  )
								: __('Written here and used only by this course.')
						}}
					</p>
				</div>
				<Button
					variant="outline"
					:label="
						isSharedQuiz ? __('Replace quiz') : __('Use an existing quiz')
					"
					@click="openPicker"
				>
					<template #prefix>
						<span class="lucide-library size-4" />
					</template>
				</Button>
			</div>

			<!-- A shared quiz is described, not edited: its questions belong to
			     every course using it, so changing them here would be an edit the
			     author cannot see the reach of. -->
			<div
				v-if="isSharedQuiz"
				class="flex flex-wrap items-center justify-between gap-3 rounded-md border bg-surface-gray-1 px-4 py-3"
			>
				<div class="min-w-0">
					<p class="truncate text-p-base-medium text-ink-gray-9">
						{{ item.quiz_summary?.title || item.quiz }}
					</p>
					<p class="text-p-sm text-ink-gray-6">{{ sharedQuizSummary }}</p>
				</div>
				<div class="flex items-center gap-2">
					<Button
						variant="subtle"
						:label="__('Edit in Quizzes')"
						@click="openQuizEditor"
					/>
					<Button
						variant="ghost"
						:label="__('Write a new quiz instead')"
						@click="detachQuiz"
					/>
				</div>
			</div>

			<QuizBuilder
				v-else-if="item.quiz"
				:quizName="item.quiz"
				@changed="$emit('refresh')"
			/>
		</section>

		<!-- Assignment / Coding Exercise: their own full-page editors -->
		<section v-else class="space-y-3">
			<h4 class="text-p-base-medium text-ink-gray-9">
				{{ __(item.item_type) }}
			</h4>
			<p class="text-p-base text-ink-gray-6">
				{{
					item.item_type === 'Assignment'
						? __(
								'Instructions, questions and the model solution are written on the assignment page.'
						  )
						: __(
								'The problem statement, starter code, solution and test cases are written on the exercise page.'
						  )
				}}
			</p>
			<div class="flex flex-wrap items-center gap-3">
				<Button
					variant="solid"
					:label="
						item.item_type === 'Assignment'
							? __('Edit assignment')
							: __('Edit coding exercise')
					"
					@click="$emit('edit-content', item)"
				/>
				<FormControl
					type="number"
					min="0"
					class="w-40"
					variant="outline"
					:modelValue="item.duration_minutes ?? 0"
					:label="__('Estimated duration (min)')"
					@change="onDurationChange"
				/>
			</div>
		</section>

		<Dialog
			v-model="showPicker"
			:options="{
				title: __('Use an existing quiz'),
				actions: [
					{
						label: __('Use this quiz'),
						variant: 'solid',
						disabled: !picked,
						onClick: applyPickedQuiz,
					},
				],
			}"
		>
			<template #body-content>
				<p class="mb-3 text-p-sm text-ink-gray-6">
					{{
						__(
							'The quiz stays in your library. Editing it later updates every course that uses it.'
						)
					}}
				</p>
				<QuizPicker
					v-model="picked"
					:courseName="courseName"
					:excludeQuiz="item.quiz"
					:autofocus="true"
				/>
			</template>
		</Dialog>

		<div class="border-t pt-5">
			<ResourceList
				:lesson="item.name"
				:resources="item.resources"
				@changed="$emit('refresh')"
				@delete="onDeleteResource"
			/>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, ref, useId } from 'vue'
import { useRouter } from 'vue-router'
import {
	Button,
	Dialog,
	FileUploader,
	FormControl,
	call,
	toast,
} from 'frappe-ui'
import RichTextEditor from '@/components/RichTextEditor.vue'
import { InputLabel } from '@/components/Form/labeling'
import QuizBuilder from './QuizBuilder.vue'
import QuizPicker from './QuizPicker.vue'
import ResourceList from './ResourceList.vue'
import {
	errorMessage,
	formatVideoLength,
	readVideoDuration,
} from '@/utils/courseCreation'
import { openExternal } from '@/utils/openExternal'
import { safeUrl } from '@/utils/safeUrl'
import type { CurriculumItem, LessonResourceRow } from '@/types'

const props = defineProps<{ item: CurriculumItem; courseName: string }>()

const emit = defineEmits<{
	update: [{ lesson: string; values: Record<string, unknown> }]
	'set-quiz': [{ lesson: string; quiz: string | null }]
	'edit-content': [CurriculumItem]
	refresh: []
}>()

const router = useRouter()
const descriptionLabelId = useId()
const attaching = ref(false)
const showPicker = ref(false)
const picked = ref<string | null>(null)

const isSharedQuiz = computed(
	() =>
		props.item.item_type === 'Quiz' && Boolean(props.item.is_shared_activity)
)

/** The one line describing a shared quiz: its size and the bar it sets. */
const sharedQuizSummary = computed(() => {
	const summary = props.item.quiz_summary
	if (!summary) return __('This quiz is no longer in your library.')
	const count =
		summary.question_count === 1
			? __('1 question')
			: __('{0} questions').format(summary.question_count)
	return `${count} · ${__('{0}% to pass').format(
		summary.passing_percentage ?? 0
	)}`
})

function openPicker() {
	picked.value = null
	showPicker.value = true
}

function applyPickedQuiz(options?: { close?: () => void }) {
	if (!picked.value) return
	emit('set-quiz', { lesson: props.item.name, quiz: picked.value })
	showPicker.value = false
	options?.close?.()
}

/**
 * Swap a library quiz back for one this item owns.
 *
 * The library quiz is left where it is — this only stops the item pointing at
 * it — so the author gets an empty quiz to write in without losing the shared
 * one they were using.
 */
function detachQuiz() {
	emit('set-quiz', { lesson: props.item.name, quiz: null })
}

/**
 * Open the shared quiz in the Quizzes section, in a new tab.
 *
 * A new tab rather than a navigation: the author is mid-way through building a
 * curriculum, and sending them away from a page of unsaved expansion state to
 * change a pass mark loses their place in the outline.
 */
function openQuizEditor() {
	if (!props.item.quiz) return
	const target = router.resolve({
		name: 'QuizForm',
		params: { quizID: props.item.quiz },
	})
	openExternal(target.href)
}

// Debounced so a burst of typing in the rich-text editor collapses into one
// write rather than a request per keystroke.
let descriptionTimer: ReturnType<typeof setTimeout> | undefined
function onDescriptionChange(value: string) {
	clearTimeout(descriptionTimer)
	descriptionTimer = setTimeout(() => {
		emit('update', { lesson: props.item.name, values: { description: value } })
	}, 900)
}

function onDurationChange(event: Event) {
	const value = Number((event.target as HTMLInputElement).value) || 0
	emit('update', {
		lesson: props.item.name,
		values: { duration_minutes: Math.max(value, 0) },
	})
}

async function onVideoUploaded(file: {
	file_url: string
	file_type?: string
	file_name?: string
}) {
	attaching.value = true
	// Measure before telling the server, so the course's total video time is
	// correct the moment the upload lands rather than after a later playback.
	const duration = await readVideoDuration(safeUrl(file.file_url))
	try {
		await call('lms.lms.course_creation.set_lecture_video', {
			lesson: props.item.name,
			file_url: file.file_url,
			file_type: file.file_type || file.file_name?.split('.').pop() || 'mp4',
			duration,
		})
		emit('refresh')
		if (!duration) {
			toast.warning(
				__(
					'The video was attached, but its length could not be read, so it will not count towards your total.'
				)
			)
		}
	} catch (error) {
		toast.error(errorMessage(error, __('Could not attach the video')))
	} finally {
		attaching.value = false
	}
}

function onVideoFailed() {
	toast.error(__('The video could not be uploaded.'))
}

async function onDeleteResource(row: LessonResourceRow) {
	try {
		await call('lms.lms.curriculum.delete_lesson_resource', {
			lesson: props.item.name,
			row: row.name,
		})
		emit('refresh')
	} catch (error) {
		toast.error(errorMessage(error, __('Could not delete the resource')))
	}
}
</script>
