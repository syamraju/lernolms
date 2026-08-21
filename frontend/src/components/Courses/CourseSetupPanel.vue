<template>
	<Dialog v-model="show" size="3xl" :title="__('Course setup')">
		<template #body-content>
			<div class="space-y-6 text-base">
				<div class="flex flex-wrap items-center gap-x-4 gap-y-2">
					<Badge :theme="statusTheme" :label="statusLabel" />
					<span class="text-p-sm text-ink-gray-6">
						{{
							__('{0} of {1} steps complete').format(doneCount, gatedCount)
						}}
					</span>
					<span v-if="status.data" class="text-p-sm text-ink-gray-6">
						{{
							__('{0} of video content uploaded').format(
								formatVideoLength(status.data.video_seconds)
							)
						}}
					</span>
				</div>

				<div
					class="h-1.5 overflow-hidden rounded-full bg-surface-gray-2"
					role="progressbar"
					:aria-valuenow="doneCount"
					:aria-valuemin="0"
					:aria-valuemax="gatedCount"
					:aria-label="__('Course setup progress')"
				>
					<div
						class="h-full rounded-full bg-[var(--cds-background-control-checked)] transition-[width]"
						:style="{ width: `${progressPercent}%` }"
					/>
				</div>

				<p class="text-p-base text-ink-gray-6">
					{{
						__(
							'This is a checklist, not a second editor — every item is edited on the tab it belongs to.'
						)
					}}
				</p>

				<SkeletonLoader v-if="!status.data" variant="form" />

				<template v-else>
					<div
						v-if="status.data.blockers.length"
						class="rounded-md border border-outline-amber-2 bg-surface-amber-1 p-4"
					>
						<div class="text-p-base-medium text-ink-gray-9">
							{{ __('Still needed before you can submit for review') }}
						</div>
						<ul class="mt-2 space-y-1 ps-5">
							<li
								v-for="(blocker, index) in status.data.blockers"
								:key="index"
								class="list-disc text-p-base text-ink-gray-8"
							>
								{{ blocker.message }}
							</li>
						</ul>
					</div>

					<section
						v-for="group in SETUP_GROUPS"
						:key="group.key"
						class="space-y-2"
					>
						<h3 class="text-p-base-semibold text-ink-gray-9">
							{{ __(group.label) }}
						</h3>
						<ul class="divide-y border-y">
							<li v-for="item in itemsFor(group.key)" :key="item.key">
								<div class="flex items-start gap-3 py-3">
									<span
										class="mt-0.5 grid size-5 shrink-0 place-items-center rounded-full border"
										:class="
											isDone(item.key)
												? 'border-[var(--cds-border-control-checked)] bg-[var(--cds-background-control-checked)] text-[var(--cds-text-inverted)]'
												: 'border-outline-gray-3'
										"
										aria-hidden="true"
									>
										<span
											v-if="isDone(item.key)"
											class="lucide-check size-3"
										/>
									</span>

									<div class="min-w-0 flex-1">
										<div class="text-p-base-medium text-ink-gray-9">
											{{ __(item.label) }}
											<span v-if="item.optional" class="text-ink-gray-5">
												{{ __('(optional)') }}
											</span>
											<span class="sr-only">
												{{
													isDone(item.key) ? __('Complete') : __('Incomplete')
												}}
											</span>
										</div>
										<p class="text-p-base text-ink-gray-6">
											{{ __(item.hint) }}
										</p>

										<div class="mt-1 flex flex-wrap items-center gap-x-1">
											<Button
												v-if="item.target"
												variant="ghost"
												class="!-ms-2"
												:label="__(item.target.label)"
												@click="go(item)"
											>
												<template #suffix>
													<span class="lucide-arrow-right size-4" />
												</template>
											</Button>
											<Button
												v-if="item.guidance"
												variant="ghost"
												:label="
													expanded === item.key
														? __('Hide guidance')
														: __('Show guidance')
												"
												@click="toggle(item.key)"
											/>
										</div>

										<div
											v-if="item.guidance && expanded === item.key"
											class="mt-3 space-y-5 rounded-md bg-surface-gray-1 p-4"
										>
											<GuidanceList
												v-for="(block, index) in item.guidance()"
												:key="index"
												:title="block.title"
												:items="block.items"
												:variant="block.variant"
											/>
										</div>
									</div>
								</div>
							</li>
						</ul>
					</section>
				</template>
			</div>
		</template>

		<template #actions>
			<div class="flex items-center justify-between gap-2">
				<p class="text-p-sm text-ink-gray-5">
					{{ submitHint }}
				</p>
				<Button
					v-if="status.data?.status === 'Under Review'"
					variant="outline"
					:loading="withdrawing"
					:label="__('Withdraw submission')"
					@click="withdrawSubmission"
				/>
				<Button
					v-else-if="status.data?.status !== 'Approved'"
					variant="solid"
					:loading="submitting"
					:disabled="!status.data?.can_submit"
					:label="__('Submit for Review')"
					@click="submitForReview"
				/>
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
/**
 * The course-setup checklist.
 *
 * This replaced a standalone eleven-step wizard at `/courses/:name/manage`.
 * The wizard had grown its own copies of the curriculum, landing-page, pricing
 * and messages editors, so the same fields were reachable from two places with
 * two save paths. The checklist keeps what only the wizard had — a sense of
 * what is left to do, and the advisory copy — and sends the author to the tab
 * that owns each field instead of editing anything itself.
 */
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Badge, Button, Dialog, call, createResource, toast } from 'frappe-ui'
import GuidanceList from '@/components/Courses/GuidanceList.vue'
import SkeletonLoader from '@/components/SkeletonLoader.vue'
import { SETUP_GROUPS, SETUP_ITEMS, itemsFor } from '@/pages/Courses/setupChecklist'
import type { SetupItem } from '@/pages/Courses/setupChecklist'
import { errorMessage, formatVideoLength } from '@/utils/courseCreation'
import type { CourseCreationStatus, Resource } from '@/types'

