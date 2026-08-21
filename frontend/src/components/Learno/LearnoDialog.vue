<!--
	The modal shell every calendar dialog shares. Figma: nodes 137:93033
	("Repeat Event"), 144:93460 ("Invitation") and 160:40807 ("Create Meet
	link") — all three are the same frame: a titled header with a square
	outlined close button, a body, and a Discard / Save footer.

	Hand-rolled rather than frappe-ui's Dialog because the student app carries
	its own tokens (see src/styles/learno.css) and frappe-ui's dialog arrives
	wearing the admin app's. The parts that are easy to get wrong are handled
	here so no caller has to: Escape closes, the overlay click closes, focus
	moves in and is restored on close, and the page behind does not scroll.
-->
<template>
	<Teleport to="body">
		<div
			v-if="open"
			class="learno fixed inset-0 z-[60] flex items-center justify-center p-4"
			role="dialog"
			aria-modal="true"
			:aria-label="title"
		>
			<div
				class="absolute inset-0 bg-black/40"
				@click="close"
				aria-hidden="true"
			/>

			<div
				ref="panel"
				class="relative flex max-h-[90vh] w-full flex-col overflow-hidden rounded-[var(--learno-r-lg)] bg-white shadow-2xl"
				:style="{ maxWidth: `${width}px` }"
				@keydown.esc.stop="close"
			>
				<header
					class="flex shrink-0 items-center justify-between border-b border-[var(--learno-line-soft)] px-6 py-5"
				>
					<h2 class="text-[18px] font-semibold text-[var(--learno-ink-strong)]">
						{{ title }}
					</h2>
					<button
						ref="closeButton"
						type="button"
						class="grid size-8 place-items-center rounded-[8px] border border-[#1e3a8a] text-[#1e3a8a] transition hover:bg-[#1e3a8a]/5"
						:aria-label="__('Close')"
						@click="close"
					>
						<span class="lucide-x size-4" aria-hidden="true" />
					</button>
				</header>

				<div class="learno-scroll min-h-0 flex-1 overflow-y-auto px-6 py-5">
					<slot />
				</div>

				<footer
					v-if="!hideFooter"
					class="flex shrink-0 items-center justify-end gap-3 border-t border-[var(--learno-line-soft)] px-6 py-4"
				>
					<slot name="footer">
						<button
							type="button"
							class="learno-btn bg-[#fff1f1] px-5 py-2.5 text-[13px] text-[#c2410c] transition hover:bg-[#ffe4e4]"
							@click="close"
						>
							<span class="lucide-trash-2 size-4" aria-hidden="true" />
							{{ discardLabel || __('Discard') }}
						</button>
						<button
							type="button"
							class="learno-btn bg-[#1e3a8a] px-5 py-2.5 text-[13px] text-white transition hover:bg-[#1c3378] disabled:opacity-55"
							:disabled="busy"
							@click="$emit('save')"
						>
							<span
								:class="[
									busy ? 'lucide-loader-circle animate-spin' : 'lucide-save',
									'size-4',
								]"
								aria-hidden="true"
							/>
							{{ saveLabel || __('Save') }}
						</button>
					</slot>
				</footer>
			</div>
		</div>
	</Teleport>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'

const props = withDefaults(
	defineProps<{
		open: boolean
		title: string
		width?: number
		busy?: boolean
		hideFooter?: boolean
		saveLabel?: string
		discardLabel?: string
	}>(),
	{ width: 564 }
)

const emit = defineEmits<{
	(e: 'update:open', value: boolean): void
	(e: 'save'): void
}>()

const panel = ref<HTMLElement | null>(null)
const closeButton = ref<HTMLElement | null>(null)
let restoreFocusTo: HTMLElement | null = null

function close() {
	emit('update:open', false)
}

// Escape has to work even before anything inside the panel is focused, so it is
// bound on the document rather than only on the panel.
function onKeydown(event: KeyboardEvent) {
	if (event.key === 'Escape') {
		event.stopPropagation()
		close()
	}
}

watch(
	() => props.open,
	async (isOpen) => {
		if (isOpen) {
			restoreFocusTo = document.activeElement as HTMLElement
			document.body.style.overflow = 'hidden'
			document.addEventListener('keydown', onKeydown)
			await nextTick()
			// The first focusable thing inside, falling back to the close button,
			// so a keyboard user lands in the dialog rather than behind it.
			const target = panel.value?.querySelector<HTMLElement>(
				'input, textarea, select, [tabindex]:not([tabindex="-1"])'
			)
			;(target || closeButton.value)?.focus()
		} else {
			document.body.style.overflow = ''
			document.removeEventListener('keydown', onKeydown)
			restoreFocusTo?.focus?.()
			restoreFocusTo = null
		}
	}
)

// A dialog unmounted while open (route change, parent v-if) would otherwise
// leave the page permanently unscrollable.
onBeforeUnmount(() => {
	document.body.style.overflow = ''
	document.removeEventListener('keydown', onKeydown)
})
</script>
