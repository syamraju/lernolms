<!--
	Calendar. Figma: frame 136:88179 — a mini month picker and a legend on the
	left, a week grid on the right with Week / Today / prev / next controls.

	The design's "+ Add New" and "Book Appointments" are author actions (only an
	evaluator or a moderator creates anything on a student's calendar), so the
	student view is read-only and those two buttons are not rendered. Everything
	on the grid comes from `get_calendar_events`.
-->
<template>
	<div class="flex h-full min-h-0 flex-col">
		<header
			class="flex shrink-0 items-center gap-4 border-b border-[var(--learno-line-soft)] bg-white px-6 py-[22px] lg:px-10"
		>
			<h1 class="text-[27px] font-semibold leading-[1.2] text-black max-lg:ps-12">
				{{ __('Calendar') }}
			</h1>
		</header>

		<div class="flex min-h-0 flex-1">
			<!-- Rail -->
			<aside
				class="learno-scroll hidden w-[240px] shrink-0 overflow-y-auto border-e border-[var(--learno-line-soft)] bg-white p-4 lg:block"
			>
				<MiniMonth v-model="cursor" :marked="markedDates" />

				<div class="mt-6 flex flex-col gap-4">
					<div v-for="group in legend" :key="group.kind" class="flex flex-col gap-1.5">
						<span class="flex items-center gap-2 text-[12px]">
							<span
								class="size-2.5 rounded-[3px]"
								:style="{ backgroundColor: group.color }"
							/>
							{{ group.label }}
						</span>
						<span class="ps-[18px] text-[11px] text-[var(--learno-ink-subtle)]">
							{{ group.count }} {{ __('this week') }}
						</span>
					</div>
				</div>
			</aside>

			<!-- Grid -->
			<div class="learno-scroll min-w-0 flex-1 overflow-auto bg-[var(--learno-canvas)]">
				<div
					class="sticky top-0 z-10 flex flex-wrap items-center gap-3 border-b border-[var(--learno-line-soft)] bg-[var(--learno-canvas)] px-5 py-4"
				>
					<h2 class="text-[18px] font-semibold">
						{{ cursor.format('MMMM') }}
						<span class="font-normal text-[var(--learno-ink-muted)]">
							{{ cursor.format('YYYY') }}
						</span>
					</h2>

					<button type="button" class="learno-pill" @click="goToday">
						{{ __('Today') }}
					</button>
					<button
						type="button"
						class="learno-pill"
						:aria-label="__('Previous week')"
						@click="shift(-1)"
					>
						<span class="lucide-chevron-left size-4 rtl:rotate-180" />
					</button>
					<button
						type="button"
						class="learno-pill"
						:aria-label="__('Next week')"
						@click="shift(1)"
					>
						<span class="lucide-chevron-right size-4 rtl:rotate-180" />
					</button>

					<span
						v-if="events.loading"
						class="lucide-loader-circle size-4 animate-spin text-[var(--learno-ink-subtle)]"
					/>
				</div>

				<div class="grid min-w-[860px] grid-cols-7">
					<div
						v-for="day in week"
						:key="day.iso"
						class="border-e border-b border-[var(--learno-line-soft)] last:border-e-0"
					>
						<div
							class="border-b px-3 py-2 text-center text-[12px]"
							:class="
								day.isToday
									? 'border-[var(--learno-primary)] font-semibold text-[var(--learno-primary)]'
									: 'border-transparent text-[var(--learno-ink-muted)]'
							"
						>
							{{ day.label }}
						</div>

						<ul class="flex min-h-[420px] flex-col gap-2 p-2">
							<li
								v-for="event in day.events"
								:key="`${event.kind}-${event.title}-${event.time}`"
								class="rounded-[6px] px-2 py-1.5 text-[10px] leading-[1.35]"
								:style="chipStyle(event.kind)"
							>
								<p class="font-semibold">{{ event.title }}</p>
								<p v-if="event.time" class="opacity-80">
									{{ formatTime(event) }}
								</p>
								<a
									v-if="event.url"
									:href="safeUrl(event.url)"
									class="mt-1 inline-block underline"
									v-external
								>
									{{ __('Join') }}
								</a>
							</li>
						</ul>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, inject, ref, watch } from 'vue'
import { createResource, usePageMeta } from 'frappe-ui'
import { safeUrl } from '@/utils/safeUrl'
import MiniMonth from '@/pages/Student/components/MiniMonth.vue'

const dayjs = inject<any>('$dayjs')

usePageMeta(() => ({ title: __('Calendar') }))

// The cursor is any day inside the week being shown; the grid derives the week
// from it, so "next week" is a seven-day shift rather than week-number maths.
const cursor = ref(dayjs())

const weekStart = computed(() => cursor.value.startOf('week'))
const weekEnd = computed(() => cursor.value.endOf('week'))

const events = createResource({
	url: 'lms.lms.student_api.get_calendar_events',
	makeParams: () => ({
		// A month either side of the shown week, so paging one week does not
		// refetch and the mini month can mark days outside the current week.
		start: weekStart.value.subtract(1, 'month').format('YYYY-MM-DD'),
		end: weekEnd.value.add(1, 'month').format('YYYY-MM-DD'),
	}),
	auto: true,
})

// Refetch only when the shown week leaves the window already loaded.
let loadedFrom = weekStart.value
watch(weekStart, (value) => {
	if (Math.abs(value.diff(loadedFrom, 'day')) > 21) {
		loadedFrom = value
		events.reload()
	}
})

const byDate = computed(() => {
	const map: Record<string, any[]> = {}
	for (const event of events.data || []) {
		const key = dayjs(event.date).format('YYYY-MM-DD')
		;(map[key] ||= []).push(event)
	}
	return map
})

const week = computed(() =>
	Array.from({ length: 7 }, (_, index) => {
		const day = weekStart.value.add(index, 'day')
		const iso = day.format('YYYY-MM-DD')
		return {
			iso,
			label: day.format('ddd D'),
			isToday: iso === dayjs().format('YYYY-MM-DD'),
			events: byDate.value[iso] || [],
		}
	})
)

const markedDates = computed(() => new Set(Object.keys(byDate.value)))

const KIND_COLOR: Record<string, { bg: string; fg: string; label: string }> = {
	live_class: { bg: '#ddf4ff', fg: '#1b4f86', label: 'Live classes' },
	evaluation: { bg: '#ffe1e1', fg: '#8f1f1f', label: 'Evaluations' },
	batch_start: { bg: '#dcfce7', fg: '#14532d', label: 'Batches' },
}

const legend = computed(() =>
	Object.entries(KIND_COLOR).map(([kind, style]) => ({
		kind,
		label: __(style.label),
		color: style.bg,
		count: week.value.reduce(
			(total, day) =>
				total + day.events.filter((event: any) => event.kind === kind).length,
			0
		),
	}))
)

function chipStyle(kind: string) {
	const style = KIND_COLOR[kind] || KIND_COLOR.batch_start
	return { backgroundColor: style.bg, color: style.fg }
}

function formatTime(event: any) {
	const at = dayjs(`${event.date}T${event.time}`)
	return at.isValid() ? at.format('h:mm A') : String(event.time)
}

function shift(weeks: number) {
	cursor.value = cursor.value.add(weeks, 'week')
}

function goToday() {
	cursor.value = dayjs()
}
</script>
