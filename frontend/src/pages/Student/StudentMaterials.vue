<!--
	Materials shelf — every downloadable file across the student's enrolled
	courses. The Figma has a Materials sidebar row but no frame for it, so this
	reuses the course Materials panel's row design (node 112:11071) under a
	per-course heading.
-->
<template>
	<div class="flex h-full min-h-0 flex-col">
		<header
			class="shrink-0 border-b border-[var(--learno-line-soft)] bg-white px-6 py-[22px] lg:px-10"
		>
			<h1 class="text-[27px] font-semibold leading-[1.2] text-black max-lg:ps-12">
				{{ __('Materials') }}
			</h1>
			<p class="mt-1 text-[13px] text-[var(--learno-ink-muted)]">
				{{ __('Everything you can download from the courses you are enrolled in.') }}
			</p>
		</header>

		<div
			class="learno-scroll min-h-0 flex-1 overflow-y-auto bg-[var(--learno-canvas)] px-6 py-7 lg:px-10"
		>
			<div v-if="shelf.loading" class="flex flex-col gap-6">
				<div
					v-for="n in 3"
					:key="n"
					class="h-40 animate-pulse rounded-[var(--learno-r-lg)] bg-black/5"
				/>
			</div>

			<p
				v-else-if="!shelf.data?.length"
				class="py-20 text-center text-[14px] text-[var(--learno-ink-muted)]"
			>
				{{ __('No downloadable materials in your courses yet.') }}
			</p>

			<section
				v-for="course in shelf.data || []"
				:key="course.course"
				class="mb-8 rounded-[var(--learno-r-lg)] bg-white p-6 lg:p-8"
			>
				<div class="mb-6 flex items-center gap-3">
					<router-link
						:to="{
							name: 'StudentCourseDetail',
							params: { courseName: course.course },
							query: { tab: 'materials' },
						}"
						class="text-[16px] font-semibold text-[var(--learno-ink-strong)] hover:text-[var(--learno-primary)]"
					>
						{{ course.course_title }}
					</router-link>
					<span class="learno-rule" aria-hidden="true" />
					<span class="text-[13px] text-[var(--learno-ink-muted)]">
						{{ course.count === 1 ? __('1 file') : `${course.count} ${__('files')}` }}
					</span>
				</div>

				<CourseMaterials :chapters="course.chapters" />
			</section>
		</div>
	</div>
</template>

<script setup lang="ts">
import { createResource, usePageMeta } from 'frappe-ui'
import CourseMaterials from '@/pages/Student/components/CourseMaterials.vue'

usePageMeta(() => ({ title: __('Materials') }))

const shelf = createResource({
	url: 'lms.lms.student_api.get_my_materials',
	auto: true,
})
</script>
