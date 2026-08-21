<!--
	Invite links — enrollment by a URL pasted into a group chat.

	The token is shown exactly once, here, at creation. Only its SHA-256 is
	stored, so it cannot be recovered later and a leaked table yields no working
	links.

	Expiry and a use cap are not optional and are not hidden behind "advanced": a
	link posted in a community group gets forwarded past the audience it was
	written for and outlives the cohort it belongs to.
-->
<template>
	<Dialog v-model="show" :options="{ title: __('Invite links'), size: 'xl' }">
		<template #body-content>
			<div class="space-y-4">
				<div v-if="fresh" class="border rounded-lg p-3 bg-surface-gray-2">
					<div class="text-p-sm text-ink-gray-7 mb-2">
						{{ __('Copy this now — it is not shown again.') }}
					</div>
					<div class="flex items-center gap-2">
						<input
							ref="freshInput"
							:value="fresh.url"
							readonly
							class="form-input flex-1 font-mono text-xs"
							@focus="$event.target.select()"
						/>
						<Button @click="copy(fresh.url)">{{ __('Copy') }}</Button>
					</div>
				</div>

				<div class="flex items-end gap-2">
					<FormControl
						type="number"
						v-model="expiresInDays"
						:label="__('Expires in (days)')"
						class="w-40"
					/>
					<FormControl
						type="number"
						v-model="maxUses"
						:label="__('Max uses')"
						class="w-40"
					/>
					<Button variant="solid" :loading="creating" @click="create">
						{{ __('Create link') }}
					</Button>
				</div>

				<div v-if="links.data?.length" class="border rounded-lg divide-y">
					<div
						v-for="link in links.data"
						:key="link.name"
						class="flex items-center gap-3 px-3 py-2 text-sm"
					>
						<div class="flex-1 min-w-0">
							<div class="text-ink-gray-8">
								{{
									__('{0} of {1} uses').format(
										link.uses,
										link.max_uses || __('unlimited')
									)
								}}
							</div>
							<div class="text-xs text-ink-gray-6">
								{{
									link.expires_on
										? __('Expires {0}').format(formatDate(link.expires_on))
										: __('No expiry')
								}}
								· {{ link.owner }}
							</div>
						</div>
						<Badge :theme="link.is_active ? 'green' : 'gray'">
							{{ link.is_active ? __('Active') : __('Revoked') }}
						</Badge>
						<Button
							v-if="link.is_active"
							variant="ghost"
							theme="red"
							@click="revoke(link)"
						>
							{{ __('Revoke') }}
						</Button>
					</div>
				</div>
				<p v-else class="text-p-sm text-ink-gray-6">
					{{ __('No invite links for this batch yet.') }}
				</p>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import {
	Badge,
	Button,
	Dialog,
	FormControl,
	call,
	createResource,
	toast,
} from 'frappe-ui'

const props = defineProps({
	modelValue: { type: Boolean, default: false },
	batch: { type: String, required: true },
})

const emit = defineEmits(['update:modelValue'])

const show = computed({
	get: () => props.modelValue,
	set: (value) => emit('update:modelValue', value),
})

const expiresInDays = ref(30)
const maxUses = ref(100)
const creating = ref(false)
const fresh = ref(null)

const links = createResource({
	url: 'lms.lms.batch_invite.get_invite_links',
	makeParams: () => ({ batch: props.batch }),
})

watch(show, (open) => {
	if (open) {
		links.reload()
	} else {
		// The one-time token must not survive a reopen: leaving it on screen
		// implies it can be retrieved, and it cannot.
		fresh.value = null
	}
})

const formatDate = (value) => new Date(value).toLocaleDateString()

const create = async () => {
	creating.value = true
	try {
		fresh.value = await call('lms.lms.batch_invite.create_invite_link', {
			batch: props.batch,
			expires_in_days: expiresInDays.value,
			max_uses: maxUses.value,
		})
		links.reload()
	} catch (err) {
		toast.error(err.messages?.[0] || err)
	}
	creating.value = false
}

const revoke = async (link) => {
	try {
		await call('lms.lms.batch_invite.revoke_invite_link', { name: link.name })
		links.reload()
		toast.success(__('Link revoked'))
	} catch (err) {
		toast.error(err.messages?.[0] || err)
	}
}

const copy = async (text) => {
	try {
		await navigator.clipboard.writeText(text)
		toast.success(__('Copied'))
	} catch {
		toast.error(__('Could not copy — select the link and copy it manually.'))
	}
}
</script>
