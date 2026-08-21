<template>
	<!-- Locked while a batch is in flight. Dismissing mid-run would unmount this
	     component, abort the XHR for the file being sent and abandon everything
	     still queued — with some lectures already created, which is a confusing
	     half-state to leave behind. The Close button says so too. -->
	<Dialog
		v-model="show"
		size="3xl"
		:title="__('Bulk uploader')"
		:dismissible="!running"
		:showCloseButton="!running"
		:disableOutsideClickToClose="running"
	>
		<template #body-content>
			<div class="space-y-5 text-base">
				<p class="text-p-base text-ink-gray-7">
					{{
						__(
							'Upload a batch of videos and get one lecture per file, named after the file. Titles and order can be changed afterwards in the curriculum.'
						)
					}}
				</p>

				<!-- Where the lectures land -->
				<section class="space-y-3">
					<FormControl
						type="select"
						:modelValue="targetChapter"
						:options="sectionOptions"
						variant="outline"
						:label="__('Add lectures to')"
						:disabled="running"
						@update:modelValue="targetChapter = $event"
					/>
					<FormControl
						v-if="targetChapter === NEW_SECTION"
						v-model="newSectionTitle"
						variant="outline"
						:label="__('New section title')"
						:placeholder="__('e.g. Raw footage')"
						:disabled="running"
					/>
					<BooleanSwitch
						size="sm"
						v-model="publishOnUpload"
						:label="__('Publish these lectures immediately')"
						:description="
							__(
								'Off by default — a freshly uploaded video is rarely ready for learners.'
							)
						"
						:disabled="running"
					/>
				</section>

				<!-- Drop zone -->
				<div
					class="rounded-md border-2 border-dashed p-6 text-center transition-colors"
					:class="
						dragging
							? 'border-outline-gray-4 bg-surface-gray-2'
							: 'border-outline-gray-2'
					"
					@dragover.prevent="dragging = true"
					@dragleave.prevent="dragging = false"
					@drop.prevent="onDrop"
				>
					<span
						class="lucide-upload mx-auto mb-2 block size-6 text-ink-gray-4"
					/>
					<p class="text-p-base text-ink-gray-7">
						{{ __('Drop video files here, or') }}
						<button
							type="button"
							class="rounded text-ink-blue-3 underline underline-offset-2 hover:text-ink-blue-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-outline-gray-4"
							:disabled="running"
							@click="fileInput?.click()"
						>
							{{ __('choose them') }}
						</button>
					</p>
					<p class="mt-1 text-p-sm text-ink-gray-5">
						{{ __('MP4, MOV, WebM, MKV or AVI.') }}
					</p>
					<input
						ref="fileInput"
						type="file"
						accept="video/*"
						multiple
						class="hidden"
						:aria-label="__('Choose video files')"
						@change="onPick"
					/>
				</div>

				<p v-if="rejected.length" class="text-p-sm text-ink-amber-3">
					{{
						__('Skipped {0} file(s) that are not video: {1}').format(
							rejected.length,
							rejected.join(', ')
						)
					}}
				</p>

				<!-- Queue -->
				<section v-if="queue.length" class="space-y-2">
					<div class="flex items-center justify-between">
						<h3 class="text-p-base-medium text-ink-gray-9">
							{{ __('{0} file(s)').format(queue.length) }}
						</h3>
						<span class="text-p-sm text-ink-gray-6" aria-live="polite">
							{{ summary }}
						</span>
					</div>
					<ul class="max-h-72 divide-y overflow-y-auto border-y">
						<li
							v-for="entry in queue"
							:key="entry.id"
							class="flex flex-wrap items-center gap-3 py-2"
						>
							<span
								class="size-4 shrink-0"
								:class="statusIcon(entry)"
								aria-hidden="true"
							/>
							<div class="min-w-0 flex-1">
								<div class="truncate text-p-base text-ink-gray-9">
									{{ entry.title }}
								</div>
								<div class="text-p-sm text-ink-gray-5">
									{{ formatSize(entry.file.size) }}
									<template v-if="entry.error">
										· <span class="text-ink-red-3">{{ entry.error }}</span>
									</template>
								</div>
								<div
									v-if="entry.status === 'uploading'"
									class="mt-1 h-1 overflow-hidden rounded bg-surface-gray-3"
								>
									<div
										class="h-full bg-[var(--cds-background-control-checked)] transition-[width]"
										:style="{ width: `${entry.progress}%` }"
									/>
								</div>
							</div>
							<span class="shrink-0 text-p-sm tabular-nums text-ink-gray-6">
								{{ statusLabel(entry) }}
							</span>
							<Button
								v-if="entry.status === 'failed' && !running"
								variant="ghost"
								:label="__('Retry {0}').format(entry.title)"
								@click="retry(entry)"
							>
								{{ __('Retry') }}
							</Button>
							<Button
								v-else-if="entry.status === 'queued' && !running"
								variant="ghost"
								class="!size-8"
								:label="__('Remove {0}').format(entry.title)"
								@click="remove(entry)"
							>
								<template #icon>
									<span class="lucide-x size-4" />
								</template>
							</Button>
						</li>
					</ul>
				</section>
			</div>
		</template>

		<template #actions>
			<div class="flex items-center justify-end gap-2">
				<Button :label="running ? __('Close when finished') : __('Close')" :disabled="running" @click="close" />
				<Button
					variant="solid"
					:disabled="!canStart"
					:loading="running"
					:label="
						running
							? __('Uploading {0} of {1}').format(doneCount + 1, queue.length)
							: __('Upload {0} file(s)').format(pendingCount)
					"
					@click="start"
				/>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
	Button,
	Dialog,
	FileUploadHandler,
	FormControl,
	call,
	toast,
} from 'frappe-ui'
import BooleanSwitch from '@/components/Controls/BooleanSwitch.vue'
import { errorMessage, readVideoDuration } from '@/utils/courseCreation'
import { safeUrl } from '@/utils/safeUrl'
import type { CurriculumSection } from '@/types'

