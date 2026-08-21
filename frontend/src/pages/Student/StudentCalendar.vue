<!--
	Calendar. Figma: frame 136:88179 — a mini month picker and a legend on the
	left, a week grid on the right with Week / Today / prev / next controls.

	The design's two header buttons are both live:

	* **Create Event** opens the Add Events sheet (Figma 137:90848) — a student
	  organises a discussion and invites people from their courses.
	* **Book Appointment** opens the four-step booking flow — course, then
	  instructor, then a free slot, then what the doubt is. A booked slot stops
	  being offered to anyone else; the guarantee is enforced server-side in
	  `LMSAppointment`, not by this grid.

	Instructors get a third button, **My availability**, which is what puts slots
	into that flow in the first place.

	Everything on the grid comes from `get_calendar_events`, which flattens five
	sources into one shape; `kind` is what colours each chip.
-->
<template>
	<div class="flex h-full min-h-0 flex-col">
		<header
			class="flex shrink-0 flex-wrap items-center gap-4 border-b border-[var(--learno-line-soft)] bg-white px-6 py-[22px] lg:px-10"
		>
			<h1
				class="text-[27px] font-semibold leading-[1.2] text-black max-lg:ps-12"
			>
				{{ __('Calendar') }}
			</h1>

			<div class="ms-auto flex flex-wrap items-center gap-2">
				<!-- Instructors only. A pure student has no availability to publish,
				     and the endpoint behind it returns nothing for them anyway. -->
				<button
					v-if="isInstructor"
					type="button"
					class="learno-btn learno-btn-secondary px-4 py-2.5 text-[13px]"
					@click="showAvailability = true"
				>
					<span class="lucide-clock size-4" aria-hidden="true" />
					{{ __('My availability') }}
				</button>

				<button
					type="button"
					class="learno-btn learno-btn-secondary px-4 py-2.5 text-[13px]"
					@click="showBooking = true"
				>
					<span class="lucide-calendar-check size-4" aria-hidden="true" />
					{{ __('Book Appointment') }}
				</button>

				<button
					type="button"
					class="learno-btn learno-btn-primary px-4 py-2.5 text-[13px]"
					@click="openEventPanel()"
				>
					<span class="lucide-plus size-4" aria-hidden="true" />
					{{ __('Create Event') }}
				</button>
			</div>
		</header>

		<div class="flex min-h-0 flex-1">
			<!-- Rail -->
			<aside
				class="learno-scroll hidden w-[240px] shrink-0 overflow-y-auto border-e border-[var(--learno-line-soft)] bg-white p-4 lg:block"
			>
				<MiniMonth v-model="cursor" :marked="markedDates" />

				<div class="mt-6 flex flex-col gap-4">
					<div
						v-for="group in legend"
						:key="group.kind"
						class="flex flex-col gap-1.5"
					>
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
			<div
				class="learno-scroll min-w-0 flex-1 overflow-auto bg-[var(--learno-canvas)]"
			>
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

						<ul class="group/day flex min-h-[420px] flex-col gap-2 p-2">
							<li
								v-for="event in day.events"
								:key="
									event.name || `${event.kind}-${event.title}-${event.time}`
								"
								class="rounded-[6px] px-2 py-1.5 text-[10px] leading-[1.35]"
								:style="chipStyle(event.kind)"
							>
								<p class="font-semibold">{{ event.title }}</p>
								<p v-if="event.time" class="opacity-80">
									{{ formatTime(event) }}
								</p>
								<p v-if="event.description" class="learno-clamp-2 opacity-75">
									{{ event.description }}
								</p>
								<div class="mt-1 flex flex-wrap items-center gap-2">
									<a
										v-if="event.url"
										:href="safeUrl(event.url)"
										class="underline"
										v-external
									>
										{{ __('Join') }}
									</a>
									<button
										v-if="canCancel(event)"
										type="button"
										class="underline opacity-80 hover:opacity-100"
										@click="cancel(event)"
									>
										{{ cancelLabel(event) }}
									</button>
								</div>
							</li>

							<li class="mt-auto">
								<button
									type="button"
									class="w-full rounded-[6px] border border-dashed border-[var(--learno-line)] py-1.5 text-[10px] text-[var(--learno-ink-subtle)] opacity-0 transition hover:border-[var(--learno-primary)] hover:text-[var(--learno-primary)] focus:opacity-100 group-hover/day:opacity-100"
									:aria-label="__('Add an event on {0}').format(day.label)"
									@click="openEventPanel(day.iso)"
								>
									+ {{ __('Add') }}
								</button>
							</li>
						</ul>
					</div>
				</div>
			</div>
		</div>

		<AddEventPanel
			v-model:open="showEventPanel"
			:date="eventPanelDate"
			:courses="myCourses"
			@created="refresh"
		/>
		<BookAppointmentModal v-model:open="showBooking" @booked="refresh" />
		<AvailabilityModal v-if="isInstructor" v-model:open="showAvailability" />
	</div>
