<template>
	<Dialog v-model="show" size="3xl" :title="__('Settings')">
		<template #body-content>
			<div class="space-y-8 text-base">
				<!-- Course status -->
				<section class="space-y-4">
					<div class="flex flex-wrap items-start justify-between gap-3">
						<div>
							<h3 class="text-p-base-semibold text-ink-gray-9">
								{{ __('Course status') }}
							</h3>
							<p class="mt-1 text-p-base text-ink-gray-6">
								{{
									doc.published
										? __('This course is published and open to learners.')
										: __('This course is not published yet.')
								}}
							</p>
						</div>
						<Dropdown
							:options="notificationOptions"
							:button="{
								label: __('Manage email notifications'),
								variant: 'outline',
								iconRight: 'chevron-down',
							}"
							side="bottom"
							align="end"
						/>
					</div>

					<div class="grid gap-3 sm:grid-cols-[10rem,1fr] sm:items-center">
						<Button
							:variant="doc.published ? 'outline' : 'solid'"
							:theme="doc.published ? 'red' : 'gray'"
							:disabled="!canPublish"
							:loading="publishing"
							:label="doc.published ? __('Unpublish') : __('Publish')"
							@click="togglePublished"
						/>
						<p class="text-p-base text-ink-gray-6">
							{{
								doc.published
									? __(
											'Unpublishing hides the course from search. Learners already enrolled keep their access.'
									  )
									: publishHint
							}}
						</p>

						<Button
							variant="outline"
							theme="red"
							:disabled="Boolean(status.data?.published)"
							:loading="deleting"
							:label="__('Delete')"
							@click="confirmDelete"
						/>
						<p class="text-p-base text-ink-gray-6">
							{{
								status.data?.published
									? __(
											'Published courses cannot be deleted — learners were promised continued access.'
									  )
									: __(
											'Deleting removes every section, lecture and enrolment on this course.'
									  )
							}}
						</p>
					</div>
				</section>

				<!-- Enrollment privacy -->
				<section class="space-y-4 border-t pt-6">
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
					<p class="max-w-2xl text-p-base text-ink-gray-6">
						{{ privacyHint }}
					</p>
				</section>

				<!-- Instructor permissions -->
				<section class="space-y-4 border-t pt-6">
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

					<div class="overflow-x-auto">
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
												__('{0} for {1}').format(
													permission.label,
													row.full_name
												)
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
				</section>
			</div>
		</template>
	</Dialog>

	<AddInstructorModal
		v-model="showAddInstructor"
		:course="doc.name"
		@added="onInstructorAdded"
	/>
</template>

<script setup lang="ts">
import { computed, getCurrentInstance, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
	Avatar,
	Badge,
	Button,
	Dialog,
	Dropdown,
	FormControl,
	call,
	createResource,
	toast,
} from 'frappe-ui'
import AddInstructorModal from '@/components/Modals/AddInstructorModal.vue'
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

const show = defineModel<boolean>({ default: false })

const router = useRouter()
const { doc, resource, status, markDirty } = useCourseManage()
const app = getCurrentInstance()!
const { $dialog } = app.appContext.config.globalProperties as {
	$dialog: DialogFn
}

const showAddInstructor = ref(false)
const publishing = ref(false)
const deleting = ref(false)

const instructors = createResource({
	url: 'lms.lms.course_creation.get_course_instructors',
	makeParams: () => ({ course: doc.value.name }),
	auto: false,
}) as Resource<CourseInstructorRow[] | null>

// Fetch on first open rather than on mount: the panel is a dialog that most
// visits to the shell never open.
watch(show, (open) => {
	if (open) void instructors.reload()
})

// A course is only publishable once review has approved it — or immediately,
// for a moderator's own course, which the server decides. Surfacing the reason
// beats a disabled button with no explanation.
const canPublish = computed(
	() => Boolean(doc.value.published) || status.data?.status === 'Approved'
)

const publishHint = computed(() => {
	if (canPublish.value) {
		return __('Publishing makes the course visible in search and catalogues.')
	}
	if (status.data?.status === 'Under Review') {
		return __('This course is awaiting review. It can be published once approved.')
	}
	return __('Submit the course for review before publishing it.')
})

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

const notificationOptions = computed(() => [
	{
		label: __('Daily Q&A digest'),
		icon: doc.value.daily_qa_digest ? 'lucide-check-square' : 'lucide-square',
		onClick: () => toggleCheck('daily_qa_digest'),
	},
	{
		label: __('Lecture ready emails'),
		icon: doc.value.lecture_ready_emails
			? 'lucide-check-square'
			: 'lucide-square',
		onClick: () => toggleCheck('lecture_ready_emails'),
	},
])

function set<K extends keyof LMSCourse>(field: K, value: LMSCourse[K]) {
	doc.value[field] = value
	markDirty()
}

function toggleCheck(field: keyof LMSCourse) {
	;(doc.value as Record<string, unknown>)[field] = !doc.value[field]
	markDirty()
}

function setPrivacy(value: string) {
	set('enrollment_privacy', value as LMSCourse['enrollment_privacy'])
	if (value !== 'Private (Password Protected)') {
		set('enrollment_password', '')
	}
}

async function togglePublished() {
	publishing.value = true
	const next = doc.value.published ? 0 : 1
	try {
		// Written straight through rather than via the shell's whole-doc save:
		// publishing is a discrete act, and a pending autosave of unrelated
		// edits should not decide whether the course goes live.
		await call('frappe.client.set_value', {
			doctype: 'LMS Course',
			name: doc.value.name,
			fieldname: 'published',
			value: next,
		})
		doc.value.published = next
		toast.success(next ? __('Course published') : __('Course unpublished'))
		void status.reload()
	} catch (error) {
		toast.error(errorMessage(error, __('Could not update publish status')))
	} finally {
		publishing.value = false
	}
}

function confirmDelete() {
	$dialog({
		title: __('Delete course'),
		message: __(
			'Deleting "{0}" also deletes every section, lecture and enrolment on it. This cannot be undone.'
		).format(doc.value.title),
		actions: [
			{
				label: __('Delete'),
				theme: 'red',
				variant: 'solid',
				async onClick(close) {
					close()
					deleting.value = true
					try {
						await call('lms.lms.api.delete_course', { course: doc.value.name })
						toast.success(__('Course deleted'))
						router.push({ name: 'Courses', query: { tab: 'created' } })
					} catch (error) {
						toast.error(errorMessage(error, __('Could not delete the course')))
					} finally {
						deleting.value = false
					}
				},
			},
		],
	})
}

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
						// The shell's copy of the doc still carries the old child
						// rows. Refetch — never save — or the shell's next whole-doc
						// write would put the removed instructor straight back.
						await resource.reload()
					} catch (error) {
						toast.error(errorMessage(error, __('Could not remove the instructor')))
					}
				},
			},
		],
	})
}

async function onInstructorAdded(rows: CourseInstructorRow[]) {
	instructors.data = rows
	// Same reason as removal: the server appended a child row the shell's doc
	// does not know about yet.
	await resource.reload()
}
</script>
