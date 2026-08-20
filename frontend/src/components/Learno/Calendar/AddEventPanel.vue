<!--
	The "Add Events" side panel. Figma: nodes 137:90848 (empty) and 164:42449
	(with invitees listed).

	It is a right-hand sheet rather than a centred dialog because the design puts
	it beside the calendar, and because the three sub-dialogs it opens (Repeat,
	Invitation, Meet link) stack on top of it — a centred dialog opening another
	centred dialog reads as the first one having been replaced.
-->
<template>
	<Teleport to="body">
		<div v-if="open" class="learno fixed inset-0 z-50 flex justify-end">
			<div class="absolute inset-0 bg-black/40" @click="close" aria-hidden="true" />

			<aside
				class="relative flex h-full w-full max-w-[516px] flex-col bg-white shadow-2xl"
				role="dialog"
				aria-modal="true"
				:aria-label="__('Add Events')"
			>
				<header
					class="flex shrink-0 items-center justify-between border-b border-[var(--learno-line-soft)] px-6 py-5"
				>
					<h2 class="text-[18px] font-semibold text-[var(--learno-ink-strong)]">
						{{ __('Add Events') }}
					</h2>
					<button
						type="button"
						class="grid size-8 place-items-center rounded-[8px] border border-[#1e3a8a] text-[#1e3a8a] transition hover:bg-[#1e3a8a]/5"
						:aria-label="__('Close')"
						@click="close"
					>
						<span class="lucide-x size-4" aria-hidden="true" />
					</button>
				</header>

				<div class="learno-scroll min-h-0 flex-1 overflow-y-auto px-6 py-5">
					<label class="mb-1.5 block text-[12px] text-[var(--learno-ink-muted)]">
						{{ __('Event Title') }}
					</label>
					<input
						ref="titleInput"
						v-model.trim="form.title"
						type="text"
						class="w-full rounded-[var(--learno-r-sm)] border border-[var(--learno-line)] px-4 py-3 text-[14px]"
						:placeholder="__('Enter Event title')"
					/>

					<p class="mb-2 mt-6 text-[12px] text-[var(--learno-ink-muted)]">
						{{ __('Date and Time') }}
					</p>

					<div v-if="!form.all_day" class="mb-3 flex items-center gap-3">
						<span
							class="lucide-clock size-6 shrink-0 text-[var(--learno-ink-subtle)]"
							aria-hidden="true"
						/>
						<TimeSelect
							v-model="form.start_time"
							:counterpart="form.end_time"
							edge="start"
							class="flex-1"
						/>
						<span class="text-[13px] text-[var(--learno-ink-muted)]">{{ __('to') }}</span>
						<TimeSelect
							v-model="form.end_time"
							:counterpart="form.start_time"
							edge="end"
							class="flex-1"
						/>
					</div>

					<div class="flex items-center gap-3">
						<span
							class="lucide-calendar size-6 shrink-0 text-[var(--learno-ink-subtle)]"
							aria-hidden="true"
						/>
						<input
							v-model="form.date"
							type="date"
							:min="today"
							class="flex-1 rounded-[var(--learno-r-sm)] border border-[var(--learno-line)] px-4 py-2.5 text-[13px]"
						/>
					</div>

					<label class="mt-5 flex cursor-pointer items-center gap-3">
						<span
							class="relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition"
							:class="form.all_day ? 'bg-[var(--learno-primary)]' : 'bg-[#d9dbe3]'"
						>
							<input v-model="form.all_day" type="checkbox" class="sr-only" />
							<span
								class="absolute size-4 rounded-full bg-white transition-all"
								:class="form.all_day ? 'start-[18px]' : 'start-0.5'"
							/>
						</span>
						<span class="text-[14px] text-[var(--learno-ink-muted)]">
							{{ __('All Day Event') }}
						</span>
					</label>

					<!-- Course scope. Not in the design, but the invite list has to be
					     scoped to something, and the brief is "colleagues and
					     instructors that are available in the course". -->
					<label class="mb-1.5 mt-6 block text-[12px] text-[var(--learno-ink-muted)]">
						{{ __('Course') }}
					</label>
					<select
						v-model="form.course"
						class="w-full rounded-[var(--learno-r-sm)] border border-[var(--learno-line)] px-4 py-3 text-[14px]"
					>
						<option value="">{{ __('Any of my courses') }}</option>
						<option v-for="course in courses" :key="course.name" :value="course.name">
							{{ course.title }}
						</option>
					</select>

					<button
						type="button"
						class="mt-6 flex w-full items-center justify-between rounded-[var(--learno-r-sm)] border border-[var(--learno-line)] px-4 py-3 text-[14px] transition hover:border-[#d8dae3]"
						@click="showRepeat = true"
					>
						<span :class="repeatSummary ? '' : 'text-[var(--learno-ink-subtle)]'">
							{{ repeatSummary || __('Repeat') }}
						</span>
						<span
							class="lucide-chevron-right size-5 text-[var(--learno-ink-subtle)] rtl:rotate-180"
							aria-hidden="true"
						/>
					</button>

					<div class="mt-4 flex items-center gap-3">
						<span
							class="lucide-users size-6 shrink-0 text-[var(--learno-ink-subtle)]"
							aria-hidden="true"
						/>
						<button
							type="button"
							class="flex-1 rounded-[var(--learno-r-sm)] border border-[var(--learno-line)] px-4 py-3 text-start text-[14px] text-[var(--learno-ink-subtle)] transition hover:border-[#d8dae3]"
							@click="showInvite = true"
						>
							{{ __('Add Participants') }}
						</button>
					</div>

					<div v-if="form.participants.length" class="mt-5">
						<p class="mb-3 text-[13px] text-[var(--learno-ink-muted)]">
							{{ __('Invited') }}
						</p>
						<ul class="flex flex-col gap-3">
							<li
								v-for="person in form.participants"
								:key="person.participant"
								class="flex items-center gap-3"
							>
								<img
									v-if="person.user_image"
									:src="safeUrl(person.user_image)"
									alt=""
									class="size-9 shrink-0 rounded-full object-cover"
								/>
								<span
									v-else
									class="grid size-9 shrink-0 place-items-center rounded-full bg-[var(--learno-primary-soft)] text-[12px] font-semibold text-[var(--learno-primary)]"
								>
									{{ (person.full_name || person.participant).charAt(0).toUpperCase() }}
								</span>
								<span class="flex min-w-0 flex-1 flex-col">
									<span class="truncate text-[14px]">
										{{ person.full_name || person.participant }}
									</span>
									<span class="text-[11px] text-[var(--learno-ink-subtle)]">
										{{ person.participant_role === 'Instructor' ? __('Instructor') : __('Student') }}
									</span>
								</span>
								<button
									type="button"
									class="text-[13px] text-[#9f1239] transition hover:underline"
									@click="removeParticipant(person.participant)"
								>
									{{ __('Cancel') }}
								</button>
							</li>
						</ul>
					</div>

					<button
						type="button"
						class="mt-5 flex w-full items-center gap-3 rounded-[var(--learno-r-sm)] border border-[var(--learno-line)] px-4 py-3 text-[14px] transition hover:border-[#d8dae3]"
						@click="showMeet = true"
					>
						<span
							class="lucide-video size-6 shrink-0 text-[var(--learno-ink-subtle)]"
							aria-hidden="true"
						/>
						<span
							class="min-w-0 flex-1 truncate text-start"
							:class="form.meet_link ? '' : 'text-[var(--learno-ink-subtle)]'"
						>
							{{ form.meet_link || __('Add Meet link') }}
						</span>
						<span
							class="lucide-chevron-right size-5 text-[var(--learno-ink-subtle)] rtl:rotate-180"
							aria-hidden="true"
						/>
					</button>

					<div class="mt-6 border-t border-[var(--learno-line-soft)] pt-5">
						<label class="mb-1.5 block text-[12px] text-[var(--learno-ink-muted)]">
							{{ __('Description') }}
						</label>
						<textarea
							v-model.trim="form.description"
							rows="4"
							class="w-full resize-y rounded-[var(--learno-r-sm)] border border-[var(--learno-line)] px-4 py-3 text-[14px]"
							:placeholder="__('Write the meet description')"
						/>
					</div>

					<p v-if="error" class="mt-4 text-[12px] text-[#ea2b2b]" role="alert">
						{{ error }}
					</p>
				</div>

				<footer class="shrink-0 border-t border-[var(--learno-line-soft)] px-6 py-5">
					<button
						type="button"
						class="learno-btn learno-btn-primary w-full py-3 text-[14px]"
						:disabled="busy"
						@click="submit"
					>
						<span
							:class="[
								busy ? 'lucide-loader-circle animate-spin' : 'lucide-plus',
								'size-4',
							]"
							aria-hidden="true"
						/>
						{{ __('Send Invitations') }}
					</button>
				</footer>
			</aside>
		</div>
	</Teleport>

	<RepeatEventModal
		v-model:open="showRepeat"
		:rule="form"
		:start-date="form.date"
		@apply="applyRepeat"
	/>
	<InvitationModal
		v-model:open="showInvite"
		:participants="form.participants"
		:course="form.course"
		:repeats="Boolean(form.repeat_enabled)"
		@apply="applyParticipants"
	/>
	<MeetLinkModal
		v-model:open="showMeet"
		:link="form.meet_link"
		:repeats="Boolean(form.repeat_enabled)"
		@apply="applyMeetLink"
	/>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { call, toast } from 'frappe-ui'
