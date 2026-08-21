<template>
	<div class="grid gap-5 lg:grid-cols-[minmax(0,1fr)_20rem]">
		<div class="min-w-0 space-y-4">
			<div class="flex flex-wrap items-center gap-2">
				<FileUploader
					:fileTypes="['image/png', 'image/jpeg']"
					:uploadArgs="{ private: false }"
					:validateFile="validateBackground"
					@success="setBackground"
				>
					<template v-slot="{ uploading, progress, openFileSelector }">
						<Button
							:variant="template.background_image ? 'subtle' : 'solid'"
							:loading="uploading"
							:label="
								uploading
									? __('Uploading {0}%').format(progress)
									: template.background_image
									? __('Replace background')
									: __('Upload background')
							"
							@click="openFileSelector"
						/>
					</template>
				</FileUploader>

				<Button
					variant="subtle"
					:label="__('Add text')"
					@click="addElement('Text')"
				/>
				<FileUploader
					:fileTypes="['image/png', 'image/jpeg']"
					:uploadArgs="{ private: false }"
					@success="addImage"
				>
					<template v-slot="{ uploading, openFileSelector }">
						<Button
							variant="subtle"
							:loading="uploading"
							:label="__('Add image')"
							@click="openFileSelector"
						/>
					</template>
				</FileUploader>
				<span class="grow" />
				<Badge
					:theme="missing.length ? 'orange' : 'green'"
					:label="
						missing.length
							? __('{0} left to place').format(missing.length)
							: __('Ready to issue')
					"
				/>
			</div>

			<CertificateCanvas
				:template="template"
				:variables="variables"
				:values="sampleValues"
				:selectedIndex="selectedIndex"
				editable
				@select="selectedIndex = $event"
				@change="patchElement"
			/>

			<p class="text-p-sm text-ink-gray-5">
				{{
					__(
						'Values shown here are samples. Each certificate is filled in with the learner’s own details when it is issued.'
					)
				}}
			</p>
		</div>

		<aside class="space-y-5">
			<!--
				The checklist is the whole gate, stated plainly. A moderator who
				cannot invite instructors needs to see the reason here rather than
				discover it in an error on the next screen.
			-->
			<section>
				<h3 class="text-p-sm-semibold text-ink-gray-8">
					{{ __('Required on every certificate') }}
				</h3>
				<ul class="mt-2 space-y-1.5">
					<li
						v-for="requirement in requirements"
						:key="requirement.key"
						class="flex items-start gap-2 text-p-sm"
					>
						<span
							class="mt-0.5 size-4 shrink-0"
							:class="
								requirement.done
									? 'lucide-check-circle-2 text-ink-green-3'
									: 'lucide-circle text-ink-gray-4'
							"
						/>
						<span
							:class="requirement.done ? 'text-ink-gray-6' : 'text-ink-gray-8'"
						>
							{{ requirement.label }}
						</span>
					</li>
				</ul>
			</section>

			<section>
				<h3 class="text-p-sm-semibold text-ink-gray-8">
					{{ __('Add a field') }}
				</h3>
				<div class="mt-2 flex flex-wrap gap-1.5">
					<Button
						v-for="variable in variables"
						:key="variable.key"
						variant="outline"
						size="sm"
						:disabled="isPlaced(variable.key)"
						:label="variable.label"
						@click="addElement('Variable', variable)"
					/>
				</div>
			</section>

			<section>
				<h3 class="text-p-sm-semibold text-ink-gray-8">
					{{ __('Issue date') }}
				</h3>
				<FormControl
					class="mt-2"
					type="select"
					:modelValue="template.issue_date_source"
					:options="[
						{ label: __('Course completion date'), value: 'Completion Date' },
						{ label: __('A fixed date'), value: 'Custom Date' },
					]"
					@update:modelValue="setIssueSource"
				/>
				<FormControl
					v-if="template.issue_date_source === 'Custom Date'"
					class="mt-2"
					type="date"
					:modelValue="template.custom_issue_date"
					@update:modelValue="template.custom_issue_date = $event"
				/>
			</section>

			<section v-if="selected">
				<div class="flex items-center justify-between">
					<h3 class="text-p-sm-semibold text-ink-gray-8">
						{{ __('Selected element') }}
					</h3>
					<Button
						variant="ghost"
						size="sm"
						:label="__('Remove')"
						@click="removeSelected"
					/>
				</div>

				<FormControl
					v-if="selected.element_type === 'Text'"
					class="mt-2"
					type="textarea"
					:label="__('Text')"
					:modelValue="selected.content"
					@update:modelValue="patchSelected({ content: $event })"
				/>

				<FormControl
					v-if="
						selected.element_type === 'Variable' && isDateVariable(selected)
					"
					class="mt-2"
					type="select"
					:label="__('Date format')"
					:modelValue="selected.date_format"
					:options="dateFormats.map((value) => ({ label: value, value }))"
					@update:modelValue="patchSelected({ date_format: $event })"
				/>

				<div
					v-if="selected.element_type !== 'Image'"
					class="mt-2 grid grid-cols-2 gap-2"
				>
					<FormControl
						type="number"
						:label="__('Font size')"
						:modelValue="selected.font_size"
						@update:modelValue="patchSelected({ font_size: Number($event) })"
					/>
					<FormControl
						type="select"
						:label="__('Weight')"
						:modelValue="selected.font_weight"
						:options="['300', '400', '500', '600', '700']"
						@update:modelValue="patchSelected({ font_weight: $event })"
					/>
					<FormControl
						type="select"
						:label="__('Align')"
						:modelValue="selected.align"
						:options="['left', 'center', 'right']"
						@update:modelValue="patchSelected({ align: $event })"
					/>
					<FormControl
						type="color"
						:label="__('Colour')"
						:modelValue="selected.color"
						@update:modelValue="patchSelected({ color: $event })"
					/>
				</div>

				<FormControl
					class="mt-2"
					type="number"
					:label="__('Rotation')"
					:modelValue="selected.rotation"
					@update:modelValue="patchSelected({ rotation: Number($event) })"
				/>
			</section>
			<p v-else class="text-p-sm text-ink-gray-5">
				{{ __('Select something on the certificate to style it.') }}
			</p>
		</aside>
	</div>
