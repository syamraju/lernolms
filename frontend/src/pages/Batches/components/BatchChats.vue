<!--
	Batch › Chats — a two-level channel tree for one cohort.

	Replaces the single flat Discussions thread this tab used to hold. The tree is
	the answer to "what channels and sub-channels are there"; the last-message
	line under each one is the answer to "what is being discussed in them", which
	is why the list carries it rather than just a name and a count.

	Access is decided server-side in lms.lms.chat — `get_channel_tree` returns
	only what the caller may read, so there is no client-side audience filtering
	to keep in step with it.
-->
<template>
	<div class="w-[95%] lg:w-[85%] mx-auto mt-5">
		<div class="flex items-center justify-between mb-4">
			<div>
				<div class="text-ink-gray-9 font-semibold">{{ __('Chats') }}</div>
				<div class="text-sm text-ink-gray-6">
					{{ __('Channels for this batch.') }}
				</div>
			</div>
			<Button v-if="isModerator" @click="showNewChannel = true">
				<template #prefix>
					<span class="lucide-plus h-4 w-4" />
				</template>
				{{ __('New channel') }}
			</Button>
		</div>

		<div v-if="tree.loading && !tree.data" class="text-ink-gray-6 text-sm py-8">
			{{ __('Loading channels…') }}
		</div>

		<div
			v-else-if="!channels.length"
			class="text-ink-gray-7 text-sm border rounded-lg p-6"
		>
			{{ __('No channels in this batch yet.') }}
		</div>

		<div v-else class="flex gap-4 min-h-[28rem]">
			<!-- The tree -->
			<aside class="w-[16rem] shrink-0 border rounded-lg p-2 overflow-y-auto">
				<template v-for="channel in channels" :key="channel.name">
					<ChannelRow
						:channel="channel"
						:active="active === channel.name"
						@select="select"
					/>
					<ChannelRow
						v-for="child in channel.children"
						:key="child.name"
						:channel="child"
						:active="active === child.name"
						nested
						@select="select"
					/>
				</template>
			</aside>

			<!-- The conversation -->
			<section class="flex-1 min-w-0 border rounded-lg flex flex-col">
				<header
					v-if="activeChannel"
					class="border-b px-4 py-3 flex items-start justify-between gap-3"
				>
					<div class="min-w-0">
						<div class="font-semibold text-ink-gray-9 truncate">
							# {{ activeChannel.title }}
						</div>
						<div
							v-if="activeChannel.description"
							class="text-sm text-ink-gray-6"
						>
							{{ activeChannel.description }}
						</div>
					</div>
					<div class="flex items-center gap-2 shrink-0">
						<Badge v-if="activeChannel.is_archived" theme="orange">
							{{ __('Archived') }}
						</Badge>
						<Badge theme="gray">{{
							audienceLabel(activeChannel.audience)
						}}</Badge>
					</div>
				</header>

				<div ref="scroller" class="flex-1 overflow-y-auto px-4 py-3 space-y-4">
					<div
						v-if="!messages.data?.length"
						class="text-ink-gray-6 text-sm py-10 text-center"
					>
						{{ __('Nothing here yet.') }}
					</div>
					<div
						v-for="message in messages.data || []"
						:key="message.name"
						class="flex gap-3"
					>
						<Avatar
							:label="message.sender_name"
							:image="message.sender_image"
							size="md"
						/>
						<div class="min-w-0 flex-1">
							<div class="flex items-baseline gap-2">
								<span class="text-ink-gray-8 font-medium text-sm">
									{{ message.sender_name }}
								</span>
								<span class="text-xs text-ink-gray-5">
									{{ timeAgo(message.creation) }}
								</span>
								<span v-if="message.edited_at" class="text-xs text-ink-gray-5">
									{{ __('edited') }}
								</span>
							</div>
							<div
								v-if="message.is_deleted"
								class="text-sm italic text-ink-gray-5"
							>
								{{ __('This message was deleted.') }}
							</div>
							<div
								v-else
								class="prose prose-sm !min-w-full text-ink-gray-8"
								v-safe-html:rich="message.content"
							></div>
						</div>
						<Button
							v-if="canDelete(message)"
							variant="ghost"
							:label="__('Delete message')"
							@click="removeMessage(message)"
						>
							<template #icon>
								<span class="lucide-trash-2 size-4" />
							</template>
						</Button>
					</div>
				</div>

				<footer v-if="activeChannel" class="border-t p-3">
					<div v-if="!canPost" class="text-sm text-ink-gray-6 px-1 py-2">
						{{ postRefusal }}
					</div>
					<div v-else class="flex gap-2">
						<textarea
							v-model="draft"
							rows="2"
							class="form-textarea flex-1 resize-none"
							:placeholder="__('Write a message…')"
							@keydown.enter.exact.prevent="send"
						/>
						<Button
							variant="solid"
							:loading="sending"
							:disabled="!draft.trim()"
							@click="send"
						>
							{{ __('Send') }}
						</Button>
					</div>
				</footer>
			</section>
		</div>

		<Dialog v-model="showNewChannel" :options="{ title: __('New channel') }">
			<template #body-content>
				<div class="space-y-4">
					<FormControl
						v-model="newChannel.title"
						:label="__('Name')"
						:placeholder="__('project-help')"
					/>
					<FormControl
						type="select"
						v-model="newChannel.parent_channel"
						:label="__('Inside')"
						:options="parentOptions"
					/>
					<FormControl
						type="select"
						v-model="newChannel.audience"
						:label="__('Who can read')"
						:options="audienceOptions"
					/>
					<FormControl
						type="select"
						v-model="newChannel.post_permission"
						:label="__('Who can post')"
						:options="postOptions"
					/>
				</div>
			</template>
			<template #actions>
				<Button
					variant="solid"
					:loading="creating"
					:disabled="!newChannel.title.trim()"
					@click="createChannel"
				>
					{{ __('Create') }}
				</Button>
			</template>
		</Dialog>
	</div>
