<!--
	The reviewer's queue.

	Instructors build a course and submit it; nothing publishes until someone
	here approves it. The queue is deliberately its own page rather than a tab on
	the course list: those tabs filter courses you can already see, and this is a
	worklist — oldest submission first, because the course that has waited
	longest is the one holding an instructor up.

	Both actions send a notification back to the instructors, so "sent back" is
	never something they have to discover by checking.
-->
<template>
	<div class="flex h-full min-h-0 flex-col">
		<header class="shrink-0 border-b px-5 py-4">
			<h1 class="text-lg font-semibold text-ink-gray-9">
				{{ __('Courses to review') }}
			</h1>
			<p class="mt-1 text-p-sm text-ink-gray-6">
				{{
					__(
						'Read through each course, then publish it or send it back with what needs changing.'
					)
				}}
			</p>
		</header>

		<div class="min-h-0 flex-1 overflow-y-auto p-5">
			<SkeletonLoader v-if="queue.loading && !queue.data" variant="list" />

			<div
				v-else-if="!courses.length"
				class="rounded-md border border-dashed p-10 text-center"
			>
				<span
					class="lucide-clipboard-check mx-auto mb-2 block size-6 text-ink-gray-4"
					aria-hidden="true"
				/>
				<p class="text-p-base text-ink-gray-6">
					{{ __('Nothing is waiting on a review right now.') }}
				</p>
			</div>

			<ul v-else class="space-y-3">
				<li
					v-for="course in courses"
					:key="course.name"
					class="rounded-md border p-4"
				>
					<div class="flex flex-wrap items-start justify-between gap-4">
						<div class="min-w-0 flex-1">
							<router-link
								:to="{
									name: 'CourseDetail',
									params: { courseName: course.name },
								}"
								class="text-p-base-semibold text-ink-gray-9 hover:underline"
							>
								{{ course.title }}
							</router-link>
							<p class="mt-1 text-p-sm text-ink-gray-6">
								{{ summaryFor(course) }}
							</p>
							<div
								v-if="course.instructors?.length"
								class="mt-2 flex flex-wrap items-center gap-2"
							>
								<span
									v-for="instructor in course.instructors"
									:key="instructor.name"
									class="flex items-center gap-1.5 rounded-full bg-surface-gray-2 py-0.5 pe-2.5 ps-0.5"
								>
									<Avatar
										:image="instructor.user_image"
										:label="instructor.full_name"
										size="xs"
									/>
									<span class="text-p-sm text-ink-gray-7">
										{{ instructor.full_name }}
									</span>
								</span>
							</div>
						</div>

						<div class="flex shrink-0 items-center gap-2">
							<Button
								variant="outline"
								:label="__('Open')"
								@click="open(course)"
							/>
							<Button
								:label="__('Send back')"
								@click="startReject(course)"
							/>
							<Button
								variant="solid"
								:loading="acting === course.name"
								:label="__('Approve and publish')"
								@click="approve(course)"
							/>
						</div>
					</div>
				</li>
			</ul>
		</div>

		<Dialog
			v-model="showReject"
			:options="{
				title: __('Send this course back'),
				actions: [
					{
						label: __('Send back'),
						variant: 'solid',
						theme: 'red',
						disabled: !feedback.trim(),
						loading: acting === rejecting?.name,
						onClick: confirmReject,
					},
				],
			}"
		>
			<template #body-content>
				<p class="mb-3 text-p-sm text-ink-gray-6">
					{{
						__(
							'The instructors get this as a notification and see it on the course, so say what has to change.'
						)
					}}
				</p>
				<FormControl
					v-model="feedback"
					type="textarea"
					:rows="5"
					variant="outline"
					:label="__('What needs changing?')"
					:placeholder="
						__('e.g. Section 3 has no assessment, and the audio drops out in lecture 5.')
					"
				/>
			</template>
		</Dialog>
	</div>
</template>

<script setup lang="ts">
import { computed, inject, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
	Avatar,
	Button,
	Dialog,
	FormControl,
	call,
	createResource,
	toast,
	usePageMeta,
} from 'frappe-ui'
import SkeletonLoader from '@/components/SkeletonLoader.vue'
import { errorMessage } from '@/utils/courseCreation'
import type { CourseReviewItem, Resource, SessionUser } from '@/types'

const router = useRouter()
const user = inject<SessionUser>('$user')
const dayjs = inject('$dayjs') as typeof import('dayjs')

usePageMeta(() => ({ title: __('Courses to review') }))

const acting = ref('')
const showReject = ref(false)
const rejecting = ref<CourseReviewItem | null>(null)
const feedback = ref('')

const queue = createResource({
	url: 'lms.lms.course_review.get_review_queue',
	auto: true,
}) as Resource<CourseReviewItem[] | null>

const courses = computed<CourseReviewItem[]>(() => queue.data ?? [])

// The server refuses this endpoint to anyone else; bouncing here as well keeps
// a non-reviewer who typed the URL from staring at an error state.
onMounted(() => {
	if (user?.data && !user.data.is_moderator && !user.data.is_evaluator) {
		router.replace({ name: 'Courses' })
	}
})

function summaryFor(course: CourseReviewItem): string {
	const lessons =
		course.lessons === 1
			? __('1 lesson')
			: __('{0} lessons').format(course.lessons ?? 0)
	const waiting = course.submitted_on
		? __('submitted {0}').format(dayjs(course.submitted_on).fromNow())
		: __('submission date unknown')
	return `${lessons} · ${waiting}`
}

function open(course: CourseReviewItem) {
	router.push({ name: 'CourseDetail', params: { courseName: course.name } })
}

async function review(course: CourseReviewItem, action: 'approve' | 'reject') {
	acting.value = course.name
	try {
		await call('lms.lms.course_review.review_course', {
			course: course.name,
			action,
			feedback: feedback.value.trim() || null,
		})
		toast.success(
			action === 'approve'
				? __('{0} is published').format(course.title)
				: __('{0} was sent back').format(course.title)
		)
		await queue.reload()
		return true
	} catch (error) {
		toast.error(errorMessage(error, __('Could not record the review')))
		return false
	} finally {
		acting.value = ''
	}
}

function approve(course: CourseReviewItem) {
	feedback.value = ''
	void review(course, 'approve')
}

function startReject(course: CourseReviewItem) {
	rejecting.value = course
	feedback.value = ''
	showReject.value = true
}

async function confirmReject(options?: { close?: () => void }) {
	if (!rejecting.value || !feedback.value.trim()) return
	const ok = await review(rejecting.value, 'reject')
	if (!ok) return
	showReject.value = false
	rejecting.value = null
	options?.close?.()
}
</script>
