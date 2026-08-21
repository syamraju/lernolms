<!--
	"There's a call happening here" — the in-thread bar.

	Shown to people who are NOT in the call; the moment you join, the dock takes
	over and this collapses to a line saying where you are, so the thread never
	shows two competing sets of call controls.
-->
<template>
	<div
		v-if="inThisCall"
		class="flex items-center gap-2 border-b border-[var(--learno-line-soft)] bg-[var(--learno-primary-soft)] px-4 py-2 text-[13px] text-[var(--learno-primary)] lg:px-6"
	>
		<Headphones class="size-4 shrink-0" />
		<span class="min-w-0 flex-1 truncate font-medium">
			{{ __('You are in this call') }}
		</span>
		<button type="button" class="learno-huddle-link" @click="$emit('leave')">
			{{ __('Leave') }}
		</button>
	</div>

	<div
		v-else-if="active"
		class="flex items-center gap-3 border-b border-[var(--learno-line-soft)] bg-[var(--learno-canvas)] px-4 py-2 lg:px-6"
	>
		<span
			class="grid size-7 shrink-0 place-items-center rounded-full bg-[var(--learno-primary-soft)] text-[var(--learno-primary)]"
		>
			<Headphones class="size-4" />
		</span>

		<div class="min-w-0 flex-1">
			<p
				class="truncate text-[13px] font-medium text-[var(--learno-ink-strong)]"
			>
				{{ __('Call in progress') }}
			</p>
			<p class="truncate text-[11px] text-[var(--learno-ink-subtle)]">
				{{ names }}
			</p>
		</div>

		<Button variant="solid" size="sm" @click="$emit('join')">
			{{ __('Join') }}
		</Button>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Button } from 'frappe-ui'
import { Headphones } from 'lucide-vue-next'

const props = defineProps<{
	active?: {
		participant_count: number
		participants: { full_name: string }[]
	} | null
	inThisCall?: boolean
}>()

defineEmits<{ (e: 'join'): void; (e: 'leave'): void }>()

const names = computed(() => {
	const people = props.active?.participants || []
	if (!people.length) return ''
	const shown = people.slice(0, 3).map((p) => p.full_name)
	const rest = people.length - shown.length
	return rest > 0
		? __('{0} and {1} more').format(shown.join(', '), rest)
		: shown.join(', ')
})
</script>
