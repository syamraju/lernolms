<template>
	<div class="min-h-dvh bg-surface-gray-1">
		<header
			class="flex items-center justify-between gap-4 border-b bg-surface-base px-5 py-4 print:hidden"
		>
			<span class="text-p-lg-semibold text-ink-gray-9">
				{{ brand.name || __('Learno') }}
			</span>
			<Button
				v-if="certificate.data"
				variant="subtle"
				:label="__('Print')"
				@click="print"
			/>
		</header>

		<main class="mx-auto w-full max-w-4xl px-5 py-10">
			<SkeletonLoader v-if="certificate.loading" />

			<!--
				A wrong code is the ordinary case, not an error: people mistype
				them off printed paper. It says what failed and shows the code
				back so the difference is visible.
			-->
			<div
				v-else-if="!certificate.data"
				class="rounded-md border bg-surface-base p-8 text-center"
			>
				<span class="mx-auto block size-8 lucide-shield-alert text-ink-gray-5" />
				<h1 class="mt-3 text-lg font-semibold text-ink-gray-9">
					{{ __('No certificate found') }}
				</h1>
				<p class="mt-2 text-p-base text-ink-gray-6">
					{{
						__(
							'Nothing has been issued with the code {0}. Check it against the certificate and try again.'
						).format(code)
					}}
				</p>
			</div>

			<template v-else>
				<div class="rounded-md border bg-surface-base p-4 print:border-0 print:p-0">
					<CertificateCanvas
						v-if="canvas"
						:template="canvas"
						:variables="[]"
					/>
					<!--
						Certificates issued before designed templates existed have
						no artwork to draw. The record itself is still real and is
						still what the link is for, so it is shown plainly rather
						than reported as missing.
					-->
					<div
						v-else
						class="grid aspect-[297/210] place-items-center rounded border border-dashed p-8 text-center"
					>
						<div>
							<p class="text-p-sm uppercase tracking-wide text-ink-gray-5">
								{{ __('Certificate of completion') }}
							</p>
							<p class="mt-3 text-2xl font-semibold text-ink-gray-9">
								{{ certificate.data.participant_name }}
							</p>
							<p class="mt-2 text-p-base text-ink-gray-7">
								{{ certificate.data.title }}
							</p>
						</div>
					</div>
				</div>

				<section
					class="mt-6 rounded-md border bg-surface-base p-5 print:hidden"
					aria-live="polite"
				>
					<div class="flex flex-wrap items-center gap-2">
						<Badge
							:theme="certificate.data.is_expired ? 'orange' : 'green'"
							:label="
								certificate.data.is_expired
									? __('Expired')
									: __('Verified certificate')
							"
						/>
						<span class="text-p-sm text-ink-gray-6">
							{{ __('Checked against {0} just now').format(organisation) }}
						</span>
					</div>

					<dl class="mt-4 grid gap-4 sm:grid-cols-2">
						<div v-for="row in rows" :key="row.label">
							<dt class="text-p-sm text-ink-gray-5">{{ row.label }}</dt>
							<dd class="mt-0.5 text-p-base text-ink-gray-9">
								{{ row.value }}
							</dd>
						</div>
					</dl>

					<p class="mt-5 border-t pt-4 text-p-sm text-ink-gray-6">
						{{ __('Authorised by {0}.').format(organisation) }}
					</p>
				</section>
			</template>
		</main>
	</div>
</template>

<script setup lang="ts">
/**
 * The public face of a certificate.
 *
 * Anyone with the link can open this, signed in or not — a certificate whose
 * proof only works for people who already have an account here proves nothing
 * to an employer. It draws the frozen snapshot the certificate was issued with,
 * so it keeps showing what was awarded even after the course has been renamed
 * or its template redesigned.
 */
import { computed } from 'vue'
import { Badge, Button, createResource, usePageMeta } from 'frappe-ui'
import CertificateCanvas from '@/components/Certificates/CertificateCanvas.vue'
import SkeletonLoader from '@/components/SkeletonLoader.vue'
import { templateFromSnapshot } from '@/utils/certificate'
import { sessionStore } from '@/stores/session'
import dayjs from '@/utils/dayjs'

const props = defineProps<{ code: string }>()

const { brand } = sessionStore() as { brand: { name?: string; favicon?: string } }

interface PublicCertificate {
	code: string
	participant_name: string
	title: string
	issue_date: string
	expiry_date: string | null
	is_expired: boolean
	organisation_name: string
	verification_url: string
	canvas: Parameters<typeof templateFromSnapshot>[0]
}

const certificate = createResource({
	url: 'lms.lms.certificates.get_public_certificate',
	makeParams: () => ({ code: props.code }),
	auto: true,
}) as { data: PublicCertificate | null; loading: boolean }

const canvas = computed(() => templateFromSnapshot(certificate.data?.canvas))

const organisation = computed(
	() => certificate.data?.organisation_name || brand.name || __('Learno')
)

const rows = computed(() => {
	const data = certificate.data
	if (!data) return []
	return [
		{ label: __('Awarded to'), value: data.participant_name },
		{ label: __('For'), value: data.title },
		{ label: __('Issued on'), value: formatDate(data.issue_date) },
		...(data.expiry_date
			? [{ label: __('Valid until'), value: formatDate(data.expiry_date) }]
			: []),
		{ label: __('Certificate ID'), value: data.code },
	]
})

function formatDate(value: string) {
	return value ? dayjs(value).format('D MMMM YYYY') : ''
}

function print() {
	window.print()
}

usePageMeta(() => ({
	title: certificate.data
		? __('Certificate {0}').format(certificate.data.code)
		: __('Verify a certificate'),
	icon: brand.favicon,
}))
</script>
