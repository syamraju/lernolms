<template>
	<div class="flex h-dvh flex-col bg-surface-base">
		<header
			class="flex shrink-0 flex-wrap items-center justify-between gap-3 border-b px-5 py-4"
		>
			<div class="min-w-0">
				<h1 class="truncate text-p-lg-semibold text-ink-gray-9">
					{{ __('Certificate') }}
				</h1>
				<p class="truncate text-p-sm text-ink-gray-6">
					{{ designer.data?.title || referenceName }}
				</p>
			</div>
			<div class="flex items-center gap-2">
				<Button variant="ghost" :label="backLabel" @click="exit" />
				<Button
					variant="solid"
					:loading="saving"
					:label="__('Save certificate')"
					@click="save"
				/>
			</div>
		</header>

		<main class="flex-1 overflow-y-auto px-5 py-6">
			<div class="mx-auto max-w-6xl">
				<SkeletonLoader v-if="designer.loading && !designer.data" />
				<template v-else-if="template && designer.data">
					<!--
						Said before the work starts, not after a save is refused.
						The gate is the reason this screen exists at all, and a
						moderator who learns about it from an error on the settings
						tab has already lost the trip.
					-->
					<div
						v-if="missing.length && isCourse"
						class="mb-5 rounded-md border border-outline-amber-2 bg-surface-amber-1 px-4 py-3 text-p-sm text-ink-gray-8"
					>
						{{
							__(
								'Instructors cannot be invited to this course until the certificate is finished.'
							)
						}}
					</div>

					<CertificateDesigner
						v-model="template"
						:variables="designer.data.variables"
						:sampleValues="designer.data.sample_values"
						:dateFormats="designer.data.date_formats"
					/>
				</template>
			</div>
		</main>
	</div>
</template>

<script setup lang="ts">
/**
 * Where a certificate is designed after the thing it belongs to already exists.
 *
 * One screen for both kinds. A course certificate and a program certificate
 * carry different mandatory fields — the server decides which, and this page
 * only passes the reference through — so a second copy of the editor would be
 * two places to fix the same bug.
 *
 * The create wizard has its own instance of `CertificateDesigner` for a course
 * that has not been inserted yet. It posts the design with the course; this
 * saves it on its own. Both write the same template.
 */
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Button, call, createResource, toast, usePageMeta } from 'frappe-ui'
import CertificateDesigner from '@/components/Certificates/CertificateDesigner.vue'
import SkeletonLoader from '@/components/SkeletonLoader.vue'
import { missingRequirements } from '@/utils/certificate'
import type {
	CertificateTemplate,
	CertificateVariable,
} from '@/utils/certificate'
import { errorMessage } from '@/utils/courseCreation'
import { sessionStore } from '@/stores/session'

const props = withDefaults(
	defineProps<{
		/** Route param for a course. Present on the course route only. */
		courseName?: string
		/** Route param for a program. Present on the program route only. */
		programName?: string
	}>(),
	{ courseName: '', programName: '' }
)

const router = useRouter()
const { brand } = sessionStore() as { brand: { favicon?: string } }

const isCourse = computed(() => Boolean(props.courseName))
const referenceDoctype = computed(() =>
	isCourse.value ? 'LMS Course' : 'LMS Program'
)
const referenceName = computed(() => props.courseName || props.programName)
const backLabel = computed(() =>
	isCourse.value ? __('Back to course') : __('Back to program')
)

interface DesignerPayload {
	title: string
	template: CertificateTemplate
	variables: CertificateVariable[]
	sample_values: Record<string, unknown>
	date_formats: string[]
	missing: { code: string; message: string }[]
	is_complete: boolean
}

const designer = createResource({
	url: 'lms.lms.certificates.get_certificate_designer',
	makeParams: () => ({
		reference_doctype: referenceDoctype.value,
		reference_name: referenceName.value,
	}),
	auto: true,
}) as {
	data: DesignerPayload | null
	loading: boolean
	reload: () => Promise<unknown>
}

const template = ref<CertificateTemplate | null>(null)
const saving = ref(false)

// Seeded once rather than bound straight to the resource: the design is edited
// locally and only written back on Save, so a refetch must not wipe an hour of
// placement work.
watch(
	() => designer.data,
	(data) => {
		if (data && !template.value) template.value = { ...data.template }
	},
	{ immediate: true }
)

const missing = computed(() =>
	template.value && designer.data
		? missingRequirements(
				designer.data.variables,
				template.value.background_image,
				template.value.elements
		  )
		: []
)

async function save() {
	if (!template.value || saving.value) return
	saving.value = true
	try {
		await call('lms.lms.certificates.save_certificate_template', {
			reference_doctype: referenceDoctype.value,
			reference_name: referenceName.value,
			template: template.value,
		})
		// Saved incomplete on purpose. Half a design is worth keeping — the
		// moderator comes back to it — and the gate that cares is on the
		// invitation, not on this button.
		toast.success(
			missing.value.length
				? __('Certificate saved. {0} still to place.').format(
						missing.value.length
				  )
				: __('Certificate saved')
		)
		await designer.reload()
	} catch (error) {
		toast.error(errorMessage(error, __('Could not save the certificate')))
	} finally {
		saving.value = false
	}
}

function exit() {
	if (isCourse.value) {
		router.push({
			name: 'CourseDetail',
			params: { courseName: props.courseName },
		})
		return
	}
	router.push({
		name: 'ProgramDetail',
		params: { programName: props.programName },
	})
}

usePageMeta(() => ({
	title: __('Certificate'),
	icon: brand.favicon,
}))
</script>
