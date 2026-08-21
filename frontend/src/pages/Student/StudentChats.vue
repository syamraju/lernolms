<!--
	Chats.

	Two kinds of thread in one list: the batch discussions the LMS already had,
	and direct 1:1 threads this page adds. Both are addressed the same way — a
	conversation id — which is what lets the call buttons in the header work the
	same for either without knowing which one it is looking at.

	The call itself is not rendered here. It belongs to the app shell (see
	App.vue), so walking off to a course mid-call does not hang up.
-->
<template>
	<div class="flex h-full min-h-0 flex-col">
		<header
			class="shrink-0 border-b border-[var(--learno-line-soft)] bg-white px-6 py-[22px] lg:px-10"
		>
			<h1 class="text-[27px] font-semibold leading-[1.2] text-black max-lg:ps-12">
				{{ __('Chats') }}
			</h1>
			<p class="mt-1 text-[13px] text-[var(--learno-ink-muted)]">
				{{ __('Message your batch or anyone in it, and call them without leaving the page.') }}
			</p>
		</header>

		<div class="flex min-h-0 flex-1">
			<aside
				class="learno-scroll w-[280px] shrink-0 overflow-y-auto border-e border-[var(--learno-line-soft)] bg-white p-3 max-lg:hidden"
			>
				<div class="mb-2 flex items-center justify-between px-2">
					<h2 class="text-[11px] font-semibold uppercase tracking-wide text-[var(--learno-ink-subtle)]">
						{{ __('Direct messages') }}
					</h2>
					<button
						type="button"
						class="learno-huddle-ghost"
						:title="__('New message')"
						@click="showPeoplePicker = true"
					>
						<Plus class="size-4" />
						<span class="sr-only">{{ __('New message') }}</span>
					</button>
				</div>

				<p
					v-if="!directThreads.length"
					class="mb-4 px-2 text-[12px] text-[var(--learno-ink-subtle)]"
				>
					{{ __('No direct messages yet.') }}
				</p>

				<button
					v-for="thread in directThreads"
					:key="thread.conversation"
					type="button"
					class="learno-chat-row"
					:class="rowClass(thread.conversation)"
					@click="select(thread.conversation)"
				>
					<Avatar
						:label="thread.peer.full_name"
						:image="thread.peer.avatar || undefined"
						size="md"
						class="shrink-0"
					/>
					<span class="min-w-0 flex-1">
						<span class="block truncate text-[13px] font-medium">
							{{ thread.peer.full_name }}
						</span>
						<span class="block truncate text-[11px] text-[var(--learno-ink-subtle)]">
							{{ preview(thread) }}
						</span>
					</span>
					<CallDot v-if="activeCalls[thread.conversation]" />
					<span v-else-if="thread.unread" class="learno-chat-unread">
						{{ thread.unread }}
					</span>
				</button>

				<h2
					class="mb-2 mt-5 px-2 text-[11px] font-semibold uppercase tracking-wide text-[var(--learno-ink-subtle)]"
				>
					{{ __('Batches') }}
				</h2>

				<p
					v-if="!myBatches.length && !batches.loading"
					class="px-2 text-[12px] text-[var(--learno-ink-subtle)]"
				>
					{{ __('You are not enrolled in any batch yet.') }}
				</p>

				<button
					v-for="batch in myBatches"
					:key="batch.conversation"
					type="button"
					class="learno-chat-row"
					:class="rowClass(batch.conversation)"
					@click="select(batch.conversation)"
				>
					<span class="min-w-0 flex-1">
						<span class="block truncate text-[13px] font-medium">{{ batch.title }}</span>
						<span
							v-if="batch.start_date"
							class="block text-[11px] text-[var(--learno-ink-subtle)]"
						>
							{{ batch.start_date }}
						</span>
					</span>
					<CallDot v-if="activeCalls[batch.conversation]" />
				</button>
			</aside>

			<div class="flex min-w-0 flex-1 flex-col bg-[var(--learno-canvas)]">
				<template v-if="selected">
					<div
						class="flex shrink-0 items-center gap-3 border-b border-[var(--learno-line-soft)] bg-white px-4 py-3 lg:px-6"
					>
						<div class="min-w-0 flex-1">
							<p class="truncate text-[15px] font-semibold text-[var(--learno-ink-strong)]">
								{{ selectedTitle }}
							</p>
							<p class="truncate text-[12px] text-[var(--learno-ink-subtle)]">
								{{ selectedSubtitle }}
							</p>
						</div>

						<button
							type="button"
							class="learno-huddle-btn"
							:disabled="inThisCall"
							:title="__('Start an audio call')"
							@click="startCall(false)"
						>
							<Phone class="size-4" />
							<span class="sr-only">{{ __('Start an audio call') }}</span>
						</button>

						<button
							type="button"
							class="learno-huddle-btn"
							:disabled="inThisCall"
							:title="__('Start a video call')"
							@click="startCall(true)"
						>
							<Video class="size-4" />
							<span class="sr-only">{{ __('Start a video call') }}</span>
						</button>
					</div>

					<HuddleBanner
						:active="activeCalls[selected] || null"
						:in-this-call="inThisCall"
						@join="startCall(false)"
						@leave="huddle.leave()"
					/>

					<DirectThread
						v-if="isDirect"
						:key="selected"
						:conversation="selected"
						class="min-h-0 flex-1"
					/>

					<div
						v-else-if="isBatch"
						class="learno-scroll min-h-0 flex-1 overflow-y-auto p-6 lg:p-8"
					>
						<div class="rounded-[var(--learno-r-lg)] bg-white p-6">
							<Discussions
								:key="selected"
								:title="__('Discussions')"
								doctype="LMS Batch"
								:docname="selectedKey"
								:emptyStateTitle="__('No messages yet')"
								:emptyStateText="__('Start a discussion')"
							/>
						</div>
					</div>

					<!-- A live class has no thread of its own: it is a room, and the
					     only thing to do here is be in it. -->
					<div v-else class="flex min-h-0 flex-1 items-center justify-center p-8">
						<p class="max-w-sm text-center text-[13px] text-[var(--learno-ink-muted)]">
							{{ __('This is a live class room. Use the call buttons above to join.') }}
						</p>
					</div>
				</template>

				<p v-else class="py-20 text-center text-[14px] text-[var(--learno-ink-muted)]">
					{{ __('Pick a conversation to open it.') }}
				</p>
			</div>
		</div>

		<NewDirectMessage v-model="showPeoplePicker" @picked="onPicked" />
	</div>
