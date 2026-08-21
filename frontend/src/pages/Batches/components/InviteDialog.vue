<!--
	Invite people to a batch — two steps, deliberately.

	Nothing is written on the first click. `preview_invitations` classifies every
	address without touching the database, and this dialog renders exactly that
	classification, counted, before the moderator confirms. "Will this create
	accounts?" has to be answerable *before* it happens: the failure mode of a
	one-click version is silently provisioning accounts for a typo'd paste.

	The result screen is per-address for the same reason — a blanket "invited!"
	over a batch operation that half-worked reports success for the people who
	were never actually invited.
-->
<template>
	<Dialog v-model="show" :options="{ title: title, size: 'xl' }">
		<template #body-content>
			<!-- Step 1: addresses -->
			<div v-if="step === 'compose'" class="space-y-3">
				<p class="text-p-sm text-ink-gray-6">
					{{
						__(
							'One email address per line. Addresses without an account will get one, and a temporary password by email.'
						)
					}}
				</p>
				<textarea
					v-model="raw"
					rows="8"
					class="form-textarea w-full font-mono text-sm"
					placeholder="ada@example.com&#10;grace@example.com"
				/>
			</div>

			<!-- Step 2: what this will do -->
			<div v-else-if="step === 'confirm'" class="space-y-4">
				<div class="text-p-base text-ink-gray-8">
					<ul class="list-disc ps-5 space-y-1">
						<li v-if="counts.existing">
							{{
								__('{0} existing users will be invited.').format(counts.existing)
							}}
						</li>
						<li v-if="counts.new" class="font-medium text-ink-gray-9">
							{{
								__(
									'{0} new accounts will be created and emailed a temporary password.'
								).format(counts.new)
							}}
						</li>
						<li v-if="counts.already_enrolled" class="text-ink-gray-6">
							{{
								__('{0} are already enrolled and will be skipped.').format(
									counts.already_enrolled
								)
							}}
						</li>
						<li v-if="counts.invalid" class="text-ink-gray-6">
							{{
								__('{0} are not valid email addresses.').format(counts.invalid)
							}}
						</li>
						<li v-if="counts.no_seats" class="text-ink-gray-6">
							{{
								__('{0} will not fit — the batch is out of seats.').format(
									counts.no_seats
								)
							}}
						</li>
					</ul>
				</div>

				<div class="border rounded-lg divide-y max-h-64 overflow-y-auto">
					<div
						v-for="row in preview?.rows || []"
						:key="row.email"
						class="flex items-center justify-between px-3 py-2 text-sm"
					>
						<span class="truncate text-ink-gray-8">
							{{ row.full_name ? `${row.full_name} · ${row.email}` : row.email }}
						</span>
						<Badge :theme="verdictTheme(row.verdict)">
							{{ verdictLabel(row.verdict) }}
						</Badge>
					</div>
				</div>

				<div
					v-if="preview && !preview.mail_configured"
					class="rounded-md border border-outline-red-2 bg-surface-red-1 px-3 py-2 text-p-sm text-ink-red-3"
				>
					{{
						__(
							'This site has no outgoing email account, so nothing can be delivered. Invitations are blocked until one is set up — a new account would be created with a password nobody could receive.'
						)
					}}
				</div>

				<p v-if="preview?.will_enqueue" class="text-p-sm text-ink-gray-6">
					{{
						__(
							'This is a large list, so it will be processed in the background.'
						)
					}}
				</p>
			</div>

			<!-- Step 3: what actually happened -->
			<div v-else class="space-y-3">
				<p v-if="queued" class="text-p-base text-ink-gray-7">
					{{
						__('{0} invitations are being sent in the background.').format(
							queuedCount
						)
					}}
				</p>
				<div v-else class="border rounded-lg divide-y max-h-72 overflow-y-auto">
					<div
						v-for="row in results"
						:key="row.email"
						class="flex items-center justify-between px-3 py-2 text-sm"
					>
						<span class="truncate text-ink-gray-8">{{ row.email }}</span>
						<Badge :theme="statusTheme(row.status)">
							{{ statusLabel(row.status) }}
						</Badge>
					</div>
				</div>
			</div>
		</template>

		<template #actions>
			<div class="flex justify-end gap-2">
				<Button v-if="step === 'confirm'" @click="step = 'compose'">
					{{ __('Back') }}
				</Button>
				<Button
					v-if="step === 'compose'"
					variant="solid"
					:loading="checking"
					:disabled="!addresses.length"
					@click="check"
				>
					{{ __('Continue') }}
				</Button>
				<Button
					v-else-if="step === 'confirm'"
					variant="solid"
					:loading="sending"
					:disabled="!willAct"
					@click="send"
				>
					{{ confirmLabel }}
				</Button>
				<Button v-else variant="solid" @click="close">{{ __('Done') }}</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { Badge, Button, Dialog, call, toast } from 'frappe-ui'

