<!--
	Book a one-to-one with an instructor. Four steps, in the order the brief
	describes: course → instructor → slot → what the doubt is.

	The Figma has no frame for this flow (the calendar only shows the "Book
	Appointments" button), so the chrome is LearnoDialog and the pieces are the
	design's own: coral pills for the chosen thing, the slot list from node
	161:40903, the same card radius everywhere.

	The important behaviour: a slot that another student takes between this list
	loading and the Book click is rejected by the server, and the failure is
	handled here by refreshing the slots and asking for another — not by a
	generic error toast, which would leave a stale grid on screen showing a slot
	that is already gone.
-->
<template>
	<LearnoDialog
		:open="open"
		:title="title"
		:width="620"
		@update:open="$emit('update:open', $event)"
	>
		<!-- Step rail -->
		<ol class="mb-6 flex items-center gap-2" :aria-label="__('Progress')">
			<li
				v-for="(label, index) in STEPS"
				:key="label"
				class="flex items-center gap-2"
			>
				<span
					class="grid size-6 place-items-center rounded-full text-[11px] font-semibold transition"
					:class="
						index <= stepIndex
							? 'bg-[var(--learno-primary)] text-white'
							: 'bg-black/5 text-[var(--learno-ink-subtle)]'
					"
				>
					{{ index + 1 }}
				</span>
				<span
					class="text-[12px]"
					:class="
						index === stepIndex
							? 'font-semibold'
							: 'text-[var(--learno-ink-subtle)]'
					"
				>
					{{ label }}
				</span>
				<span
					v-if="index < STEPS.length - 1"
					class="mx-1 h-px w-5 bg-[var(--learno-line)]"
					aria-hidden="true"
				/>
			</li>
		</ol>

		<!-- 1. Course -->
		<section v-if="step === 'course'">
			<p
				v-if="courses.loading"
				class="py-8 text-center text-[13px] text-[var(--learno-ink-subtle)]"
			>
				{{ __('Loading your courses…') }}
			</p>
			<p
				v-else-if="!courses.data?.length"
				class="py-10 text-center text-[13px] text-[var(--learno-ink-muted)]"
			>
				{{
					__('None of your courses have an instructor taking appointments yet.')
				}}
			</p>
			<ul v-else class="flex flex-col gap-2">
				<li v-for="course in courses.data" :key="course.name">
					<button
						type="button"
						class="learno-card flex w-full items-center gap-4 p-4 text-start transition hover:shadow-[var(--learno-shadow)]"
						@click="pickCourse(course)"
					>
						<img
							v-if="course.image"
							:src="safeUrl(course.image)"
							alt=""
							class="size-12 shrink-0 rounded-[8px] object-cover"
						/>
						<span
							v-else
							class="grid size-12 shrink-0 place-items-center rounded-[8px] bg-[var(--learno-primary-soft)] text-[var(--learno-primary)]"
						>
							<span class="lucide-book-open size-5" aria-hidden="true" />
						</span>
						<span class="min-w-0 flex-1 truncate text-[15px] font-semibold">
							{{ course.title }}
						</span>
						<span
							class="lucide-chevron-right size-5 text-[var(--learno-ink-subtle)] rtl:rotate-180"
							aria-hidden="true"
						/>
					</button>
				</li>
			</ul>
		</section>

		<!-- 2. Instructor -->
		<section v-else-if="step === 'instructor'">
			<p
				v-if="instructors.loading"
				class="py-8 text-center text-[13px] text-[var(--learno-ink-subtle)]"
			>
				{{ __('Loading instructors…') }}
			</p>
			<p
				v-else-if="!instructors.data?.length"
				class="py-10 text-center text-[13px] text-[var(--learno-ink-muted)]"
			>
				{{ __('No instructor on this course is taking appointments.') }}
			</p>
			<ul v-else class="flex flex-col gap-2">
				<li v-for="person in instructors.data" :key="person.name">
					<button
						type="button"
						class="learno-card flex w-full items-center gap-4 p-4 text-start transition hover:shadow-[var(--learno-shadow)]"
						@click="pickInstructor(person)"
					>
						<img
							v-if="person.user_image"
							:src="safeUrl(person.user_image)"
							alt=""
							class="size-12 shrink-0 rounded-full object-cover"
						/>
						<span
							v-else
							class="grid size-12 shrink-0 place-items-center rounded-full bg-[var(--learno-primary-soft)] text-[15px] font-semibold text-[var(--learno-primary)]"
						>
							{{ (person.full_name || person.name).charAt(0).toUpperCase() }}
						</span>
						<span class="flex min-w-0 flex-1 flex-col">
							<span class="truncate text-[15px] font-semibold">
								{{ person.full_name || person.name }}
							</span>
							<span class="text-[12px] text-[var(--learno-ink-subtle)]">
								{{ __('{0} minute sessions').format(person.slot_duration) }}
							</span>
						</span>
						<span
							class="lucide-chevron-right size-5 text-[var(--learno-ink-subtle)] rtl:rotate-180"
							aria-hidden="true"
						/>
					</button>
				</li>
			</ul>
		</section>

		<!-- 3. Slot -->
		<section v-else-if="step === 'slot'">
			<p
				v-if="slots.loading"
				class="py-8 text-center text-[13px] text-[var(--learno-ink-subtle)]"
			>
				{{ __('Checking availability…') }}
			</p>
			<p
				v-else-if="!slots.data?.length"
				class="py-10 text-center text-[13px] text-[var(--learno-ink-muted)]"
			>
				{{ __('No free slots in the next 60 days.') }}
			</p>
			<div v-else class="flex flex-col gap-5">
				<div v-for="day in slots.data" :key="day.date">
					<p
						class="mb-2 text-[13px] font-semibold text-[var(--learno-ink-strong)]"
					>
						{{ formatDay(day.date) }}
					</p>
					<div class="flex flex-wrap gap-2">
						<button
							v-for="slot in day.slots"
							:key="`${day.date}-${slot.start_time}`"
							type="button"
							class="rounded-[var(--learno-r-sm)] border px-4 py-2 text-[13px] transition"
							:class="
								isChosen(day.date, slot)
									? 'border-transparent bg-[var(--learno-primary)] text-white'
									: 'border-[var(--learno-line)] hover:bg-[var(--learno-canvas)]'
							"
							@click="pickSlot(day, slot)"
						>
							{{ formatTime(slot.start_time) }}
						</button>
					</div>
				</div>
			</div>
		</section>

		<!-- 4. Topic -->
		<section v-else>
			<div
				class="mb-5 rounded-[var(--learno-r-md)] bg-[var(--learno-canvas)] p-4"
			>
				<p class="text-[13px] font-semibold text-[var(--learno-ink-strong)]">
					{{ chosen.instructorName }}
				</p>
				<p class="mt-1 text-[12px] text-[var(--learno-ink-muted)]">
					{{ chosen.courseTitle }}
				</p>
				<p class="mt-2 text-[13px]">
					{{ formatDay(chosen.date) }} · {{ formatTime(chosen.startTime) }}–{{
						formatTime(chosen.endTime)
					}}
				</p>
			</div>

			<label class="mb-1.5 block text-[12px] text-[var(--learno-ink-muted)]">
				{{ __('What would you like to go over?') }}
			</label>
			<textarea
				ref="topicInput"
				v-model.trim="topic"
				rows="5"
				class="w-full resize-y rounded-[var(--learno-r-sm)] border border-[var(--learno-line)] px-4 py-3 text-[14px]"
				:placeholder="__('Describe your doubt so the instructor can prepare')"
			/>
		</section>

		<p v-if="error" class="mt-4 text-[12px] text-[#ea2b2b]" role="alert">
			{{ error }}
		</p>

		<template #footer>
			<div class="flex w-full items-center justify-between gap-3">
				<button
					v-if="stepIndex > 0"
					type="button"
					class="learno-btn learno-btn-secondary px-5 py-2.5 text-[13px]"
					@click="back"
				>
					<span
						class="lucide-arrow-left size-4 rtl:rotate-180"
						aria-hidden="true"
					/>
					{{ __('Back') }}
				</button>
				<span v-else />

				<button
					v-if="step === 'topic'"
					type="button"
					class="learno-btn learno-btn-primary px-6 py-2.5 text-[13px]"
					:disabled="busy || !topic"
					@click="confirm"
				>
					<span
						:class="[
							busy ? 'lucide-loader-circle animate-spin' : 'lucide-check',
							'size-4',
						]"
						aria-hidden="true"
					/>
					{{ __('Book session') }}
				</button>
			</div>
		</template>
	</LearnoDialog>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { call, createResource, toast } from 'frappe-ui'
