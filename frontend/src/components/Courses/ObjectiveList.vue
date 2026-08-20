<template>
	<div class="space-y-2">
		<Draggable
			v-model="rows"
			item-key="key"
			handle="[data-drag-handle]"
			:animation="150"
			ghost-class="opacity-40"
			class="space-y-2"
			@update:model-value="commit"
		>
			<template #item="{ element, index }">
				<div class="group flex items-center gap-2">
					<button
						type="button"
						data-drag-handle
						class="shrink-0 cursor-grab rounded p-1 text-ink-gray-4 transition-colors hover:text-ink-gray-7 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-outline-gray-4 active:cursor-grabbing"
						:aria-label="__('Reorder item {0}').format(index + 1)"
						@keydown.up.prevent="move(index, index - 1)"
						@keydown.down.prevent="move(index, index + 1)"
					>
						<span class="lucide-grip-vertical size-4" />
					</button>

					<div class="relative min-w-0 flex-1">
						<input
							:value="element.objective"
							type="text"
							:maxlength="maxLength"
							:placeholder="placeholderFor(index)"
							:aria-label="__('{0} {1}').format(itemLabel, index + 1)"
							class="w-full rounded-md border border-outline-gray-2 bg-surface-base py-1.5 pe-14 ps-3 text-p-base text-ink-gray-9 transition-colors placeholder:text-ink-gray-4 hover:border-outline-gray-3 focus:border-outline-gray-4 focus:outline-none"
							@input="onInput(index, $event)"
							@keydown.enter.prevent="addAfter(index)"
						/>
						<span
							class="pointer-events-none absolute end-3 top-1/2 -translate-y-1/2 text-p-sm tabular-nums text-ink-gray-4"
						>
							{{ maxLength - (element.objective?.length ?? 0) }}
						</span>
					</div>

					<Button
						variant="ghost"
						theme="red"
						class="!size-8 shrink-0"
						:label="__('Delete item {0}').format(index + 1)"
						@click="remove(index)"
					>
						<template #icon>
							<span class="lucide-trash-2 size-4" />
						</template>
					</Button>
				</div>
			</template>
		</Draggable>

		<button
			type="button"
			class="flex items-center gap-2 rounded px-1 py-1 text-p-base-medium text-ink-blue-3 transition-colors hover:text-ink-blue-2 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-outline-gray-4"
			@click="addAfter(rows.length - 1)"
		>
			<span class="lucide-plus size-4" />
			{{ addLabel }}
		</button>
	</div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Button } from 'frappe-ui'
import Draggable from 'vuedraggable'
import type { LMSCourseObjective } from '@/types/lms/LMSCourseObjective'

/**
 * The editable list behind all three planning tables (objectives,
 * requirements, intended learners).
 *
 * Blank rows are a UI affordance, not data. The component shows `minRows`
 * boxes so the page reads as "you need four of these", but `objective` is a
 * required field on the child doctype — persisting an empty row makes every
 * subsequent save of the course fail validation. So the blanks live only in
 * `rows`, and what is emitted upward is always the filled subset.
 */

type Row = LMSCourseObjective & { key: string }

const props = withDefaults(
	defineProps<{
		modelValue?: LMSCourseObjective[]
		/** Rotated through the rows as example copy. */
		placeholders?: string[]
		addLabel?: string
		/** Screen-reader name for a single row, e.g. "Objective". */
		itemLabel?: string
		maxLength?: number
		/** Empty rows rendered to show how many are expected. */
		minRows?: number
	}>(),
	{
		modelValue: () => [],
		placeholders: () => [],
		addLabel: 'Add more to your response',
		itemLabel: 'Item',
		maxLength: 160,
		minRows: 0,
	}
)

const emit = defineEmits<{ 'update:modelValue': [LMSCourseObjective[]] }>()

// vuedraggable needs a stable key per row. Child rows only get a docname after
// a save, so new ones fall back to a counter — never the index, which would
// change under a reorder and make Vue reuse the wrong input.
let nextKey = 0
const keyFor = (row: LMSCourseObjective) => row.name || `new-${nextKey++}`

const rows = ref<Row[]>([])

function seed(source: LMSCourseObjective[]) {
	const next: Row[] = source.map((row) => ({ ...row, key: keyFor(row) }))
	while (next.length < props.minRows) {
		next.push({ objective: '', key: `new-${nextKey++}` } as Row)
	}
	rows.value = next
}

/** What the parent would hold if we committed `rows` right now. */
const filled = (source: Row[]) =>
	source
		.filter((row) => (row.objective ?? '').trim())
		.map(({ key, ...row }) => row as LMSCourseObjective)

// Re-seed only on a genuine external change. Without the comparison, our own
// emit round-trips back through `modelValue` and wipes the blank row the
// author is in the middle of typing into. The first run always seeds: an empty
// incoming value still has to produce the `minRows` placeholder boxes, which
// the equality check alone would read as "already in sync".
let seeded = false
watch(
	() => props.modelValue,
	(incoming) => {
		const rowsIn = incoming ?? []
		if (seeded) {
			const current = filled(rows.value)
			const same =
				current.length === rowsIn.length &&
				current.every(
					(row, index) => row.objective === rowsIn[index]?.objective
				)
			if (same) return
		}
		seeded = true
		seed(rowsIn)
	},
	{ immediate: true, deep: true }
)

function placeholderFor(index: number): string {
	if (!props.placeholders.length) return ''
	return props.placeholders[index % props.placeholders.length]
}

function commit() {
	emit('update:modelValue', filled(rows.value))
}

function onInput(index: number, event: Event) {
	const row = rows.value[index]
	if (!row) return
	row.objective = (event.target as HTMLInputElement).value
	commit()
}

function move(from: number, to: number) {
	if (to < 0 || to >= rows.value.length) return
	const [moved] = rows.value.splice(from, 1)
	rows.value.splice(to, 0, moved)
	commit()
}

function addAfter(index: number) {
	rows.value.splice(index + 1, 0, {
		objective: '',
		key: `new-${nextKey++}`,
	} as Row)
	// Deliberately no commit: an empty row is not data yet, and emitting here
	// would be a no-op that only marks the course dirty.
}

function remove(index: number) {
	rows.value.splice(index, 1)
	commit()
}
</script>
