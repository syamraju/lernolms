<template>
	<Dialog v-model="show" :title="title">
		<template #body-content>
			<div class="space-y-4 text-base">
				<p class="text-p-base text-ink-gray-7">
					{{
						__(
							'You are almost ready to submit your course. Here are the items still outstanding.'
						)
					}}
				</p>

				<ul class="space-y-3">
					<li
						v-for="(group, step) in grouped"
						:key="step"
						class="rounded-md border p-3"
					>
						<div class="text-p-base-medium text-ink-gray-9">
							{{ stepLabel(step) }}
						</div>
						<ul class="mt-1.5 space-y-1 ps-5">
							<li
								v-for="(blocker, index) in group"
								:key="index"
								class="list-disc text-p-base text-ink-gray-7"
							>
								{{ blocker.message }}
							</li>
						</ul>
						<Button
							variant="ghost"
							class="!-ms-2 mt-2"
							:label="__('Go to {0}').format(stepLabel(step))"
							@click="go(step)"
						/>
					</li>
				</ul>

				<p class="text-p-sm text-ink-gray-5">
					{{
						__(
							'Once these are complete, Submit for Review will send the course to a moderator.'
						)
					}}
				</p>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button, Dialog } from 'frappe-ui'
import { findStep } from '@/pages/Courses/Manage/steps'
import type { CourseSubmitBlocker } from '@/types'

const props = defineProps<{ blockers: CourseSubmitBlocker[] }>()
const emit = defineEmits<{ go: [string] }>()

const show = defineModel<boolean>({ default: false })

// Held in script rather than inlined in the template: the apostrophe would
// otherwise have to be escaped inside the attribute's own quoting.
const title = __("Why can't I submit for review?")

// Grouped by step so a single rail entry with three unmet requirements reads
// as one place to go, not three separate errands.
const grouped = computed<Record<string, CourseSubmitBlocker[]>>(() => {
	const map: Record<string, CourseSubmitBlocker[]> = {}
	for (const blocker of props.blockers) {
		;(map[blocker.step] ??= []).push(blocker)
	}
	return map
})

function stepLabel(key: string): string {
	return __(findStep(key)?.label ?? key)
}

function go(step: string) {
	show.value = false
	emit('go', step)
}
</script>
