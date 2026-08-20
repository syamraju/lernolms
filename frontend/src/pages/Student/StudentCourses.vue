<!--
	The student course list. Figma: frames 7:2 (grid), 90:4279 (grid + filters
	open) and 122:81352's header.

	Two structural notes on the translation from the design:

	* The three header counts are the *scope* control. The design draws them as
	  cards and the pill row below as tabs; wiring the counts as read-only text
	  and the pills as scopes would have left the counts decorative, so they are
	  the scope selector and the pills select the content type. That keeps every
	  affordance in the design doing something real.
	* The design's Assessments / Projects / Assignments pills have no
	  student-facing list in this LMS — quizzes, assignments and programming
	  exercises are lesson content, reached from inside a session, and their
	  doctype lists are author tools. They are omitted rather than rendered as
	  dead chrome.
-->
<template>
	<div class="flex h-full min-h-0 flex-col">
		<!-- Header ------------------------------------------------------- -->
		<header
			class="flex shrink-0 flex-col gap-[21px] border-b border-[var(--learno-line-soft)] bg-white px-6 py-[22px] lg:px-10"
		>
			<div class="flex flex-wrap items-center gap-4 max-lg:ps-12">
				<h1 class="text-[27px] font-semibold leading-[1.2] text-black">
					{{ __('Courses') }}
				</h1>

				<div class="flex flex-wrap gap-[7px]">
					<button
						v-for="chip in scopeChips"
						:key="chip.value"
						type="button"
						class="learno-count"
						:class="scope === chip.value && 'is-active'"
						:aria-pressed="scope === chip.value"
						@click="setScope(chip.value)"
					>
						<span class="font-semibold" :style="{ color: chip.color }">
							{{ chip.count }}
						</span>
						<span>{{ chip.label }}</span>
					</button>
				</div>
			</div>

			<div class="flex flex-wrap items-center justify-between gap-3">
				<div class="flex flex-wrap items-center gap-1">
					<button
						v-for="type in contentTypes"
						:key="type.value"
						type="button"
						class="learno-pill"
						:aria-pressed="contentType === type.value"
						@click="contentType = type.value"
					>
						{{ type.label }}
					</button>
				</div>

				<div class="flex items-center gap-2.5">
					<label class="relative block w-[322px] max-w-[45vw]">
						<span class="sr-only">{{ __('Search your Course') }}</span>
						<span
							class="lucide-search pointer-events-none absolute start-3.5 top-1/2 size-[21px] -translate-y-1/2 text-[#c2c2c2]"
							aria-hidden="true"
						/>
						<input
							v-model="searchInput"
							type="search"
							class="learno-input ps-[46px]"
							:placeholder="__('Search your Course')"
						/>
					</label>

					<div
						class="flex items-center gap-px rounded-[77px] border border-[var(--learno-line-soft)] bg-[#f6f6f6] p-[3px]"
						role="group"
						:aria-label="__('View')"
					>
						<button
							v-for="mode in ['list', 'grid']"
							:key="mode"
							type="button"
							class="flex h-[30px] w-[33px] items-center justify-center rounded-[45px] transition"
							:class="
								view === mode
									? 'bg-[var(--learno-primary)] text-white'
									: 'text-[#5d5d5d] hover:bg-white'
							"
							:aria-pressed="view === mode"
							:aria-label="mode === 'grid' ? __('Grid view') : __('List view')"
							@click="view = mode"
						>
							<span
								:class="[
									mode === 'grid' ? 'lucide-grid-3x3' : 'lucide-menu',
									'size-[18px]',
								]"
								aria-hidden="true"
							/>
						</button>
					</div>

					<button
						type="button"
						class="rounded-[49px] border p-2 transition"
						:class="
							showFilters
								? 'border-transparent bg-[var(--learno-primary)] text-white'
								: 'border-[#ececec] bg-[var(--learno-canvas-soft)] text-[#5d5d5d] hover:border-[#d8d8d8]'
						"
						:aria-pressed="showFilters"
						:aria-label="__('Filters')"
						@click="showFilters = !showFilters"
					>
						<span class="lucide-filter size-[21px]" aria-hidden="true" />
					</button>
				</div>
			</div>
		</header>

		<!-- Filter drawer. Figma: frame 90:4279's second header row. -->
		<div
			v-if="showFilters"
			class="flex shrink-0 flex-wrap items-end gap-6 border-b border-[var(--learno-line-soft)] bg-white px-6 py-4 lg:px-10"
		>
			<label class="flex flex-col gap-1.5">
				<span class="text-[12px] text-[var(--learno-ink-muted)]">
					{{ __('Subject') }}
				</span>
				<select v-model="category" class="learno-select">
					<option value="">{{ __('All') }}</option>
					<option
						v-for="option in categoryOptions"
						:key="option.value"
						:value="option.value"
					>
						{{ option.label }}
					</option>
				</select>
			</label>

			<label class="flex flex-col gap-1.5">
				<span class="text-[12px] text-[var(--learno-ink-muted)]">
					{{ __('Certification') }}
				</span>
				<select v-model="certification" class="learno-select">
					<option value="">{{ __('All') }}</option>
					<option value="1">{{ __('With certificate') }}</option>
				</select>
			</label>

			<label class="ms-auto flex flex-col gap-1.5">
				<span class="text-[12px] text-[var(--learno-ink-muted)]">
					{{ __('Sort') }}
				</span>
				<select v-model="sort" class="learno-select">
					<option value="enrollments desc">{{ __('Most enrolled') }}</option>
					<option value="published_on desc">{{ __('Newest') }}</option>
					<option value="title asc">{{ __('Title (A–Z)') }}</option>
				</select>
			</label>
		</div>

		<!-- Body ---------------------------------------------------------- -->
		<div
			class="learno-scroll min-h-0 flex-1 overflow-y-auto bg-[var(--learno-canvas)] px-6 py-7 lg:px-10"
		>
			<template v-if="contentType === 'courses'">
				<CourseSection
					v-for="section in sections"
					:key="section.key"
					:title="section.title"
					:count="section.count"
					:courses="section.courses"
					:view="view"
					:enrolling="enrolling"
					@enroll="enroll"
				/>

				<p
					v-if="!loading && !totalShown"
					class="py-16 text-center text-[14px] text-[var(--learno-ink-muted)]"
				>
					{{ __('No courses match this view yet.') }}
				</p>

				<div v-if="loading" class="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
					<div
						v-for="n in 4"
						:key="n"
						class="h-[404px] animate-pulse rounded-[var(--learno-r-lg)] bg-black/5"
					/>
				</div>

				<div v-if="hasMore && !loading" class="mt-8 flex justify-center">
					<button
						type="button"
						class="learno-btn learno-btn-secondary"
						@click="loadMore"
					>
						{{ __('Load more') }}
					</button>
				</div>
			</template>

			<!-- Bundles = LMS Program, the only other student-facing collection -->
			<template v-else>
				<SectionHeading
					:title="__('Learning paths')"
					:count="programs.data?.length || 0"
				/>
				<div class="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
					<router-link
						v-for="program in programs.data || []"
						:key="program.name"
						:to="{
							name: 'ProgramDetail',
							params: { programName: program.name },
						}"
						class="learno-card flex flex-col gap-2 p-5 transition hover:shadow-[var(--learno-shadow)]"
					>
						<span class="learno-tag w-fit bg-[#bedbff] text-[#11279a]">
							{{ __('Bundle') }}
						</span>
						<h3
							class="text-[16px] font-semibold text-[var(--learno-ink-title)]"
						>
							{{ program.title }}
						</h3>
						<p class="text-[12px] text-[var(--learno-ink-muted)]">
							{{
								program.course_count === 1
									? __('1 course')
									: __('{0} courses').format(program.course_count || 0)
							}}
						</p>
					</router-link>
				</div>
				<p
					v-if="programs.data && !programs.data.length"
					class="py-16 text-center text-[14px] text-[var(--learno-ink-muted)]"
				>
					{{ __('No learning paths published yet.') }}
				</p>
			</template>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { call, createListResource, createResource, toast } from 'frappe-ui'
