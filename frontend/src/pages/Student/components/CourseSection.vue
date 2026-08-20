<!--
	One titled band of course cards. Figma: node 100:9980 — a heading with a
	rule, then a four-up grid.

	The list view is not in the Figma; it is what the header's list/grid toggle
	has to switch to, so it reuses the same card at a wider aspect rather than
	introducing a second card design.
-->
<template>
	<section class="mb-[38px] last:mb-0">
		<SectionHeading :title="title" :count="count" />

		<div
			:class="
				view === 'grid'
					? 'grid gap-5 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4'
					: 'grid gap-4 lg:grid-cols-2'
			"
		>
			<LearnoCourseCard
				v-for="course in courses"
				:key="course.name"
				:course="course"
				:enrolling="enrolling === course.name"
				@enroll="$emit('enroll', $event)"
			/>
		</div>
	</section>
</template>

<script setup lang="ts">
import SectionHeading from '@/pages/Student/components/SectionHeading.vue'
import LearnoCourseCard from '@/components/Learno/LearnoCourseCard.vue'

defineProps<{
	title: string
	count: number
	courses: any[]
	view: 'grid' | 'list'
	enrolling?: string
}>()

defineEmits<{ (e: 'enroll', course: any): void }>()
</script>
