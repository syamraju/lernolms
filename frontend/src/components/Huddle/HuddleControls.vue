<!--
	The call's controls. Mic and camera read as pressed when they are OFF,
	because that is the state worth noticing -- a muted mic you cannot see is
	the single most common thing to get wrong in a call.
-->
<template>
	<div class="flex items-center gap-2">
		<button
			type="button"
			class="learno-huddle-btn"
			:class="muted ? 'learno-huddle-btn--danger' : ''"
			:aria-pressed="muted"
			:title="muted ? __('Unmute') : __('Mute')"
			@click="$emit('toggle-mute')"
		>
			<MicOff v-if="muted" class="size-4" />
			<Mic v-else class="size-4" />
			<span class="sr-only">{{ muted ? __('Unmute') : __('Mute') }}</span>
		</button>

		<button
			type="button"
			class="learno-huddle-btn"
			:class="cameraOn ? '' : 'learno-huddle-btn--danger'"
			:aria-pressed="!cameraOn"
			:title="cameraOn ? __('Turn camera off') : __('Turn camera on')"
			@click="$emit('toggle-camera')"
		>
			<Video v-if="cameraOn" class="size-4" />
			<VideoOff v-else class="size-4" />
			<span class="sr-only">
				{{ cameraOn ? __('Turn camera off') : __('Turn camera on') }}
			</span>
		</button>

		<button
			v-if="screenshareSupported"
			type="button"
			class="learno-huddle-btn"
			:class="screensharing ? 'learno-huddle-btn--active' : ''"
			:aria-pressed="screensharing"
			:title="screensharing ? __('Stop sharing') : __('Share screen')"
			@click="$emit('toggle-screenshare')"
		>
			<MonitorUp class="size-4" />
			<span class="sr-only">
				{{ screensharing ? __('Stop sharing') : __('Share screen') }}
			</span>
		</button>

		<button
			type="button"
			class="learno-huddle-btn learno-huddle-btn--leave"
			:title="__('Leave call')"
			@click="$emit('leave')"
		>
			<PhoneOff class="size-4" />
			<span class="text-[13px] font-medium">{{ __('Leave') }}</span>
		</button>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import {
	Mic,
	MicOff,
	MonitorUp,
	PhoneOff,
	Video,
	VideoOff,
} from 'lucide-vue-next'

defineProps<{
	muted: boolean
	cameraOn: boolean
	screensharing: boolean
}>()

defineEmits<{
	(e: 'toggle-mute'): void
	(e: 'toggle-camera'): void
	(e: 'toggle-screenshare'): void
	(e: 'leave'): void
}>()

// getDisplayMedia is absent on most mobile browsers. Offering a button that
// can only fail is worse than not offering it.
const screenshareSupported = computed(
	() =>
		typeof navigator !== 'undefined' &&
		!!navigator.mediaDevices?.getDisplayMedia
)
</script>
