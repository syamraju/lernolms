<!--
	Session player. Figma: frames 122:81352 (Download tab) and 122:84557.

	Layout: a breadcrumb bar, a collapsible outline rail, then the lesson —
	player, title, "Mark as Complete", and a Notes / Download tab pair over the
	authored content.

	Locked lessons are not a client concern to enforce, only to reflect:
	`get_lesson` already returns `{locked: 1, redirect_to}` for a gated lesson, so
	this page follows that redirect rather than deciding for itself what the
	student may open.
-->
<template>
	<div class="flex h-full min-h-0 flex-col">
		<!-- Breadcrumb -->
		<nav
			class="flex shrink-0 items-center gap-2 border-b border-[var(--learno-line-soft)] bg-white px-6 py-[18px] text-[14px] lg:px-10"
			:aria-label="__('Breadcrumb')"
		>
			<router-link
				:to="{ name: 'StudentDashboard' }"
				class="flex items-center gap-1.5 text-[var(--learno-ink-muted)] hover:text-[var(--learno-ink)] max-lg:ms-12"
			>
				<span class="lucide-house size-4" aria-hidden="true" />
				{{ __('Home') }}
			</router-link>
			<span class="lucide-chevron-right size-4 text-[#c2c2c2] rtl:rotate-180" />
			<router-link
				:to="{ name: 'StudentCourseDetail', params: { courseName } }"
				class="truncate text-[var(--learno-ink-muted)] hover:text-[var(--learno-ink)]"
			>
				{{ lesson.data?.course_title || courseName }}
			</router-link>
			<span class="lucide-chevron-right size-4 text-[#c2c2c2] rtl:rotate-180" />
			<span class="text-[var(--learno-primary)]">{{ __('Sessions') }}</span>
		</nav>

		<div class="flex min-h-0 flex-1">
			<!-- Outline rail -->
			<div
				class="learno-scroll shrink-0 overflow-y-auto border-e border-[var(--learno-line-soft)] bg-white transition-[width]"
				:class="railOpen ? 'w-[260px]' : 'w-[52px]'"
			>
				<button
					type="button"
					class="flex w-full items-center gap-2 border-b border-[var(--learno-line-soft)] px-4 py-3 text-[12px] text-[var(--learno-ink)]"
					:aria-expanded="railOpen"
					@click="railOpen = !railOpen"
				>
					<span
						class="lucide-panel-left size-4 shrink-0"
						aria-hidden="true"
					/>
					<span v-if="railOpen">{{ __('Hide Sessions') }}</span>
				</button>

				<div v-if="railOpen" class="p-3">
					<p
						class="mb-2 px-1 text-[11px] font-semibold uppercase tracking-wide text-[var(--learno-ink-subtle)]"
					>
						{{ __('Sessions') }}
					</p>

					<div
						v-for="chapter in outline.data || []"
						:key="chapter.name"
						class="mb-4"
					>
						<p
							class="mb-1.5 flex items-center gap-1.5 px-1 text-[12px] font-semibold text-[var(--learno-ink-strong)]"
						>
							<span
								class="lucide-square-minus size-3.5 text-[#1cb0f6]"
								aria-hidden="true"
							/>
							{{ chapter.title }}
						</p>

						<ul class="flex flex-col">
							<li v-for="item in chapter.lessons || []" :key="item.name">
								<component
									:is="item.locked ? 'div' : 'router-link'"
									:to="
										item.locked
											? undefined
											: {
													name: 'StudentSession',
													params: {
														courseName,
														chapterNumber: String(item.number).split('-')[0],
														lessonNumber: String(item.number).split('-')[1],
													},
												}
									"
									class="flex flex-col gap-1 rounded-e-[6px] border-s-2 px-3 py-2 transition"
									:class="rowClass(item)"
								>
									<span class="flex items-center gap-1.5">
										<span
											:class="[
												item.locked
													? 'lucide-lock'
													: item.is_complete
														? 'lucide-circle-check-big'
														: 'lucide-circle',
												'size-3 shrink-0',
											]"
											aria-hidden="true"
										/>
										<span class="text-[9px] uppercase tracking-wide">
											{{ item.number }}
										</span>
									</span>
									<span class="learno-clamp-2 text-[11px] leading-[1.35]">
										{{ item.title }}
									</span>
								</component>
							</li>
						</ul>
					</div>
				</div>
			</div>

			<!-- Lesson -->
			<div
				class="learno-scroll min-w-0 flex-1 overflow-y-auto bg-[var(--learno-canvas)]"
			>
				<div v-if="lesson.loading && !lesson.data" class="p-8">
					<div class="h-[420px] animate-pulse rounded-[var(--learno-r-lg)] bg-black/5" />
				</div>

				<div
					v-else-if="lesson.data?.no_preview"
					class="flex flex-col items-center gap-4 px-6 py-24 text-center"
				>
					<span
						class="lucide-lock size-8 text-[var(--learno-ink-subtle)]"
						aria-hidden="true"
					/>
					<p class="text-[15px] font-semibold">
						{{ __('Enroll to open this session') }}
					</p>
					<router-link
						:to="{ name: 'StudentCourseDetail', params: { courseName } }"
						class="learno-btn learno-btn-primary px-5 py-2.5 text-[13px]"
					>
						{{ __('Go to course') }}
					</router-link>
				</div>

				<div v-else-if="lesson.data" class="px-6 py-6 lg:px-10">
					<div
						class="mb-5 flex items-center justify-between gap-4 text-[12px] text-[var(--learno-ink-muted)]"
					>
						<span class="flex min-w-0 items-center gap-2">
							<span class="truncate">{{ lesson.data.chapter_title }}</span>
							<span class="lucide-chevron-right size-3.5 rtl:rotate-180" />
							<span class="truncate text-[var(--learno-primary)]">
								{{ lesson.data.title }}
							</span>
						</span>
						<a
							href="mailto:?subject=Issue%20with%20a%20session"
							class="shrink-0 text-[var(--learno-primary)] hover:underline"
						>
							{{ __('Report Issue') }}
						</a>
					</div>

					<!-- Hero player, when the lesson has a video of its own. Lessons
					     whose video lives inside a content block get it rendered in
					     place by LessonBody instead, so this stays empty for them. -->
					<div
						v-if="heroYoutubeId"
						class="mb-6 overflow-hidden rounded-[var(--learno-r-md)] bg-black"
					>
						<div
							class="video-player aspect-video w-full"
							data-plyr-provider="youtube"
							:data-plyr-embed-id="heroYoutubeId"
						/>
					</div>

					<div class="mb-5 flex flex-wrap items-center justify-between gap-4">
						<h1
							class="text-[24px] font-semibold text-[var(--learno-primary)]"
						>
							{{ lesson.data.title }}
						</h1>

						<button
							v-if="canComplete"
							type="button"
							class="learno-btn learno-btn-primary px-5 py-2.5 text-[13px]"
							:disabled="completing || isComplete"
							@click="markComplete"
						>
							<span
								:class="[
									completing
										? 'lucide-loader-circle animate-spin'
										: 'lucide-check',
									'size-4',
								]"
								aria-hidden="true"
							/>
							{{ isComplete ? __('Completed') : __('Mark as Complete') }}
						</button>
					</div>

					<!-- Notes / Download -->
					<div class="mb-6 flex items-center gap-1" role="tablist">
						<button
							v-for="item in panels"
							:key="item.value"
							type="button"
							role="tab"
							class="learno-tab flex items-center gap-2"
							:aria-selected="panel === item.value"
							@click="panel = item.value"
						>
							<span :class="[item.icon, 'size-4']" aria-hidden="true" />
							{{ item.label }}
						</button>
					</div>

					<div
						v-if="panel === 'downloads'"
						class="mb-8 rounded-[var(--learno-r-md)] bg-white p-5"
					>
						<CourseMaterials
							:chapters="lessonMaterials"
							:loading="materials.loading"
						/>
					</div>

					<div
						v-else-if="panel === 'notes'"
						class="mb-8 rounded-[var(--learno-r-md)] bg-white p-5"
					>
						<ul v-if="notes.data?.length" class="flex flex-col gap-3">
							<li
								v-for="note in notes.data"
								:key="note.name"
								class="rounded-[var(--learno-r-sm)] border-s-2 border-[var(--learno-primary)] bg-[var(--learno-canvas)] px-4 py-3"
							>
								<p
									v-if="note.highlighted_text"
									class="mb-1 text-[11px] italic text-[var(--learno-ink-subtle)]"
								>
									“{{ note.highlighted_text }}”
								</p>
								<p class="text-[13px] text-[var(--learno-ink)]">
									{{ note.note }}
								</p>
							</li>
						</ul>
						<p v-else class="text-[13px] text-[var(--learno-ink-muted)]">
							{{ __('You have not taken any notes on this session yet.') }}
						</p>
					</div>

					<!-- Content -->
					<div class="rounded-[var(--learno-r-md)] bg-white p-6 lg:p-8">
						<LessonBody :key="lesson.data.name" :lesson="lesson.data" />
					</div>

					<!-- Prev / next -->
					<div class="mt-6 flex items-center justify-between gap-4">
						<button
							type="button"
							class="learno-btn learno-btn-secondary px-5 py-2.5 text-[13px]"
							:disabled="!lesson.data.prev"
							@click="go(lesson.data.prev)"
						>
							<span class="lucide-arrow-left size-4 rtl:rotate-180" />
							{{ __('Previous') }}
						</button>
						<button
							type="button"
							class="learno-btn learno-btn-primary px-5 py-2.5 text-[13px]"
							:disabled="!lesson.data.next"
							@click="go(lesson.data.next)"
						>
							{{ __('Next session') }}
							<span class="lucide-arrow-right size-4 rtl:rotate-180" />
						</button>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, inject, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { createListResource, createResource, toast, usePageMeta } from 'frappe-ui'
