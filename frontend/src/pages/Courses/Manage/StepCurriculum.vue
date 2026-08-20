<template>
	<div class="space-y-6">
		<p class="text-p-base text-ink-gray-7">
			{{
				__(
					'Start putting together your course by creating sections and lectures. Use your course outline to structure the content and label everything clearly.'
				)
			}}
		</p>

		<div
			class="flex flex-wrap items-center gap-x-6 gap-y-2 rounded-md border bg-surface-gray-1 px-4 py-3 text-p-sm"
		>
			<span class="text-ink-gray-7">
				<strong class="tabular-nums text-ink-gray-9">{{ lectureCount }}</strong>
				{{ lectureCount === 1 ? __('lecture') : __('lectures') }}
				<span class="text-ink-gray-5">
					{{ __('of {0} required').format(MIN_LECTURES) }}
				</span>
			</span>
			<span class="text-ink-gray-7">
				<strong class="tabular-nums text-ink-gray-9">
					{{ formatVideoLength(status.data?.video_seconds) }}
				</strong>
				{{ __('of video') }}
				<span class="text-ink-gray-5">{{ __('of 30min required') }}</span>
			</span>
			<span
				v-if="status.data?.lectures_without_duration"
				class="text-ink-amber-3"
			>
				{{
					status.data.lectures_without_duration === 1
						? __(
								'1 lecture has a video added outside this page, so its length is not counted.'
						  )
						: __(
								'{0} lectures have videos added outside this page, so their length is not counted.'
						  ).format(status.data.lectures_without_duration)
				}}
			</span>
		</div>

		<SkeletonLoader v-if="curriculum.loading && !curriculum.data" variant="form" />

		<div v-else-if="!sections.length" class="rounded-md border border-dashed p-8 text-center">
			<span class="lucide-layers mx-auto mb-2 block size-6 text-ink-gray-4" />
			<p class="text-p-base text-ink-gray-6">
				{{ __('No sections yet. Add your first one to get started.') }}
			</p>
		</div>

		<Draggable
			v-else
			:model-value="sections"
			item-key="name"
			handle="[data-section-handle]"
			:animation="150"
			class="space-y-4"
			@update:model-value="reorderSections"
		>
			<template #item="{ element: section, index: sectionIndex }">
				<section class="rounded-md border bg-surface-gray-1 p-4">
					<header class="flex items-center gap-2">
						<button
							type="button"
							data-section-handle
							class="cursor-grab rounded p-1 text-ink-gray-4 hover:text-ink-gray-7 active:cursor-grabbing"
							:aria-label="__('Reorder section {0}').format(sectionIndex + 1)"
						>
							<span class="lucide-grip-vertical size-4" />
						</button>
						<span class="text-p-base-semibold text-ink-gray-9">
							{{ __('Section {0}:').format(sectionIndex + 1) }}
						</span>
						<input
							:value="section.title"
							class="min-w-0 flex-1 rounded border border-transparent bg-transparent px-2 py-1 text-p-base text-ink-gray-9 transition-colors hover:border-outline-gray-2 focus:border-outline-gray-4 focus:bg-surface-base focus:outline-none"
							:aria-label="__('Section title')"
							@change="renameSection(section, $event)"
						/>
						<Button
							variant="ghost"
							theme="red"
							class="!size-8"
							:label="__('Delete section')"
							@click="confirmDeleteSection(section)"
						>
							<template #icon>
								<span class="lucide-trash-2 size-4" />
							</template>
						</Button>
					</header>

					<ul class="mt-3 space-y-2">
						<li
							v-for="(lesson, lessonIndex) in section.lessons"
							:key="lesson.name"
							class="flex flex-wrap items-center gap-2 rounded-md border bg-surface-base px-3 py-2"
						>
							<span class="shrink-0 text-p-sm text-ink-gray-5">
								{{ __('Lecture {0}:').format(lessonIndex + 1) }}
							</span>
							<input
								:value="lesson.title"
								class="min-w-0 flex-1 rounded border border-transparent bg-transparent px-1 py-0.5 text-p-base text-ink-gray-9 transition-colors hover:border-outline-gray-2 focus:border-outline-gray-4 focus:outline-none"
								:aria-label="__('Lecture title')"
								@change="renameLecture(lesson, $event)"
							/>
							<span
								class="shrink-0 rounded-sm px-1.5 py-0.5 text-xs tabular-nums"
								:class="
									lesson.video_duration
										? 'bg-surface-green-2 text-ink-green-3'
										: 'bg-surface-gray-2 text-ink-gray-6'
								"
							>
								{{
									lesson.video_duration
										? formatVideoLength(lesson.video_duration)
										: __('No video')
								}}
							</span>
							<FileUploader
								:fileTypes="['video/*']"
								:uploadArgs="{
									private: true,
									doctype: 'Course Lesson',
									docname: lesson.name,
									fieldname: 'content',
								}"
								@success="(file: UploadedFile) => attachVideo(lesson, file)"
								@failure="onUploadFailure"
							>
								<template #default="{ uploading, progress, openFileSelector }">
									<Button
										variant="subtle"
										:loading="uploading || savingLesson === lesson.name"
										:label="
											uploading
												? `${__('Uploading')} ${progress}%`
												: lesson.video_duration
												? __('Replace video')
												: __('Add video')
										"
										@click="openFileSelector"
									/>
								</template>
							</FileUploader>
							<Button
								variant="ghost"
								class="!size-8"
								:label="__('Edit lecture content')"
								@click="editLesson(section, lesson)"
							>
								<template #icon>
									<span class="lucide-pencil size-4" />
								</template>
							</Button>
							<Button
								variant="ghost"
								theme="red"
								class="!size-8"
								:label="__('Delete lecture')"
								@click="confirmDeleteLecture(section, lesson)"
							>
								<template #icon>
									<span class="lucide-trash-2 size-4" />
								</template>
							</Button>
						</li>
					</ul>

					<Button
						class="mt-3"
						variant="outline"
						:loading="addingLectureTo === section.name"
						:label="__('Curriculum item')"
						@click="addLecture(section)"
					>
						<template #prefix>
							<span class="lucide-plus size-4" />
						</template>
					</Button>
				</section>
			</template>
		</Draggable>

		<Button
			variant="outline"
			:loading="addingSection"
			:label="__('Section')"
			@click="addSection"
		>
			<template #prefix>
				<span class="lucide-plus size-4" />
			</template>
		</Button>
	</div>
