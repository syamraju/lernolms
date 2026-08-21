<!--
	Batch › Calendar — one month grid over everything scheduled in this cohort.

	No new storage behind it: timetable rows, live classes, evaluations and
	appointments all already existed, but the only view of them was the timetable
	grid buried in Settings. Every entry carries `kind`, which is what the colours
	key off — the same contract lms.lms.student_api.get_calendar_events uses, so
	the student calendar and this one render from one shape.
-->
<template>
	<div class="w-[95%] lg:w-[85%] mx-auto mt-5">
		<div class="flex items-center justify-between mb-4">
			<div>
				<div class="text-ink-gray-9 font-semibold">{{ monthLabel }}</div>
				<div class="text-sm text-ink-gray-6">
					{{ __('Classes, deadlines and evaluations in this batch.') }}
				</div>
			</div>
			<div class="flex items-center gap-1">
				<Button
					variant="ghost"
					:label="__('Previous month')"
					@click="shift(-1)"
				>
					<template #icon><span class="lucide-chevron-left size-4" /></template>
				</Button>
				<Button variant="subtle" @click="today">{{ __('Today') }}</Button>
				<Button variant="ghost" :label="__('Next month')" @click="shift(1)">
					<template #icon
						><span class="lucide-chevron-right size-4"
					/></template>
				</Button>
			</div>
		</div>

		<div class="flex flex-wrap gap-3 mb-3 text-xs text-ink-gray-6">
			<span
				v-for="kind in legend"
				:key="kind.key"
				class="flex items-center gap-1.5"
			>
				<span class="size-2.5 rounded-full" :class="kind.dot" />
				{{ kind.label }}
			</span>
		</div>

		<div class="border rounded-lg overflow-hidden">
			<div class="grid grid-cols-7 bg-surface-gray-2 text-xs text-ink-gray-6">
				<div v-for="day in weekdays" :key="day" class="px-2 py-2 text-center">
					{{ day }}
				</div>
			</div>
			<div class="grid grid-cols-7">
				<div
					v-for="cell in cells"
					:key="cell.iso"
					class="min-h-[6.5rem] border-t border-e p-1.5 last:border-e-0"
					:class="[
						cell.inMonth ? '' : 'bg-surface-gray-1',
						cell.isToday ? 'ring-1 ring-inset ring-outline-gray-3' : '',
					]"
				>
					<div
						class="text-xs mb-1"
						:class="cell.inMonth ? 'text-ink-gray-7' : 'text-ink-gray-4'"
					>
						{{ cell.day }}
					</div>
					<div class="space-y-1">
						<button
							v-for="event in cell.events"
							:key="event.key"
							type="button"
							class="w-full text-start text-[11px] leading-tight rounded px-1.5 py-1 truncate"
							:class="tone(event.kind)"
							:title="eventTitle(event)"
							@click="open(event)"
						>
							{{ event.title }}
						</button>
					</div>
				</div>
			</div>
		</div>

		<div v-if="calendar.loading" class="text-sm text-ink-gray-6 mt-3">
			{{ __('Loading…') }}
		</div>
	</div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { Button, createResource } from 'frappe-ui'

const props = defineProps({
	batch: {
		type: Object,
		required: true,
	},
})

const cursor = ref(startOfMonth(new Date()))

function startOfMonth(date) {
	return new Date(date.getFullYear(), date.getMonth(), 1)
}

function iso(date) {
	// Local, not toISOString(): the latter converts to UTC first, which shifts
	// the date by one for anyone east or west of it and lands events on the
	// wrong day.
	const month = `${date.getMonth() + 1}`.padStart(2, '0')
	const day = `${date.getDate()}`.padStart(2, '0')
	return `${date.getFullYear()}-${month}-${day}`
}

// The grid always shows whole weeks, so the query window is the grid, not the
// month — an event on a leading or trailing day would otherwise render blank.
const gridStart = computed(() => {
	const first = cursor.value
	const start = new Date(first)
	start.setDate(first.getDate() - first.getDay())
	return start
})

const gridEnd = computed(() => {
	const end = new Date(gridStart.value)
	end.setDate(end.getDate() + 41)
	return end
})

const batchName = computed(() => props.batch.data?.name)

const calendar = createResource({
	url: 'lms.lms.batch_calendar.get_batch_calendar',
	makeParams: () => ({
		batch: batchName.value,
		start: iso(gridStart.value),
		end: iso(gridEnd.value),
	}),
	auto: true,
})

watch([cursor, batchName], () => calendar.reload())

const monthLabel = computed(() =>
	cursor.value.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })
)

const weekdays = [
	__('Sun'),
	__('Mon'),
	__('Tue'),
	__('Wed'),
	__('Thu'),
	__('Fri'),
	__('Sat'),
]

const byDate = computed(() => {
	const map = {}
	for (const [index, event] of (calendar.data || []).entries()) {
		const key = String(event.date).slice(0, 10)
		;(map[key] ||= []).push({ ...event, key: `${key}-${index}` })
	}
	return map
})

const todayIso = iso(new Date())

const cells = computed(() => {
	const out = []
	for (let offset = 0; offset < 42; offset++) {
		const date = new Date(gridStart.value)
		date.setDate(date.getDate() + offset)
		const key = iso(date)
		out.push({
			iso: key,
			day: date.getDate(),
			inMonth: date.getMonth() === cursor.value.getMonth(),
			isToday: key === todayIso,
			events: byDate.value[key] || [],
		})
	}
	return out
})

const legend = [
	{ key: 'live_class', label: __('Live class'), dot: 'bg-blue-500' },
	{ key: 'timetable', label: __('Timetable'), dot: 'bg-green-500' },
	{ key: 'evaluation', label: __('Evaluation'), dot: 'bg-purple-500' },
	{ key: 'appointment', label: __('Appointment'), dot: 'bg-amber-500' },
	{ key: 'batch_start', label: __('Batch start / end'), dot: 'bg-gray-500' },
]

const tones = {
	live_class: 'bg-blue-100 text-blue-900',
	timetable: 'bg-green-100 text-green-900',
	evaluation: 'bg-purple-100 text-purple-900',
	appointment: 'bg-amber-100 text-amber-900',
	batch_start: 'bg-gray-200 text-gray-900',
	batch_end: 'bg-gray-200 text-gray-900',
}

const tone = (kind) => tones[kind] || 'bg-surface-gray-2 text-ink-gray-8'

const eventTitle = (event) => {
	const parts = [event.title]
	if (event.start_time) parts.push(String(event.start_time).slice(0, 5))
	return parts.join(' · ')
}

const open = (event) => {
	if (event.url) window.open(event.url, '_blank', 'noopener')
}

const shift = (months) => {
	const next = new Date(cursor.value)
	next.setMonth(next.getMonth() + months)
	cursor.value = startOfMonth(next)
}

const today = () => {
	cursor.value = startOfMonth(new Date())
}
</script>