</template>

<script setup lang="ts">
import { computed, inject, ref, watch } from 'vue'
import { call, createResource, toast, usePageMeta } from 'frappe-ui'
import { safeUrl } from '@/utils/safeUrl'
import MiniMonth from '@/pages/Student/components/MiniMonth.vue'
import AddEventPanel from '@/components/Learno/Calendar/AddEventPanel.vue'
import BookAppointmentModal from '@/components/Learno/Calendar/BookAppointmentModal.vue'
import AvailabilityModal from '@/components/Learno/Calendar/AvailabilityModal.vue'

const dayjs = inject<any>('$dayjs')
const userResource = inject<any>('$user')

usePageMeta(() => ({ title: __('Calendar') }))

const showEventPanel = ref(false)
const showBooking = ref(false)
const showAvailability = ref(false)
const eventPanelDate = ref('')

// Only someone who teaches has hours to publish. `is_instructor` is the same
// flag the sidebar's admin switch keys off.
const isInstructor = computed(() =>
	Boolean(userResource?.data?.is_instructor || userResource?.data?.is_moderator)
)

// The Add Events sheet scopes its invite list by course, so it needs the
// student's own shelf. Enrolled only — you cannot invite people from a course
// you are not in.
const enrolled = createResource({
	url: 'lms.lms.student_api.get_student_courses',
	params: { filters: { enrolled: 1 }, limit_page_length: 100 },
	auto: true,
})

const myCourses = computed(() => enrolled.data || [])

function openEventPanel(date?: string) {
	eventPanelDate.value = date || dayjs().format('YYYY-MM-DD')
	showEventPanel.value = true
}

function refresh() {
	events.reload()
}

// Only the two kinds this app creates are cancellable, and only by someone on
// them. Live classes, evaluations and batch starts belong to staff.
function canCancel(event: any) {
	if (event.kind === 'appointment') return true
	return event.kind === 'event' && event.is_owner
}

// An event is stored as one row plus a repeat rule, so there is nowhere to
// record "skip this one occurrence" — deleting removes the series. The label
// says so rather than letting a student find out afterwards.
function cancelLabel(event: any) {
	if (event.kind === 'appointment') return __('Cancel')
	return event.participants?.length && event.repeat_enabled
		? __('Delete series')
		: __('Delete')
}

async function cancel(event: any) {
	const method =
		event.kind === 'appointment'
			? 'lms.lms.calendar_api.cancel_appointment'
			: 'lms.lms.calendar_api.delete_event'
	try {
		await call(method, { name: event.name })
		toast.success(
			event.kind === 'appointment'
				? __('Appointment cancelled')
				: __('Event deleted')
		)
		refresh()
	} catch (e: any) {
		toast.error(e?.messages?.[0] || e?.message || __('Could not cancel that'))
	}
}

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
	appointment: { bg: '#fff1f1', fg: '#9f1239', label: 'One-to-one' },
	event: { bg: '#ede9fe', fg: '#5b21b6', label: 'My events' },
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
