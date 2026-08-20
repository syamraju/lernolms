<template>
	<div class="space-y-8">
		<p class="text-p-base text-ink-gray-7">
			{{
				__(
					'Planning your course carefully will create a clear learning path for students and help you once you film. Think about the main skill you are teaching and work backwards from there.'
				)
			}}
		</p>

		<section class="space-y-3">
			<h3 class="text-p-base-semibold text-ink-gray-9">
				{{ __('What is primarily taught in your course?') }}
			</h3>
			<p class="text-p-base text-ink-gray-6">
				{{
					__(
						'Naming the single skill at the centre of your course keeps every section pointed at the same outcome.'
					)
				}}
			</p>
			<FormControl
				:modelValue="doc.primary_topic"
				variant="outline"
				class="max-w-md"
				:label="__('Primarily taught')"
				:placeholder="__('e.g. Landscape Photography')"
				@update:modelValue="setPrimaryTopic"
			/>
		</section>

		<GuidanceList :title="__('Here are our best practices')" :items="PRACTICES" />

		<GuidanceList
			:title="__('Requirements')"
			:items="REQUIREMENTS"
			variant="bullets"
		/>
	</div>
</template>

<script setup lang="ts">
import { FormControl } from 'frappe-ui'
import GuidanceList from '@/components/Courses/GuidanceList.vue'
import { useCourseManage } from '@/composables/useCourseManage'

const { doc, markDirty } = useCourseManage()

const PRACTICES = [
	{
		title: __('Start with your goals.'),
		body: __(
			'Setting goals for what learners will accomplish in your course helps you determine what content to include and how you will teach it.'
		),
	},
	{
		title: __('Create an outline.'),
		body: __(
			'Decide what skills you will teach and how you will teach them. Group related lectures into sections, and give each section at least three lectures with a single clear learning objective.'
		),
	},
	{
		title: __('Introduce yourself and create momentum.'),
		body: __(
			'People online want to start learning quickly. Structure the first section so it builds excitement and gets learners moving.'
		),
	},
	{
		title: __('Sections have a clear learning objective.'),
		body: __(
			'Introduce each section with a short description of the outcome, and summarise what was covered at the end.'
		),
	},
	{
		title: __('Lectures cover one concept.'),
		body: __(
			'A focused lecture of two to seven minutes gives learners something to complete in a single sitting.'
		),
	},
	{
		title: __('Mix and match your lecture types.'),
		body: __(
			'Alternate between filming yourself, your screen, and slides or other visuals. Showing yourself helps learners feel connected.'
		),
	},
	{
		title: __('Practice activities create hands-on learning.'),
		body: __(
			'Help learners apply your lessons to their own work with projects, assignments, coding exercises or worksheets.'
		),
	},
]

const REQUIREMENTS = [
	{ body: __('Your course must have at least 5 lectures') },
	{ body: __('All lectures must add up to at least 30+ minutes of total video') },
	{
		body: __(
			'Your course is composed of valuable educational content and free of promotional or distracting material'
		),
	},
]

function setPrimaryTopic(value: string) {
	doc.value.primary_topic = value
	markDirty()
}
</script>