const props = defineProps({
	modelValue: { type: Boolean, default: false },
	batch: { type: String, required: true },
})

const emit = defineEmits(['update:modelValue', 'invited'])

const show = computed({
	get: () => props.modelValue,
	set: (value) => emit('update:modelValue', value),
})

const step = ref('compose')
const raw = ref('')
const preview = ref(null)
const results = ref([])
const queued = ref(false)
const queuedCount = ref(0)
const checking = ref(false)
const sending = ref(false)

const addresses = computed(() =>
	raw.value
		.split(/[\n,;]+/)
		.map((line) => line.trim())
		.filter(Boolean)
)

const counts = computed(() => preview.value?.counts || {})

// Nothing to do is not a thing to confirm.
const willAct = computed(
	() =>
		Boolean(preview.value?.mail_configured) &&
		(counts.value.existing || 0) + (counts.value.new || 0) > 0
)

const title = computed(() => {
	if (step.value === 'compose') return __('Invite people')
	if (step.value === 'confirm') return __('Confirm invitations')
	return __('Invitations sent')
})

const confirmLabel = computed(() => {
	const fresh = counts.value.new || 0
	if (fresh) return __('Create {0} accounts and invite').format(fresh)
	return __('Send invitations')
})

const verdictLabels = {
	existing: __('Will be invited'),
	new: __('New account'),
	already_enrolled: __('Already enrolled'),
	invalid: __('Not an email'),
	no_seats: __('No seats left'),
}

const verdictThemes = {
	existing: 'green',
	new: 'blue',
	already_enrolled: 'gray',
	invalid: 'red',
	no_seats: 'orange',
}

const statusLabels = {
	created: __('Account created'),
	enrolled: __('Invited'),
	already_enrolled: __('Already enrolled'),
	invalid: __('Not an email'),
	failed: __('Failed'),
}

const statusThemes = {
	created: 'blue',
	enrolled: 'green',
	already_enrolled: 'gray',
	invalid: 'red',
	failed: 'red',
}

const verdictLabel = (verdict) => verdictLabels[verdict] || verdict
const verdictTheme = (verdict) => verdictThemes[verdict] || 'gray'
const statusLabel = (status) => statusLabels[status] || status
const statusTheme = (status) => statusThemes[status] || 'gray'

const check = async () => {
	checking.value = true
	try {
		preview.value = await call('lms.lms.batch_invite.preview_invitations', {
			batch: props.batch,
			emails: addresses.value,
		})
		step.value = 'confirm'
	} catch (err) {
		toast.error(err.messages?.[0] || err)
	}
	checking.value = false
}

const send = async () => {
	sending.value = true
	try {
		const result = await call('lms.lms.batch_invite.send_invitations', {
			batch: props.batch,
			emails: addresses.value,
		})
		queued.value = Boolean(result.queued)
		queuedCount.value = result.count
		results.value = result.results || []
		step.value = 'done'
		emit('invited')
	} catch (err) {
		toast.error(err.messages?.[0] || err)
	}
	sending.value = false
}

const close = () => {
	show.value = false
}

// Reset on close so reopening never shows the previous run's verdicts as if
// they described the addresses now in the box.
watch(show, (open) => {
	if (open) return
	step.value = 'compose'
	raw.value = ''
	preview.value = null
	results.value = []
	queued.value = false
})
</script>
