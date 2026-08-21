<!--
	One person in a call.

	The tile decides what to show from the ROSTER flags, not from whether a
	track happens to be flowing: a camera that is off and a camera that is two
	seconds from producing its first frame look identical at the track level,
	and rendering a black rectangle for the second one reads as broken.
-->
<template>
	<div
		class="relative flex aspect-video min-h-0 items-center justify-center overflow-hidden rounded-[var(--learno-r-md)] bg-[#101828]"
		:class="speakingRing"
	>
		<video
			v-show="showsVideo"
			ref="videoEl"
			class="h-full w-full"
			:class="participant.screensharing ? 'object-contain' : 'object-cover'"
			autoplay
			playsinline
			:muted="isSelf"
		/>

		<div v-if="!showsVideo" class="flex flex-col items-center gap-2">
			<Avatar
				:label="participant.full_name"
				:image="participant.avatar || undefined"
				size="2xl"
			/>
		</div>

		<div
			class="pointer-events-none absolute inset-x-0 bottom-0 flex items-end justify-between gap-2 p-2"
		>
			<span
				class="max-w-[70%] truncate rounded-[var(--learno-r-sm)] bg-black/55 px-2 py-1 text-[12px] font-medium text-white"
			>
				{{ isSelf ? __('You') : participant.full_name }}
				<span v-if="participant.screensharing" class="opacity-75">
					· {{ __('sharing') }}
				</span>
			</span>

			<span
				v-if="participant.muted"
				class="grid size-6 shrink-0 place-items-center rounded-full bg-black/55 text-white"
				:aria-label="__('Muted')"
			>
				<MicOff class="size-3.5" />
			</span>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Avatar } from 'frappe-ui'
import { MicOff } from 'lucide-vue-next'
import type { HuddleParticipant } from '@/composables/useHuddle'

const props = defineProps<{
	participant: HuddleParticipant
	stream: MediaStream | null
	isSelf?: boolean
	speaking?: boolean
}>()

const videoEl = ref<HTMLVideoElement | null>(null)

const showsVideo = computed(
	() =>
		(props.participant.video || props.participant.screensharing) &&
		!!props.stream
)

const speakingRing = computed(() =>
	props.speaking ? 'ring-2 ring-[var(--learno-primary)] ring-offset-1' : ''
)

// srcObject is a property, not an attribute, so it cannot be bound in the
// template. Re-assign whenever the stream identity changes -- the composable
// hands out a new Map on every track change, but the same MediaStream object.
watch(
	[videoEl, () => props.stream],
	([el, stream]) => {
		if (!el) return
		if (el.srcObject !== stream) el.srcObject = stream
	},
	{ immediate: true }
)
</script>
