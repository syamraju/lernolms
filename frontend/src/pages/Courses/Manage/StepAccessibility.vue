<template>
	<div class="space-y-8">
		<p class="text-p-base text-ink-gray-7">
			{{
				__(
					'An accessible course reaches more learners and is easier for everyone to follow. Work through the list below — most items cost minutes, not hours.'
				)
			}}
		</p>

		<section class="space-y-3">
			<h3 class="text-p-base-semibold text-ink-gray-9">
				{{ __('Accessibility checklist') }}
			</h3>
			<ul class="divide-y border-y">
				<li
					v-for="item in checklist"
					:key="item.key"
					class="flex items-start gap-3 py-3"
				>
					<span
						class="mt-0.5 grid size-5 shrink-0 place-items-center rounded-full border"
						:class="
							item.done
								? 'border-outline-gray-5 bg-surface-gray-7 text-white'
								: 'border-outline-gray-3'
						"
						aria-hidden="true"
					>
						<span v-if="item.done" class="lucide-check size-3" />
					</span>
					<div class="min-w-0">
						<div class="text-p-base-medium text-ink-gray-9">
							{{ item.title }}
							<span class="sr-only">
								{{ item.done ? __('Done') : __('Not done') }}
							</span>
						</div>
						<p class="text-p-base text-ink-gray-6">{{ item.body }}</p>
						<Button
							v-if="!item.done && item.step"
							variant="ghost"
							class="!-ms-2 mt-1"
							:label="item.action"
							@click="goToStep(item.step)"
						/>
					</div>
				</li>
			</ul>
		</section>

		<GuidanceList
			:title="__('While you film and edit')"
			:items="PRODUCTION_TIPS"
			variant="bullets"
		/>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button } from 'frappe-ui'
import GuidanceList from '@/components/Courses/GuidanceList.vue'
import { useCourseManage } from '@/composables/useCourseManage'
import { countWords } from '@/utils/courseCreation'

const PRODUCTION_TIPS = [
	{
		body: __(
			'Describe out loud anything you show on screen, so learners who cannot see it still follow along'
		),
	},
	{ body: __('Keep on-screen text large, high contrast and on screen long enough to read') },
	{ body: __('Avoid conveying meaning through colour alone') },
	{ body: __('Speak clearly and at a steady pace, and avoid heavy background music') },
]

const { doc, status, goToStep } = useCourseManage()

// Every row is derived from data the author has already entered elsewhere, so
// this page reports on real state rather than asking them to tick boxes twice.
const checklist = computed(() => [
	{
		key: 'captions',
		done: Boolean(doc.value.captions_enabled),
		title: __('Captions are enabled'),
		body: __(
			'Automatic captions make your lectures usable by learners who are deaf or hard of hearing, and by anyone watching without sound.'
		),
		step: 'captions',
		action: __('Go to Captions'),
	},
	{
		key: 'objectives',
		done: (status.data?.objectives ?? 0) >= 4,
		title: __('Learning outcomes are written out'),
		body: __(
			'Clear outcomes let learners using a screen reader judge the course without watching a promo video.'
		),
		step: 'intended-learners',
		action: __('Go to Intended learners'),
	},
	{
		key: 'description',
		done: countWords(doc.value.description) >= 50,
		title: __('The course has a full text description'),
		body: __(
			'A written description is the accessible equivalent of your promotional video.'
		),
		step: 'landing-page',
		action: __('Go to Course landing page'),
	},
	{
		key: 'requirements',
		done: (status.data?.requirements ?? 0) > 0,
		title: __('Requirements are stated up front'),
		body: __(
			'Naming the tools and prior knowledge needed prevents learners from committing to a course they cannot complete.'
		),
		step: 'intended-learners',
		action: __('Go to Intended learners'),
	},
])
</script>