import { safeUrl } from '@/utils/safeUrl'
import TimeSelect from '@/components/Learno/Calendar/TimeSelect.vue'
import RepeatEventModal from '@/components/Learno/Calendar/RepeatEventModal.vue'
import InvitationModal from '@/components/Learno/Calendar/InvitationModal.vue'
import MeetLinkModal from '@/components/Learno/Calendar/MeetLinkModal.vue'

const props = defineProps<{
	open: boolean
	/** Prefills the date when the panel is opened from a specific day cell. */
	date?: string
	courses: any[]
}>()

const emit = defineEmits<{
	(e: 'update:open', value: boolean): void
	(e: 'created'): void
}>()

const titleInput = ref<HTMLInputElement | null>(null)
const showRepeat = ref(false)
const showInvite = ref(false)
const showMeet = ref(false)
const busy = ref(false)
const error = ref('')

const today = new Date().toISOString().slice(0, 10)

function blank() {
	return {
		title: '',
		course: '',
		date: props.date || today,
		start_time: '09:30:00',
		end_time: '10:30:00',
		all_day: false,
		description: '',
		meet_link: '',
		participants: [] as any[],
		repeat_enabled: 0,
		repeat_every: 1,
		repeat_unit: 'Weeks',
		repeat_on: '',
		repeat_ends: 'Never',
		repeat_until: '',
		repeat_count: 2,
	}
}

