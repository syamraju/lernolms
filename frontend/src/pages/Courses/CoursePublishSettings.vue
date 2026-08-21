<template>
	<div class="">
		<CollapsibleSection :label="__('Visibility')">
			<div class="flex flex-col gap-y-4">
				<BooleanSwitch
					size="sm"
					v-model="doc.upcoming"
					:label="__('Upcoming')"
					:description="__('Not yet open for enrollment.')"
					@update:modelValue="markDirty()"
				/>
				<BooleanSwitch
					size="sm"
					v-model="doc.featured"
					:label="__('Featured')"
					:description="__('Highlight on the homepage.')"
					@update:modelValue="markDirty()"
				/>
				<BooleanSwitch
					size="sm"
					v-model="selfEnrollment"
					:label="__('Self enrollment')"
					:description="__('Let users enroll themselves.')"
				/>
			</div>
		</CollapsibleSection>

		<CollapsibleSection :label="__('Pace and progression')">
			<div class="flex flex-col gap-y-4">
				<BooleanSwitch
					size="sm"
					v-model="doc.enforce_lesson_completion"
					:label="__('Enforce Lesson Completion')"
					:description="
						__('Students must complete each lesson before the next one opens.')
					"
					@update:modelValue="onEnforceCompletionChange"
				/>

				<!--
					Section gating is a sub-setting of the sequential gate: with
					nothing being unlocked in the first place there is no order to
					relax, so it is hidden rather than shown as a switch that does
					nothing.
				-->
				<BooleanSwitch
					v-if="doc.enforce_lesson_completion"
					size="sm"
					v-model="doc.enforce_section_completion"
					:label="__('Unlock one section at a time')"
					:description="
						__(
							'Everything inside the current section stays open, in any order. The next section unlocks once this one is fully complete — including any quiz, at the pass mark you set on it.'
						)
					"
					@update:modelValue="markDirty()"
				/>

				<div class="border-t -mx-5" />

				<FormControl
					v-model.number="doc.completion_deadline_days"
					type="number"
					min="0"
					:label="__('Days to complete')"
					variant="outline"
					@input="markDirty()"
				/>
				<p class="-mt-2 text-p-sm text-ink-gray-6">
					{{ deadlineDescription }}
				</p>
			</div>
		</CollapsibleSection>

		<CollapsibleSection :label="__('Pricing and certification')">
			<div class="flex flex-col gap-y-4">
				<BooleanSwitch
					size="sm"
					:modelValue="Boolean(doc?.paid_course)"
					:label="__('Paid course')"
					:description="__('Charge learners to enroll in this course.')"
					@update:modelValue="setPaidCourse"
				/>

				<template v-if="doc?.paid_course">
					<Link
						v-model="doc.currency"
						doctype="Currency"
						:label="__('Currency')"
						:filters="{ enabled: 1 }"
						:placeholder="__('Select currency')"
						variant="outline"
						:required="true"
						@update:modelValue="markDirty()"
					/>
					<FormControl
						v-model="doc.course_price"
						type="number"
						min="0"
						:label="__('Course price')"
						variant="outline"
						:required="true"
						@input="markDirty()"
					/>
					<div class="border-t -mx-5" />
					<BooleanSwitch
						size="sm"
						v-model="doc.enable_certification"
						:label="__('Completion certificate')"
						:description="
							__('Issue a free certificate when learners complete the course.')
						"
						@update:modelValue="markDirty()"
					/>
				</template>

				<template v-else>
					<div class="border-t -mx-5" />
					<BooleanSwitch
						size="sm"
						v-model="doc.enable_certification"
						:label="__('Completion certificate')"
						:description="
							__('Issue a free certificate when learners complete the course.')
						"
						@update:modelValue="markDirty()"
					/>
					<BooleanSwitch
						size="sm"
						:modelValue="doc.paid_certificate"
						:label="__('Paid certificate')"
						:description="
							__(
								'Sell an evaluator-graded certificate alongside this free course.'
							)
						"
						@update:modelValue="setPaidCertificate"
					/>
					<template v-if="doc.paid_certificate">
						<Link
							v-model="doc.currency"
							doctype="Currency"
							:label="__('Currency')"
							:filters="{ enabled: 1 }"
							:placeholder="__('Select currency')"
							variant="outline"
							:required="true"
							@update:modelValue="markDirty()"
						/>
						<FormControl
							v-model="doc.course_price"
							type="number"
							min="0"
							:label="__('Certificate price')"
							variant="outline"
							:required="true"
							@input="markDirty()"
						/>
						<Link
							ref="evaluatorLinkRef"
							v-model="doc.evaluator"
							doctype="Course Evaluator"
							:label="__('Evaluator')"
							:placeholder="__('Select evaluator')"
							variant="outline"
							:onCreate="openEvaluatorModal"
							@update:modelValue="markDirty()"
						/>
						<FormControl
							v-model="doc.timezone"
							type="combobox"
							:label="__('Timezone')"
							:options="timezoneOptions"
							:placeholder="__('Select timezone')"
							variant="outline"
							@update:modelValue="markDirty()"
						/>
					</template>
				</template>

				<div
					v-if="doc?.enable_certification || doc?.paid_certificate"
					class="flex flex-wrap items-center gap-1 text-p-sm text-ink-gray-6"
				>
					<span>
						{{
							__(
								'The certificate is artwork with the learner’s name, the dates and the course name placed on it. It has to be finished before instructors can be invited.'
							)
						}}
					</span>
					<router-link
						v-if="doc?.name"
						:to="{
							name: 'CourseCertificateDesigner',
							params: { courseName: doc.name },
						}"
						class="font-medium text-ink-gray-8 underline"
					>
						{{ __('Open the designer') }}
					</router-link>
					<!--
						The print-format route still exists for courses certified
						before the designer did, so the way to it stays — one step
						further back, where it belongs now.
					-->
					<button
						type="button"
						class="font-medium text-ink-gray-8 underline"
						@click="openPrintFormats"
					>
						{{ __('Legacy print formats') }}
					</button>
				</div>
			</div>
		</CollapsibleSection>
	</div>

	<NewMemberModal
		v-model="showMemberModal"
		:defaultRoles="['batch_evaluator']"
		@created="onEvaluatorCreated"
	/>

	<Dialog
		v-model:open="showPaymentsAppModal"
		:title="__('Payments app required')"
		:actions="[
			{
				label: __('Get the Payments app'),
				variant: 'solid',
				onClick: ({ close }: any) => {
					openPaymentsApp()
					close()
				},
			},
		]"
	>
		<template #default>
			<p class="text-p-base text-ink-gray-7">
				{{
					__(
						'Selling a paid course or certificate needs the Payments app. Ask your administrator to install it, then turn on pricing here.'
					)
				}}
			</p>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { Dialog, FormControl, createResource } from 'frappe-ui'