import { usePageMeta } from 'frappe-ui'
import CourseSection from '@/pages/Student/components/CourseSection.vue'
import SectionHeading from '@/pages/Student/components/SectionHeading.vue'

const PAGE_LENGTH = 12

const route = useRoute()
const router = useRouter()

usePageMeta(() => ({ title: __('Courses') }))

const scope = ref<string>((route.query.scope as string) || 'all')
const contentType = ref<'courses' | 'bundles'>('courses')
const view = ref<'grid' | 'list'>('grid')
const showFilters = ref(false)
const searchInput = ref('')
const search = ref('')
const category = ref('')
const certification = ref('')
const sort = ref('enrollments desc')
const start = ref(0)
const courses = ref<any[]>([])
const loading = ref(false)
const enrolling = ref('')

// Typing must not fire a request per keystroke; 300ms is the same debounce the
// admin course list uses.
let searchTimer: ReturnType<typeof setTimeout> | undefined
watch(searchInput, (value) => {
	clearTimeout(searchTimer)
	searchTimer = setTimeout(() => {
		search.value = value.trim()
	}, 300)
})

const summary = createResource({
	url: 'lms.lms.student_api.get_enrollment_summary',
	auto: true,
})

const categories = createResource({
	url: 'lms.lms.utils.get_course_categories',
	auto: true,
})

