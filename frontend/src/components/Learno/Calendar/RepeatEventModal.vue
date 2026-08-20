<!--
	Repeat rule editor. Figma: node 137:93033.

	Edits a local copy and only emits on Save, so Discard genuinely discards —
	binding straight to the parent's object would make Discard a no-op after the
	user had already changed something.
-->
<template>
	<LearnoDialog
		:open="open"
		:title="__('Repeat Event')"
		:width="564"
		@update:open="$emit('update:open', $event)"
		@save="save"
	>
		<div class="flex flex-col gap-7 py-2">
			<div class="flex items-center gap-6">
				<label class="w-[70px] text-[15px] text-[var(--learno-ink-muted)]">
					{{ __('Every') }}
				</label>
				<input
					v-model.number="draft.repeat_every"
					type="number"
					min="1"
					max="52"
					class="w-[130px] rounded-[var(--learno-r-sm)] border border-[var(--learno-line)] px-3 py-2.5 text-[14px]"
				/>
				<select
					v-model="draft.repeat_unit"
					class="w-[140px] rounded-[var(--learno-r-sm)] border border-[var(--learno-line)] px-3 py-2.5 text-[14px]"
				>
					<option value="Days">{{ __('Days') }}</option>
					<option value="Weeks">{{ __('Weeks') }}</option>
					<option value="Months">{{ __('Months') }}</option>
				</select>
			</div>

			<div v-if="draft.repeat_unit === 'Weeks'" class="flex items-center gap-6">
				<label class="w-[70px] text-[15px] text-[var(--learno-ink-muted)]">
					{{ __('On') }}
				</label>
				<div class="flex flex-wrap gap-2">
					<button
						v-for="day in DAYS"
						:key="day.full"
						type="button"
						class="grid size-11 place-items-center rounded-[var(--learno-r-sm)] border text-[14px] transition"
						:class="
							selectedDays.includes(day.full)
								? 'border-transparent bg-[var(--learno-primary)] text-white'
								: 'border-[var(--learno-line)] text-[var(--learno-ink)] hover:bg-[var(--learno-canvas)]'
						"
						:aria-pressed="selectedDays.includes(day.full)"
						@click="toggleDay(day.full)"
					>
						{{ day.short }}
					</button>
				</div>
			</div>

			<fieldset class="flex flex-col gap-5">
				<legend class="mb-2 text-[14px] text-[var(--learno-ink-muted)]">
					{{ __('Ends on') }}
				</legend>

				<label class="flex items-center gap-4">
					<input
						v-model="draft.repeat_ends"
						type="radio"
						value="Never"
						class="size-5 accent-[#1e3a8a]"
					/>
					<span class="text-[16px]">{{ __('Never') }}</span>
				</label>

				<label class="flex items-center gap-4">
					<input
						v-model="draft.repeat_ends"
						type="radio"
						value="On Date"
						class="size-5 accent-[#1e3a8a]"
					/>
					<span class="w-[70px] text-[16px]">{{ __('Date') }}</span>
					<input
						v-model="draft.repeat_until"
						type="date"
						:min="minDate"
						:disabled="draft.repeat_ends !== 'On Date'"
						class="flex-1 rounded-[var(--learno-r-sm)] border border-[var(--learno-line)] px-3 py-2.5 text-[14px] disabled:opacity-50"
					/>
				</label>

				<label class="flex items-center gap-4">
					<input
						v-model="draft.repeat_ends"
						type="radio"
						value="After"
						class="size-5 accent-[#1e3a8a]"
					/>
					<span class="w-[70px] text-[16px]">{{ __('After') }}</span>
					<input
						v-model.number="draft.repeat_count"
						type="number"
						min="1"
						max="200"
						:disabled="draft.repeat_ends !== 'After'"
						class="w-[130px] rounded-[var(--learno-r-sm)] border border-[var(--learno-line)] px-3 py-2.5 text-[14px] disabled:opacity-50"
					/>
					<span class="text-[16px] text-[var(--learno-ink-muted)]">
						{{ __('Times') }}
					</span>
				</label>
			</fieldset>

			<p v-if="error" class="text-[12px] text-[#ea2b2b]" role="alert">
				{{ error }}
			</p>
		</div>
	</LearnoDialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import LearnoDialog from '@/components/Learno/LearnoDialog.vue'

const DAYS = [
	{ short: 'Sn', full: 'Sunday' },
	{ short: 'Mn', full: 'Monday' },
	{ short: 'Tu', full: 'Tuesday' },
	{ short: 'We', full: 'Wednesday' },
	{ short: 'Th', full: 'Thursday' },
	{ short: 'Fr', full: 'Friday' },
	{ short: 'Sa', full: 'Saturday' },
]

const props = defineProps<{
	open: boolean
	rule: Record<string, any>
	/** The event's own date — the repeat cannot end before it. */
	startDate?: string
}>()

const emit = defineEmits<{
	(e: 'update:open', value: boolean): void
	(e: 'apply', rule: Record<string, any>): void
}>()

const draft = ref<Record<string, any>>(blank())
const error = ref('')

const minDate = computed(() => props.startDate || '')

function blank() {
	return {
		repeat_every: 1,
		repeat_unit: 'Weeks',
		repeat_on: '',
		repeat_ends: 'Never',
		repeat_until: '',
		repeat_count: 2,
	}
}

// Re-seed on every open so a dialog closed with Discard does not reopen showing
// the abandoned edits.
watch(
	() => props.open,
	(isOpen) => {
		if (!isOpen) return
		draft.value = { ...blank(), ...(props.rule || {}) }
		error.value = ''
	},
	{ immediate: true }
)

const selectedDays = computed(() =>
	String(draft.value.repeat_on || '')
		.split(',')
		.map((day) => day.trim())
		.filter(Boolean)
)

function toggleDay(day: string) {
	const next = new Set(selectedDays.value)
	next.has(day) ? next.delete(day) : next.add(day)
	// Kept in the canonical week order so the string is stable regardless of the
	// order the user clicked in — the server matches on these names.
	draft.value.repeat_on = DAYS.filter((entry) => next.has(entry.full))
		.map((entry) => entry.full)
		.join(',')
}

function save() {
	error.value = ''

	if (Number(draft.value.repeat_every) < 1) {
		error.value = __('Repeat at least every 1 unit.')
		return
	}
	if (draft.value.repeat_ends === 'On Date' && !draft.value.repeat_until) {
		error.value = __('Pick the date the repeat ends on.')
		return
	}
	if (draft.value.repeat_ends === 'After' && Number(draft.value.repeat_count) < 1) {
		error.value = __('Set how many times the event repeats.')
		return
	}

	emit('apply', { ...draft.value, repeat_enabled: 1 })
	emit('update:open', false)
}
</script>