</template>

<script setup lang="ts">
import { computed, inject, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Avatar, call, createResource, usePageMeta } from 'frappe-ui'
import { Phone, Plus, Video } from 'lucide-vue-next'
import Discussions from '@/components/Discussions.vue'
import DirectThread from '@/components/Chat/DirectThread.vue'
import NewDirectMessage from '@/components/Chat/NewDirectMessage.vue'
import HuddleBanner from '@/components/Huddle/HuddleBanner.vue'
import CallDot from '@/components/Huddle/CallDot.vue'

usePageMeta(() => ({ title: __('Chats') }))

const route = useRoute()
const router = useRouter()
const huddle = inject<any>('$huddle')
const huddleTitles = inject<Record<string, string>>('$huddleTitles', {})
const socket = inject<any>('$socket')

const selected = ref('')
const showPeoplePicker = ref(false)
const activeCalls = ref<Record<string, any>>({})
// A thread opened from the people picker has no messages yet, so it is not in
// get_conversations. Held here until it does.
const pendingThreads = ref<any[]>([])
// A thread arrived at by deep link -- a live class, a ring, a calendar entry --
// which the sidebar has never listed. Kept out of the sidebar (it is not one of
// your threads) but rendered in full.
const linked = ref<any>(null)

// The student_api variant, not lms.lms.api's: that one substitutes upcoming
// published batches when the student has none, which would list threads they
// are not a member of.
const batches = createResource({ url: 'lms.lms.student_api.get_my_batches', auto: true })
const conversations = createResource({ url: 'lms.lms.direct_message.get_conversations', auto: true })

const myBatches = computed(() =>
	(batches.data || []).map((batch: any) => ({
		conversation: `batch:${batch.name}`,
		name: batch.name,
		title: batch.title || batch.name,
		start_date: batch.start_date,
	}))
)

const directThreads = computed(() => {
	const fetched = conversations.data || []
	const known = new Set(fetched.map((t: any) => t.conversation))
	return [...fetched, ...pendingThreads.value.filter((t) => !known.has(t.conversation))]
})

