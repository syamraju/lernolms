<!--
	Course detail. Figma: frames 90:5108 (About), 99:9366 (Certificate),
	100:9718 (Sessions), 112:11071 (Materials).

	The four tabs are query-driven (`?tab=sessions`) rather than local state so
	the card's "Continue" can deep-link into Sessions and so a reload keeps the
	tab. The three data sources behind them load lazily — a student who only
	reads About never pays for the materials scan.
-->
<template>
	<div class="learno-scroll flex h-full min-h-0 flex-col overflow-y-auto">
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
				:to="{ name: 'StudentCourses' }"
				class="text-[var(--learno-ink-muted)] hover:text-[var(--learno-ink)]"
			>
				{{ __('Courses') }}
			</router-link>
			<span class="lucide-chevron-right size-4 text-[#c2c2c2] rtl:rotate-180" />
			<span class="truncate text-[var(--learno-primary)]">
				{{ course.data?.title || courseName }}
			</span>
		</nav>

		<div class="flex-1 bg-[var(--learno-canvas)] p-3 lg:p-4">
			<template v-if="course.data?.name">
				<!-- Hero -->
				<section
					class="flex flex-col overflow-hidden rounded-[var(--learno-r-lg)] bg-[#eff6ff] lg:flex-row"
				>
					<div class="flex flex-1 flex-col gap-4 p-6 lg:p-8">
						<span
							v-if="organisation"
							class="flex w-fit items-center gap-1.5 text-[14px] font-semibold text-[var(--learno-ink-strong)]"
						>
							<LearnoMark
								class="size-5 text-[var(--learno-primary)]"
								label=""
							/>
							{{ organisation }}
						</span>

						<h1
							class="text-[28px] font-semibold leading-[1.2] text-[var(--learno-ink-strong)]"
						>
							{{ course.data.title }}
						</h1>

						<p
							v-if="course.data.short_introduction"
							class="learno-clamp-3 max-w-[52ch] text-[12px] leading-[1.6] text-[var(--learno-ink-muted)]"
						>
							{{ course.data.short_introduction }}
						</p>

						<div v-if="course.data.instructors?.length" class="flex flex-col gap-1.5">
							<span
								class="text-[11px] font-semibold text-[var(--learno-ink-strong)]"
							>
								{{ __('Instructors') }}
							</span>
							<div class="flex flex-wrap gap-2 rounded-[var(--learno-r-md)] bg-white/70 p-2">
								<span
									v-for="person in course.data.instructors"
									:key="person.name"
									class="flex items-center gap-2 pe-3"
								>
									<img
										v-if="person.user_image"
										:src="safeUrl(person.user_image)"
										alt=""
										class="size-8 rounded-full object-cover"
									/>
									<span
										v-else
										class="grid size-8 place-items-center rounded-full bg-[var(--learno-primary-soft)] text-[11px] font-semibold text-[var(--learno-primary)]"
									>
										{{ (person.full_name || '?').charAt(0) }}
									</span>
									<span class="flex flex-col leading-tight">
										<span class="text-[12px] font-medium">
											{{ person.full_name }}
										</span>
										<span
											v-if="person.bio"
											class="max-w-[18ch] truncate text-[9px] text-[var(--learno-ink-muted)]"
										>
											{{ person.bio }}
										</span>
									</span>
								</span>
							</div>
						</div>

						<div class="mt-2 flex flex-wrap items-center gap-5">
							<button
								type="button"
								class="learno-btn learno-btn-primary px-6 py-2.5 text-[14px]"
								:disabled="busy"
								@click="startOrEnroll"
							>
								<span
									:class="[
										busy ? 'lucide-loader-circle animate-spin' : 'lucide-plus',
										'size-4',
									]"
									aria-hidden="true"
								/>
								{{ primaryLabel }}
							</button>

							<span class="flex items-center gap-1.5 text-[12px] text-[var(--learno-ink-muted)]">
								<span class="size-2 rounded-full bg-[#1cb0f6]" />
								{{ chapterCount }} {{ __('Chapters') }}
							</span>
							<span class="flex items-center gap-1.5 text-[12px] text-[var(--learno-ink-muted)]">
								<span class="size-2 rounded-full bg-[#ff9600]" />
								{{ course.data.lessons || 0 }} {{ __('Sessions') }}
							</span>
							<span class="flex items-center gap-1.5 text-[12px] text-[var(--learno-ink-muted)]">
								<span class="lucide-users size-3.5" aria-hidden="true" />
								{{ course.data.enrollments || 0 }} {{ __('Enrolments') }}
							</span>
						</div>
					</div>

					<div class="relative w-full shrink-0 lg:w-[46%]">
						<img
							v-if="course.data.image"
							:src="safeUrl(course.data.image)"
							alt=""
							class="size-full min-h-[220px] object-cover"
						/>
						<div
							v-else
							class="grid size-full min-h-[220px] place-items-center bg-[var(--learno-primary-soft)] text-[var(--learno-primary)]"
						>
							<LearnoMark class="size-16" label="" />
						</div>
					</div>
				</section>

				<!-- Stat strip -->
				<section
					class="mt-1 grid grid-cols-2 gap-6 rounded-[var(--learno-r-lg)] bg-[#fff1f1] px-6 py-6 lg:grid-cols-4 lg:px-10"
				>
					<div v-for="stat in stats" :key="stat.label" class="flex flex-col gap-1">
						<span class="text-[20px] font-semibold text-[#900303]">
							{{ stat.value }}
						</span>
						<span class="text-[11px] text-[var(--learno-ink-muted)]">
							{{ stat.label }}
						</span>
					</div>
				</section>

				<!-- Progress, for members only -->
				<div
					v-if="course.data.membership"
					class="mt-3 flex items-center gap-3 px-2"
				>
					<div class="h-1.5 flex-1 overflow-hidden rounded-full bg-black/5">
						<div
							class="h-full rounded-full bg-[var(--learno-primary)] transition-[width]"
							:style="{ width: `${progressPct}%` }"
						/>
					</div>
					<span class="text-[12px] text-[var(--learno-ink-muted)]">
						{{ progressPct }}% {{ __('complete') }}
					</span>
				</div>

				<!-- Tabs -->
				<div class="my-4 flex justify-center gap-1" role="tablist">
					<button
						v-for="item in tabs"
						:key="item.value"
						type="button"
						role="tab"
						class="learno-tab"
						:aria-selected="tab === item.value"
						@click="selectTab(item.value)"
					>
						{{ item.label }}
					</button>
				</div>

				<!-- Panels -->
				<section
					class="rounded-[var(--learno-r-lg)] bg-white p-6 lg:p-9"
					role="tabpanel"
				>
					<CourseAbout
						v-if="tab === 'about'"
						:course="course.data"
						:outline="outline.data || []"
					/>
					<CourseCertificate v-else-if="tab === 'certificate'" :course="course.data" />
					<CourseSessions
						v-else-if="tab === 'sessions'"
						:course-name="courseName"
						:outline="outline.data || []"
						:loading="outline.loading"
						:is-member="Boolean(course.data.membership)"
					/>
					<CourseMaterials
						v-else
						:chapters="materials.data || []"
						:loading="materials.loading"
					/>
				</section>
			</template>

			<div
				v-else-if="course.loading"
				class="h-[420px] animate-pulse rounded-[var(--learno-r-lg)] bg-black/5"
			/>

			<p v-else class="py-24 text-center text-[14px] text-[var(--learno-ink-muted)]">
				{{ __('This course is not available.') }}
			</p>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { call, createResource, toast, usePageMeta } from 'frappe-ui'
