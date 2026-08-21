<template>
	<section id="audience" class="scroll-mt-4 space-y-8 border-t pt-6">
		<div>
			<div class="text-base-semibold text-ink-gray-9">
				{{ __('Who this course is for') }}
			</div>
			<p class="mt-1 text-p-base text-ink-gray-6">
				{{
					__(
						'These descriptions are publicly visible on the course landing page and help learners decide whether the course is right for them.'
					)
				}}
			</p>
		</div>

		<div class="space-y-3">
			<h3 class="text-p-base-semibold text-ink-gray-9">
				{{ __('What will students learn in your course?') }}
			</h3>
			<p class="text-p-base text-ink-gray-6">
				{{
					__(
						'You must enter at least {0} learning objectives or outcomes that learners can expect to achieve after completing your course.'
					).format(MIN_OBJECTIVES)
				}}
			</p>
			<ObjectiveList
				:modelValue="doc.learning_objectives"
				:placeholders="OBJECTIVE_PLACEHOLDERS"
				:itemLabel="__('Learning objective')"
				:minRows="MIN_OBJECTIVES"
				:addLabel="__('Add more to your response')"
				@update:modelValue="setRows('learning_objectives', $event)"
			/>
			<p
				v-if="objectiveCount < MIN_OBJECTIVES"
				class="text-p-sm text-ink-amber-3"
			>
				{{
					__('{0} more needed before you can submit for review.').format(
						MIN_OBJECTIVES - objectiveCount
					)
				}}
			</p>
		</div>

		<div class="space-y-3">
			<h3 class="text-p-base-semibold text-ink-gray-9">
				{{ __('What are the requirements or prerequisites for your course?') }}
			</h3>
			<p class="text-p-base text-ink-gray-6">
				{{
					__(
						'List the required skills, experience, tools or equipment learners should have before taking your course. If there are none, use this space to lower the barrier for beginners.'
					)
				}}
			</p>
			<ObjectiveList
				:modelValue="doc.requirements"
				:placeholders="REQUIREMENT_PLACEHOLDERS"
				:itemLabel="__('Requirement')"
				:minRows="1"
				:addLabel="__('Add more to your response')"
				@update:modelValue="setRows('requirements', $event)"
			/>
		</div>

		<div class="space-y-3">
			<h3 class="text-p-base-semibold text-ink-gray-9">
				{{ __('Who is this course for?') }}
			</h3>
			<p class="text-p-base text-ink-gray-6">
				{{
					__(
						'Write a clear description of the intended learners who will find your course valuable. This helps you attract the right people.'
					)
				}}
			</p>
			<ObjectiveList
				:modelValue="doc.intended_learners"
				:placeholders="LEARNER_PLACEHOLDERS"
				:itemLabel="__('Intended learner')"
				:minRows="1"
				:addLabel="__('Add more to your response')"
				@update:modelValue="setRows('intended_learners', $event)"
			/>
		</div>
	</section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import ObjectiveList from '@/components/Courses/ObjectiveList.vue'
import { useCourseManage } from '@/composables/useCourseManage'
import type { LMSCourseObjective } from '@/types/lms/LMSCourseObjective'
import type { LMSCourse } from '@/types/lms/LMSCourse'

// Kept in step with MIN_OBJECTIVES in lms/lms/course_creation.py — the server
// is the one that actually gates submission; this only shapes the copy and the
// number of rows shown up front.
const MIN_OBJECTIVES = 4

const OBJECTIVE_PLACEHOLDERS = [
	__('Example: Define the roles and responsibilities of a project manager'),
	__('Example: Estimate project timelines and budgets'),
	__('Example: Identify and manage project risks'),
	__(
		'Example: Complete a case study to manage a project from conception to completion'
	),
]

const REQUIREMENT_PLACEHOLDERS = [
	__(
		'Example: No programming experience needed. You will learn everything you need to know'
	),
]

const LEARNER_PLACEHOLDERS = [
	__('Example: Beginner photographers curious about landscape work'),
]

const { doc, markDirty } = useCourseManage()

const objectiveCount = computed(
	() =>
		(doc.value.learning_objectives ?? []).filter((row) =>
			(row.objective ?? '').trim()
		).length
)

type ObjectiveField =
	| 'learning_objectives'
	| 'requirements'
	| 'intended_learners'

function setRows(field: ObjectiveField, rows: LMSCourseObjective[]) {
	const target = doc.value as LMSCourse
	target[field] = rows
	markDirty()
}
</script>
