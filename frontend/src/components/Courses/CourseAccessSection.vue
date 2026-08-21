<template>
	<section id="access" class="scroll-mt-4 space-y-8 border-t pt-6">
		<div>
			<div class="text-base-semibold text-ink-gray-9">
				{{ __('Access and instructors') }}
			</div>
			<p class="mt-1 text-p-base text-ink-gray-6">
				{{ __('Who can enrol, and who can edit.') }}
			</p>
		</div>

		<div class="space-y-4">
			<h3 class="text-p-base-semibold text-ink-gray-9">
				{{ __('Enrollment (privacy)') }}
			</h3>
			<FormControl
				type="select"
				class="max-w-md"
				:modelValue="doc.enrollment_privacy || 'Public'"
				:options="PRIVACY_OPTIONS"
				variant="outline"
				:label="__('Who can enrol')"
				@update:modelValue="setPrivacy"
			/>
			<FormControl
				v-if="doc.enrollment_privacy === 'Private (Password Protected)'"
				class="max-w-md"
				type="password"
				:modelValue="doc.enrollment_password"
				variant="outline"
				:label="__('Enrollment password')"
				autocomplete="new-password"
				@update:modelValue="set('enrollment_password', $event)"
			/>
			<p
				v-if="passwordMissing"
				class="max-w-md text-p-sm text-ink-red-3"
				role="alert"
			>
				{{ __('Set a password, or the course cannot be enrolled in.') }}
			</p>
			<p class="max-w-2xl text-p-base text-ink-gray-6">{{ privacyHint }}</p>
		</div>

		<div class="space-y-4">
			<h3 class="text-p-base-semibold text-ink-gray-9">
				{{ __('Email notifications') }}
			</h3>
			<BooleanSwitch
				size="sm"
				:modelValue="Boolean(doc.daily_qa_digest)"
				:label="__('Daily Q&A digest')"
				:description="__('One email a day summarising new learner questions.')"
				@update:modelValue="setCheck('daily_qa_digest', $event)"
			/>
			<BooleanSwitch
				size="sm"
				:modelValue="Boolean(doc.lecture_ready_emails)"
				:label="__('Lecture ready emails')"
				:description="
					__('Tell enrolled learners when a new lecture is published.')
				"
				@update:modelValue="setCheck('lecture_ready_emails', $event)"
			/>
		</div>

		<div class="space-y-4">
			<div class="flex flex-wrap items-center justify-between gap-3">
				<h3 class="text-p-base-semibold text-ink-gray-9">
					{{ __('Instructor permissions') }}
				</h3>
				<Button
					variant="ghost"
					:label="__('Add instructor')"
					@click="showAddInstructor = true"
				>
					<template #prefix>
						<span class="lucide-plus size-4" />
					</template>
				</Button>
			</div>

			<SkeletonLoader
				v-if="instructors.loading && !instructors.data"
				variant="form"
			/>
			<div v-else class="overflow-x-auto">
				<table class="w-full min-w-[42rem] text-p-sm">
					<thead>
						<tr class="border-b text-start text-ink-gray-6">
							<th class="py-2 pe-3 text-start font-medium">
								{{ __('Instructor') }}
							</th>
							<th
								v-for="permission in PERMISSIONS"
								:key="permission.key"
								class="px-2 py-2 text-center font-medium"
							>
								{{ permission.label }}
							</th>
							<th class="w-10" />
						</tr>
					</thead>
					<tbody>
						<tr
							v-for="row in instructors.data ?? []"
							:key="row.name"
							class="border-b last:border-b-0"
						>
							<td class="py-2 pe-3">
								<div class="flex items-center gap-2">
									<Avatar
										:image="row.user_image ?? undefined"
										:label="row.full_name"
										size="sm"
									/>
									<div class="min-w-0">
										<div class="truncate text-ink-gray-9">
											{{ row.full_name }}
										</div>
										<div class="truncate text-xs text-ink-gray-5">
											{{ row.instructor }}
										</div>
									</div>
									<Badge
										v-if="row.invitation_status === 'Pending'"
										theme="orange"
										:label="__('Pending')"
									/>
								</div>
							</td>
							<td
								v-for="permission in PERMISSIONS"
								:key="permission.key"
								class="px-2 py-2 text-center"
							>
								<input
									type="checkbox"
									class="size-4 rounded border-outline-gray-3 text-ink-gray-9 focus:ring-outline-gray-4"
									:checked="Boolean(row[permission.key])"
									:aria-label="
										__('{0} for {1}').format(permission.label, row.full_name)
									"
									@change="togglePermission(row, permission.key)"
								/>
							</td>
							<td class="py-2 text-end">
								<Button
									variant="ghost"
									theme="red"
									class="!size-8"
									:label="__('Remove {0}').format(row.full_name)"
									@click="removeInstructor(row)"
								>
									<template #icon>
										<span class="lucide-x size-4" />
									</template>
								</Button>
							</td>
						</tr>
					</tbody>
				</table>
			</div>
		</div>

		<AddInstructorModal
			v-model="showAddInstructor"
			:course="doc.name"
			@added="onInstructorAdded"
		/>
	</section>
