<!--
	One row in the batch channel tree. Sub-channels indent; nothing nests deeper,
	because LMSChatChannel.validate_depth refuses a third level.
-->
<template>
	<button
		type="button"
		class="w-full text-start rounded-md px-2 py-1.5 mb-0.5 flex items-center gap-2 transition"
		:class="[
			nested ? 'ps-6' : '',
			active ? 'bg-surface-gray-3 text-ink-gray-9' : 'hover:bg-surface-gray-2',
		]"
		@click="$emit('select', channel.name)"
	>
		<span class="text-ink-gray-5 shrink-0">#</span>
		<span
			class="truncate flex-1 text-sm"
			:class="channel.is_archived ? 'text-ink-gray-5' : ''"
		>
			{{ channel.title }}
		</span>
		<Badge v-if="channel.unread" theme="blue" size="sm">
			{{ channel.unread }}
		</Badge>
		<span
			v-else-if="channel.is_archived"
			class="lucide-archive size-3.5 text-ink-gray-5 shrink-0"
		/>
	</button>
</template>

<script setup>
import { Badge } from 'frappe-ui'

defineProps({
	channel: { type: Object, required: true },
	active: { type: Boolean, default: false },
	nested: { type: Boolean, default: false },
})

defineEmits(['select'])
</script>
