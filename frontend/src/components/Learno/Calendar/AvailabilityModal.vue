<!--
	Where an instructor publishes the hours students can book against.

	Shown only to someone who actually teaches a course — the button that opens
	it is hidden otherwise, and `get_my_courses_for_availability` returns nothing
	for a pure student, so there is no way in by URL either.

	One row per weekday window. The slot length is a property of the whole
	course's availability rather than of each window, because that is what the
	student-facing grid divides by and a per-window length would make two
	adjacent windows produce a ragged grid.
-->
<template>
	<LearnoDialog
		:open="open"
		:title="__('Your availability')"
		:width="640"
		:busy="busy"
		:save-label="__('Publish')"
		@update:open="$emit('update:open', $event)"
		@save="save"
	>
		<div v-if="courses.loading" class="py-10 text-center text-[13px] text-[var(--learno-ink-subtle)]">
			{{ __('Loading your courses…') }}
		</div>

		<p
			v-else-if="!courses.data?.length"
			class="py-10 text-center text-[13px] text-[var(--learno-ink-muted)]"
		>
			{{ __('You are not an instructor on any course.') }}
		</p>

		<div v-else class="flex flex-col gap-6">
			<div>
				<label class="mb-1.5 block text-[12px] text-[var(--learno-ink-muted)]">
					{{ __('Course') }}
				</label>
				<select
					v-model="selectedCourse"
					class="w-full rounded-[var(--learno-r-sm)] border border-[var(--learno-line)] px-4 py-3 text-[14px]"
				>
					<option v-for="course in courses.data" :key="course.name" :value="course.name">
						{{ course.title }}
					</option>
				</select>
			</div>

			<div class="flex flex-wrap items-end gap-6">
				<div>
					<label class="mb-1.5 block text-[12px] text-[var(--learno-ink-muted)]">
						{{ __('Session length') }}
					</label>
					<select
						v-model.number="form.slot_duration"
						class="w-[160px] rounded-[var(--learno-r-sm)] border border-[var(--learno-line)] px-4 py-2.5 text-[14px]"
					>
						<option v-for="minutes in [15, 20, 30, 45, 60, 90]" :key="minutes" :value="minutes">
							{{ __('{0} minutes').format(minutes) }}
						</option>
					</select>
				</div>

				<label class="flex cursor-pointer items-center gap-3 pb-2">
					<span
						class="relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition"
						:class="form.published ? 'bg-[var(--learno-primary)]' : 'bg-[#d9dbe3]'"
					>
						<input v-model="form.published" type="checkbox" class="sr-only" />
						<span
							class="absolute size-4 rounded-full bg-white transition-all"
							:class="form.published ? 'start-[18px]' : 'start-0.5'"
						/>
					</span>
					<span class="text-[13px] text-[var(--learno-ink-muted)]">
						{{ __('Taking bookings') }}
					</span>
				</label>
			</div>

			<div>
				<div class="mb-3 flex items-center justify-between">
					<p class="text-[13px] font-semibold text-[var(--learno-ink-strong)]">
						{{ __('Weekly hours') }}
					</p>
					<button
						type="button"
						class="learno-btn learno-btn-secondary px-4 py-2"
						@click="addRow"
					>
						<span class="lucide-plus size-4" aria-hidden="true" />
						{{ __('Add window') }}
					</button>
				</div>

				<p
					v-if="!form.schedule.length"
					class="rounded-[var(--learno-r-sm)] bg-[var(--learno-canvas)] px-4 py-6 text-center text-[13px] text-[var(--learno-ink-muted)]"
				>
					{{ __('Add at least one window before publishing.') }}
				</p>

				<ul v-else class="flex flex-col gap-2">
					<li
						v-for="(row, index) in form.schedule"
						:key="index"
						class="flex items-center gap-2"
					>
						<select
							v-model="row.day"
							class="w-[140px] rounded-[var(--learno-r-sm)] border border-[var(--learno-line)] px-3 py-2.5 text-[13px]"
						>
							<option v-for="day in DAYS" :key="day" :value="day">{{ day }}</option>
						</select>
						<TimeSelect
							v-model="row.start_time"
							:counterpart="row.end_time"
							edge="start"
							:step-minutes="15"
							class="flex-1"
						/>
						<span class="text-[12px] text-[var(--learno-ink-muted)]">{{ __('to') }}</span>
						<TimeSelect
							v-model="row.end_time"
							:counterpart="row.start_time"
							edge="end"
							:step-minutes="15"
							class="flex-1"
						/>
						<button
							type="button"
							class="grid size-9 shrink-0 place-items-center rounded text-[var(--learno-ink-subtle)] transition hover:bg-black/5"
							:aria-label="__('Remove window')"
							@click="form.schedule.splice(index, 1)"
						>
							<span class="lucide-trash-2 size-4" aria-hidden="true" />
						</button>
					</li>
				</ul>
			</div>

			<div>
				<p class="mb-3 text-[13px] font-semibold text-[var(--learno-ink-strong)]">
					{{ __('Time off') }}
				</p>
				<div class="flex flex-wrap items-center gap-3">
					<input
						v-model="form.unavailable_from"
						type="date"
						class="rounded-[var(--learno-r-sm)] border border-[var(--learno-line)] px-3 py-2.5 text-[13px]"
					/>
					<span class="text-[12px] text-[var(--learno-ink-muted)]">{{ __('to') }}</span>
					<input
						v-model="form.unavailable_to"
						type="date"
						class="rounded-[var(--learno-r-sm)] border border-[var(--learno-line)] px-3 py-2.5 text-[13px]"
					/>
					<button
						v-if="form.unavailable_from || form.unavailable_to"
						type="button"
						class="text-[12px] text-[var(--learno-ink-subtle)] underline"
						@click="form.unavailable_from = form.unavailable_to = ''"
					>
						{{ __('Clear') }}
					</button>
				</div>
				<p class="mt-2 text-[11px] text-[var(--learno-ink-subtle)]">
					{{ __('Slots inside this window are not offered. Existing bookings are unaffected.') }}
				</p>
			</div>

			<p v-if="error" class="text-[12px] text-[#ea2b2b]" role="alert">{{ error }}</p>
		</div>
	</LearnoDialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { call, createResource, toast } from 'frappe-ui'
