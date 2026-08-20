<!--
	Meet link editor. Figma: node 160:40807.

	The design shows a generated link with a copy button. Nothing in this LMS
	mints meeting URLs for a student-organised event (the Zoom/Google Meet
	integrations belong to batches and live classes, which only staff create), so
	the field is an input the organiser pastes into rather than a generator that
	would have nothing to generate. The copy affordance is kept and works on
	whatever is in the field.
-->
<template>
	<LearnoDialog
		:open="open"
		:title="__('Create Meet link')"
		:width="564"
		@update:open="$emit('update:open', $event)"
		@save="save"
	>
		<div class="flex flex-col gap-6 py-2">
			<fieldset v-if="repeats" class="flex flex-col gap-4">
				<label class="flex items-center gap-4">
					<input v-model="scope" type="radio" value="this" class="size-5 accent-[#1e3a8a]" />
					<span class="text-[16px]">{{ __('This Event') }}</span>
				</label>
				<label class="flex items-center gap-4">
					<input v-model="scope" type="radio" value="all" class="size-5 accent-[#1e3a8a]" />
					<span class="text-[16px]">{{ __('All Events') }}</span>
				</label>
			</fieldset>

			<div class="flex items-center gap-3 border-t border-[var(--learno-line-soft)] pt-6">
				<span
					class="lucide-video size-6 shrink-0 text-[var(--learno-ink-subtle)]"
					aria-hidden="true"
				/>
				<div class="relative flex-1">
					<input
						v-model.trim="draft"
						type="url"
						inputmode="url"
						class="w-full rounded-[var(--learno-r-sm)] border border-[var(--learno-line)] py-3 pe-11 ps-4 text-[14px]"
						placeholder="https://meet.example.com/abc-defg-hij"
					/>
					<button
						type="button"
						class="absolute end-2 top-1/2 grid size-8 -translate-y-1/2 place-items-center rounded text-[var(--learno-ink-subtle)] transition hover:bg-black/5 disabled:opacity-40"
						:disabled="!draft"
						:aria-label="__('Copy link')"
						@click="copy"
					>
						<span
							:class="[copied ? 'lucide-check' : 'lucide-copy', 'size-4']"
							aria-hidden="true"
						/>
					</button>
				</div>
			</div>

			<p
				class="rounded-[var(--learno-r-sm)] bg-[#eff6ff] px-4 py-3 text-[13px] text-[#1e3a8a]"
			>
				{{ __('Share this meet link for others to join the meet') }}
			</p>

			<p v-if="error" class="text-[12px] text-[#ea2b2b]" role="alert">
				{{ error }}
			</p>
		</div>
	</LearnoDialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import LearnoDialog from '@/components/Learno/LearnoDialog.vue'

const props = defineProps<{
	open: boolean
	link?: string
	repeats?: boolean
}>()

const emit = defineEmits<{
	(e: 'update:open', value: boolean): void
	(e: 'apply', link: string, scope: 'this' | 'all'): void
}>()

const draft = ref('')
const scope = ref<'this' | 'all'>('this')
const copied = ref(false)
const error = ref('')

watch(
	() => props.open,
	(isOpen) => {
		if (!isOpen) return
		draft.value = props.link || ''
		scope.value = 'this'
		copied.value = false
		error.value = ''
	},
	{ immediate: true }
)

async function copy() {
	try {
		await navigator.clipboard.writeText(draft.value)
		copied.value = true
		setTimeout(() => (copied.value = false), 1500)
	} catch {
		// Clipboard access is denied in some embeddings; the field is selectable,
		// so failing quietly is better than an error the user cannot act on.
	}
}

function save() {
	error.value = ''
	const value = draft.value.trim()

	// Only http(s) — the value ends up in an href, and `javascript:` there is an
	// XSS vector that safeUrl would strip on render anyway. Rejecting it here
	// tells the organiser why the link vanished.
	if (value && !/^https?:\/\//i.test(value)) {
		error.value = __('Enter a link starting with http:// or https://')
		return
	}

	emit('apply', value, scope.value)
	emit('update:open', false)
}
</script>
