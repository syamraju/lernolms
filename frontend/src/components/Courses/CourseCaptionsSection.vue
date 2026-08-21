<template>
	<section id="captions" class="scroll-mt-4 space-y-6 border-t pt-6">
		<div class="text-base-semibold text-ink-gray-9">
			{{ __('Captions') }}
		</div>
		<div class="flex flex-wrap items-center justify-between gap-3">
			<div class="flex flex-wrap items-center gap-3">
				<FormControl
					type="select"
					:modelValue="doc.captions_language"
					:options="CAPTION_LANGUAGES"
					:label="__('Captions language')"
					variant="outline"
					@update:modelValue="setLanguage"
				/>
				<div class="pt-5 text-p-sm text-ink-gray-6">
					{{
						__('{0}/{1} lectures captioned').format(
							captions.data?.captioned ?? 0,
							captions.data?.total ?? 0
						)
					}}
				</div>
			</div>
			<Button
				class="mt-5"
				:variant="doc.captions_enabled ? 'outline' : 'solid'"
				:label="doc.captions_enabled ? __('Disable') : __('Enable')"
				@click="toggleCaptions"
			/>
		</div>

		<p class="text-p-base text-ink-gray-7">
			{{
				__(
					'Learners at every level of language proficiency value subtitles — they make content easier to follow and to remember, and they are essential for learners who are deaf or hard of hearing.'
				)
			}}
		</p>

		<div
			v-if="doc.captions_enabled"
			class="flex items-start gap-3 rounded-md border border-outline-gray-2 bg-surface-gray-1 p-4"
		>
			<span class="lucide-info mt-0.5 size-5 shrink-0 text-ink-gray-6" />
			<div>
				<div class="text-p-base-medium text-ink-gray-9">
					{{ __('Reach more students with captions') }}
				</div>
				<p class="mt-1 text-p-base text-ink-gray-6">
					{{
						__(
							'Captions are generated automatically once your course is published, and become available within 48 hours. You can review and edit them on this page after they are generated.'
						)
					}}
				</p>
			</div>
		</div>
		<div
			v-else
			class="flex items-start gap-3 rounded-md border border-outline-amber-2 bg-surface-amber-1 p-4"
		>
			<span
				class="lucide-triangle-alert mt-0.5 size-5 shrink-0 text-ink-amber-3"
			/>
			<p class="text-p-base text-ink-gray-8">
				{{
					__(
						'Automatic captions are switched off for this course. Learners who rely on subtitles will not be able to follow your lectures unless you upload caption files yourself.'
					)
				}}
			</p>
		</div>

		<div class="flex gap-2">
			<Button
				:variant="filter === 'all' ? 'subtle' : 'ghost'"
				:label="__('All')"
				@click="filter = 'all'"
			>
				<template v-if="filter === 'all'" #prefix>
					<span class="lucide-check size-4" />
				</template>
			</Button>
			<Button
				:variant="filter === 'uncaptioned' ? 'subtle' : 'ghost'"
				:label="__('Uncaptioned ({0})').format(uncaptionedCount)"
				@click="filter = 'uncaptioned'"
			/>
		</div>

		<SkeletonLoader v-if="captions.loading && !captions.data" variant="form" />

		<div v-else-if="!visibleSections.length" class="rounded-md border border-dashed p-8 text-center">
			<p class="text-p-base text-ink-gray-6">
				{{
					filter === 'uncaptioned'
						? __('Every lecture has captions.')
						: __('Add lectures in the Curriculum step to caption them.')
				}}
			</p>
		</div>

		<div v-else class="space-y-6">
			<section v-for="section in visibleSections" :key="section.name">
				<h3 class="text-p-base-semibold text-ink-gray-9">
					{{ section.title }}
				</h3>
				<ul class="mt-2 divide-y border-t">
					<li
						v-for="(lesson, index) in section.lessons"
						:key="lesson.name"
						class="flex flex-wrap items-center gap-3 py-3"
					>
						<span class="min-w-0 flex-1 truncate text-p-base text-ink-gray-9">
							{{ __('Lecture {0}: {1}').format(index + 1, lesson.title) }}
						</span>
						<span class="text-p-sm text-ink-gray-5">
							{{ __('Uncaptioned') }}
						</span>
						<FileUploader
							:fileTypes="['.vtt', '.srt']"
							:uploadArgs="{
								private: false,
								doctype: 'Course Lesson',
								docname: lesson.name,
								fieldname: 'content',
							}"
							@success="onCaptionUploaded"
							@failure="onCaptionFailed"
						>
							<template #default="{ uploading, progress, openFileSelector }">
								<Button
									variant="outline"
									:loading="uploading"
									:label="
										uploading ? `${__('Uploading')} ${progress}%` : __('Upload')
									"
									@click="openFileSelector"
								/>
							</template>
						</FileUploader>
					</li>
				</ul>
			</section>
		</div>
	</section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Button, FileUploader, FormControl, createResource, toast } from 'frappe-ui'
import SkeletonLoader from '@/components/SkeletonLoader.vue'
import { useCourseManage } from '@/composables/useCourseManage'
import type { Resource } from '@/types'

const CAPTION_LANGUAGES = [
	'English (US)',
	'English (UK)',
	'Spanish',
	'French',
	'German',
	'Portuguese',
	'Hindi',
	'Japanese',
]

interface CaptionLesson {
	name: string
	title: string
}
interface CaptionSection {
	name: string
	title: string
	lessons: CaptionLesson[]
}
interface CaptionStatus {
	enabled: 0 | 1
	language: string
	total: number
	captioned: number
	sections: CaptionSection[]
}

const { doc, markDirty } = useCourseManage()
const filter = ref<'all' | 'uncaptioned'>('all')

const captions = createResource({
	url: 'lms.lms.course_creation.get_caption_status',
	makeParams: () => ({ course: doc.value.name }),
	auto: true,
}) as Resource<CaptionStatus | null>

// Nothing is captioned before publish, so "uncaptioned" is currently every
// lecture. Kept as a derived value rather than hard-coded so the filter keeps
// working unchanged once per-lecture caption state exists.
const uncaptionedCount = computed(
	() => (captions.data?.total ?? 0) - (captions.data?.captioned ?? 0)
)

const visibleSections = computed<CaptionSection[]>(() =>
	(captions.data?.sections ?? []).filter((section) => section.lessons.length)
)

function setLanguage(value: string) {
	doc.value.captions_language = value
	markDirty()
}

function toggleCaptions() {
	doc.value.captions_enabled = doc.value.captions_enabled ? 0 : 1
	markDirty()
}

function onCaptionUploaded() {
	toast.success(__('Caption file uploaded'))
	void captions.reload()
}

function onCaptionFailed() {
	toast.error(__('The caption file could not be uploaded.'))
}
</script>