const props = defineProps<{ courseName: string; published?: boolean }>()
const emit = defineEmits<{ changed: [] }>()

const show = defineModel<boolean>({ default: false })

const router = useRouter()
const expanded = ref('')
const submitting = ref(false)
const withdrawing = ref(false)

const status = createResource({
	url: 'lms.lms.course_creation.get_course_creation_status',
	makeParams: () => ({ course: props.courseName }),
	auto: false,
}) as Resource<CourseCreationStatus | null>

// Fetched on open, and re-fetched on every re-open: the author leaves to make
// a change and comes back expecting the tick to have moved.
watch(show, (open) => {
	if (open) void status.reload()
})

function isDone(key: string): boolean {
	return Boolean(status.data?.steps?.[key])
}

// Optional items are excluded from the count so "9 of 9" lines up with what
// the server will actually let you submit.
const gatedItems = computed(() => SETUP_ITEMS.filter((item) => !item.optional))
const gatedCount = computed(() => gatedItems.value.length)
const doneCount = computed(
	() => gatedItems.value.filter((item) => isDone(item.key)).length
)
const progressPercent = computed(() =>
	gatedCount.value ? (doneCount.value / gatedCount.value) * 100 : 0
)

const statusLabel = computed(() => {
	if (props.published) return __('Live')
	switch (status.data?.status) {
		case 'Under Review':
			return __('In review')
		case 'Approved':
			return __('Approved')
		default:
			return __('Draft')
	}
})

const statusTheme = computed(() => {
	if (props.published) return 'green'
	switch (status.data?.status) {
		case 'Under Review':
			return 'orange'
		case 'Approved':
			return 'blue'
		default:
			return 'gray'
	}
})

const submitHint = computed(() => {
	switch (status.data?.status) {
		case 'Under Review':
			return __('A moderator is reviewing this course.')
		case 'Approved':
			return __('Approved. Publish it from Settings when you are ready.')
		default:
			return status.data?.can_submit
				? __('Everything required is done.')
				: __('Clear the items above to submit.')
	}
})

function toggle(key: string) {
	expanded.value = expanded.value === key ? '' : key
}

function go(item: SetupItem) {
	if (!item.target) return
	show.value = false
	router.push({
		name: 'CourseDetail',
		params: { courseName: props.courseName },
		hash: `#${item.target.tab}`,
		query: item.target.query ?? {},
	})
}

async function submitForReview() {
	if (submitting.value) return
	submitting.value = true
	try {
		await call('lms.lms.course_creation.submit_course_for_review', {
			course: props.courseName,
		})
		toast.success(__('Course submitted for review'))
		void status.reload()
		emit('changed')
	} catch (error) {
		toast.error(errorMessage(error, __('Could not submit the course')))
	} finally {
		submitting.value = false
	}
}

async function withdrawSubmission() {
	if (withdrawing.value) return
	withdrawing.value = true
	try {
		await call('lms.lms.course_creation.withdraw_course_submission', {
			course: props.courseName,
		})
		toast.success(__('Submission withdrawn'))
		void status.reload()
		emit('changed')
	} catch (error) {
		toast.error(errorMessage(error, __('Could not withdraw the submission')))
	} finally {
		withdrawing.value = false
	}
}
</script>
