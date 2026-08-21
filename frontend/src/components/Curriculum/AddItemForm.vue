<template>
	<div class="rounded-md border border-dashed p-3">
		<!-- Step 1: which kind of item -->
		<div v-if="!chosen" class="space-y-3">
			<div class="text-p-base-medium text-ink-gray-9">
				{{ __('What are you adding?') }}
			</div>
			<div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
				<button
					v-for="type in ITEM_TYPES"
					:key="type"
					type="button"
					class="flex items-start gap-3 rounded-md border border-outline-gray-2 p-3 text-start transition-colors hover:border-outline-gray-4 hover:bg-surface-gray-1 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-outline-gray-4"
					@click="choose(type)"
				>
					<span
						class="mt-0.5 size-5 shrink-0 text-ink-gray-6"
						:class="ITEM_TYPE_META[type].icon"
						aria-hidden="true"
					/>
					<span class="min-w-0">
						<span class="block text-p-base-medium text-ink-gray-9">
							{{ __(ITEM_TYPE_META[type].label) }}
						</span>
						<span class="block text-p-sm text-ink-gray-6">
							{{ __(ITEM_TYPE_META[type].description) }}
						</span>
					</span>
				</button>
			</div>
			<Button variant="ghost" :label="__('Cancel')" @click="$emit('cancel')" />
		</div>

		<!-- Step 2: name it -->
		<div v-else class="space-y-3">
			<div class="flex items-center gap-2">
				<span
					class="size-4 shrink-0 text-ink-gray-6"
					:class="ITEM_TYPE_META[chosen].icon"
					aria-hidden="true"
				/>
				<span class="text-p-base-medium text-ink-gray-9">
					{{ __('New {0}').format(__(ITEM_TYPE_META[chosen].label)) }}
				</span>
			</div>

			<div class="relative">
				<input
					ref="titleInput"
					v-model="title"
					type="text"
					:maxlength="TITLE_LIMIT"
					:placeholder="__('Enter a title')"
					:aria-label="__('Title')"
					class="w-full rounded-md border border-outline-gray-2 bg-surface-base py-1.5 pe-14 ps-3 text-p-base text-ink-gray-9 transition-colors hover:border-outline-gray-3 focus:border-outline-gray-4 focus:outline-none"
					@keydown.enter.prevent="submit"
					@keydown.esc="$emit('cancel')"
				/>
				<span
					class="pointer-events-none absolute end-3 top-1/2 -translate-y-1/2 text-p-sm tabular-nums text-ink-gray-4"
				>
					{{ TITLE_LIMIT - title.length }}
				</span>
			</div>

			<textarea
				v-if="chosen === 'Quiz' || chosen === 'Assignment'"
				v-model="description"
				rows="2"
				:placeholder="
					__('{0} description (optional)').format(
						__(ITEM_TYPE_META[chosen].label)
					)
				"
				:aria-label="__('Description')"
				class="w-full rounded-md border border-outline-gray-2 bg-surface-base px-3 py-1.5 text-p-base text-ink-gray-9 transition-colors hover:border-outline-gray-3 focus:border-outline-gray-4 focus:outline-none"
			/>

			<div class="flex items-center justify-end gap-2">
				<Button :label="__('Cancel')" @click="$emit('cancel')" />
				<Button
					variant="solid"
					:disabled="!title.trim()"
					:loading="loading"
					:label="__('Add {0}').format(__(ITEM_TYPE_META[chosen].label))"
					@click="submit"
				/>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { nextTick, ref } from 'vue'
import { Button } from 'frappe-ui'
import { ITEM_TYPES, ITEM_TYPE_META } from '@/utils/curriculum'
import type { CurriculumItemType } from '@/types'

const TITLE_LIMIT = 80

defineProps<{ loading?: boolean }>()

const emit = defineEmits<{
	add: [{ itemType: CurriculumItemType; title: string; description: string }]
	cancel: []
}>()

const chosen = ref<CurriculumItemType | null>(null)
const title = ref('')
const description = ref('')
const titleInput = ref<HTMLInputElement | null>(null)

async function choose(type: CurriculumItemType) {
	chosen.value = type
	// Picking a type is a commitment to naming one, so put the cursor where the
	// author is about to type instead of making them aim for the field.
	await nextTick()
	titleInput.value?.focus()
}

function submit() {
	if (!chosen.value || !title.value.trim()) return
	emit('add', {
		itemType: chosen.value,
		title: title.value.trim(),
		description: description.value.trim(),
	})
}
</script>
