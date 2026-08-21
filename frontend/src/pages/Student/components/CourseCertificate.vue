<!--
	Certificate panel. Figma: node 99:9366 — explanatory copy beside the
	certificate artwork.

	The artwork in the design is a mock. What goes here instead is the student's
	real state: the issued certificate if there is one, the requirements if there
	is not, and a plain statement when the course does not certify at all. A
	decorative certificate image for a course that issues none would be a lie.
-->
<template>
	<div class="grid gap-10 lg:grid-cols-2">
		<div class="flex flex-col gap-4 self-center">
			<h2 class="text-[16px] font-semibold text-[var(--learno-ink-strong)]">
				{{ __('Learning Path and Course Inclusions') }}
			</h2>

			<p class="max-w-[52ch] text-[13px] leading-[1.7] text-[var(--learno-ink-muted)]">
				<template v-if="!offered">
					{{ __('This course does not issue a certificate.') }}
				</template>
				<template v-else-if="certificate">
					{{
						__(
							'Your certificate for this course has been issued. Open it to view, print or share it.'
						)
					}}
				</template>
				<template v-else>
					{{
						__(
							'Complete every session in this course to earn your certificate. It is issued by the organisation once the course is finished.'
						)
					}}
				</template>
			</p>

			<div v-if="offered" class="mt-2 flex flex-col gap-3">
				<div class="flex items-center gap-3">
					<div class="h-1.5 w-48 overflow-hidden rounded-full bg-black/5">
						<div
							class="h-full rounded-full bg-[var(--learno-primary)]"
							:style="{ width: `${progress}%` }"
						/>
					</div>
					<span class="text-[12px] text-[var(--learno-ink-muted)]">
						{{ progress }}% {{ __('complete') }}
					</span>
				</div>

				<!--
					A designed certificate has a page of its own on this platform
					— the same one anybody with the link can open — so it is an
					SPA route rather than a redirect to a rendered PDF.
				-->
				<router-link
					v-if="certificateCode"
					:to="{
						name: 'CertificateVerification',
						params: { code: certificateCode },
					}"
					class="learno-btn learno-btn-primary w-fit px-5 py-2.5 text-[13px]"
				>
					<span class="lucide-award size-4" aria-hidden="true" />
					{{ __('View certificate') }}
				</router-link>
				<a
					v-else-if="certificate"
					:href="safeUrl(certificateHref)"
					class="learno-btn learno-btn-primary w-fit px-5 py-2.5 text-[13px]"
					v-external
				>
					<span class="lucide-award size-4" aria-hidden="true" />
					{{ __('View certificate') }}
				</a>
				<router-link
					v-else-if="course.paid_certificate"
					:to="{
						name: 'CourseCertification',
						params: { courseName: course.name },
					}"
					class="learno-btn learno-btn-secondary w-fit px-5 py-2.5 text-[13px]"
				>
					<span class="lucide-calendar-check size-4" aria-hidden="true" />
					{{ __('Book an evaluation') }}
				</router-link>
			</div>
		</div>

		<div
			class="grid min-h-[260px] place-items-center rounded-[var(--learno-r-md)] border border-dashed border-[var(--learno-line)] bg-[var(--learno-canvas)] p-8 text-center"
		>
			<div class="flex flex-col items-center gap-3">
				<span
					class="grid size-14 place-items-center rounded-full"
					:class="
						certificate
							? 'bg-[#fff8e1] text-[#cd7900]'
							: 'bg-black/5 text-[var(--learno-ink-subtle)]'
					"
				>
					<span class="lucide-award size-7" aria-hidden="true" />
				</span>
				<p class="text-[13px] font-semibold text-[var(--learno-ink-strong)]">
					{{
						certificate
							? __('Certificate of Achievement')
							: offered
								? __('Not earned yet')
								: __('No certificate for this course')
					}}
				</p>
				<p
					v-if="certificate"
					class="text-[12px] text-[var(--learno-ink-muted)]"
				>
					{{ __('Issued to {0}').format(holderName) }}
				</p>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, inject } from 'vue'
import { safeUrl } from '@/utils/safeUrl'

const props = defineProps<{ course: Record<string, any> }>()

const userResource = inject<any>('$user')

const offered = computed(() =>
	Boolean(props.course.enable_certification || props.course.paid_certificate)
)

const certificate = computed(() => props.course.membership?.certificate || '')

// Present only on certificates issued since verification links existed. Older
// ones keep the print-format link below rather than pointing at a page that
// cannot resolve them.
const certificateCode = computed(
	() => props.course.membership?.certificate_code || ''
)

const progress = computed(() =>
	Math.min(100, Math.round(Number(props.course.membership?.progress || 0)))
)

const holderName = computed(
	() => userResource?.data?.full_name || userResource?.data?.name || ''
)

// /certificate is a server-rendered Frappe web page (lms/www/certificate.py)
// that redirects to the PDF for the chosen print format — not an SPA route, so
// this is a document link rather than a router-link.
const certificateHref = computed(
	() => `/certificate?certificate_id=${encodeURIComponent(certificate.value)}`
)
</script>
