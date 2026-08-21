<template>
	<Dialog v-model="show" :title="__('Add instructor')">
		<template #body-content>
			<div class="space-y-5 text-base">
				<MultiLink
					v-model="selected"
					doctype="User"
					url="lms.lms.api.search_users_by_role"
					:searchParams="{ roles: JSON.stringify(INSTRUCTOR_ROLES) }"
					:transform="transformUsers"
					:label="__('Who are you inviting?')"
					:placeholder="__('Search by name or email')"
					:required="true"
				>
					<template #item-prefix="{ item }">
						<Avatar :image="item.image" :label="item.label" size="sm" />
					</template>
				</MultiLink>

				<fieldset class="space-y-2">
					<legend class="mb-1 text-p-base-medium text-ink-gray-9">
						{{ __('Permissions') }}
					</legend>
					<p class="text-p-sm text-ink-gray-6">
						{{
							__(
								'Choose what this instructor can do. You can change any of it later from settings.'
							)
						}}
					</p>
					<div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
						<label
							v-for="permission in PERMISSIONS"
							:key="permission.key"
							class="flex cursor-pointer items-center gap-2.5 rounded-md border px-3 py-2 transition-colors hover:border-outline-gray-4"
							:class="
								permissions[permission.key]
									? 'border-outline-gray-5 bg-surface-gray-1'
									: 'border-outline-gray-2'
							"
						>
							<input
								v-model="permissions[permission.key]"
								type="checkbox"
								class="size-4 rounded border-outline-gray-3 text-ink-gray-9 focus:ring-outline-gray-4"
							/>
							<span class="text-p-base text-ink-gray-9">
								{{ permission.label }}
							</span>
						</label>
					</div>
				</fieldset>
			</div>
		</template>
		<template #actions>
			<div class="flex items-center justify-end gap-2">
				<Button :label="__('Cancel')" @click="show = false" />
				<Button
					variant="solid"
					:disabled="!selected.length"
					:loading="saving"
					:label="
						selected.length > 1
							? __('Send {0} invitations').format(selected.length)
							: __('Send invitation')
					"
					@click="submit"
				/>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { reactive, ref, watch } from 'vue'
import { Avatar, Button, Dialog, call, toast } from 'frappe-ui'
import MultiLink from '@/components/Controls/MultiLink.vue'
import { errorMessage } from '@/utils/courseCreation'
import type { CourseInstructorRow } from '@/types'

const INSTRUCTOR_ROLES = ['Course Creator', 'Moderator']

const PERMISSIONS = [
	{ key: 'is_visible', label: __('Visible') },
	{ key: 'can_manage_course', label: __('Manage course') },
	{ key: 'can_manage_captions', label: __('Captions') },
	{ key: 'can_view_performance', label: __('Performance') },
	{ key: 'can_manage_qa', label: __('Q&A') },
	{ key: 'can_manage_assignments', label: __('Assignments') },
	{ key: 'can_manage_reviews', label: __('Reviews') },
] as const

type PermissionKey = typeof PERMISSIONS[number]['key']

interface RawUserHit {
	label?: string
	value?: string
	name?: string
	user_image?: string
}

const props = defineProps<{ course: string }>()
const emit = defineEmits<{ added: [CourseInstructorRow[]] }>()

const show = defineModel<boolean>({ default: false })

const selected = ref<string[]>([])
const saving = ref(false)

// A co-instructor is visible and can look at performance by default. Anything
// that changes the course itself stays off until it is granted deliberately.
const defaults: Record<PermissionKey, boolean> = {
	is_visible: true,
	can_manage_course: false,
	can_manage_captions: false,
	can_view_performance: true,
	can_manage_qa: false,
	can_manage_assignments: false,
	can_manage_reviews: false,
}

const permissions = reactive<Record<PermissionKey, boolean>>({ ...defaults })

watch(show, (open) => {
	if (!open) return
	selected.value = []
	Object.assign(permissions, defaults)
})

function transformUsers(rows: Record<string, unknown>[]) {
	return (rows as RawUserHit[]).map((user) => ({
		label: user.label || user.name || user.value || '',
		value: user.value || user.name || '',
		image: user.user_image || '',
	}))
}

async function submit() {
	if (!selected.value.length || saving.value) return
	saving.value = true
	// Sequential: each invite appends a child row to the same course document,
	// so concurrent saves would race and one of them would lose.
	let rows: CourseInstructorRow[] = []
	const failed: string[] = []
	for (const email of selected.value) {
		try {
			rows = (await call('lms.lms.course_creation.add_course_instructor', {
				course: props.course,
				email,
				permissions: { ...permissions },
			})) as CourseInstructorRow[]
		} catch (error) {
			failed.push(
				errorMessage(error, __('{0} could not be added').format(email))
			)
		}
	}
	saving.value = false

	if (rows.length) emit('added', rows)
	if (failed.length) {
		failed.forEach((message) => toast.error(message))
		// Leave the dialog open on a partial failure so the author can see what
		// went wrong and retry, rather than having it vanish mid-invite.
		if (failed.length === selected.value.length) return
	} else {
		toast.success(
			selected.value.length > 1
				? __('{0} invitations sent').format(selected.value.length)
				: __('Invitation sent to {0}').format(selected.value[0])
		)
	}
	show.value = false
}
</script>
