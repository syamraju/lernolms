<!--
	The call itself, floating over whatever page you are on.

	Deliberately app-level rather than part of the chat page: a call you have to
	stay on one screen to keep is a call you hang up by accident. Walking off to
	a course while talking is the normal thing to do, so the dock follows.
-->
<template>
	<Teleport to="body">
		<section
			v-if="huddle.active.value"
			class="fixed bottom-4 end-4 z-40 flex flex-col overflow-hidden rounded-[var(--learno-r-lg)] border border-[var(--learno-line)] bg-white shadow-[0_18px_40px_rgba(16,24,40,0.18)]"
			:class="
				expanded
					? 'w-[min(680px,calc(100vw-2rem))]'
					: 'w-[min(320px,calc(100vw-2rem))]'
			"
			role="region"
			:aria-label="__('Call')"
		>
			<header
				class="flex shrink-0 items-center gap-2 border-b border-[var(--learno-line-soft)] px-3 py-2.5"
			>
				<span
					class="grid size-6 shrink-0 place-items-center rounded-full"
					:class="
						huddle.status.value === 'live'
							? 'bg-[var(--learno-primary-soft)] text-[var(--learno-primary)]'
							: 'bg-[var(--learno-canvas)] text-[var(--learno-ink-subtle)]'
					"
				>
					<Headphones class="size-3.5" />
				</span>

				<div class="min-w-0 flex-1">
					<p
						class="truncate text-[13px] font-semibold text-[var(--learno-ink-strong)]"
					>
						{{ title || __('Call') }}
					</p>
					<p class="text-[11px] text-[var(--learno-ink-subtle)]">
						{{ subtitle }}
					</p>
				</div>

				<button
					type="button"
					class="learno-huddle-ghost"
					:title="expanded ? __('Minimise') : __('Expand')"
					@click="expanded = !expanded"
				>
					<Minus v-if="expanded" class="size-4" />
					<Maximize2 v-else class="size-4" />
					<span class="sr-only">
						{{ expanded ? __('Minimise') : __('Expand') }}
					</span>
				</button>
			</header>

			<p
				v-if="huddle.error.value"
				class="shrink-0 bg-[var(--learno-primary-soft)] px-3 py-2 text-[12px] text-[var(--learno-primary)]"
			>
				{{ huddle.error.value }}
			</p>

			<div
				v-if="expanded"
				class="learno-scroll grid max-h-[46vh] shrink-0 gap-2 overflow-y-auto p-3"
				:class="gridClass"
			>
				<HuddleTile
					v-for="participant in huddle.roster.value"
					:key="participant.peer_id"
					:participant="participant"
					:stream="streamFor(participant)"
					:is-self="participant.user === currentUser"
				/>
			</div>

			<footer
				class="flex shrink-0 items-center justify-between gap-2 border-t border-[var(--learno-line-soft)] px-3 py-2.5"
			>
				<div v-if="!expanded" class="flex -space-x-2">
					<Avatar
						v-for="participant in huddle.roster.value.slice(0, 4)"
						:key="participant.peer_id"
						:label="participant.full_name"
						:image="participant.avatar || undefined"
						size="sm"
						class="ring-2 ring-white"
					/>
				</div>
				<span v-else class="text-[12px] text-[var(--learno-ink-subtle)]">
					{{ statusLabel }}
				</span>

				<HuddleControls
					:muted="huddle.muted.value"
					:camera-on="huddle.cameraOn.value"
					:screensharing="huddle.screensharing.value"
					@toggle-mute="huddle.toggleMute()"
					@toggle-camera="huddle.toggleCamera()"
					@toggle-screenshare="huddle.toggleScreenshare()"
					@leave="huddle.leave()"
				/>
			</footer>
		</section>
	</Teleport>
</template>

<script setup lang="ts">
import { computed, inject, ref } from 'vue'
import { Avatar } from 'frappe-ui'
import { Headphones, Maximize2, Minus } from 'lucide-vue-next'
import HuddleControls from './HuddleControls.vue'
import HuddleTile from './HuddleTile.vue'
import type { HuddleParticipant } from '@/composables/useHuddle'
import { sessionStore } from '@/stores/session'

const props = defineProps<{
	/** A human label for the thread being called, resolved by whoever knows it. */
	titles?: Record<string, string>
}>()

const huddle = inject<any>('$huddle')
const { user } = sessionStore()
const currentUser = user

const expanded = ref(true)

const title = computed(() => props.titles?.[huddle.conversation.value] || '')

const statusLabel = computed(() =>
	huddle.status.value === 'joining' ? __('Connecting…') : __('In call')
)

const subtitle = computed(() => {
	const count = huddle.roster.value.length
	if (huddle.status.value === 'joining') return __('Connecting…')
	return count === 1
		? __('Just you — waiting for others')
		: __('{0} people').format(count)
})

// Two columns from two people up; a single tile gets the full width so a 1:1
// call is not a postage stamp in a wide panel.
const gridClass = computed(() =>
	huddle.roster.value.length > 1 ? 'grid-cols-2' : 'grid-cols-1'
)

function streamFor(participant: HuddleParticipant): MediaStream | null {
	if (participant.user === currentUser) return huddle.localStream.value
	return huddle.remoteStreams.value.get(participant.user) || null
}
</script>
