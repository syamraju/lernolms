<!--
	Dashboard. The sidebar in the Figma has a Dashboard row but the file has no
	dashboard frame, so this is built from the design's own vocabulary — the
	count chips from the courses header, the course card, and the cream canvas —
	rather than invented chrome.

	Everything on it is the student's real state: their shelf, their next live
	sessions, their streak.
-->
<template>
	<div class="learno-scroll flex h-full min-h-0 flex-col overflow-y-auto">
		<header
			class="shrink-0 border-b border-[var(--learno-line-soft)] bg-white px-6 py-[22px] lg:px-10"
		>
			<p class="text-[14px] text-[var(--learno-ink-muted)] max-lg:ps-12">
				{{ greeting }}
			</p>
			<h1 class="mt-1 text-[27px] font-semibold leading-[1.2] text-black">
				{{ user?.full_name || __('Welcome back') }}
			</h1>
		</header>

		<div class="flex-1 bg-[var(--learno-canvas)] px-6 py-7 lg:px-10">
			<!-- Counters -->
			<div class="mb-9 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
				<router-link
					v-for="tile in tiles"
					:key="tile.label"
					:to="tile.to"
					class="learno-card flex flex-col gap-1 p-5 transition hover:shadow-[var(--learno-shadow)]"
				>
					<span class="text-[26px] font-semibold" :style="{ color: tile.color }">
						{{ tile.value }}
					</span>
					<span class="text-[12px] text-[var(--learno-ink-muted)]">
						{{ tile.label }}
					</span>
				</router-link>
			</div>

			<!-- Continue learning -->
			<section v-if="inProgress.length" class="mb-10">
				<SectionHeading
					:title="__('Continue learning')"
					:count="inProgress.length"
				/>
				<div class="grid gap-5 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
					<LearnoCourseCard
						v-for="course in inProgress"
						:key="course.name"
						:course="course"
					/>
				</div>
			</section>

			<!-- Upcoming -->
			<section v-if="upcoming.length" class="mb-10">
				<SectionHeading :title="__('Coming up')" :count="upcoming.length" />
				<ul class="grid gap-4 lg:grid-cols-2 2xl:grid-cols-3">
					<li
						v-for="event in upcoming"
						:key="`${event.kind}-${event.context}-${event.date}-${event.title}`"
						class="learno-card flex items-start gap-4 p-5"
					>
						<span
							class="grid size-10 shrink-0 place-items-center rounded-full"
							:style="kindStyle(event.kind)"
						>
							<span :class="[kindIcon(event.kind), 'size-4']" aria-hidden="true" />
						</span>
						<div class="flex min-w-0 flex-1 flex-col gap-1">
							<span
								class="truncate text-[14px] font-semibold text-[var(--learno-ink-strong)]"
							>
								{{ event.title }}
							</span>
							<span class="text-[11px] text-[var(--learno-ink-muted)]">
								{{ formatWhen(event) }}
							</span>
						</div>
						<a
							v-if="event.url"
							:href="safeUrl(event.url)"
							class="learno-btn learno-btn-primary shrink-0"
							v-external
						>
							{{ __('Join') }}
						</a>
					</li>
				</ul>
			</section>

			<p
				v-if="!loading && !inProgress.length && !upcoming.length"
				class="py-16 text-center text-[14px] text-[var(--learno-ink-muted)]"
			>
				{{ __('Nothing on your shelf yet.') }}
				<router-link
					:to="{ name: 'StudentCourses' }"
					class="text-[var(--learno-primary)] underline"
				>
					{{ __('Browse courses') }}
				</router-link>
			</p>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, inject, ref, onMounted } from 'vue'
import { call, createResource, usePageMeta } from 'frappe-ui'
import SectionHeading from '@/pages/Student/components/SectionHeading.vue'
import LearnoCourseCard from '@/components/Learno/LearnoCourseCard.vue'
import { safeUrl } from '@/utils/safeUrl'

const dayjs = inject<any>('$dayjs')
const userResource = inject<any>('$user')

usePageMeta(() => ({ title: __('Dashboard') }))

const user = computed(() => userResource?.data)
const courses = ref<any[]>([])
const loading = ref(true)

const summary = createResource({
	url: 'lms.lms.student_api.get_enrollment_summary',
	auto: true,
})

const streak = createResource({
	url: 'lms.lms.api.get_streak_info',
	auto: true,
})

// A fortnight ahead: far enough that a weekly cohort always shows something,
// short enough that the list stays a to-do rather than a calendar.
const events = createResource({
	url: 'lms.lms.student_api.get_calendar_events',
	makeParams: () => ({
		start: dayjs().format('YYYY-MM-DD'),
		end: dayjs().add(14, 'day').format('YYYY-MM-DD'),
	}),
	auto: true,
})

onMounted(async () => {
	try {
		const rows = await call('lms.lms.student_api.get_student_courses', {
			filters: { enrolled: 1 },
			limit_page_length: 12,
		})
		courses.value = Array.isArray(rows) ? rows : []
	} finally {
		loading.value = false
	}
})

const greeting = computed(() => {
	const hour = Number(dayjs().format('H'))
	if (hour < 12) return __('Good morning')
	if (hour < 18) return __('Good afternoon')
	return __('Good evening')
})

const inProgress = computed(() =>
	courses.value.filter((course) => Number(course.progress || 0) < 100).slice(0, 8)
)

const upcoming = computed(() => (events.data || []).slice(0, 6))

const tiles = computed(() => [
	{
		label: __('Courses in progress'),
		value: summary.data?.pending ?? 0,
		color: 'var(--learno-stat-pending)',
		to: { name: 'StudentCourses', query: { scope: 'pending' } },
	},
	{
		label: __('Courses enrolled'),
		value: summary.data?.enrolled ?? 0,
		color: 'var(--learno-stat-total)',
		to: { name: 'StudentCourses', query: { scope: 'enrolled' } },
	},
	{
		label: __('Courses completed'),
		value: summary.data?.completed ?? 0,
		color: 'var(--learno-stat-done)',
		to: { name: 'StudentCourses', query: { scope: 'completed' } },
	},
	{
		label: __('Day streak'),
		value: streak.data?.current_streak ?? 0,
		color: 'var(--learno-primary)',
		to: { name: 'StudentCalendar' },
	},
])

const KIND_STYLE: Record<string, { bg: string; fg: string }> = {
	live_class: { bg: '#ddf4ff', fg: '#2b70c9' },
	evaluation: { bg: '#fff1f1', fg: '#ea2b2b' },
	batch_start: { bg: '#dcfce7', fg: '#166534' },
}

function kindStyle(kind: string) {
	const style = KIND_STYLE[kind] || KIND_STYLE.batch_start
	return { backgroundColor: style.bg, color: style.fg }
}

function kindIcon(kind: string) {
	if (kind === 'live_class') return 'lucide-video'
	if (kind === 'evaluation') return 'lucide-clipboard-check'
	return 'lucide-flag'
}

function formatWhen(event: any) {
	const date = dayjs(event.date).format('DD MMM YYYY')
	if (!event.time) return date
	// `time` is a Frappe Time (HH:mm:ss); dayjs needs a date to parse it against.
	const at = dayjs(`${event.date}T${event.time}`)
	return at.isValid() ? `${date} · ${at.format('h:mm A')}` : date
}
</script>