</template>

<script setup lang="ts">
/**
 * The certificate designer: an uploaded background, and the fields placed on it.
 *
 * It is a controlled component. The template lives in the parent — the create
 * wizard holds one for a course that does not exist yet and posts it alongside
 * the course, the settings page holds one it saves on its own. Keeping the state
 * out of here is what lets the same editor serve both without knowing which it
 * is in.
 */
import { computed } from 'vue'
import { Badge, Button, FileUploader, FormControl, toast } from 'frappe-ui'
import CertificateCanvas from '@/components/Certificates/CertificateCanvas.vue'
import { missingRequirements, newElement } from '@/utils/certificate'
import type {
	CertificateElement,
	CertificateTemplate,
	CertificateVariable,
	ElementType,
} from '@/utils/certificate'

const props = withDefaults(
	defineProps<{
		variables: CertificateVariable[]
		sampleValues?: Record<string, unknown>
		dateFormats?: string[]
	}>(),
	{ sampleValues: () => ({}), dateFormats: () => [] }
)

const template = defineModel<CertificateTemplate>({ required: true })
const selectedIndex = defineModel<number>('selectedIndex', { default: -1 })

// 12 MB: certificate artwork is a full-bleed image and a 300dpi A4 export lands
// well inside it, but a raw camera file does not belong on a certificate.
const MAX_BACKGROUND_BYTES = 12 * 1024 * 1024

const selected = computed<CertificateElement | null>(
	() => template.value.elements[selectedIndex.value] ?? null
)

const missing = computed(() =>
	missingRequirements(
		props.variables,
		template.value.background_image,
		template.value.elements
	)
)

const placedKeys = computed(
	() =>
		new Set(
			template.value.elements
				.filter((element) => element.element_type === 'Variable')
				.map((element) => element.variable || '')
		)
)

const requirements = computed(() => [
	{
		key: 'background',
		label: __('A background image'),
		done: Boolean(template.value.background_image),
	},
	...props.variables
		.filter((variable) => variable.mandatory)
		.map((variable) => ({
			key: variable.key,
			label: variable.label,
			done: placedKeys.value.has(variable.key),
		})),
])

function isPlaced(key: string) {
	return placedKeys.value.has(key)
}

function isDateVariable(element: CertificateElement) {
	return (
		props.variables.find((entry) => entry.key === element.variable)?.type ===
		'date'
	)
}

function validateBackground(file: File) {
	if (file.size > MAX_BACKGROUND_BYTES) {
		return __('Please use a background under {0} MB.').format(
			MAX_BACKGROUND_BYTES / 1024 / 1024
		)
	}
	return null
}

/**
 * Adopt an uploaded image, and take the canvas size from it.
 *
 * The image's own pixel size becomes the coordinate system, so a moderator who
 * replaces a 1754px background with a 3508px one does not have every field jump
 * to a quarter of the page. Measuring it rather than assuming a default is what
 * keeps the two in step.
 */
function setBackground(file: { file_url: string }) {
	const probe = new Image()
	probe.onload = () => {
		template.value = {
			...template.value,
			background_image: file.file_url,
			canvas_width: probe.naturalWidth || template.value.canvas_width,
			canvas_height: probe.naturalHeight || template.value.canvas_height,
		}
	}
	probe.onerror = () => {
		toast.error(__('That image could not be read. Try a PNG or JPG.'))
	}
	probe.src = file.file_url
}

function addElement(kind: ElementType, variable?: CertificateVariable) {
	if (kind === 'Variable' && variable && isPlaced(variable.key)) return
	const element = newElement(
		kind,
		{
			width: template.value.canvas_width,
			height: template.value.canvas_height,
		},
		template.value.elements.length,
		variable
	)
	template.value = {
		...template.value,
		elements: [...template.value.elements, element],
	}
	selectedIndex.value = template.value.elements.length - 1
}

function addImage(file: { file_url: string }) {
	addElement('Image')
	patchSelected({ image: file.file_url })
}

function patchElement(index: number, patch: Partial<CertificateElement>) {
	template.value = {
		...template.value,
		elements: template.value.elements.map((element, position) =>
			position === index ? { ...element, ...patch } : element
		),
	}
}

function patchSelected(patch: Partial<CertificateElement>) {
	if (selectedIndex.value < 0) return
	patchElement(selectedIndex.value, patch)
}

function removeSelected() {
	if (selectedIndex.value < 0) return
	const index = selectedIndex.value
	template.value = {
		...template.value,
		elements: template.value.elements.filter(
			(_, position) => position !== index
		),
	}
	selectedIndex.value = -1
}

function setIssueSource(value: 'Completion Date' | 'Custom Date') {
	template.value = {
		...template.value,
		issue_date_source: value,
		// Switching back to the completion date drops the fixed one rather than
		// keeping it hidden, so re-opening the select cannot quietly re-apply a
		// date the moderator has already moved away from.
		custom_issue_date:
			value === 'Custom Date' ? template.value.custom_issue_date : null,
	}
}
</script>
