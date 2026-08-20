<template>
	<div class="space-y-8">
		<p class="text-p-base text-ink-gray-7">
			{{
				__(
					'Write optional messages that are sent automatically when a learner joins or completes your course. Leave a box blank to send nothing.'
				)
			}}
		</p>

		<section class="space-y-1.5">
			<InputLabel
				:id="welcomeLabelId"
				:for-id="welcomeId"
				:label="__('Welcome message')"
			/>
			<RichTextEditor
				:id="welcomeId"
				:content="doc.welcome_message"
				:editable="true"
				:fixedMenu="true"
				editorClass="prose-sm max-w-none border-b border-x border-outline-gray-2 rounded-b-md py-1 px-2 min-h-[7rem]"
				@change="set('welcome_message', $event)"
			/>
			<p class="text-p-sm text-ink-gray-5">
				{{
					__(
						'Sent as soon as someone enrols. Point them at the first lecture and set expectations.'
					)
				}}
			</p>
		</section>

		<section class="space-y-1.5">
			<InputLabel
				:id="congratsLabelId"
				:for-id="congratsId"
				:label="__('Congratulations message')"
			/>
			<RichTextEditor
				:id="congratsId"
				:content="doc.congratulations_message"
				:editable="true"
				:fixedMenu="true"
				editorClass="prose-sm max-w-none border-b border-x border-outline-gray-2 rounded-b-md py-1 px-2 min-h-[7rem]"
				@change="set('congratulations_message', $event)"
			/>
			<p class="text-p-sm text-ink-gray-5">
				{{
					__(
						'Sent on completion. A good place to ask for a review or suggest what to learn next.'
					)
				}}
			</p>
		</section>
	</div>
</template>

<script setup lang="ts">
import { useId } from 'vue'
import RichTextEditor from '@/components/RichTextEditor.vue'
import { InputLabel } from '@/components/Form/labeling'
import { useCourseManage } from '@/composables/useCourseManage'
import type { LMSCourse } from '@/types/lms/LMSCourse'

const { doc, markDirty } = useCourseManage()

const welcomeId = useId()
const welcomeLabelId = useId()
const congratsId = useId()
const congratsLabelId = useId()

function set(field: keyof LMSCourse, value: string) {
	;(doc.value as Record<string, unknown>)[field] = value
	markDirty()
}
</script>
