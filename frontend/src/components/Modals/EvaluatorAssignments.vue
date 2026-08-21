<!--
	Who marks what.

	A subjective quiz has no answer key, so its submissions have to reach a person.
	This is where a moderator decides which person: an evaluator is given courses,
	or programs that stand in for every course inside them, and their queue is
	exactly the submissions from those courses.
-->
<template>
	<Dialog v-model="show" size="3xl" :title="__('Assign evaluators')">
		<template #body-content>
			<div class="space-y-5 text-base">
				<p class="text-p-base text-ink-gray-7">
					{{
						__(
							'An evaluator only ever sees submissions from the courses you give them here. A program covers every course inside it, now and later.'
						)
					}}
				</p>

				<SkeletonLoader
					v-if="evaluators.loading && !evaluators.data"
					variant="form"
				/>

				<p
					v-else-if="!evaluatorOptions.length"
					class="rounded-md border border-dashed p-6 text-center text-p-base text-ink-gray-6"
				>
					{{
						__(
							'Nobody has the evaluator role yet. Add it to a user from their profile first.'
						)
					}}
				</p>

				<template v-else>
					<FormControl
						type="select"
						variant="outline"
						:options="evaluatorOptions"
						:modelValue="selected"
						:label="__('Evaluator')"
						@update:modelValue="onSelect"
					/>

					<div class="grid grid-cols-1 gap-5 md:grid-cols-2">
						<PickList
							:title="__('Courses')"
							:items="courseItems"
							:selected="chosenCourses"
							:empty="__('No courses yet.')"
							:search-label="__('Search courses')"
							@toggle="toggle(chosenCourses, $event)"
						/>
						<PickList
							:title="__('Programs')"
							:items="programItems"
							:selected="chosenPrograms"
							:empty="__('No programs yet.')"
							:search-label="__('Search programs')"
							@toggle="toggle(chosenPrograms, $event)"
						/>
					</div>

					<p class="text-p-sm text-ink-gray-6">
						{{ coverageSummary }}
					</p>
				</template>
			</div>
		</template>

		<template #actions>
			<div class="flex items-center justify-end gap-2">
				<Button :label="__('Close')" @click="show = false" />
				<Button
					variant="solid"
					:disabled="!selected"
					:loading="saving"
					:label="__('Save assignments')"
					@click="save"
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
	FormControl,
	call,
	createResource,
	toast,
} from 'frappe-ui'
import PickList from '@/components/Modals/PickList.vue'
import SkeletonLoader from '@/components/SkeletonLoader.vue'
import { errorMessage } from '@/utils/courseCreation'
import type { EvaluatorAssignment, Resource } from '@/types'

const show = defineModel<boolean>({ required: true })
const emit = defineEmits<{ saved: [] }>()

const evaluators = createResource({
	url: 'lms.lms.evaluation.list_evaluators',
	auto: true,
}) as Resource<EvaluatorAssignment[] | null>

const courses = createResource({
	url: 'frappe.client.get_list',
	makeParams: () => ({
		doctype: 'LMS Course',
		fields: ['name', 'title'],
		order_by: 'title asc',
		limit_page_length: 0,
	}),
	auto: true,
}) as Resource<{ name: string; title: string }[] | null>

const programs = createResource({
	url: 'frappe.client.get_list',
	makeParams: () => ({
		doctype: 'LMS Program',
		fields: ['name', 'title'],
		order_by: 'title asc',
		limit_page_length: 0,
	}),
	auto: true,
}) as Resource<{ name: string; title: string }[] | null>

const selected = ref('')
const chosenCourses = ref<string[]>([])
const chosenPrograms = ref<string[]>([])
const saving = ref(false)

const evaluatorOptions = computed(() =>
	(evaluators.data ?? []).map((row) => ({
		label: row.full_name || row.evaluator,
		value: row.name,
	}))
)

const courseItems = computed(() =>
	(courses.data ?? []).map((row) => ({ value: row.name, label: row.title }))
)
const programItems = computed(() =>
	(programs.data ?? []).map((row) => ({ value: row.name, label: row.title }))
)

// Open on the first evaluator rather than an empty select: the moderator came
// here to assign someone, and one fewer click gets them to the lists.
watch(
	() => evaluators.data,
	(rows) => {
		if (!selected.value && rows?.length) onSelect(rows[0].name)
	}
)

function onSelect(name: string) {
	selected.value = name
	const row = (evaluators.data ?? []).find((item) => item.name === name)
	chosenCourses.value = (row?.courses ?? []).map((item) => item.course)
	chosenPrograms.value = (row?.programs ?? []).map((item) => item.program)
}

function toggle(list: { value: string[] }, name: string) {
	// Replaced rather than spliced: the lists are passed down as props, and a
	// new array is what tells the child its selection changed.
	list.value = list.value.includes(name)
		? list.value.filter((item) => item !== name)
		: [...list.value, name]
}

const coverageSummary = computed(() => {
	const courseCount = chosenCourses.value.length
	const programCount = chosenPrograms.value.length
	if (!courseCount && !programCount) {
		return __('Nothing assigned — this evaluator will have an empty queue.')
	}
	const parts = []
	if (courseCount) {
		parts.push(
			courseCount === 1 ? __('1 course') : __('{0} courses').format(courseCount)
		)
	}
	if (programCount) {
		parts.push(
			programCount === 1
				? __('1 program')
				: __('{0} programs').format(programCount)
		)
	}
	return __('Assigned: {0}.').format(parts.join(__(' and ')))
})

async function save() {
	if (!selected.value || saving.value) return
	saving.value = true
	try {
		evaluators.data = (await call(
			'lms.lms.evaluation.set_evaluator_assignments',
			{
				evaluator: selected.value,
				courses: chosenCourses.value,
				programs: chosenPrograms.value,
			}
		)) as EvaluatorAssignment[]
		toast.success(__('Assignments saved'))
		emit('saved')
	} catch (error) {
		toast.error(errorMessage(error, __('Could not save the assignments')))
	} finally {
		saving.value = false
	}
}
</script>