</template>

<script setup lang="ts">
import { computed, getCurrentInstance, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Button, FileUploader, call, createResource, toast } from 'frappe-ui'
import Draggable from 'vuedraggable'
import SkeletonLoader from '@/components/SkeletonLoader.vue'
import { useCourseManage } from '@/composables/useCourseManage'
import {
	errorMessage,
	formatVideoLength,
	readVideoDuration,
} from '@/utils/courseCreation'
import { safeUrl } from '@/utils/safeUrl'
import type { Resource } from '@/types'

// Mirrors MIN_LECTURES in lms/lms/course_creation.py; used for the counter
// copy only — the server is what actually gates submission.
const MIN_LECTURES = 5

interface CurriculumLesson {
	name: string
	title: string
	video_duration?: number
	include_in_preview?: 0 | 1
}
interface CurriculumSection {
	name: string
	title: string
	idx: number
	lessons: CurriculumLesson[]
}
interface UploadedFile {
	file_url: string
	file_type?: string
	file_name?: string
}

interface DialogAction {
	label: string
	theme?: string
	variant?: string
	onClick: (close: () => void) => void
}
type DialogFn = (opts: {
	title: string
	message: string
	actions: DialogAction[]
}) => void

const router = useRouter()
const { doc, status } = useCourseManage()
const app = getCurrentInstance()!
const { $dialog } = app.appContext.config.globalProperties as {
	$dialog: DialogFn
}

const addingSection = ref(false)
const addingLectureTo = ref('')
const savingLesson = ref('')

const curriculum = createResource({
	url: 'lms.lms.course_creation.get_curriculum',
	makeParams: () => ({ course: doc.value.name }),
	auto: true,
}) as Resource<CurriculumSection[] | null>

const sections = computed<CurriculumSection[]>(() => curriculum.data ?? [])
const lectureCount = computed(() =>
	sections.value.reduce((total, section) => total + section.lessons.length, 0)
)

/** Refetch both the tree and the rail's counters after any structural change. */
async function refresh() {
	await curriculum.reload()
	void status.reload()
}

async function run(action: () => Promise<unknown>, fallback: string) {
	try {
		await action()
		await refresh()
	} catch (error) {
		toast.error(errorMessage(error, fallback))
	}
}