import BooleanSwitch from '@/components/Controls/BooleanSwitch.vue'
import { computed, inject, ref } from 'vue'
import CollapsibleSection from '@/components/CollapsibleSection.vue'
import Link from '@/components/Controls/Link.vue'
import NewMemberModal from '@/components/Modals/NewMemberModal.vue'
import { useSettings } from '@/stores/settings'
import type { CourseFormContext, Resource } from '@/types'
import { openExternal } from '@/utils/openExternal'

const { resource, markDirty } = inject<CourseFormContext>('courseForm')!
const dayjs = inject('$dayjs') as typeof import('dayjs')

const settingsStore = useSettings()
// Only block when we positively know the app is missing; if settings haven't
// loaded yet, let it through (the backend validation is the hard guard).
const paymentsAppMissing = computed<boolean>(
	() =>
		!!settingsStore.settings.data &&
		!settingsStore.settings.data.is_payments_app_installed
)

const doc = computed(() => resource.doc)
const evaluatorLinkRef = ref<{ reload: () => void } | null>(null)
const showMemberModal = ref<boolean>(false)
const showPaymentsAppModal = ref<boolean>(false)

const deadlineDescription = computed<string>(() => {
	const days = Number(doc.value?.completion_deadline_days) || 0
	if (!days) {
		return __(
			'Leave at 0 for no deadline — learners take as long as they need.'
		)
	}
	return __(
		'Each learner has {0} day(s) from enrolling. After that their enrollment is marked overdue; nothing is taken away.'
	).format(days)
})

/**
 * Turning sequencing off leaves section gating meaningless, so it goes with it.
 * A hidden switch that is still on would come back the next time sequencing is
 * enabled, silently applying a rule the author last saw two settings ago.
 */
function onEnforceCompletionChange(value: boolean) {
	if (!value && resource.doc) resource.doc.enforce_section_completion = 0
	markDirty()
}

const publishedOnLabel = computed<string>(() =>
	doc.value?.published_on
		? dayjs(doc.value.published_on).format('DD MMM YYYY')
		: ''
)

const selfEnrollment = computed<boolean>({
	get: () => !resource.doc?.disable_self_learning,
	set: (val: boolean) => {
		if (!resource.doc) return
		resource.doc.disable_self_learning = val ? 0 : 1
		markDirty()
	},
})

function setPaidCourse(val: boolean) {
	if (!resource.doc) return
	if (val && paymentsAppMissing.value) {
		showPaymentsAppModal.value = true
		return
	}
	resource.doc.paid_course = val ? 1 : 0
	// A paid course is already monetized: the paid-certificate flow only
	// applies to free courses, so clear it when switching to paid.
	if (val) resource.doc.paid_certificate = 0
	markDirty()
}

function setPaidCertificate(val: boolean) {
	if (!resource.doc) return
	if (val && paymentsAppMissing.value) {
		showPaymentsAppModal.value = true
		return
	}
	resource.doc.paid_certificate = val ? 1 : 0
	markDirty()
}

function openPaymentsApp() {
	openExternal('https://frappecloud.com/marketplace/apps/payments')
}

const timezoneResource = createResource({
	url: 'frappe.geo.country_info.get_country_timezone_info',
	auto: true,
	transform: (data: { all_timezones: string[] }) => data.all_timezones,
}) as Resource<string[] | null>

const timezoneOptions = computed<{ label: string; value: string }[]>(() =>
	(timezoneResource.data || []).map((tz) => ({ label: tz, value: tz }))
)

function openEvaluatorModal() {
	showMemberModal.value = true
}

function openPrintFormats() {
	openExternal('/app/print-format?doc_type=LMS Certificate')
}

function onEvaluatorCreated(created: { name: string }) {
	if (!resource.doc) return
	resource.doc.evaluator = created.name
	evaluatorLinkRef.value?.reload()
	markDirty()
}
</script>