const isDirect = computed(() => selected.value.startsWith('dm:'))
const isBatch = computed(() => selected.value.startsWith('batch:'))
const selectedKey = computed(() => selected.value.split(/:(.*)/s)[1] || '')

const selectedTitle = computed(() => {
	if (!selected.value) return ''
	if (isDirect.value) {
		const thread = directThreads.value.find((t: any) => t.conversation === selected.value)
		if (thread) return thread.peer.full_name
	}
	const batch = myBatches.value.find((b) => b.conversation === selected.value)
	if (batch) return batch.title
	if (linked.value?.conversation === selected.value) return linked.value.title
	return selectedKey.value
})

const selectedSubtitle = computed(() => {
	const active = activeCalls.value[selected.value]
	if (active) return __('{0} in a call').format(active.participant_count)
	if (isDirect.value) return __('Direct message')
	if (isBatch.value) return __('Batch discussion')
	return __('Live class')
})

const inThisCall = computed(
	() => huddle.active.value && huddle.conversation.value === selected.value
)

function rowClass(conversation: string) {
	return selected.value === conversation
		? 'bg-[var(--learno-primary-soft)] text-[var(--learno-primary)]'
		: 'hover:bg-[var(--learno-canvas)]'
}

function preview(thread: any) {
	const last = thread.last_message
	if (!last) return __('No messages yet')
	return last.content
}

function select(conversation: string) {
	selected.value = conversation
}

function onPicked(conversation: string, person: any) {
	pendingThreads.value = [
		{ conversation, kind: 'dm', peer: person, last_message: null, unread: 0 },
		...pendingThreads.value,
	]
	selected.value = conversation
}

async function startCall(video: boolean) {
	const target = selected.value
	if (!target) return

	await huddle.join(target, { video })
	// A batch call announces itself with a badge everyone in the thread sees; a
	// 1:1 has nobody watching a badge, so it has to ring.
	if (target.startsWith('dm:')) {
		await call('lms.lms.huddle.ring', { conversation: target }).catch(() => {})
	}
}

async function refreshActive() {
	const ids = [
		...myBatches.value.map((b) => b.conversation),
		...directThreads.value.map((t: any) => t.conversation),
	]
	if (!ids.length) return
	activeCalls.value = await call('lms.lms.huddle.get_active', { conversations: ids }).catch(
		() => activeCalls.value
	)
}

function onLifecycle(payload: any) {
	const next = { ...activeCalls.value }
	if (payload.active) {
		next[payload.conversation] = {
			...(next[payload.conversation] || { participants: [] }),
			participant_count: payload.participant_count,
			active: true,
		}
	} else {
		delete next[payload.conversation]
	}
	activeCalls.value = next
	// The lifecycle frame carries a count but not who; refetch for the faces.
	void refreshActive()
}

// Open something on arrival: a two-pane view whose right pane is empty reads as
// broken rather than as a prompt.
watch([myBatches, directThreads], () => {
	if (selected.value) return
	const first = directThreads.value[0]?.conversation || myBatches.value[0]?.conversation
	if (first) selected.value = first
})

watch([myBatches, directThreads], refreshActive)

// The dock outlives this page, so hand it the name of whatever we opened.
watch([selected, selectedTitle], ([conversation, title]) => {
	if (conversation && title) huddleTitles[conversation] = title
})

// Deep links: ?c=<conversation> opens a thread, &call=1 joins its call. One
// route serves the calendar entry, the reminder mail and the ring alike.
async function openLinkedConversation() {
	const target = route.query.c
	if (typeof target !== 'string' || !target) return

	selected.value = target
	try {
		linked.value = await call('lms.lms.direct_message.get_thread', { conversation: target })
	} catch {
		// No access, or the class was deleted. Fall back to the default pick.
		selected.value = ''
		return
	}

	if (route.query.call) {
		// Strip the flag before joining: a reload of this URL must not silently
		// pull someone back into a call they hung up.
		await router.replace({ query: { ...route.query, call: undefined } })
		await startCall(false).catch(() => {})
	}
}

onMounted(() => {
	socket?.on('lms_huddle_lifecycle', onLifecycle)
	void openLinkedConversation()
})
onUnmounted(() => socket?.off('lms_huddle_lifecycle', onLifecycle))
</script>