const form = ref(blank())

watch(
	() => props.open,
	async (isOpen) => {
		if (!isOpen) return
		form.value = blank()
		error.value = ''
		await nextTick()
		titleInput.value?.focus()
	},
	{ immediate: true }
)

const repeatSummary = computed(() => {
	if (!form.value.repeat_enabled) return ''
	const every = form.value.repeat_every || 1
	const unit = String(form.value.repeat_unit || 'Weeks').toLowerCase()
	const base =
		every === 1 ? __('Every {0}').format(unit.replace(/s$/, '')) : `${__('Every')} ${every} ${unit}`
	if (form.value.repeat_ends === 'On Date' && form.value.repeat_until) {
		return `${base} · ${__('until')} ${form.value.repeat_until}`
	}
	if (form.value.repeat_ends === 'After' && form.value.repeat_count) {
		return `${base} · ${form.value.repeat_count}×`
	}
	return base
})

function applyRepeat(rule: Record<string, any>) {
	form.value = { ...form.value, ...rule }
}

function applyParticipants(participants: any[]) {
	form.value.participants = participants
}

function applyMeetLink(link: string) {
	form.value.meet_link = link
}

function removeParticipant(participant: string) {
	form.value.participants = form.value.participants.filter(
		(person: any) => person.participant !== participant
	)
}

function close() {
	emit('update:open', false)
}

async function submit() {
	error.value = ''

	if (!form.value.title) {
		error.value = __('Give the event a title.')
		return
	}
	if (!form.value.date) {
		error.value = __('Pick a date.')
		return
	}
	if (!form.value.all_day && form.value.start_time >= form.value.end_time) {
		error.value = __('The event ends before it starts.')
		return
	}

	busy.value = true
	try {
		await call('lms.lms.calendar_api.create_event', {
			payload: {
				...form.value,
				all_day: form.value.all_day ? 1 : 0,
				// The server rejects times on an all-day event; send nothing rather
				// than values it would have to ignore.
				start_time: form.value.all_day ? null : form.value.start_time,
				end_time: form.value.all_day ? null : form.value.end_time,
				participants: form.value.participants.map((person: any) => ({
					participant: person.participant,
				})),
			},
		})
		toast.success(__('Event created'))
		emit('created')
		close()
	} catch (e: any) {
		error.value = e?.messages?.[0] || e?.message || __('Could not create the event')
	} finally {
		busy.value = false
	}
}
</script>