const VIDEO_EXTENSIONS = ['mp4', 'mov', 'webm', 'mkv', 'avi']
const NEW_SECTION = '__new__'

type Status = 'queued' | 'uploading' | 'creating' | 'done' | 'failed'

interface Entry {
	id: string
	file: File
	title: string
	status: Status
	progress: number
	error: string
}

const props = defineProps<{
	courseName: string
	sections: CurriculumSection[]
}>()

const emit = defineEmits<{ uploaded: [] }>()

const show = defineModel<boolean>({ default: false })

const fileInput = ref<HTMLInputElement | null>(null)
const dragging = ref(false)
const running = ref(false)
const queue = ref<Entry[]>([])
const rejected = ref<string[]>([])
const targetChapter = ref('')
const newSectionTitle = ref('')
const publishOnUpload = ref(false)

let seq = 0

const sectionOptions = computed(() => [
	...props.sections.map((s) => ({ label: s.title, value: s.name })),
	{ label: __('New section…'), value: NEW_SECTION },
])

const pendingCount = computed(
	() => queue.value.filter((e) => e.status === 'queued' || e.status === 'failed').length
)
const doneCount = computed(() => queue.value.filter((e) => e.status === 'done').length)
const failedCount = computed(() => queue.value.filter((e) => e.status === 'failed').length)

const summary = computed(() => {
	if (!queue.value.length) return ''
	const parts = [__('{0} done').format(doneCount.value)]
	if (failedCount.value) parts.push(__('{0} failed').format(failedCount.value))
	return parts.join(' · ')
})

const canStart = computed(() => {
	if (running.value || !pendingCount.value) return false
	if (!targetChapter.value) return false
	if (targetChapter.value === NEW_SECTION && !newSectionTitle.value.trim()) return false
	return true
})

// Default the target to the last section, which is where a batch of new
// footage usually belongs, and fall back to creating one when the course has
// no sections yet.
watch(
	show,
	(open) => {
		if (!open) return
		queue.value = []
		rejected.value = []
		newSectionTitle.value = ''
		publishOnUpload.value = false
		targetChapter.value = props.sections.length
			? props.sections[props.sections.length - 1].name
			: NEW_SECTION
	},
	{ immediate: true }
)

function extensionOf(name: string): string {
	return (name.split('.').pop() ?? '').toLowerCase()
}

/** Strip the extension and tidy separators, so "01_intro-clip.mp4" reads as "01 intro clip". */
function titleFromFilename(name: string): string {
	const base = name.replace(/\.[^.]+$/, '')
	return base.replace(/[_-]+/g, ' ').replace(/\s+/g, ' ').trim() || name
}

function addFiles(files: File[]) {
	const accepted: Entry[] = []
	for (const file of files) {
		if (!VIDEO_EXTENSIONS.includes(extensionOf(file.name))) {
			rejected.value.push(file.name)
			continue
		}
		accepted.push({
			id: `f${seq++}`,
			file,
			title: titleFromFilename(file.name),
			status: 'queued',
			progress: 0,
			error: '',
		})
	}
	queue.value = [...queue.value, ...accepted]
}

