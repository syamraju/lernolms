<!--
	Someone is calling you.

	No missed-call record behind this on purpose: a ring you were not at the
	keyboard for is a chat message's job, and the caller can send one. The toast
	expires on its own so a call answered elsewhere does not leave a stale
	"Answer" button on the screen.
-->
<template>
	<Teleport to="body">
		<div
			v-if="ring"
			class="fixed top-4 end-4 z-50 flex w-[min(340px,calc(100vw-2rem))] items-center gap-3 rounded-[var(--learno-r-lg)] border border-[var(--learno-line)] bg-white p-3 shadow-[0_18px_40px_rgba(16,24,40,0.18)]"
			role="alert"
		>
			<Avatar
				:label="ring.from.full_name"
				:image="ring.from.avatar || undefined"
				size="xl"
				class="animate-pulse"
			/>

			<div class="min-w-0 flex-1">
				<p class="truncate text-[13px] font-semibold text-[var(--learno-ink-strong)]">
					{{ ring.from.full_name }}
				</p>
				<p class="text-[12px] text-[var(--learno-ink-subtle)]">
					{{ __('Incoming call') }}
				</p>
			</div>

			<button
				type="button"
				class="learno-huddle-btn learno-huddle-btn--leave"
				:title="__('Decline')"
				@click="dismiss"
			>
				<PhoneOff class="size-4" />
				<span class="sr-only">{{ __('Decline') }}</span>
			</button>

			<button
				type="button"
				class="learno-huddle-btn learno-huddle-btn--answer"
				:title="__('Answer')"
				@click="answer"
			>
				<Phone class="size-4" />
				<span class="sr-only">{{ __('Answer') }}</span>
			</button>
		</div>
	</Teleport>
</template>

<script setup lang="ts">
import { inject, onMounted, onUnmounted, ref } from 'vue'
import { Avatar } from 'frappe-ui'
import { Phone, PhoneOff } from 'lucide-vue-next'

interface Ring {
	conversation: string
	from: { user: string; full_name: string; avatar: string | null }
}

const RING_TIMEOUT = 45000

const socket = inject<any>('$socket')
const huddle = inject<any>('$huddle')

const ring = ref<Ring | null>(null)
let expiry: number | undefined

function dismiss() {
	ring.value = null
	if (expiry) window.clearTimeout(expiry)
	expiry = undefined
}

async function answer() {
	const target = ring.value?.conversation
	dismiss()
	if (target) await huddle.join(target)
}

function onRing(payload: Ring) {
	// Already in the call being rung? Then this is a second person joining, not
	// an invitation.
	if (huddle.active.value && huddle.conversation.value === payload.conversation) return

	ring.value = payload
	if (expiry) window.clearTimeout(expiry)
	expiry = window.setTimeout(dismiss, RING_TIMEOUT)
}

onMounted(() => socket?.on('lms_huddle_ring', onRing))
onUnmounted(() => {
	socket?.off('lms_huddle_ring', onRing)
	if (expiry) window.clearTimeout(expiry)
})
</script>