</template>

<script setup>
import { computed, inject, nextTick, ref, watch } from 'vue'
import {
	Avatar,
	Badge,
	Button,
	Dialog,
	FormControl,
	call,
	createResource,
	toast,
} from 'frappe-ui'
import { timeAgo } from '@/utils'
import ChannelRow from '@/pages/Batches/components/ChannelRow.vue'

const props = defineProps({
	batch: {
		type: Object,
		required: true,
	},
})

const user = inject('$user')
const active = ref('')
const draft = ref('')
const sending = ref(false)
const creating = ref(false)
const showNewChannel = ref(false)
const scroller = ref(null)

const newChannel = ref({
	title: '',
	parent_channel: '',
	audience: 'Everyone',
	post_permission: 'Everyone',
})

const batchName = computed(() => props.batch.data?.name)

// The batch doc already says whether the viewer moderates it; asking the server
// again per render would be a round trip for something it has to know anyway.
const isModerator = computed(() =>
	Boolean(props.batch.data?.is_moderator || user.data?.is_system_manager)
)

const tree = createResource({
	url: 'lms.lms.chat.get_channel_tree',
	makeParams: () => ({ batch: batchName.value }),
	auto: true,
})

const channels = computed(() => tree.data || [])

const flat = computed(() => {
	const out = []
	for (const channel of channels.value) {
		out.push(channel)
		for (const child of channel.children || []) out.push(child)
	}
	return out
})

const activeChannel = computed(() =>
	flat.value.find((channel) => channel.name === active.value)
)

const messages = createResource({
	url: 'lms.lms.chat.get_messages',
	makeParams: () => ({ channel: active.value }),
})

// Mirrors lms.lms.chat.can_post. The server is the gate — this only decides
// whether to render a composer the user would be refused at.
const canPost = computed(() => {
	const channel = activeChannel.value
	if (!channel) return false
	if (channel.is_archived) return isModerator.value
	if (channel.post_permission === 'Staff') return isStaff.value
	return true
})

const isStaff = computed(() =>
	Boolean(
		props.batch.data?.is_moderator ||
			props.batch.data?.is_staff ||
			user.data?.is_system_manager
	)
)

const postRefusal = computed(() => {
	const channel = activeChannel.value
	if (!channel) return ''
	if (channel.is_archived) return __('This channel is archived.')
	return __('Only the people running this batch can post here.')
})

const parentOptions = computed(() => [
	{ label: __('Top level'), value: '' },
	...channels.value.map((channel) => ({
		label: `# ${channel.title}`,
		value: channel.name,
	})),
])

const audienceOptions = [
	{ label: __('Everyone in the batch'), value: 'Everyone' },
	{ label: __('Staff only'), value: 'Staff' },
	{ label: __('Students only'), value: 'Students' },
]

const postOptions = [
	{ label: __('Everyone who can read it'), value: 'Everyone' },
	{ label: __('Staff only'), value: 'Staff' },
]

const audienceLabel = (audience) =>
	audienceOptions.find((option) => option.value === audience)?.label || audience

const canDelete = (message) =>
	!message.is_deleted &&
	(message.sender === user.data?.name || isModerator.value)

const select = (name) => {
	active.value = name
}

// Open the first channel on arrival: a two-pane view whose right pane is empty
// reads as broken rather than as a prompt.
watch(
	channels,
	(rows) => {
		if (!active.value && rows.length) active.value = rows[0].name
	},
	{ immediate: true }
)

watch(active, async (channel) => {
	if (!channel) return
	await messages.reload()
	await nextTick()
	if (scroller.value) scroller.value.scrollTop = scroller.value.scrollHeight
	// Clearing the badge is a side effect of having looked, so it follows the
	// read rather than being a button.
	call('lms.lms.chat.mark_read', { channel }).then(() => tree.reload())
})

watch(batchName, () => tree.reload())

const send = async () => {
	const content = draft.value.trim()
	if (!content) return
	sending.value = true
	try {
		await call('lms.lms.chat.post_message', {
			channel: active.value,
			content,
		})
		draft.value = ''
		await messages.reload()
		await nextTick()
		if (scroller.value) scroller.value.scrollTop = scroller.value.scrollHeight
		tree.reload()
	} catch (err) {
		toast.error(err.messages?.[0] || err)
	}
	sending.value = false
}

const removeMessage = async (message) => {
	try {
		await call('lms.lms.chat.delete_message', { message: message.name })
		messages.reload()
		tree.reload()
	} catch (err) {
		toast.error(err.messages?.[0] || err)
	}
}

const createChannel = async () => {
	creating.value = true
	try {
		const created = await call('lms.lms.chat.create_channel', {
			batch: batchName.value,
			title: newChannel.value.title.trim(),
			parent_channel: newChannel.value.parent_channel || null,
			audience: newChannel.value.audience,
			post_permission: newChannel.value.post_permission,
		})
		showNewChannel.value = false
		newChannel.value = {
			title: '',
			parent_channel: '',
			audience: 'Everyone',
			post_permission: 'Everyone',
		}
		await tree.reload()
		active.value = created.name
		toast.success(__('Channel created'))
	} catch (err) {
		toast.error(err.messages?.[0] || err)
	}
	creating.value = false
}
</script>
