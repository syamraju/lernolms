<template>
	<section class="space-y-5">
		<div
			v-if="description"
			class="ProseMirror prose prose-sm max-w-none text-ink-gray-7"
			v-safe-html:rich="description"
		/>

		<Quiz v-if="itemType === 'Quiz' && quiz" :quizName="quiz" />

		<Assignment
			v-else-if="itemType === 'Assignment' && assignment"
			:assignmentID="assignment"
			:showTitle="false"
		/>

		<template v-else-if="itemType === 'Coding Exercise' && exercise">
			<iframe
				v-if="exerciseUrl"
				:src="safeUrl(exerciseUrl)"
				:title="__('Coding exercise')"
				class="h-[900px] w-full rounded-md border"
			/>
			<SkeletonLoader v-else variant="form" />
		</template>
	</section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { call } from 'frappe-ui'
import Quiz from '@/components/Quiz.vue'
import Assignment from '@/components/Assignment.vue'
import SkeletonLoader from '@/components/SkeletonLoader.vue'
import { getLmsRoute } from '@/utils/basePath'
import { safeUrl } from '@/utils/safeUrl'
import { usersStore } from '@/stores/user'
import type { CurriculumItemType } from '@/types'

/**
 * The activity a typed curriculum item puts in front of a learner.
 *
 * A Lecture renders nothing here — its content is the lesson body, which
 * Lesson.vue already draws. The other three delegate to the players the app
 * already has, so a quiz reached from the curriculum behaves exactly like one
 * embedded in a lesson body.
 */
const props = defineProps<{
	itemType?: CurriculumItemType
	description?: string | null
	quiz?: string | null
	assignment?: string | null
	exercise?: string | null
}>()

const { userResource } = usersStore()
const exerciseUrl = ref('')

// The exercise player lives on its own route and is embedded in a frame, the
// same way the in-body `program` block does it. Resolving the learner's
// existing submission first means reopening the item resumes their attempt
// instead of silently starting a new one.
async function resolveExerciseUrl() {
	if (props.itemType !== 'Coding Exercise' || !props.exercise) {
		exerciseUrl.value = ''
		return
	}
	let submission = 'new'
	try {
		const found = (await call('frappe.client.get_value', {
			doctype: 'LMS Programming Exercise Submission',
			filters: { exercise: props.exercise, member: userResource.data?.name },
			fieldname: ['name'],
		})) as { name?: string } | null
		if (found?.name) submission = found.name
	} catch {
		// No submission yet, or the lookup is not permitted — either way the
		// learner starts a fresh attempt rather than seeing an error.
	}
	exerciseUrl.value = getLmsRoute(
		`programming-exercises/${props.exercise}/submission/${submission}?fromLesson=1`
	)
}

onMounted(resolveExerciseUrl)
watch(() => [props.itemType, props.exercise], resolveExerciseUrl)
</script>