import { extractYoutubeID } from '@/utils/lessonMacros'
import LessonBody from '@/pages/Student/components/LessonBody.vue'
import CourseMaterials from '@/pages/Student/components/CourseMaterials.vue'

const route = useRoute()
const router = useRouter()
const userResource = inject<any>('$user')

const courseName = computed(() => String(route.params.courseName))
const chapterNumber = computed(() => String(route.params.chapterNumber))
const lessonNumber = computed(() => String(route.params.lessonNumber))

const railOpen = ref(true)
const panel = ref<'notes' | 'downloads'>('downloads')
const completing = ref(false)

const panels = computed(() => [
	{ value: 'notes' as const, label: __('Notes'), icon: 'lucide-sticky-note' },
	{
		value: 'downloads' as const,
		label: __('Download'),
		icon: 'lucide-download',
	},
])

const lesson = createResource({
	url: 'lms.lms.utils.get_lesson',
	makeParams: () => ({
		course: courseName.value,
		chapter: chapterNumber.value,
		lesson: lessonNumber.value,
	}),
	auto: true,
	onSuccess(data: any) {
		// The gate answers with a redirect rather than the lesson when the
		// requested one is locked. Following it here keeps every entry point
		// (deep link, outline click, next button) honest with one rule.
		if (data?.locked && data.redirect_to) {
			const [chapter, item] = String(data.redirect_to).split('-')
			router.replace({
				name: 'StudentSession',
				params: {
					courseName: courseName.value,
					chapterNumber: chapter,
					lessonNumber: item,
				},
			})
		}
	},
})

