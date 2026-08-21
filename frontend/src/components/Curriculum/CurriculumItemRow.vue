<template>
	<li class="rounded-md border bg-surface-base">
		<div class="flex flex-wrap items-center gap-2 px-3 py-2">
			<button
				type="button"
				data-item-handle
				class="shrink-0 cursor-grab rounded p-1 text-ink-gray-4 transition-colors hover:text-ink-gray-7 active:cursor-grabbing"
				:aria-label="__('Reorder {0}').format(item.title)"
			>
				<span class="lucide-grip-vertical size-4" />
			</button>

			<span
				class="shrink-0 text-ink-gray-6"
				:class="itemIcon(item.item_type)"
				aria-hidden="true"
			/>

			<span class="shrink-0 text-p-sm text-ink-gray-5">
				{{ __('{0} {1}:').format(__(item.item_type), position) }}
			</span>

			<input
				:value="item.title"
				class="min-w-0 flex-1 rounded border border-transparent bg-transparent px-1 py-0.5 text-p-base text-ink-gray-9 transition-colors hover:border-outline-gray-2 focus:border-outline-gray-4 focus:outline-none"
				:aria-label="__('Item title')"
				@change="onRename"
			/>

			<span
				v-if="duration"
				class="shrink-0 rounded-sm bg-surface-gray-2 px-1.5 py-0.5 text-xs tabular-nums text-ink-gray-6"
			>
				{{ duration }}
			</span>

			<Badge
				:theme="item.is_published ? 'green' : 'orange'"
				:label="item.is_published ? __('Published') : __('Draft')"
			/>

			<Tooltip :text="publishTooltip">
				<Button
					variant="ghost"
					class="!size-8"
					:loading="isBusy(`item-pub:${item.name}`)"
					:disabled="!item.is_published && !publishable.ok"
					:label="
						item.is_published
							? __('Unpublish {0}').format(item.title)
							: __('Publish {0}').format(item.title)
					"
					@click="$emit('toggle-published', item)"
				>
					<template #icon>
						<span
							class="size-4"
							:class="item.is_published ? 'lucide-eye' : 'lucide-eye-off'"
						/>
					</template>
				</Button>
			</Tooltip>

			<Button
				variant="ghost"
				class="!size-8"
				:label="expanded ? __('Collapse') : __('Expand')"
				:aria-expanded="expanded"
				@click="$emit('toggle-expanded', item)"
			>
				<template #icon>
					<span
						class="lucide-chevron-down size-4 transition-transform"
						:class="expanded && 'rotate-180'"
					/>
				</template>
			</Button>

			<Button
				variant="ghost"
				theme="red"
				class="!size-8"
				:loading="isBusy(`item-del:${item.name}`)"
				:label="__('Delete {0}').format(item.title)"
				@click="$emit('delete', item)"
			>
				<template #icon>
					<span class="lucide-trash-2 size-4" />
				</template>
			</Button>
		</div>

		<div v-if="expanded" class="border-t px-4 py-4">
			<slot name="body" />
		</div>
	</li>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Badge, Button, Tooltip } from 'frappe-ui'
import { canPublishItem, itemDuration, itemIcon } from '@/utils/curriculum'
import type { CurriculumItem } from '@/types'

const props = defineProps<{
	item: CurriculumItem
	/** 1-based position among items of the same type in this section. */
	position: number
	expanded: boolean
	isBusy: (key: string) => boolean
}>()

const emit = defineEmits<{
	rename: [{ item: CurriculumItem; title: string }]
	'toggle-published': [CurriculumItem]
	'toggle-expanded': [CurriculumItem]
	delete: [CurriculumItem]
}>()

const duration = computed(() => itemDuration(props.item))
const publishable = computed(() => canPublishItem(props.item))

// A disabled control with no explanation is a dead end, so the reason the item
// cannot go live yet rides on the tooltip.
const publishTooltip = computed(() => {
	if (props.item.is_published) return __('Hide this from learners')
	return publishable.value.ok ? __('Show this to learners') : publishable.value.reason
})

// Emitting rather than mutating keeps this row purely presentational — the
// section above owns every write, so there is one place that talks to the API.
function onRename(event: Event) {
	const input = event.target as HTMLInputElement
	const title = input.value.trim()
	if (!title || title === props.item.title) {
		// Restore the stored title so a cleared field doesn't look saved.
		input.value = props.item.title
		return
	}
	emit('rename', { item: props.item, title })
}
</script>