import LearnoMark from '@/components/Learno/LearnoMark.vue'
import CourseAbout from '@/pages/Student/components/CourseAbout.vue'
import CourseCertificate from '@/pages/Student/components/CourseCertificate.vue'
import CourseSessions from '@/pages/Student/components/CourseSessions.vue'
import CourseMaterials from '@/pages/Student/components/CourseMaterials.vue'
import { safeUrl } from '@/utils/safeUrl'

const route = useRoute()
const router = useRouter()

const courseName = computed(() => String(route.params.courseName))
const busy = ref(false)

const TAB_VALUES = ['about', 'certificate', 'sessions', 'materials'] as const
type Tab = (typeof TAB_VALUES)[number]

const tab = computed<Tab>(() => {
	const requested = String(route.query.tab || 'about') as Tab
	return TAB_VALUES.includes(requested) ? requested : 'about'
})

const tabs = computed(() => [
	{ value: 'about', label: __('About') },
	{ value: 'certificate', label: __('Certificate') },
	{ value: 'sessions', label: __('Sessions') },
	{ value: 'materials', label: __('Materials') },
])

const course = createResource({
	url: 'lms.lms.utils.get_course_details',
	makeParams: () => ({ course: courseName.value }),
	auto: true,
})

// `progress: true` is what marks lessons complete and applies the lock gate, so
// the outline the student sees matches what the player will let them open.
const outline = createResource({
	url: 'lms.lms.utils.get_course_outline',
	makeParams: () => ({ course: courseName.value, progress: true }),
	auto: true,
})