async function addSection() {
	addingSection.value = true
	await run(
		() =>
			call('lms.lms.api.upsert_chapter', {
				title: __('Untitled section'),
				course: doc.value.name,
				is_scorm_package: false,
			}),
		__('Could not add the section')
	)
	addingSection.value = false
}

function renameSection(section: CurriculumSection, event: Event) {
	const title = (event.target as HTMLInputElement).value.trim()
	if (!title || title === section.title) return
	void run(
		() =>
			call('lms.lms.api.upsert_chapter', {
				title,
				course: doc.value.name,
				is_scorm_package: false,
				name: section.name,
			}),
		__('Could not rename the section')
	)
}

function confirmDeleteSection(section: CurriculumSection) {
	$dialog({
		title: __('Delete section'),
		message: __(
			'Deleting "{0}" also deletes its {1} lecture(s) and their content. This cannot be undone.'
		).format(section.title, section.lessons.length),
		actions: [
			{
				label: __('Delete'),
				theme: 'red',
				variant: 'solid',
				onClick(close) {
					void run(
						() => call('lms.lms.api.delete_chapter', { chapter: section.name }),
						__('Could not delete the section')
					)
					close()
				},
			},
		],
	})
}

function reorderSections(next: CurriculumSection[]) {
	// Optimistic: reorder locally so the drag doesn't snap back while the
	// request is in flight, then reconcile with the server's answer.
	curriculum.data = next
	// Sequential, not Promise.all: update_chapter_index rewrites every sibling's
	// idx on each call, so concurrent requests would race on the same rows and
	// leave the order half-applied.
	void run(async () => {
		for (const [index, section] of next.entries()) {
			await call('lms.lms.api.update_chapter_index', {
				chapter: section.name,
				course: doc.value.name,
				idx: index,
			})
		}
	}, __('Could not reorder the sections'))
}

async function addLecture(section: CurriculumSection) {
	addingLectureTo.value = section.name
	await run(
		() => call('lms.lms.api.create_lesson', { chapter: section.name }),
		__('Could not add the lecture')
	)
	addingLectureTo.value = ''
}

function renameLecture(lesson: CurriculumLesson, event: Event) {
	const title = (event.target as HTMLInputElement).value.trim()
	if (!title || title === lesson.title) return
	void run(
		() =>
			call('lms.lms.course_creation.rename_lecture', {
				lesson: lesson.name,
				title,
			}),
		__('Could not rename the lecture')
	)
}

function confirmDeleteLecture(
	section: CurriculumSection,
	lesson: CurriculumLesson
) {
	$dialog({
		title: __('Delete lecture'),
		message: __('Delete "{0}"? This cannot be undone.').format(lesson.title),
		actions: [
			{
				label: __('Delete'),
				theme: 'red',
				variant: 'solid',
				onClick(close) {
					void run(
						() =>
							call('lms.lms.api.delete_lesson', {
								lesson: lesson.name,
								chapter: section.name,
							}),
						__('Could not delete the lecture')
					)
					close()
				},
			},
		],
	})
}

async function attachVideo(lesson: CurriculumLesson, file: UploadedFile) {
	savingLesson.value = lesson.name
	// Read the length from the uploaded file before telling the server about
	// it, so the course's "N min of video" total is right the moment the
	// upload lands rather than after a later playback.
	const duration = await readVideoDuration(safeUrl(file.file_url))
	const fileType =
		file.file_type || file.file_name?.split('.').pop() || 'mp4'
	await run(
		() =>
			call('lms.lms.course_creation.set_lecture_video', {
				lesson: lesson.name,
				file_url: file.file_url,
				file_type: fileType,
				duration,
			}),
		__('Could not attach the video')
	)
	savingLesson.value = ''
	if (!duration) {
		toast.warning(
			__(
				'The video was attached, but its length could not be read, so it will not count towards your total.'
			)
		)
	}
}

function onUploadFailure() {
	toast.error(__('The video could not be uploaded.'))
}

/** Hand off to the existing block editor for the lecture's full content. */
function editLesson(section: CurriculumSection, lesson: CurriculumLesson) {
	const sectionIndex = sections.value.indexOf(section) + 1
	const lessonIndex = section.lessons.indexOf(lesson) + 1
	router.push({
		name: 'CourseDetail',
		params: { courseName: doc.value.name },
		hash: '#editor',
		query: { editLesson: `${sectionIndex}-${lessonIndex}` },
	})
}
</script>
