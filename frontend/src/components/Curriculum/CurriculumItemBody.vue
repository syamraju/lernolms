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
		<QuizBuilder
			v-else-if="item.item_type === 'Quiz' && item.quiz"
			:quizName="item.quiz"
			@changed="$emit('refresh')"
		/>

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
import { ref, useId } from 'vue'
import { Button, FileUploader, FormControl, call, toast } from 'frappe-ui'
import RichTextEditor from '@/components/RichTextEditor.vue'
import { InputLabel } from '@/components/Form/labeling'
import QuizBuilder from './QuizBuilder.vue'
import ResourceList from './ResourceList.vue'
import {
	errorMessage,
	formatVideoLength,
	readVideoDuration,
} from '@/utils/courseCreation'
import { safeUrl } from '@/utils/safeUrl'
import type { CurriculumItem, LessonResourceRow } from '@/types'

const props = defineProps<{ item: CurriculumItem }>()

const emit = defineEmits<{
	update: [{ lesson: string; values: Record<string, unknown> }]
	'edit-content': [CurriculumItem]
	refresh: []
}>()

const descriptionLabelId = useId()
const attaching = ref(false)

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
