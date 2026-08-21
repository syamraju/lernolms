<template>
	<section class="rounded-md border bg-surface-gray-1 p-4">
		<header class="flex flex-wrap items-center gap-2">
			<button
				type="button"
				data-section-handle
				class="shrink-0 cursor-grab rounded p-1 text-ink-gray-4 transition-colors hover:text-ink-gray-7 active:cursor-grabbing"
				:aria-label="__('Reorder {0}').format(section.title)"
			>
				<span class="lucide-grip-vertical size-4" />
			</button>

			<span class="shrink-0 text-p-base-semibold text-ink-gray-9">
				{{
					section.is_published
						? __('Section {0}:').format(position)
						: __('Unpublished section:')
				}}
			</span>

			<input
				:value="section.title"
				class="min-w-0 flex-1 rounded border border-transparent bg-transparent px-2 py-1 text-p-base text-ink-gray-9 transition-colors hover:border-outline-gray-2 focus:border-outline-gray-4 focus:bg-surface-base focus:outline-none"
				:aria-label="__('Section title')"
				@change="onRenameSection"
			/>

			<span class="shrink-0 text-p-sm text-ink-gray-5">
				{{
					section.items.length === 1
						? __('1 item')
						: __('{0} items').format(section.items.length)
				}}
			</span>

			<Tooltip :text="publishTooltip">
				<Button
					variant="ghost"
					class="!size-8"
					:loading="isBusy(`section-pub:${section.name}`)"
					:label="
						section.is_published
							? __('Unpublish section')
							: __('Publish section')
					"
					@click="$emit('toggle-published', section)"
				>
					<template #icon>
						<span
							class="size-4"
							:class="section.is_published ? 'lucide-eye' : 'lucide-eye-off'"
						/>
					</template>
				</Button>
			</Tooltip>

			<Button
				variant="ghost"
				theme="red"
				class="!size-8"
				:loading="isBusy(`section-del:${section.name}`)"
				:label="__('Delete section')"
				@click="$emit('delete', section)"
			>
				<template #icon>
					<span class="lucide-trash-2 size-4" />
				</template>
			</Button>
		</header>

		<div class="mt-2 ps-8">
			<input
				:value="section.learning_objective ?? ''"
				:placeholder="
					__('What will students be able to do at the end of this section?')
				"
				:aria-label="__('Section learning objective')"
				class="w-full rounded border border-transparent bg-transparent px-2 py-1 text-p-sm text-ink-gray-7 transition-colors placeholder:text-ink-gray-4 hover:border-outline-gray-2 focus:border-outline-gray-4 focus:bg-surface-base focus:outline-none"
				@change="onObjectiveChange"
			/>
		</div>

		<!-- `tag="ul"`: the rows are <li>, and vuedraggable renders a <div> by
		     default. That put list items in a non-list parent — invalid nesting,
		     and the browser painted a disc marker beside every row. -->
		<Draggable
			:model-value="section.items"
			item-key="name"
			tag="ul"
			handle="[data-item-handle]"
			:animation="150"
			group="curriculum-items"
			class="mt-3 list-none space-y-2 p-0"
			@update:model-value="(items: CurriculumItem[]) => $emit('reorder-items', { section, items })"
		>
			<template #item="{ element }">
				<CurriculumItemRow
					:item="element"
					:position="positionOf(element)"
					:expanded="expandedItem === element.name"
					:isBusy="isBusy"
					@rename="$emit('rename-item', $event)"
					@toggle-published="$emit('toggle-item-published', $event)"
					@toggle-expanded="$emit('toggle-expanded', $event)"
					@delete="$emit('delete-item', $event)"
				>
					<template #body>
						<CurriculumItemBody
							:item="element"
							:courseName="courseName"
							@update="$emit('update-item', $event)"
							@set-quiz="$emit('set-quiz', $event)"
							@edit-content="$emit('edit-content', $event)"
							@refresh="$emit('refresh')"
						/>
					</template>
				</CurriculumItemRow>
			</template>
		</Draggable>

		<div class="mt-3">
			<AddItemForm
				v-if="addingItem"
				:courseName="courseName"
				:loading="isBusy(`item:new:${section.name}`)"
				@add="onAddItem"
				@cancel="addingItem = false"
			/>
			<Button
				v-else
				variant="outline"
				:label="__('Curriculum item')"
				@click="addingItem = true"
			>
				<template #prefix>
					<span class="lucide-plus size-4" />
				</template>
			</Button>
		</div>
	</section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Button, Tooltip } from 'frappe-ui'
import Draggable from 'vuedraggable'
import CurriculumItemRow from './CurriculumItemRow.vue'
import CurriculumItemBody from './CurriculumItemBody.vue'
import AddItemForm from './AddItemForm.vue'
import type {
	CurriculumItem,
	CurriculumItemType,
	CurriculumSection,
} from '@/types'

const props = defineProps<{
	section: CurriculumSection
	courseName: string
	/** 1-based position among published sections, matching the learner's view. */
	position: number
	expandedItem: string
	isBusy: (key: string) => boolean
}>()

const emit = defineEmits<{
	'rename-section': [{ section: CurriculumSection; title: string }]
	'update-objective': [{ section: CurriculumSection; objective: string }]
	'toggle-published': [CurriculumSection]
	delete: [CurriculumSection]
	'add-item': [
		{
			section: CurriculumSection
			itemType: CurriculumItemType
			title: string
			description: string
			quiz: string | null
		}
	]
	'set-quiz': [{ lesson: string; quiz: string | null }]
	'rename-item': [{ item: CurriculumItem; title: string }]
	'toggle-item-published': [CurriculumItem]
	'toggle-expanded': [CurriculumItem]
	'delete-item': [CurriculumItem]
	'update-item': [{ lesson: string; values: Record<string, unknown> }]
	'edit-content': [CurriculumItem]
	'reorder-items': [{ section: CurriculumSection; items: CurriculumItem[] }]
	refresh: []
}>()

const addingItem = ref(false)

// Numbering runs per type, the way the learner reads it — "Lecture 1, Quiz 1,
// Lecture 2" rather than a single running count across kinds.
const positionsByName = computed(() => {
	const counters: Record<string, number> = {}
	const map: Record<string, number> = {}
	for (const item of props.section.items) {
		counters[item.item_type] = (counters[item.item_type] ?? 0) + 1
		map[item.name] = counters[item.item_type]
	}
	return map
})

function positionOf(item: CurriculumItem): number {
	return positionsByName.value[item.name] ?? 1
}

const publishTooltip = computed(() =>
	props.section.is_published
		? __('Hide this section and everything in it')
		: __('Show this section to learners')
)

function onRenameSection(event: Event) {
	const input = event.target as HTMLInputElement
	const title = input.value.trim()
	if (!title || title === props.section.title) {
		input.value = props.section.title
		return
	}
	emit('rename-section', { section: props.section, title })
}

function onObjectiveChange(event: Event) {
	const objective = (event.target as HTMLInputElement).value.trim()
	if (objective === (props.section.learning_objective ?? '')) return
	emit('update-objective', { section: props.section, objective })
}

function onAddItem(payload: {
	itemType: CurriculumItemType
	title: string
	description: string
	quiz: string | null
}) {
	addingItem.value = false
	emit('add-item', { section: props.section, ...payload })
}
</script>