</template>

<script setup lang="ts">
import { computed, getCurrentInstance, ref } from 'vue'
import {
	Avatar,
	Badge,
	Button,
	FormControl,
	call,
	createResource,
	toast,
} from 'frappe-ui'
import AddInstructorModal from '@/components/Modals/AddInstructorModal.vue'
import BooleanSwitch from '@/components/Controls/BooleanSwitch.vue'
import SkeletonLoader from '@/components/SkeletonLoader.vue'
import { useCourseManage } from '@/composables/useCourseManage'
import { errorMessage } from '@/utils/courseCreation'
import type { CourseInstructorRow, Resource } from '@/types'
import type { LMSCourse } from '@/types/lms/LMSCourse'

type PermissionKey = keyof Pick<
	CourseInstructorRow,
	| 'is_visible'
	| 'can_manage_course'
	| 'can_manage_captions'
	| 'can_view_performance'
	| 'can_manage_qa'
	| 'can_manage_assignments'
	| 'can_manage_reviews'
>

const PERMISSIONS: { key: PermissionKey; label: string }[] = [
	{ key: 'is_visible', label: __('Visible') },
	{ key: 'can_manage_course', label: __('Manage') },
	{ key: 'can_manage_captions', label: __('Captions') },
	{ key: 'can_view_performance', label: __('Performance') },
	{ key: 'can_manage_qa', label: __('Q&A') },
	{ key: 'can_manage_assignments', label: __('Assignments') },
	{ key: 'can_manage_reviews', label: __('Reviews') },
]

const PRIVACY_OPTIONS = [
	'Public',
	'Private (Invite Only)',
	'Private (Password Protected)',
]

interface DialogAction {
	label: string
	theme?: string
	variant?: string
	onClick: (close: () => void) => void
}
type DialogFn = (opts: {
	title: string
	message: string
	actions: DialogAction[]
}) => void

const { doc, resource, markDirty } = useCourseManage()
const app = getCurrentInstance()!
const { $dialog } = app.appContext.config.globalProperties as {
	$dialog: DialogFn
}

const showAddInstructor = ref(false)

const instructors = createResource({
	url: 'lms.lms.course_creation.get_course_instructors',
	makeParams: () => ({ course: doc.value.name }),
	auto: true,
}) as Resource<CourseInstructorRow[] | null>

const passwordMissing = computed(
	() =>
		doc.value.enrollment_privacy === 'Private (Password Protected)' &&
		!doc.value.enrollment_password
)

const privacyHint = computed(() => {
	switch (doc.value.enrollment_privacy) {
		case 'Private (Invite Only)':
			return __(
				'Only people you enrol directly can reach the course. It never appears in search.'
			)
		case 'Private (Password Protected)':
			return __(
				'The course stays out of search results. Share the URL and password with the learners you want to enrol. This is a low bar — anyone can pass the password on.'
			)
		default:
			return __(
				'Public courses appear in search results and anyone on the site can enrol.'
			)
	}
})

function set<K extends keyof LMSCourse>(field: K, value: LMSCourse[K]) {
	doc.value[field] = value
	markDirty()
}

function setCheck(field: keyof LMSCourse, value: boolean) {
	;(doc.value as Record<string, unknown>)[field] = value
	markDirty()
}

function setPrivacy(value: string) {
	set('enrollment_privacy', value as LMSCourse['enrollment_privacy'])
	if (value !== 'Private (Password Protected)') {
		set('enrollment_password', '')
	}
}

// Permissions are rows on a child table with their own endpoint, so they save
// immediately rather than riding along with the course document's autosave.
async function togglePermission(row: CourseInstructorRow, key: PermissionKey) {
	const permissions = Object.fromEntries(
		PERMISSIONS.map((permission) => [
			permission.key,
			permission.key === key
				? !row[permission.key]
				: Boolean(row[permission.key]),
		])
	)
	try {
		instructors.data = await call(
			'lms.lms.course_creation.update_instructor_permissions',
			{ course: doc.value.name, row: row.name, permissions }
		)
	} catch (error) {
		toast.error(errorMessage(error, __('Could not update permissions')))
	}
}

function removeInstructor(row: CourseInstructorRow) {
	$dialog({
		title: __('Remove instructor'),
		message: __('Remove {0} from this course?').format(row.full_name),
		actions: [
			{
				label: __('Remove'),
				theme: 'red',
				variant: 'solid',
				async onClick(close) {
					close()
					try {
						instructors.data = await call(
							'lms.lms.course_creation.remove_course_instructor',
							{ course: doc.value.name, row: row.name }
						)
						// The form's copy of the doc still carries the old child
						// rows. Refetch — never save — or the form's next whole-doc
						// write would put the removed instructor straight back.
						await resource.reload()
					} catch (error) {
						toast.error(
							errorMessage(error, __('Could not remove the instructor'))
						)
					}
				},
			},
		],
	})
}

async function onInstructorAdded(rows: CourseInstructorRow[]) {
	instructors.data = rows
	// Same reason as removal: the server appended a child row the form's doc
	// does not know about yet.
	await resource.reload()
}
</script>