const categoryOptions = computed(() =>
	(categories.data || []).filter((option: any) => option.value)
)

const programs = createListResource({
	doctype: 'LMS Program',
	fields: ['name', 'title', 'course_count'],
	filters: { published: 1 },
	pageLength: 60,
	auto: true,
})

const scopeChips = computed(() => [
	{
		value: 'pending',
		label: __('Pending'),
		count: summary.data?.pending ?? 0,
		color: 'var(--learno-stat-pending)',
	},
	{
		value: 'enrolled',
		label: __('Courses'),
		count: summary.data?.enrolled ?? 0,
		color: 'var(--learno-stat-total)',
	},
	{
		value: 'completed',
		label: __('Completed'),
		count: summary.data?.completed ?? 0,
		color: 'var(--learno-stat-done)',
	},
])

const contentTypes = [
	{ value: 'courses' as const, label: __('Courses') },
	{ value: 'bundles' as const, label: __('Bundles') },
]

// `pending` and `completed` are progress bands the list endpoint cannot express
// as a filter, so they are fetched as "enrolled" and split client-side. That is
// sound because an enrolled shelf is small and already fully paged in by the
// time a student narrows it; the two bands never hide a course that the
// enrolled scope would have shown.
const serverFilters = computed(() => {
	const filters: Record<string, any> = {}
	if (scope.value !== 'all') filters.enrolled = 1
	if (search.value) filters.title = search.value
	if (category.value) filters.category = category.value
	if (certification.value) filters.certification = 1
	return filters
})

const banded = computed(() => {
	if (scope.value === 'pending') {
		return courses.value.filter((course) => Number(course.progress || 0) < 100)
	}
	if (scope.value === 'completed') {
		return courses.value.filter((course) => Number(course.progress || 0) >= 100)
	}
	return courses.value
})

const SCOPE_TITLES: Record<string, string> = {
	pending: __('In progress'),
	completed: __('Completed'),
	enrolled: __('My courses'),
}

// The design's two "Assigned Courses" bands. On the unfiltered view the shelf
// splits into what the student has started and what is left to explore; a
// narrowed scope is already one band, so it renders as one.
const sections = computed(() => {
	const rows = banded.value
	if (scope.value !== 'all') {
		return [
			{
				key: scope.value,
				title: SCOPE_TITLES[scope.value] || __('Courses'),
				count: rows.length,
				courses: rows,
			},
		]
	}

	const mine = rows.filter((course) => course.membership)
	const rest = rows.filter((course) => !course.membership)
	const out = []
	if (mine.length) {
		out.push({
			key: 'mine',
			title: __('Continue learning'),
			count: mine.length,
			courses: mine,
		})
	}
	if (rest.length) {
		out.push({
			key: 'rest',
			title: mine.length ? __('Explore courses') : __('Assigned Courses'),
			count: rest.length,
			courses: rest,
		})
	}
	return out
})