import LearnoDialog from '@/components/Learno/LearnoDialog.vue'
import TimeSelect from '@/components/Learno/Calendar/TimeSelect.vue'

const DAYS = [
	'Monday',
	'Tuesday',
	'Wednesday',
	'Thursday',
	'Friday',
	'Saturday',
	'Sunday',
]

const props = defineProps<{ open: boolean }>()

const emit = defineEmits<{
	(e: 'update:open', value: boolean): void
	(e: 'saved'): void
}>()

const selectedCourse = ref('')
const busy = ref(false)
const error = ref('')

const form = ref({
	slot_duration: 30,
	published: true,
	unavailable_from: '',
	unavailable_to: '',
	schedule: [] as any[],
})

const courses = createResource({
	url: 'lms.lms.calendar_api.get_my_courses_for_availability',
	onSuccess(data: any[]) {
		if (!selectedCourse.value && data?.length) selectedCourse.value = data[0].name
	},
})

watch(
	() => props.open,
	(isOpen) => {
		if (!isOpen) return
		error.value = ''
		courses.reload()
	},
	{ immediate: true }
)

// Load whatever is already saved for the chosen course, so switching courses
// shows that course's hours rather than carrying the previous one's over.
watch([selectedCourse, () => courses.data], () => {
	const row = (courses.data || []).find((c: any) => c.name === selectedCourse.value)
	if (!row) return

	form.value = {
		slot_duration: row.availability?.slot_duration || 30,
		published: row.availability ? Boolean(row.availability.published) : true,
		unavailable_from: row.availability?.unavailable_from || '',
		unavailable_to: row.availability?.unavailable_to || '',
		schedule: (row.schedule || []).map((slot: any) => ({
			day: slot.day,
			start_time: slot.start_time,
			end_time: slot.end_time,
		})),
	}
})

function addRow() {
	// Seeded with a plausible working hour rather than 00:00, which nobody wants
	// and everybody would have to change.
	form.value.schedule.push({
		day: 'Monday',
		start_time: '10:00:00',
		end_time: '12:00:00',
	})
}

async function save() {
	error.value = ''

	if (!selectedCourse.value) {
		error.value = __('Pick a course.')
		return
	}
	if (!form.value.schedule.length) {
		error.value = __('Add at least one weekly window.')
		return
	}
	for (const row of form.value.schedule) {
		if (row.start_time >= row.end_time) {
			error.value = __('Each window must end after it starts.')
			return
		}
	}

	busy.value = true
	try {
		await call('lms.lms.calendar_api.save_availability', {
			payload: {
				course: selectedCourse.value,
				slot_duration: form.value.slot_duration,
				published: form.value.published ? 1 : 0,
				unavailable_from: form.value.unavailable_from || null,
				unavailable_to: form.value.unavailable_to || null,
				schedule: form.value.schedule,
			},
		})
		toast.success(__('Availability published'))
		emit('saved')
		emit('update:open', false)
	} catch (e: any) {
		error.value = e?.messages?.[0] || e?.message || __('Could not save your availability')
	} finally {
		busy.value = false
	}
}
</script>