const outline = createResource({
	url: 'lms.lms.utils.get_course_outline',
	makeParams: () => ({ course: courseName.value, progress: true }),
	auto: true,
})

const materials = createResource({
	url: 'lms.lms.student_api.get_course_materials',
	makeParams: () => ({ course: courseName.value }),
	auto: true,
})

const notes = createListResource({
	doctype: 'LMS Lesson Note',
	fields: ['name', 'color', 'highlighted_text', 'note'],
	filters: computed(() => ({
		lesson: lesson.data?.name,
		member: userResource?.data?.name,
	})) as any,
})

usePageMeta(() => ({ title: lesson.data?.title || __('Session') }))

watch(
	() => [courseName.value, chapterNumber.value, lessonNumber.value].join('/'),
	() => {
		lesson.reload()
	}
)

// The notes list filters on a lesson name that only exists after the lesson
// resource resolves, so it is fetched on that edge rather than `auto`.
watch(
	() => lesson.data?.name,
	(name) => {
		if (name && userResource?.data?.name) notes.reload()
	}
)

const heroYoutubeId = computed(() =>
	lesson.data?.youtube ? extractYoutubeID(lesson.data.youtube) : ''
)

const isComplete = computed(() => Boolean(lesson.data?.progress))

// Only a member records progress. A moderator previewing has no enrollment row,
// so save_progress would no-op server-side while the button showed success.
const canComplete = computed(() => Boolean(lesson.data?.membership))

// The Download tab shows this lesson's files, not the whole course's, so the
// course-wide payload is narrowed here rather than fetched twice.
const lessonMaterials = computed(() => {
	const name = lesson.data?.name
	if (!name) return []
	return (materials.data || [])
		.map((chapter: any) => ({
			...chapter,
			files: (chapter.files || []).filter((file: any) => file.lesson === name),
		}))
		.filter((chapter: any) => chapter.files.length)
})

const progress = createResource({
	url: 'lms.lms.doctype.course_lesson.course_lesson.save_progress',
	onSuccess() {
		lesson.reload()
		outline.reload()
	},
})

async function markComplete() {
	if (completing.value || isComplete.value) return
	completing.value = true
	try {
		await progress.submit({
			lesson: lesson.data.name,
			course: courseName.value,
		})
		toast.success(__('Marked as complete'))
	} catch (error: any) {
		toast.error(error?.messages?.[0] || __('Could not save your progress'))
	} finally {
		completing.value = false
	}
}

function go(index?: string) {
	if (!index) return
	const [chapter, item] = String(index).split('-')
	router.push({
		name: 'StudentSession',
		params: {
			courseName: courseName.value,
			chapterNumber: chapter,
			lessonNumber: item,
		},
	})
}

function rowClass(item: any) {
	const active =
		String(item.number) === `${chapterNumber.value}-${lessonNumber.value}`
	if (active) {
		return 'border-[var(--learno-primary)] bg-[var(--learno-primary-soft)] text-[var(--learno-primary)] font-semibold'
	}
	if (item.locked) {
		return 'border-transparent text-[var(--learno-ink-subtle)] cursor-not-allowed'
	}
	return 'border-transparent text-[var(--learno-ink)] hover:bg-[var(--learno-canvas)]'
}
</script>