import LearnoDialog from '@/components/Learno/LearnoDialog.vue'
import { safeUrl } from '@/utils/safeUrl'

const props = defineProps<{ open: boolean }>()

const emit = defineEmits<{
	(e: 'update:open', value: boolean): void
	(e: 'booked'): void
}>()

const STEPS = [__('Course'), __('Instructor'), __('Slot'), __('Topic')]
const ORDER = ['course', 'instructor', 'slot', 'topic'] as const
type Step = typeof ORDER[number]

const step = ref<Step>('course')
const topic = ref('')
const busy = ref(false)
const error = ref('')
const topicInput = ref<HTMLTextAreaElement | null>(null)

const chosen = ref({
	course: '',
	courseTitle: '',
	instructor: '',
	instructorName: '',
	date: '',
	startTime: '',
	endTime: '',
})

const stepIndex = computed(() => ORDER.indexOf(step.value))

const title = computed(
	() =>
		({
			course: __('Book an appointment'),
			instructor: __('Pick an instructor'),
			slot: __('Pick a time'),
			topic: __('Describe your doubt'),
		}[step.value])
)

const courses = createResource({
	url: 'lms.lms.calendar_api.get_bookable_courses',
})

const instructors = createResource({
	url: 'lms.lms.calendar_api.get_bookable_instructors',
	makeParams: () => ({ course: chosen.value.course }),
})

