<template>
	<div class="space-y-8">
		<p class="text-p-base text-ink-gray-7">
			{{
				__(
					'Promotions let you offer this course at a discount for a limited time. Coupons are managed centrally so the same code can cover several courses.'
				)
			}}
		</p>

		<section
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
					:label="__('Go to Pricing')"
					@click="goToStep('pricing')"
				/>
			</div>
		</section>

		<section v-else class="space-y-4">
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
		</section>

		<GuidanceList :title="__('Getting the most from a promotion')" :items="TIPS" />
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { Badge, Button, createResource } from 'frappe-ui'
import SkeletonLoader from '@/components/SkeletonLoader.vue'
import GuidanceList from '@/components/Courses/GuidanceList.vue'
import { useCourseManage } from '@/composables/useCourseManage'
import { useSettings } from '@/stores/settings'
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

const TIPS = [
	{
		title: __('Announce the end date.'),
		body: __(
			'A deadline is what turns interest into an enrolment. Say when the offer closes wherever you share the code.'
		),
	},
	{
		title: __('Keep the code short and readable.'),
		body: __(
			'Codes get typed by hand and read aloud in videos. Avoid characters that look alike.'
		),
	},
	{
		title: __('One code per channel.'),
		body: __(
			'Separate codes for your newsletter, social posts and partners tell you which channel actually converts.'
		),
	},
]

const router = useRouter()
const { doc, goToStep } = useCourseManage()

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
 * Coupons live in the app-wide Settings dialog, which is only mounted by the
 * desktop sidebar — and this shell deliberately renders without one. So leave
 * the shell first, then open the dialog once the layout that owns it has
 * mounted. The poll is bounded: if Settings never appears (a phone, where it
 * has no mount point at all), `openSettings` says so rather than doing nothing.
 */
async function openCouponSettings() {
	await router.push({ name: 'Courses', query: { tab: 'created' } })
	const settingsStore = useSettings()
	for (let attempt = 0; attempt < 20; attempt++) {
		if (settingsStore.isSettingsMounted) break
		await new Promise((resolve) => setTimeout(resolve, 50))
	}
	openSettings('Coupons')
}
</script>
