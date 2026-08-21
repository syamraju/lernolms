<!--
	A 1:1 thread.

	Message bodies are rendered as TEXT, never as HTML — the field is plain text
	end to end, so there is no sanitizer to get wrong and no markup a sender can
	smuggle through. System messages ("Huddle started") are centred and unowned,
	because attributing them to whoever triggered them reads as if they typed it.
-->
<template>
	<div class="flex h-full min-h-0 flex-col">
		<div
			ref="scroller"
			class="learno-scroll min-h-0 flex-1 overflow-y-auto px-4 py-4 lg:px-6"
		>
			<p
				v-if="messages.loading && !rows.length"
				class="py-10 text-center text-[13px] text-[var(--learno-ink-subtle)]"
			>
				{{ __('Loading…') }}
			</p>

			<p
				v-else-if="!rows.length"
				class="py-16 text-center text-[13px] text-[var(--learno-ink-subtle)]"
			>
				{{ __('No messages yet. Say hello.') }}
			</p>

			<ul v-else class="flex flex-col gap-3">
				<li v-for="message in rows" :key="message.name">
					<p
						v-if="message.message_type === 'System'"
						class="text-center text-[12px] text-[var(--learno-ink-subtle)]"
					>
						{{ message.content }}
					</p>

					<div
						v-else
						class="flex items-end gap-2"
						:class="isMine(message) ? 'flex-row-reverse' : ''"
					>
						<Avatar
							:label="message.full_name"
							:image="message.avatar || undefined"
							size="sm"
							class="shrink-0"
						/>
						<div
							class="max-w-[min(70%,32rem)] rounded-[var(--learno-r-md)] px-3 py-2"
							:class="
								isMine(message)
									? 'bg-[var(--learno-primary)] text-white'
									: 'bg-white text-[var(--learno-ink-strong)]'
							"
						>
							<p
								class="whitespace-pre-wrap break-words text-[13px] leading-[1.5]"
							>
								{{ message.content }}
							</p>
							<p
								class="mt-1 text-[10px]"
								:class="
									isMine(message)
										? 'text-white/70'
										: 'text-[var(--learno-ink-subtle)]'
								"
							>
								{{ timeAgo(message.creation) }}
							</p>
						</div>
					</div>
				</li>
			</ul>
		</div>

		<form
			class="flex shrink-0 items-end gap-2 border-t border-[var(--learno-line-soft)] bg-white px-4 py-3 lg:px-6"
			@submit.prevent="send"
		>
			<textarea
				v-model="draft"
				rows="1"
				:placeholder="__('Write a message')"
				class="learno-scroll max-h-32 min-h-[38px] flex-1 resize-none rounded-[var(--learno-r-md)] border border-[var(--learno-line)] px-3 py-2 text-[13px] outline-none focus:border-[var(--learno-primary)]"
				@keydown.enter.exact.prevent="send"
			/>
			<Button
				variant="solid"
				:disabled="!draft.trim() || sending"
				@click="send"
			>
				{{ __('Send') }}
			</Button>
		</form>
	</div>
</template>

<script setup lang="ts">
import {
	computed,
	inject,
	nextTick,
	onMounted,
	onUnmounted,
	ref,
	watch,
} from 'vue'
import { Avatar, Button, call, createResource } from 'frappe-ui'
import { timeAgo } from '@/utils'
import { sessionStore } from '@/stores/session'

const props = defineProps<{ conversation: string }>()

const socket = inject<any>('$socket')
const { user } = sessionStore()

const draft = ref('')
const sending = ref(false)
const scroller = ref<HTMLElement | null>(null)
const live = ref<any[]>([])

const messages = createResource({
	url: 'lms.lms.direct_message.get_messages',
	makeParams: () => ({ conversation: props.conversation }),
	auto: true,
})

// The fetched page plus anything that arrived over the socket since. Kept
// separate so a refetch does not have to reconcile against optimistic rows.
const rows = computed(() => [...(messages.data || []), ...live.value])

const isMine = (message: any) => message.sender === user

async function send() {
	const content = draft.value.trim()
	if (!content || sending.value) return

	sending.value = true
	draft.value = ''
	try {
		await call('lms.lms.direct_message.send_message', {
			conversation: props.conversation,
			content,
		})
	} catch (e) {
		// Put the text back rather than losing it to a failed request.
		draft.value = content
	} finally {
		sending.value = false
	}
}

function scrollToEnd() {
	nextTick(() => {
		const el = scroller.value
		if (el) el.scrollTop = el.scrollHeight
	})
}

function onMessage(message: any) {
	if (message.conversation !== props.conversation) return
	if (rows.value.some((m) => m.name === message.name)) return
	live.value = [...live.value, message]
	scrollToEnd()
}

watch(
	() => props.conversation,
	() => {
		live.value = []
		messages.reload()
		void call('lms.lms.direct_message.mark_read', {
			conversation: props.conversation,
		}).catch(() => {})
	}
)

watch(() => messages.data, scrollToEnd)

onMounted(() => {
	socket?.on('lms_direct_message', onMessage)
	void call('lms.lms.direct_message.mark_read', {
		conversation: props.conversation,
	}).catch(() => {})
})

onUnmounted(() => socket?.off('lms_direct_message', onMessage))
</script>
