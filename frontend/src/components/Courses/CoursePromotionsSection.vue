<template>
	<section id="promotions" class="scroll-mt-4 space-y-8 border-t pt-6">
		<div>
			<div class="text-base-semibold text-ink-gray-9">
				{{ __('Promotions') }}
			</div>
			<p class="mt-1 text-p-base text-ink-gray-6">
				{{
					__(
						'Offer this course at a discount for a limited time. Coupons are managed centrally so the same code can cover several courses.'
					)
				}}
			</p>
		</div>

		<div
			v-if="!doc.paid_course"
			class="flex items-start gap-3 rounded-md border border-outline-gray-2 bg-surface-gray-1 p-4"
		>
			<span class="lucide-info mt-0.5 size-5 shrink-0 text-ink-gray-6" />
			<div>
				<div class="text-p-base-medium text-ink-gray-9">
					{{ __('This course is free') }}
				</div>
				<p class="mt-1 text-p-base text-ink-gray-6">
					{{
						__(
							'Coupons apply to paid courses. Set a price first if you want to run a promotion.'
						)
					}}
				</p>
				<Button
					variant="outline"
					class="mt-2"
					:label="__('Go to pricing')"
					@click="focusSection('publish')"
				/>
			</div>
		</div>

		<div v-else class="space-y-4">
			<div class="flex flex-wrap items-center justify-between gap-3">
				<h3 class="text-p-base-semibold text-ink-gray-9">
					{{ __('Coupons covering this course') }}
				</h3>
				<Button
					variant="outline"
					:label="__('Manage coupons')"
					@click="openCouponSettings"
				>
					<template #prefix>
						<span class="lucide-external-link size-4" />
					</template>
				</Button>
			</div>

			<SkeletonLoader v-if="coupons.loading && !coupons.data" variant="form" />

			<div
				v-else-if="!activeCoupons.length"
				class="rounded-md border border-dashed p-8 text-center"
			>
				<span class="lucide-ticket mx-auto mb-2 block size-6 text-ink-gray-4" />
				<p class="text-p-base text-ink-gray-6">
					{{ __('No coupons currently apply to this course.') }}
				</p>
			</div>

			<ul v-else class="divide-y border-y">
				<li
					v-for="coupon in activeCoupons"
					:key="coupon.name"
					class="flex flex-wrap items-center gap-3 py-3"
				>
					<span
						class="rounded bg-surface-gray-2 px-2 py-0.5 font-mono text-p-sm text-ink-gray-9"
					>
						{{ coupon.code }}
					</span>
					<span class="text-p-base text-ink-gray-8">
						{{ discountLabel(coupon) }}
					</span>
					<span class="text-p-sm text-ink-gray-5">
						{{
							coupon.expires_on
								? __('Expires {0}').format(coupon.expires_on)
								: __('No expiry')
						}}
					</span>
					<Badge
						class="ms-auto"
						:theme="coupon.enabled ? 'green' : 'gray'"
						:label="coupon.enabled ? __('Active') : __('Disabled')"
					/>
				</li>
			</ul>
		</div>
	</section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Badge, Button, createResource } from 'frappe-ui'
import SkeletonLoader from '@/components/SkeletonLoader.vue'
import { useCourseManage } from '@/composables/useCourseManage'
import { openSettings } from '@/utils'
import type { Resource } from '@/types'

interface CouponRow {
	name: string
	code: string
	discount_type: 'Percentage' | 'Fixed Amount'
	percentage_discount?: number
	fixed_amount_discount?: number
	expires_on?: string
	enabled?: 0 | 1
}

const { doc, focusSection } = useCourseManage()

// Coupon items are a child table keyed by (reference_doctype, reference_name),
// so the course's coupons are found through the child rows rather than a field
// on the coupon itself.
const coupons = createResource({
	url: 'frappe.client.get_list',
	makeParams: () => ({
		doctype: 'LMS Coupon',
		filters: [
			['LMS Coupon Item', 'reference_doctype', '=', 'LMS Course'],
			['LMS Coupon Item', 'reference_name', '=', doc.value.name],
		],
		fields: [
			'name',
			'code',
			'discount_type',
			'percentage_discount',
			'fixed_amount_discount',
			'expires_on',
			'enabled',
		],
		limit_page_length: 50,
	}),
	auto: true,
}) as Resource<CouponRow[] | null>

const activeCoupons = computed<CouponRow[]>(() => coupons.data ?? [])

function discountLabel(coupon: CouponRow): string {
	if (coupon.discount_type === 'Percentage') {
		return __('{0}% off').format(coupon.percentage_discount ?? 0)
	}
	return __('{0} {1} off').format(
		doc.value.currency ?? '',
		coupon.fixed_amount_discount ?? 0
	)
}

/**
 * Coupons live in the app-wide Settings dialog, which the desktop sidebar
 * mounts. The Settings tab renders inside that layout, so the dialog is
 * already available and can just be opened.
 */
function openCouponSettings() {
	openSettings('Coupons')
}
</script>