function onPick(event: Event) {
	const input = event.target as HTMLInputElement
	addFiles([...(input.files ?? [])])
	// Clear so picking the same file again still fires a change event.
	input.value = ''
}

function onDrop(event: DragEvent) {
	dragging.value = false
	addFiles([...(event.dataTransfer?.files ?? [])])
}

function remove(entry: Entry) {
	queue.value = queue.value.filter((e) => e.id !== entry.id)
}

function statusLabel(entry: Entry): string {
	switch (entry.status) {
		case 'uploading':
			return `${entry.progress}%`
		case 'creating':
			return __('Creating…')
		case 'done':
			return __('Added')
		case 'failed':
			return __('Failed')
		default:
			return __('Queued')
	}
}

function statusIcon(entry: Entry): string {
	switch (entry.status) {
		case 'done':
			return 'lucide-circle-check text-ink-green-3'
		case 'failed':
			return 'lucide-circle-alert text-ink-red-3'
		case 'uploading':
		case 'creating':
			return 'lucide-loader-circle animate-spin text-ink-gray-5'
		default:
			return 'lucide-circle-dashed text-ink-gray-4'
	}
}

function formatSize(bytes: number): string {
	if (bytes < 1024) return `${bytes} B`
	if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
	return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

/** Resolve the chapter to add into, creating one first if the author asked for that. */
async function resolveChapter(): Promise<string | null> {
	if (targetChapter.value !== NEW_SECTION) return targetChapter.value
	try {
		const tree = (await call('lms.lms.curriculum.upsert_section', {
			course: props.courseName,
			title: newSectionTitle.value.trim(),
		})) as CurriculumSection[]
		const created = tree[tree.length - 1]
		if (!created) throw new Error('no section returned')
		// Switch the selector onto the real section so a retry after a partial
		// failure adds to it rather than creating a second one.
		targetChapter.value = created.name
		return created.name
	} catch (error) {
		toast.error(errorMessage(error, __('Could not create the section')))
		return null
	}
}

async function uploadOne(entry: Entry, chapter: string) {
	entry.status = 'uploading'
	entry.progress = 0
	entry.error = ''

	const handler = new FileUploadHandler()
	// The payload is { uploaded, total } — not { progress, total }. Reading the
	// wrong key leaves the bar at 0% for the whole upload with no error.
	handler.on('progress', (data: { uploaded: number; total: number }) => {
		entry.progress = data.total
			? Math.round((data.uploaded / data.total) * 100)
			: 0
	})

	// Private and unattached at upload time: the lesson does not exist yet, so
	// there is no docname to attach to. create_lecture_from_upload writes the
	// file into the lesson body immediately afterwards, which is what puts it
	// behind the lesson's own permission check.
	const uploaded = (await handler.upload(entry.file, {
		private: true,
	})) as { file_url: string }

	entry.status = 'creating'
	// Measure from the uploaded URL rather than the local File: same bytes, and
	// it confirms the file is actually readable back before a lecture is built
	// around it.
	const duration = await readVideoDuration(safeUrl(uploaded.file_url))

	await call('lms.lms.curriculum.create_lecture_from_upload', {
		chapter,
		title: entry.title,
		file_url: uploaded.file_url,
		file_type: extensionOf(entry.file.name),
		duration,
		publish: publishOnUpload.value ? 1 : 0,
	})
	entry.status = 'done'
	entry.progress = 100
}

async function start() {
	if (!canStart.value) return
	running.value = true
	const chapter = await resolveChapter()
	if (!chapter) {
		running.value = false
		return
	}

	// Sequential, deliberately. Lectures are appended in queue order, so
	// uploading in parallel would interleave the idx assignments and scramble
	// the order the author chose. It also keeps one huge batch from saturating
	// the connection.
	for (const entry of queue.value) {
		if (entry.status === 'done') continue
		try {
			await uploadOne(entry, chapter)
		} catch (error) {
			entry.status = 'failed'
			entry.error = errorMessage(error, __('Upload failed'))
		}
	}

	running.value = false
	emit('uploaded')

	if (failedCount.value) {
		toast.warning(
			__('{0} added, {1} failed. Retry the failures or remove them.').format(
				doneCount.value,
				failedCount.value
			)
		)
	} else {
		toast.success(
			doneCount.value === 1
				? __('1 lecture added')
				: __('{0} lectures added').format(doneCount.value)
		)
	}
}

async function retry(entry: Entry) {
	entry.status = 'queued'
	entry.error = ''
	await start()
}

function close() {
	if (running.value) return
	show.value = false
}
</script>
