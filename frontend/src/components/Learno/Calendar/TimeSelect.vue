<!--
	The time field and its dropdown. Figma: node 161:40903 — a scrolling list of
	half-hour options, each with the resulting duration beside it.

	The duration hint is the reason this is not a plain <select>: it is computed
	against the *other* end of the range, so the list has to know whether it is
	the start or the end field and what the counterpart currently holds.
-->
<template>
	<div ref="root" class="relative">
		<button
			type="button"
			class="w-full rounded-[var(--learno-r-sm)] border border-[var(--learno-line)] bg-white px-4 py-2.5 text-[13px] text-[var(--learno-ink)] transition hover:border-[#d8dae3]"
			:aria-expanded="open"
			aria-haspopup="listbox"
			@click="open = !open"
		>
			{{ label || placeholder }}
		</button>

		<ul
			v-if="open"
			class="learno-scroll absolute z-30 mt-1 max-h-[280px] w-full overflow-y-auto rounded-[var(--learno-r-md)] border border-[var(--learno-line)] bg-white p-2 shadow-xl"
			role="listbox"
		>
			<li v-for="option in options" :key="option.value">
				<button
					type="button"
					role="option"
					:aria-selected="option.value === modelValue"
					class="flex w-full items-center justify-between gap-3 rounded-[var(--learno-r-sm)] border px-3 py-2 text-[13px] transition"
					:class="
						option.value === modelValue
							? 'border-transparent bg-[var(--learno-primary)] text-white'
							: 'border-[var(--learno-line)] text-[var(--learno-ink)] hover:bg-[var(--learno-canvas)]'
					"
					@click="pick(option.value)"
				>
					<span>{{ option.label }}</span>
					<span
						v-if="option.hint"
						:class="
							option.value === modelValue
								? 'text-white/80'
								: 'text-[var(--learno-ink-subtle)]'
						"
					>
						{{ option.hint }}
					</span>
				</button>
			</li>
		</ul>
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

const props = withDefaults(
	defineProps<{
		/** "HH:mm:ss" */
		modelValue: string
		/** The other end of the range, used only for the duration hint. */
		counterpart?: string
		/** 'start' measures forward to the counterpart, 'end' measures back from it. */
		edge?: 'start' | 'end'
		stepMinutes?: number
		placeholder?: string
	}>(),
	{ edge: 'start', stepMinutes: 30, placeholder: '--:--' }
)

const emit = defineEmits<{ (e: 'update:modelValue', value: string): void }>()

const root = ref<HTMLElement | null>(null)
const open = ref(false)

function toMinutes(value?: string) {
	if (!value) return null
	const [h, m] = value.split(':').map(Number)
	if (Number.isNaN(h) || Number.isNaN(m)) return null
	return h * 60 + m
}

function toClock(minutes: number) {
	return `${String(Math.floor(minutes / 60)).padStart(2, '0')}:${String(
		minutes % 60
	).padStart(2, '0')}:00`
}

function toLabel(minutes: number) {
	const hour24 = Math.floor(minutes / 60)
	const suffix = hour24 < 12 ? 'AM' : 'PM'
	const hour12 = hour24 % 12 === 0 ? 12 : hour24 % 12
	return `${String(hour12).padStart(2, '0')}:${String(minutes % 60).padStart(
		2,
		'0'
	)} ${suffix}`
}

const label = computed(() => {
	const minutes = toMinutes(props.modelValue)
	return minutes === null ? '' : toLabel(minutes)
})

const options = computed(() => {
	const other = toMinutes(props.counterpart)
	const out = []
	for (let at = 0; at < 24 * 60; at += props.stepMinutes) {
		// The hint is only meaningful when it describes a forward-running range;
		// an option that would invert the range simply carries no hint.
		let hint = ''
		if (other !== null) {
			const span = props.edge === 'start' ? other - at : at - other
			if (span > 0) hint = formatSpan(span)
		}
		out.push({ value: toClock(at), label: toLabel(at), hint })
	}
	return out
})

function formatSpan(minutes: number) {
	const hours = Math.floor(minutes / 60)
	const rest = minutes % 60
	if (!hours) return `${rest} min`
	if (!rest) return hours === 1 ? __('1 hr') : `${hours} hrs`
	return `${hours}h ${rest}m`
}

function pick(value: string) {
	emit('update:modelValue', value)
	open.value = false
}

// Click-away rather than a blur handler: blur fires before the option's click
// lands, which would close the list without ever selecting anything.
function onDocumentClick(event: MouseEvent) {
	if (!open.value) return
	if (!root.value?.contains(event.target as Node)) open.value = false
}

onMounted(() => document.addEventListener('click', onDocumentClick))
onBeforeUnmount(() => document.removeEventListener('click', onDocumentClick))
</script>
