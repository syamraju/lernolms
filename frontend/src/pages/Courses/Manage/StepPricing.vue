<template>
	<div class="space-y-6">
		<div
			v-if="!canSetPrice"
			class="flex items-start gap-3 rounded-md border border-outline-amber-2 bg-surface-amber-1 p-4"
		>
			<span
				class="lucide-triangle-alert mt-0.5 size-5 shrink-0 text-ink-amber-3"
			/>
			<div>
				<div class="text-p-base-medium text-ink-gray-9">
					{{ __('Payments are not set up on this site yet.') }}
				</div>
				<p class="mt-1 text-p-base text-ink-gray-8">
					{{
						__(
							'You can still publish this course for free. A price can be set once an administrator configures a payment gateway.'
						)
					}}
				</p>
			</div>
		</div>

		<section class="space-y-4">
			<h3 class="text-p-base-semibold text-ink-gray-9">
				{{ __('Course price') }}
			</h3>
			<p class="text-p-base text-ink-gray-6">
				{{
					__(
						'Choose whether this course is free or paid. Free courses reach the widest audience; paid courses need a currency and an amount above zero.'
					)
				}}
			</p>

			<div class="flex flex-wrap items-end gap-3">
				<FormControl
					type="select"
					:modelValue="doc.paid_course ? 'Paid' : 'Free'"
					:options="['Free', 'Paid']"
					variant="outline"
					:label="__('Pricing')"
					:disabled="!canSetPrice"
					@update:modelValue="setPricingMode"
				/>
				<template v-if="doc.paid_course">
					<Link
						:modelValue="doc.currency"
						doctype="Currency"
						:filters="{ enabled: 1 }"
						:label="__('Currency')"
						:placeholder="__('Select currency')"
						variant="outline"
						@update:modelValue="set('currency', $event)"
					/>
					<FormControl
						type="number"
						min="0"
						:modelValue="doc.course_price"
						variant="outline"
						:label="__('Amount')"
						@update:modelValue="setPrice"
					/>
				</template>
			</div>

			<p v-if="priceError" class="text-p-sm text-ink-red-3">
				{{ priceError }}
			</p>
		</section>

		<section class="space-y-4 border-t pt-6">
			<h3 class="text-p-base-semibold text-ink-gray-9">
				{{ __('Certification') }}
			</h3>
			<BooleanSwitch
				size="sm"
				:modelValue="Boolean(doc.enable_certification)"
				:label="__('Completion certificate')"
				:description="
					__('Issue a certificate when a learner completes this course.')
				"
				@update:modelValue="setCheck('enable_certification', $event)"
			/>
			<BooleanSwitch
				v-if="!doc.paid_course"
				size="sm"
				:modelValue="Boolean(doc.paid_certificate)"
				:label="__('Paid certificate')"
				:description="
					__(
						'Sell an evaluator-graded certificate alongside this otherwise free course.'
					)
				"
				:disabled="!canSetPrice"
				@update:modelValue="setCheck('paid_certificate', $event)"
			/>
		</section>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { FormControl, createResource } from 'frappe-ui'
import BooleanSwitch from '@/components/Controls/BooleanSwitch.vue'
import Link from '@/components/Controls/Link.vue'
import { useCourseManage } from '@/composables/useCourseManage'
import type { Resource } from '@/types'
import type { LMSCourse } from '@/types/lms/LMSCourse'

const { doc, markDirty } = useCourseManage()

// A paid course is meaningless without somewhere for the money to go, so the
// price controls stay disabled until a gateway exists. Mirrors what Udemy does
// with its premium-instructor application, adapted to this app's actual gate.
const paymentGateways = createResource({
	url: 'frappe.client.get_count',
	makeParams: () => ({ doctype: 'Payment Gateway' }),
	auto: true,
}) as Resource<number | null>

const canSetPrice = computed(() => (paymentGateways.data ?? 0) > 0)

const priceError = computed(() => {
	if (!doc.value.paid_course) return ''
	if (!doc.value.currency) return __('Select a currency for this paid course.')
	if (!Number(doc.value.course_price)) {
		return __('A paid course needs an amount above zero.')
	}
	return ''
})

function set<K extends keyof LMSCourse>(field: K, value: LMSCourse[K]) {
	doc.value[field] = value
	markDirty()
}

function setCheck(field: keyof LMSCourse, value: boolean) {
	;(doc.value as Record<string, unknown>)[field] = value
	markDirty()
}

function setPrice(value: string | number) {
	doc.value.course_price = Number(value) || 0
	markDirty()
}

function setPricingMode(mode: string) {
	const paid = mode === 'Paid'
	doc.value.paid_course = paid ? 1 : 0
	if (!paid) {
		// Clearing the amount when switching back to free keeps a stale price
		// from reappearing if the author flips the toggle again later.
		doc.value.course_price = 0
	} else {
		doc.value.paid_certificate = 0
	}
	markDirty()
}
</script>
