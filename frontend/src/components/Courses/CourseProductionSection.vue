<template>
	<section id="production" class="scroll-mt-4 space-y-8 border-t pt-6">
		<div>
			<div class="text-base-semibold text-ink-gray-9">
				{{ __('Test video') }}
			</div>
			<p class="mt-1 text-p-base text-ink-gray-6">
				{{
					__(
						'Film a short test video before you record the real thing. A minute of footage catches problems with lighting, sound and framing while they are still cheap to fix.'
					)
				}}
			</p>
		</div>

		<div class="space-y-3">
			<h3 class="text-p-base-semibold text-ink-gray-9">
				{{ __('What feedback would be helpful?') }}
			</h3>
			<p class="text-p-base text-ink-gray-6">
				{{ __('Select one or more areas to focus on when you review it.') }}
			</p>
			<div class="space-y-2">
				<label
					v-for="area in FEEDBACK_AREAS"
					:key="area"
					class="flex cursor-pointer items-center gap-3 rounded-md border p-3 transition-colors hover:border-outline-gray-4"
					:class="
						selectedAreas.includes(area)
							? 'border-outline-gray-5 bg-surface-gray-1'
							: 'border-outline-gray-2'
					"
				>
					<input
						type="checkbox"
						class="size-4 rounded border-outline-gray-3 text-ink-gray-9 focus:ring-outline-gray-4"
						:checked="selectedAreas.includes(area)"
						@change="toggleArea(area)"
					/>
					<span class="text-p-base-medium text-ink-gray-9">{{ __(area) }}</span>
				</label>
			</div>
		</div>

		<div class="space-y-3">
			<h3 class="text-p-base-semibold text-ink-gray-9">
				{{ __('Upload your test video') }}
			</h3>
			<p class="text-p-base text-ink-gray-6">
				{{
					__(
						'This video is only for your own review. It is never shown to learners and does not count towards your course content.'
					)
				}}
			</p>
			<Uploader
				type="video"
				:modelValue="doc.test_video"
				:label="__('Test video')"
				:description="__('MP4 or WebM. Around a minute of footage is plenty.')"
				@update:modelValue="setTestVideo"
			/>
		</div>

		<GuidanceList
			:title="__('What to check when you watch it back')"
			:items="CHECKLIST"
			variant="bullets"
		/>
	</section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Uploader from '@/components/Controls/Uploader.vue'
import GuidanceList from '@/components/Courses/GuidanceList.vue'
import { useCourseManage } from '@/composables/useCourseManage'

const FEEDBACK_AREAS = ['Video production', 'Audio production', 'Delivery']

const CHECKLIST = [
	{ body: __('Your face is evenly lit with no hard shadows or backlight') },
	{ body: __('Audio is clear, close-miked and free of room echo') },
	{
		body: __('You are framed from the chest up, with the camera at eye level'),
	},
	{ body: __('The background is tidy and not competing for attention') },
	{ body: __('You speak at a steady pace and look into the lens') },
]

const { doc, markDirty } = useCourseManage()

// Stored as a comma-separated string on the doc, which keeps it to one Small
// Text field instead of a child table for what is a fixed three-item choice.
const selectedAreas = computed<string[]>(() =>
	(doc.value.test_video_feedback ?? '')
		.split(',')
		.map((area) => area.trim())
		.filter(Boolean)
)

function toggleArea(area: string) {
	const current = selectedAreas.value
	const next = current.includes(area)
		? current.filter((item) => item !== area)
		: [...current, area]
	doc.value.test_video_feedback = next.join(', ')
	markDirty()
}

function setTestVideo(url: string) {
	doc.value.test_video = url
	markDirty()
}
</script>
