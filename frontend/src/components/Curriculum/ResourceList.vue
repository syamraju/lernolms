<template>
	<section class="space-y-3">
		<h4 class="text-p-base-medium text-ink-gray-9">{{ __('Resources') }}</h4>

		<div v-if="grouped.downloads.length" class="space-y-1">
			<div class="text-p-sm-medium text-ink-gray-7">
				{{ __('Downloadable materials') }}
			</div>
			<ul class="divide-y border-y">
				<li
					v-for="row in grouped.downloads"
					:key="row.name"
					class="flex items-center gap-2 py-2"
				>
					<span class="lucide-file-down size-4 shrink-0 text-ink-gray-5" />
					<a
						:href="safeUrl(row.file ?? '')"
						v-external
						class="min-w-0 flex-1 truncate text-p-base text-ink-gray-9 hover:underline"
					>
						{{ row.title }}
					</a>
					<Button
						variant="ghost"
						theme="red"
						class="!size-8"
						:label="__('Delete {0}').format(row.title)"
						@click="$emit('delete', row)"
					>
						<template #icon>
							<span class="lucide-trash-2 size-4" />
						</template>
					</Button>
				</li>
			</ul>
		</div>

		<div v-if="grouped.links.length" class="space-y-1">
			<div class="text-p-sm-medium text-ink-gray-7">
				{{ __('External resources') }}
			</div>
			<ul class="divide-y border-y">
				<li
					v-for="row in grouped.links"
					:key="row.name"
					class="flex items-center gap-2 py-2"
				>
					<span class="lucide-external-link size-4 shrink-0 text-ink-gray-5" />
					<a
						:href="safeUrl(row.url ?? '')"
						v-external
						class="min-w-0 flex-1 truncate text-p-base text-ink-gray-9 hover:underline"
					>
						{{ row.title }}
					</a>
					<Button
						variant="ghost"
						theme="red"
						class="!size-8"
						:label="__('Delete {0}').format(row.title)"
						@click="$emit('delete', row)"
					>
						<template #icon>
							<span class="lucide-trash-2 size-4" />
						</template>
					</Button>
				</li>
			</ul>
		</div>

		<!-- Add form -->
		<div v-if="adding" class="space-y-3 rounded-md border border-dashed p-3">
			<FormControl
				v-model="draft.resource_type"
				type="select"
				variant="outline"
				:options="RESOURCE_TYPES"
				:label="__('Resource type')"
			/>
			<FormControl
				v-model="draft.title"
				variant="outline"
				:label="__('Title')"
				:placeholder="__('What learners will see')"
			/>
			<FormControl
				v-if="draft.resource_type === 'External Resource'"
				v-model="draft.url"
				variant="outline"
				:label="__('URL')"
				placeholder="https://"
			/>
			<div v-else class="space-y-1.5">
				<InputLabel :id="fileLabelId" :label="__('File')" />
				<FileUploader
					:uploadArgs="{
						private: true,
						doctype: 'Course Lesson',
						docname: lesson,
						fieldname: 'resources',
					}"
					@success="onUploaded"
					@failure="onUploadFailed"
				>
					<template #default="{ uploading, progress, openFileSelector }">
						<div class="flex items-center gap-2">
							<Button
								:loading="uploading"
								:label="
									uploading
										? `${__('Uploading')} ${progress}%`
										: draft.file
										? __('Replace file')
										: __('Choose file')
								"
								@click="openFileSelector"
							/>
							<span v-if="draft.file" class="truncate text-p-sm text-ink-gray-6">
								{{ draft.file_name }}
							</span>
						</div>
					</template>
				</FileUploader>
			</div>
			<div class="flex items-center justify-end gap-2">
				<Button :label="__('Cancel')" @click="cancel" />
				<Button
					variant="solid"
					:disabled="!canSave"
					:loading="saving"
					:label="__('Add resource')"
					@click="submit"
				/>
			</div>
		</div>

		<Button v-else variant="outline" :label="__('Resources')" @click="adding = true">
			<template #prefix>
				<span class="lucide-plus size-4" />
			</template>
		</Button>
	</section>
</template>

<script setup lang="ts">
import { computed, reactive, ref, useId } from 'vue'
import { Button, FileUploader, FormControl, call, toast } from 'frappe-ui'
import { InputLabel } from '@/components/Form/labeling'
import { errorMessage } from '@/utils/courseCreation'
import { safeUrl } from '@/utils/safeUrl'
import type { LessonResourceRow, ResourceType } from '@/types'

const RESOURCE_TYPES: ResourceType[] = [
	'Downloadable File',
	'External Resource',
	'Source Code',
]

const props = defineProps<{
	lesson: string
	resources: LessonResourceRow[]
}>()

const emit = defineEmits<{
	changed: [LessonResourceRow[]]
	delete: [LessonResourceRow]
}>()

const fileLabelId = useId()
const adding = ref(false)
const saving = ref(false)

const draft = reactive({
	resource_type: 'Downloadable File' as ResourceType,
	title: '',
	url: '',
	file: '',
	file_name: '',
})

// Downloads and links are listed apart because they behave differently for a
// learner: one saves to disk, the other leaves the site.
const grouped = computed(() => ({
	downloads: props.resources.filter(
		(row) => row.resource_type !== 'External Resource'
	),
	links: props.resources.filter((row) => row.resource_type === 'External Resource'),
}))

const canSave = computed(() => {
	if (!draft.title.trim()) return false
	return draft.resource_type === 'External Resource'
		? Boolean(draft.url.trim())
		: Boolean(draft.file)
})

function onUploaded(file: { file_url: string; file_name?: string }) {
	draft.file = file.file_url
	draft.file_name = file.file_name ?? file.file_url.split('/').pop() ?? ''
	// Uploading before naming is the common order, so seed the title from the
	// filename rather than leaving the author to retype it.
	if (!draft.title.trim()) draft.title = draft.file_name
}

function onUploadFailed() {
	toast.error(__('The file could not be uploaded.'))
}

function cancel() {
	adding.value = false
	Object.assign(draft, {
		resource_type: 'Downloadable File',
		title: '',
		url: '',
		file: '',
		file_name: '',
	})
}

async function submit() {
	if (!canSave.value || saving.value) return
	saving.value = true
	try {
		const rows = await call('lms.lms.curriculum.add_lesson_resource', {
			lesson: props.lesson,
			resource_type: draft.resource_type,
			title: draft.title.trim(),
			file: draft.resource_type === 'External Resource' ? null : draft.file,
			url: draft.resource_type === 'External Resource' ? draft.url.trim() : null,
		})
		emit('changed', rows as LessonResourceRow[])
		cancel()
	} catch (error) {
		toast.error(errorMessage(error, __('Could not add the resource')))
	} finally {
		saving.value = false
	}
}
</script>
