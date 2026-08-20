<template>
	<Tooltip :text="`${props.progress}%`">
		<div
			class="w-full bg-surface-gray-3 rounded-full h-1"
			:class="$attrs.class"
		>
			<!-- Cloudscape fills a progress bar with the primary blue on a pale
			     grey track, not near-black on grey. `surface-blue-7` is the ramp
			     position that carries CDS's #006ce0 in light and #42b4ff in dark,
			     which are exactly `background/progress/bar/content/default` in
			     the two modes; the track's `surface-gray-3` is already CDS's
			     `background/progress/bar/layout/default`. -->
			<div
				class="bg-surface-blue-7 rounded-full"
				:class="progressBarHeight"
				:style="{ width: progressBarWidth }"
			></div>
		</div>
	</Tooltip>
</template>

<script setup>
import { computed } from 'vue'
import { Tooltip } from 'frappe-ui'

const props = defineProps({
	progress: {
		type: Number,
		default: 0,
	},
	size: {
		type: String,
		default: 'sm',
	},
})

const progressBarWidth = computed(() => {
	const formattedPercentage = Math.min(Math.ceil(props.progress), 100)
	return `${formattedPercentage}%`
})

const progressBarHeight = computed(() => {
	if (props.size === 'sm') {
		return 'h-1'
	}
	if (props.size === 'md') {
		return 'h-2'
	}
	if (props.size === 'lg') {
		return 'h-3'
	}
})
</script>