const totalShown = computed(() => banded.value.length)
const hasMore = ref(false)

async function fetchPage(reset = false) {
	if (reset) {
		start.value = 0
		courses.value = []
	}
	loading.value = true
	try {
		const rows = await call('lms.lms.student_api.get_student_courses', {
			filters: serverFilters.value,
			start: start.value,
			limit_page_length: PAGE_LENGTH,
		})
		const page = Array.isArray(rows) ? rows : []
		courses.value = reset ? page : courses.value.concat(page)
		// A short page is the end of the sequence. The endpoint pages a
		// featured-then-rest list, so a length check is the only reliable signal.
		hasMore.value = page.length === PAGE_LENGTH
		courses.value = sortRows(courses.value)
	} catch (error: any) {
		toast.error(error?.messages?.[0] || __('Could not load courses'))
	} finally {
		loading.value = false
	}
}

function sortRows(rows: any[]) {
	const copy = [...rows]
	if (sort.value === 'title asc') {
		return copy.sort((a, b) => String(a.title).localeCompare(String(b.title)))
	}
	if (sort.value === 'published_on desc') {
		return copy.sort(
			(a, b) =>
				new Date(b.published_on || 0).getTime() -
				new Date(a.published_on || 0).getTime()
		)
	}
	return copy.sort(
		(a, b) => Number(b.enrollments || 0) - Number(a.enrollments || 0)
	)
}

function loadMore() {
	start.value += PAGE_LENGTH
	fetchPage(false)
}

function setScope(next: string) {
	scope.value = scope.value === next ? 'all' : next
	// The scope is worth a shareable URL, and it is what a back button should
	// restore. Nothing else in this header is.
	router.replace({
		query: {
			...route.query,
			scope: scope.value === 'all' ? undefined : scope.value,
		},
	})
}

async function enroll(course: any) {
	enrolling.value = course.name
	try {
		const membership = await call('lms.lms.student_api.enroll', {
			course: course.name,
		})
		// Patch in place rather than refetching the page: a refetch would reorder
		// and repage the list under the cursor that just clicked.
		const row = courses.value.find((item) => item.name === course.name)
		if (row) {
			row.membership = membership
			row.progress = Number(membership?.progress || 0)
			row.enrollments = Number(row.enrollments || 0) + 1
		}
		summary.reload()
		toast.success(__('Enrolled in {0}').format(course.title))
	} catch (error: any) {
		toast.error(error?.messages?.[0] || __('Could not enroll'))
	} finally {
		enrolling.value = ''
	}
}

watch(
	[scope, search, category, certification],
	() => {
		if (contentType.value === 'courses') fetchPage(true)
	},
	{ immediate: true }
)

watch(sort, () => {
	courses.value = sortRows(courses.value)
})

watch(contentType, (value) => {
	if (value === 'courses' && !courses.value.length) fetchPage(true)
})
</script>

<style scoped>
.learno-count {
	display: inline-flex;
	align-items: center;
	gap: 9px;
	border-radius: var(--learno-r-sm);
	border: 1px solid var(--learno-line-hair);
	background: #fff;
	padding: 5px 17px;
	font-size: 16px;
	line-height: 1.2;
	color: #000;
	transition: border-color 120ms ease, box-shadow 120ms ease;
}

.learno-count:hover {
	border-color: rgba(0, 0, 0, 0.18);
}

.learno-count.is-active {
	border-color: var(--learno-primary);
	box-shadow: 0 0 0 1px var(--learno-primary);
}

.learno-select {
	min-width: 190px;
	border-radius: var(--learno-r-sm);
	border: 1px solid var(--learno-line-hair);
	background: #fff;
	padding: 8px 12px;
	font-size: 14px;
	color: var(--learno-ink);
}

.learno-select:focus {
	outline: none;
	border-color: var(--learno-primary);
}
</style>
