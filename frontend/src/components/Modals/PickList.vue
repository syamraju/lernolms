<!--
	A searchable checkbox list. Small enough not to earn its own store: the
	selection lives with the caller, and this only draws it and reports clicks.
-->
<template>
	<fieldset class="space-y-2">
		<legend class="text-p-base-medium text-ink-gray-9">
			{{ title }}
			<span v-if="selected.length" class="text-ink-gray-5">
				({{ selected.length }})
			</span>
		</legend>

		<div class="relative">
			<input
				v-model="search"
				type="text"
				:placeholder="searchLabel"
				:aria-label="searchLabel"
				class="w-full rounded-md border border-outline-gray-2 bg-surface-base py-1.5 pe-3 ps-9 text-p-base text-ink-gray-9 transition-colors hover:border-outline-gray-3 focus:border-outline-gray-4 focus:outline-none"
			/>
			<span
				class="lucide-search pointer-events-none absolute start-3 top-1/2 size-4 -translate-y-1/2 text-ink-gray-5"
				aria-hidden="true"
			/>
		</div>

		<p v-if="!visible.length" class="text-p-sm text-ink-gray-6">
			{{ search ? __('Nothing matches "{0}".').format(search) : empty }}
		</p>

		<ul v-else class="max-h-64 space-y-1 overflow-y-auto rounded-md border p-1">
			<li v-for="item in visible" :key="item.value">
				<label
					class="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-p-base text-ink-gray-8 transition-colors hover:bg-surface-gray-1"
				>
					<input
						type="checkbox"
						class="size-4 shrink-0 rounded border-outline-gray-3 text-ink-gray-9 focus:ring-outline-gray-4"
						:checked="selected.includes(item.value)"
						@change="emit('toggle', item.value)"
					/>
					<span class="min-w-0 flex-1 truncate">
						{{ item.label || item.value }}
					</span>
				</label>
			</li>
		</ul>
	</fieldset>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

interface PickItem {
	value: string
	label?: string | null
}

const props = defineProps<{
	title: string
	items: PickItem[]
	selected: string[]
	empty: string
	searchLabel: string
}>()

const emit = defineEmits<{ toggle: [string] }>()

const search = ref('')

const visible = computed(() => {
	const term = search.value.trim().toLowerCase()
	if (!term) return props.items
	return props.items.filter((item) =>
		`${item.label ?? ''} ${item.value}`.toLowerCase().includes(term)
	)
})
</script>
