<template>
	<div class="space-y-8">
		<p class="text-p-base text-ink-gray-7">
			{{
				__(
					'Good production keeps learners watching. You do not need a studio — a quiet room, a window and a decent microphone will get you most of the way there.'
				)
			}}
		</p>

		<GuidanceList :title="__('Film with confidence')" :items="FILMING" />

		<GuidanceList
			:title="__('Technical requirements')"
			:items="TECHNICAL"
			variant="bullets"
		/>

		<GuidanceList :title="__('Editing your lectures')" :items="EDITING" />

		<section
			class="flex items-start gap-3 rounded-md border border-outline-gray-2 bg-surface-gray-1 p-4"
		>
			<span class="lucide-lightbulb mt-0.5 size-5 shrink-0 text-ink-gray-6" />
			<div class="space-y-1">
				<div class="text-p-base-medium text-ink-gray-9">
					{{ __('Not filmed your test video yet?') }}
				</div>
				<p class="text-p-base text-ink-gray-6">
					{{
						__(
							'A one-minute test recording will surface lighting and audio problems before you commit to a full course.'
						)
					}}
				</p>
				<Button
					variant="outline"
					class="mt-2"
					:label="__('Go to Setup & test video')"
					@click="goToStep('test-video')"
				/>
			</div>
		</section>
	</div>
</template>

<script setup lang="ts">
import { Button } from 'frappe-ui'
import GuidanceList from '@/components/Courses/GuidanceList.vue'
import { useCourseManage } from '@/composables/useCourseManage'

const FILMING = [
	{
		title: __('Use natural or soft light.'),
		body: __(
			'Face a window or place two soft lights at 45 degrees to your left and right. Avoid overhead lighting, which casts shadows under the eyes.'
		),
	},
	{
		title: __('Get the microphone close.'),
		body: __(
			'Audio quality matters more to learners than video quality. A lapel or USB microphone within an arm’s length of you beats a camera’s built-in mic every time.'
		),
	},
	{
		title: __('Film in a quiet, soft room.'),
		body: __(
			'Carpets, curtains and bookshelves absorb echo. Turn off fans and air conditioning while recording.'
		),
	},
	{
		title: __('Talk to one person.'),
		body: __(
			'Address the camera as though a single learner were in the room. It reads as warmer than presenting to an audience.'
		),
	},
]

const TECHNICAL = [
	{ body: __('Film and export in HD — 1080p at 16:9 is the safe default') },
	{ body: __('Export video as MP4 with H.264 encoding') },
	{ body: __('Record audio at 44.1 kHz or higher, in stereo') },
	{ body: __('Keep audio free of background hum, clipping and echo') },
]

const EDITING = [
	{
		title: __('Cut the dead air.'),
		body: __(
			'Trim long pauses, false starts and setup time. Learners feel every wasted second.'
		),
	},
	{
		title: __('Show, then tell.'),
		body: __(
			'Cut to your screen, slides or the object you are describing while you talk about it.'
		),
	},
	{
		title: __('Keep lectures short.'),
		body: __(
			'Two to seven minutes per lecture is the sweet spot. Split anything longer at a natural boundary.'
		),
	},
]

const { goToStep } = useCourseManage()
</script>
