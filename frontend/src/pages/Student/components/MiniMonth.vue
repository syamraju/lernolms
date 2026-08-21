<!--
	The month picker in the calendar rail. Figma: node 136:88179's left column.

	A dot under a date means the calendar has something on it, which is what
	makes the picker worth clicking rather than just scenery.
-->
<template>
	<div>
		<div class="mb-2 flex items-center justify-between">
			<button
				type="button"
				class="rounded p-1 text-[var(--learno-ink-subtle)] hover:bg-black/5"
				:aria-label="__('Previous month')"
				@click="shiftMonth(-1)"
			>
				<span class="lucide-chevron-up size-4" aria-hidden="true" />
			</button>
			<span class="text-[12px] font-semibold">
				{{ view.format('MMMM YYYY') }}
			</span>
			<button
				type="button"
				class="rounded p-1 text-[var(--learno-ink-subtle)] hover:bg-black/5"
				:aria-label="__('Next month')"
				@click="shiftMonth(1)"
			>
				<span class="lucide-chevron-down size-4" aria-hidden="true" />
			</button>
		</div>

		<div class="grid grid-cols-7 gap-y-1 text-center">
			<span
				v-for="label in dayLabels"
				:key="label"
				class="text-[10px] text-[var(--learno-ink-subtle)]"
			>
				{{ label }}
			</span>

			<button
				v-for="day in days"
				:key="day.iso"
				type="button"
				class="relative mx-auto grid size-6 place-items-center rounded-full text-[10px] transition"
				:class="dayClass(day)"
				@click="$emit('update:modelValue', day.value)"
			>
				{{ day.number }}
				<span
					v-if="marked.has(day.iso)"
					class="absolute -bottom-0.5 size-1 rounded-full bg-[var(--learno-primary)]"
					aria-hidden="true"
				/>
			</button>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, inject, ref, watch } from 'vue'

const dayjs = inject<any>('$dayjs')

const props = defineProps<{ modelValue: any; marked: Set<string> }>()
defineEmits<{ (e: 'update:modelValue', value: any): void }>()

// The month on screen tracks the selection but can also be paged past it, so it
// is its own ref rather than a computed off `modelValue`.
const view = ref(props.modelValue.startOf('month'))

watch(
	() => props.modelValue,
	(value) => {
		if (!value.isSame(view.value, 'month')) {
			view.value = value.startOf('month')
		}
	}
)

const dayLabels = computed(() =>
	Array.from({ length: 7 }, (_, index) =>
		dayjs().startOf('week').add(index, 'day').format('dd')
	)
)

// Six rows, always: a month grid that changes height makes the rail below it
// jump as you page through the year.
const days = computed(() => {
	const first = view.value.startOf('month').startOf('week')
	return Array.from({ length: 42 }, (_, index) => {
		const value = first.add(index, 'day')
		return {
			value,
			iso: value.format('YYYY-MM-DD'),
			number: value.date(),
			outside: !value.isSame(view.value, 'month'),
			isToday: value.isSame(dayjs(), 'day'),
			isSelected: value.isSame(props.modelValue, 'day'),
		}
	})
})

function dayClass(day: any) {
	if (day.isSelected)
		return 'bg-[var(--learno-primary)] text-white font-semibold'
	if (day.isToday) return 'text-[var(--learno-primary)] font-semibold'
	if (day.outside) return 'text-[#c9ccd6]'
	return 'text-[var(--learno-ink)] hover:bg-black/5'
}

function shiftMonth(months: number) {
	view.value = view.value.add(months, 'month')
}
</script>