// Lazy: the materials scan walks every lesson's content, so it only runs once
// the student actually opens that tab.
const materials = createResource({
	url: 'lms.lms.student_api.get_course_materials',
	makeParams: () => ({ course: courseName.value }),
})

usePageMeta(() => ({ title: course.data?.title || __('Course') }))

watch(
	courseName,
	() => {
		course.reload()
		outline.reload()
		materials.reset()
		if (tab.value === 'materials') materials.reload()
	},
	{ flush: 'post' }
)

watch(tab, (value) => {
	if (value === 'materials' && !materials.data && !materials.loading) {
		materials.reload()
	}
})

const organisation = computed(() => {
	const instructor = course.data?.instructors?.[0]
	return instructor?.full_name || ''
})

const chapterCount = computed(() => outline.data?.length || 0)

const progressPct = computed(() =>
	Math.min(100, Math.round(Number(course.data?.membership?.progress || 0)))
)

const stats = computed(() => [
	{ value: `${chapterCount.value}`, label: __('Chapters in your path') },
	{
		value: `${course.data?.lessons || 0}`,
		label: __('Sessions to unlock'),
	},
	{
		value: course.data?.category || __('General'),
		label: __('Subject'),
	},
	{
		value: certificateEnabled.value ? __('Certificate') : __('No certificate'),
		label: certificateEnabled.value
			? __('from the organisation')
			: __('not offered for this course'),
	},
])

const certificateEnabled = computed(() =>
	Boolean(
		course.data?.enable_certification || course.data?.paid_certificate
	)
)

const primaryLabel = computed(() => {
	if (!course.data?.membership) return __('Enroll now')
	return progressPct.value > 0 ? __('Continue') : __('Start now')
})

function selectTab(value: string) {
	router.replace({ query: { ...route.query, tab: value } })
}

// One button, two jobs, because the design has one button: enrol if needed,
// then open the lesson the server says to resume at. `current_lesson` on the
// detail payload is already the chapter-lesson index (and already gate-checked),
// unlike the raw docname the list endpoint returns.
async function startOrEnroll() {
	busy.value = true
	try {
		if (!course.data?.membership) {
			await call('lms.lms.student_api.enroll', { course: courseName.value })
			await course.reload()
			await outline.reload()
			toast.success(__('Enrolled in {0}').format(course.data?.title || ''))
		}
		openResume()
	} catch (error: any) {
		toast.error(error?.messages?.[0] || __('Could not start this course'))
	} finally {
		busy.value = false
	}
}

function openResume() {
	const index = String(course.data?.current_lesson || '1-1')
	const [chapterNumber, lessonNumber] = index.split('-')
	router.push({
		name: 'StudentSession',
		params: {
			courseName: courseName.value,
			chapterNumber: chapterNumber || '1',
			lessonNumber: lessonNumber || '1',
		},
	})
}
</script>
