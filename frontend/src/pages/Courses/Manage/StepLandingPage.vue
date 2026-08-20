<template>
	<div class="space-y-8">
		<p class="text-p-base text-ink-gray-7">
			{{
				__(
					'Your course landing page is what convinces someone to enrol. Make every field count — the title, image and description do most of the work.'
				)
			}}
		</p>

		<section class="space-y-5">
			<FormControl
				:modelValue="doc.title"
				variant="outline"
				:label="__('Course title')"
				:required="true"
				:maxlength="60"
				:placeholder="__('Insert your course title')"
				@update:modelValue="set('title', $event)"
			/>
			<FormControl
				:modelValue="doc.subtitle"
				variant="outline"
				:label="__('Course subtitle')"
				:maxlength="120"
				:placeholder="__('Insert your course subtitle')"
				:description="
					__('One sentence with the key skills learners will walk away with.')
				"
				@update:modelValue="set('subtitle', $event)"
			/>
			<FormControl
				:modelValue="doc.short_introduction"
				type="textarea"
				:rows="2"
				variant="outline"
				:label="__('Short introduction')"
				:required="true"
				@update:modelValue="set('short_introduction', $event)"
			/>

			<div class="space-y-1.5">
				<InputLabel
					:id="descriptionLabelId"
					:for-id="descriptionId"
					:label="__('Course description')"
					:required="true"
				/>
				<RichTextEditor
					:id="descriptionId"
					:content="doc.description"
					:editable="true"
					:fixedMenu="true"
					editorClass="prose-sm max-w-none border-b border-x border-outline-gray-2 rounded-b-md py-1 px-2 min-h-[10rem]"
					@change="setDescription"
				/>
				<p
					class="text-p-sm"
					:class="
						descriptionWords >= MIN_DESCRIPTION_WORDS
							? 'text-ink-gray-5'
							: 'text-ink-amber-3'
					"
				>
					{{
						descriptionWords >= MIN_DESCRIPTION_WORDS
							? __('{0} words').format(descriptionWords)
							: __('{0} of {1} words — a description of at least {1} words is required to submit.').format(
									descriptionWords,
									MIN_DESCRIPTION_WORDS
							  )
					}}
				</p>
			</div>
		</section>

		<section class="space-y-5 border-t pt-6">
			<h3 class="text-p-base-semibold text-ink-gray-9">{{ __('Basic info') }}</h3>
			<div class="grid grid-cols-1 gap-5 md:grid-cols-3">
				<FormControl
					type="select"
					:modelValue="doc.language"
					:options="LANGUAGES"
					variant="outline"
					:label="__('Language')"
					@update:modelValue="set('language', $event)"
				/>
				<FormControl
					type="select"
					:modelValue="doc.level"
					:options="LEVELS"
					variant="outline"
					:label="__('Level')"
					@update:modelValue="set('level', $event)"
				/>
				<Link
					:modelValue="doc.category"
					doctype="LMS Category"
					:label="__('Category')"
					:placeholder="__('Select category')"
					:inlineCreate="true"
					inlineCreatePlaceholder="Category name"
					:onCreate="onCreateCategory"
					variant="outline"
					@update:modelValue="set('category', $event)"
				/>
			</div>
			<FormControl
				:modelValue="doc.primary_topic"
				variant="outline"
				class="md:max-w-md"
				:label="__('What is primarily taught in your course?')"
				:placeholder="__('e.g. Landscape Photography')"
				@update:modelValue="set('primary_topic', $event)"
			/>
		</section>

		<section class="space-y-5 border-t pt-6">
			<h3 class="text-p-base-semibold text-ink-gray-9">
				{{ __('Course image') }}
			</h3>
			<Uploader
				type="image"
				:modelValue="doc.image"
				:label="__('Course image')"
				:description="
					__(
						'1280x720 pixels, .jpg, .jpeg, .gif or .png, and no text baked into the image.'
					)
				"
				@update:modelValue="set('image', $event)"
			/>
		</section>

		<section class="space-y-5 border-t pt-6">
			<h3 class="text-p-base-semibold text-ink-gray-9">
				{{ __('Promotional video') }}
			</h3>
			<p class="text-p-base text-ink-gray-6">
				{{
					__(
						'A promo video is a quick, compelling preview of what learners will get. Courses with a well-made one enrol noticeably better.'
					)
				}}
			</p>
			<Uploader
				type="video"
				:modelValue="doc.promo_video"
				:label="__('Promotional video')"
				@update:modelValue="set('promo_video', $event)"
			/>
			<FormControl
				:modelValue="doc.video_link"
				variant="outline"
				:label="__('Or embed a video link')"
				:placeholder="__('YouTube or Vimeo URL')"
				@update:modelValue="set('video_link', $event)"
			/>
		</section>

		<section class="space-y-3 border-t pt-6">
			<h3 class="text-p-base-semibold text-ink-gray-9">
				{{ __('Instructors') }}
			</h3>
			<p class="text-p-base text-ink-gray-6">
				{{
					__(
						'Instructors and their permissions are managed from course settings.'
					)
				}}
			</p>
			<div v-if="instructorNames.length" class="flex flex-wrap gap-2">
				<span
					v-for="name in instructorNames"
					:key="name"
					class="rounded-full bg-surface-gray-2 px-3 py-1 text-p-sm text-ink-gray-8"
				>
					{{ name }}
				</span>
			</div>
		</section>
	</div>
</template>

<script setup lang="ts">
import { computed, useId } from 'vue'
import { FormControl } from 'frappe-ui'
import Link from '@/components/Controls/Link.vue'
import Uploader from '@/components/Controls/Uploader.vue'
import RichTextEditor from '@/components/RichTextEditor.vue'
import { InputLabel } from '@/components/Form/labeling'
import { useCourseManage } from '@/composables/useCourseManage'
import { countWords } from '@/utils/courseCreation'
import { createLMSCategory } from '@/utils'
import { createHandler } from '@/utils/createHandler'
import type { LMSCourse } from '@/types/lms/LMSCourse'

// Mirrors MIN_DESCRIPTION_WORDS in lms/lms/course_creation.py.
const MIN_DESCRIPTION_WORDS = 50

const LANGUAGES = [
	'English',
	'Spanish',
	'French',
	'German',
	'Portuguese',
	'Hindi',
	'Arabic',
	'Japanese',
	'Mandarin',
]

const LEVELS = [
	'All Levels',
	'Beginner Level',
	'Intermediate Level',
	'Expert Level',
]

const { doc, markDirty } = useCourseManage()
const descriptionId = useId()
const descriptionLabelId = useId()

const descriptionWords = computed(() => countWords(doc.value.description))

const instructorNames = computed(() =>
	(doc.value.instructors ?? [])
		.map((row) => row.instructor)
		.filter((name): name is string => Boolean(name))
)

function set<K extends keyof LMSCourse>(field: K, value: LMSCourse[K]) {
	doc.value[field] = value
	markDirty()
}

function setDescription(value: string) {
	doc.value.description = value
	markDirty()
}

function onCreateCategory(value: string | null, done?: () => void) {
	createHandler(value, done, (name) => {
		createLMSCategory(name).then((categoryName?: string) => {
			if (!categoryName) return
			set('category', categoryName)
			done?.()
		})
	})
}
</script>
