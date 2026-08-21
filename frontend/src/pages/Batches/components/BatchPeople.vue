<!--
	Batch › People — the roster, and the moderator's controls over it.

	This is a moderator's replacement for site-wide user visibility. `get_members`
	(Settings › Members) is System Manager only now; a moderator sees the people in
	the batches they actually run, which is what this reads.

	Instructors and evaluators appear here but cannot be removed here: they are
	derived from the courses in the curriculum, so there is no row to delete —
	changing them means changing the batch's courses or those courses' staff.
-->
<template>
	<div class="w-[95%] lg:w-[85%] mx-auto mt-5">
		<div class="flex items-center justify-between mb-4">
			<div>
				<div class="text-ink-gray-9 font-semibold">{{ __('People') }}</div>
				<div class="text-sm text-ink-gray-6">
					{{
						__('{0} in this batch').format(
							`${people.data?.length || 0} ${__('people')}`
						)
					}}
				</div>
			</div>
			<div class="flex items-center gap-2">
				<Button @click="showLinks = true">
					<template #prefix><span class="lucide-link h-4 w-4" /></template>
					{{ __('Invite link') }}
				</Button>
				<Button variant="solid" @click="openInvite">
					<template #prefix><span class="lucide-user-plus h-4 w-4" /></template>
					{{ __('Invite people') }}
				</Button>
			</div>
		</div>

		<div
			v-if="!people.data?.length"
			class="text-ink-gray-7 text-sm border rounded-lg p-6"
		>
			{{ __('Nobody has been added to this batch yet.') }}
		</div>

		<div v-else class="border rounded-lg divide-y">
			<div
				v-for="person in people.data"
				:key="person.user"
				class="flex items-center gap-3 px-4 py-3"
			>
				<Avatar
					:label="person.full_name"
					:image="person.user_image"
					size="lg"
				/>
				<div class="min-w-0 flex-1">
					<div class="text-ink-gray-8 font-medium truncate">
						{{ person.full_name }}
					</div>
					<div class="text-xs text-ink-gray-6 truncate">{{ person.user }}</div>
				</div>
				<Badge :theme="relationTheme(person.relation)">
					{{ relationLabel(person.relation) }}
				</Badge>
				<Badge v-if="person.must_reset_password" theme="orange">
					{{ __('Invite pending') }}
				</Badge>
				<Badge v-else-if="person.never_signed_in" theme="gray">
					{{ __('Never signed in') }}
				</Badge>
				<Dropdown
					v-if="menu(person).length"
					:options="menu(person)"
					placement="left"
				>
					<template v-slot="{ open }">
						<Button
							variant="ghost"
							:label="__('Actions')"
							:aria-expanded="open"
						>
							<template #icon>
								<span class="lucide-ellipsis-vertical w-4 h-4" />
							</template>
						</Button>
					</template>
				</Dropdown>
			</div>
		</div>

		<InviteDialog
			v-model="showInvite"
			:batch="batchName"
			@invited="people.reload()"
		/>

		<InviteLinkDialog v-model="showLinks" :batch="batchName" />

		<Dialog
			v-model="showReset"
			:options="{
				title: __('Re-issue a temporary password'),
				actions: [
					{
						label: __('Send temporary password'),
						variant: 'solid',
						loading: resetting,
						onClick: confirmReset,
					},
				],
			}"
		>
			<template #body-content>
				<p class="text-p-base text-ink-gray-7">
					{{
						__(
							'{0} will be emailed a new temporary password and asked to choose their own the next time they sign in. Their current password stops working immediately.'
						).format(resetTarget?.full_name || '')
					}}
				</p>
				<p class="text-p-sm text-ink-gray-6 mt-3">
					{{ __('You will not see the password — it goes only to them.') }}
				</p>
			</template>
		</Dialog>
	</div>
</template>

<script setup>
import { computed, ref } from 'vue'
import {
	Avatar,
	Badge,
	Button,
	Dialog,
	Dropdown,
	call,
	createResource,
	toast,
} from 'frappe-ui'
import InviteDialog from '@/pages/Batches/components/InviteDialog.vue'
import InviteLinkDialog from '@/pages/Batches/components/InviteLinkDialog.vue'

const props = defineProps({
	batch: {
		type: Object,
		required: true,
	},
})

const showInvite = ref(false)
const showLinks = ref(false)
const showReset = ref(false)
const resetting = ref(false)
const resetTarget = ref(null)

const batchName = computed(() => props.batch.data?.name)

const people = createResource({
	url: 'lms.lms.batch_people.get_batch_people',
	makeParams: () => ({ batch: batchName.value }),
	auto: true,
})

const relationLabels = {
	moderator: __('Moderator'),
	instructor: __('Instructor'),
	evaluator: __('Evaluator'),
	student: __('Student'),
}

const relationThemes = {
	moderator: 'blue',
	instructor: 'green',
	evaluator: 'purple',
	student: 'gray',
}

const relationLabel = (relation) => relationLabels[relation] || relation
const relationTheme = (relation) => relationThemes[relation] || 'gray'

const openInvite = () => {
	showInvite.value = true
}

// Only students carry actions: a derived instructor has no row here to act on,
// and the password rule refuses anybody holding a staff role anyway.
const menu = (person) => {
	if (person.relation !== 'student') return []
	return [
		{
			label: __('Re-issue password'),
			icon: 'lucide-key-round',
			onClick: () => {
				resetTarget.value = person
				showReset.value = true
			},
		},
		{
			label: __('Remove from batch'),
			icon: 'lucide-user-minus',
			theme: 'red',
			onClick: () => removePerson(person),
		},
	]
}

const confirmReset = async (close) => {
	resetting.value = true
	try {
		await call('lms.lms.batch_invite.reissue_password', {
			batch: batchName.value,
			user: resetTarget.value.user,
		})
		toast.success(__('A temporary password has been emailed to them'))
		showReset.value = false
		people.reload()
	} catch (err) {
		toast.error(err.messages?.[0] || err)
	}
	resetting.value = false
	close?.()
}

const removePerson = async (person) => {
	try {
		await call('lms.lms.batch_people.remove_from_batch', {
			batch: batchName.value,
			user: person.user,
		})
		toast.success(__('Removed from batch'))
		people.reload()
	} catch (err) {
		toast.error(err.messages?.[0] || err)
	}
}
</script>