const slots = createResource({
	url: 'lms.lms.calendar_api.get_available_slots',
	makeParams: () => ({
		course: chosen.value.course,
		instructor: chosen.value.instructor,
	}),
})

watch(
	() => props.open,
	(isOpen) => {
		if (!isOpen) return
		reset()
		courses.reload()
	},
	{ immediate: true }
)

function reset() {
	step.value = 'course'
	topic.value = ''
	error.value = ''
	chosen.value = {
		course: '',
		courseTitle: '',
		instructor: '',
		instructorName: '',
		date: '',
		startTime: '',
		endTime: '',
	}
}

function pickCourse(course: any) {
	chosen.value.course = course.name
	chosen.value.courseTitle = course.title
	step.value = 'instructor'
	instructors.reload()
}

function pickInstructor(person: any) {
	chosen.value.instructor = person.name
	chosen.value.instructorName = person.full_name || person.name
	step.value = 'slot'
	slots.reload()
}

async function pickSlot(day: any, slot: any) {
	chosen.value.date = day.date
	chosen.value.startTime = slot.start_time
	chosen.value.endTime = slot.end_time
	step.value = 'topic'
	await nextTick()
	topicInput.value?.focus()
}

function isChosen(date: string, slot: any) {
	return (
		chosen.value.date === date && chosen.value.startTime === slot.start_time
	)
}

function back() {
	error.value = ''
	step.value = ORDER[Math.max(0, stepIndex.value - 1)]
}

async function confirm() {
	error.value = ''
	busy.value = true
	try {
		await call('lms.lms.calendar_api.book_appointment', {
			payload: {
				course: chosen.value.course,
				instructor: chosen.value.instructor,
				date: chosen.value.date,
				start_time: chosen.value.startTime,
				end_time: chosen.value.endTime,
				topic: topic.value,
			},
		})
		toast.success(__('Session booked'))
		emit('booked')
		emit('update:open', false)
	} catch (e: any) {
		const message =
			e?.messages?.[0] || e?.message || __('Could not book that slot')
		error.value = message

		// Someone else took it first. Send the student back to a freshly loaded
		// grid rather than leaving them staring at a slot that no longer exists.
		if (/taken|past|outside|paused|not taking/i.test(message)) {
			step.value = 'slot'
			await slots.reload()
		}
	} finally {
		busy.value = false
	}
}

function formatDay(iso: string) {
	if (!iso) return ''
	return new Date(`${iso}T00:00:00`).toLocaleDateString(undefined, {
		weekday: 'long',
		day: 'numeric',
		month: 'short',
	})
}

function formatTime(value: string) {
	if (!value) return ''
	const [h, m] = value.split(':').map(Number)
	const suffix = h < 12 ? 'AM' : 'PM'
	const hour12 = h % 12 === 0 ? 12 : h % 12
	return `${String(hour12).padStart(2, '0')}:${String(m).padStart(
		2,
		'0'
	)} ${suffix}`
}
</script>
