<template>
	<div class="space-y-6">
		<p class="text-p-base text-ink-gray-7">
			{{
				__(
					'Build your course out of sections holding lectures and practice — quizzes, coding exercises and assignments. Label everything clearly; this is the outline learners navigate by.'
				)
			}}
		</p>

		<div
			class="flex flex-wrap items-center gap-x-6 gap-y-2 rounded-md border bg-surface-gray-1 px-4 py-3 text-p-sm"
		>
			<span class="text-ink-gray-7">
				<strong class="tabular-nums text-ink-gray-9">{{ lectureCount }}</strong>
				{{ lectureCount === 1 ? __('lecture') : __('lectures') }}
				<span class="text-ink-gray-5">
					{{ __('of {0} required').format(MIN_LECTURES) }}
				</span>
			</span>
			<span class="text-ink-gray-7">
				<strong class="tabular-nums text-ink-gray-9">
					{{ formatVideoLength(status.data?.video_seconds) }}
				</strong>
				{{ __('of video') }}
				<span class="text-ink-gray-5">{{ __('of 30min required') }}</span>
			</span>
			<span v-if="practiceCount" class="text-ink-gray-7">
				<strong class="tabular-nums text-ink-gray-9">{{ practiceCount }}</strong>
				{{ practiceCount === 1 ? __('practice activity') : __('practice activities') }}
			</span>
			<span v-if="draftCount" class="text-ink-amber-3">
				{{
					draftCount === 1
						? __('1 item is still a draft and hidden from learners.')
						: __('{0} items are still drafts and hidden from learners.').format(
								draftCount
						  )
				}}
			</span>
			<span
				v-if="status.data?.lectures_without_duration"
				class="text-ink-amber-3"
			>
				{{
					status.data.lectures_without_duration === 1
						? __(
								'1 lecture has a video added outside this page, so its length is not counted.'
						  )
						: __(
								'{0} lectures have videos added outside this page, so their length is not counted.'
						  ).format(status.data.lectures_without_duration)
				}}
			</span>
		</div>

		<SkeletonLoader v-if="resource.loading && !resource.data" variant="form" />

		<div
			v-else-if="!sections.length"
			class="rounded-md border border-dashed p-8 text-center"
		>
			<span class="lucide-layers mx-auto mb-2 block size-6 text-ink-gray-4" />
			<p class="text-p-base text-ink-gray-6">
				{{ __('No sections yet. Add your first one to get started.') }}
			</p>
		</div>

		<Draggable
			v-else
			:model-value="sections"
			item-key="name"
			handle="[data-section-handle]"
			:animation="150"
			class="space-y-4"
			@update:model-value="onReorderSections"
		>
			<template #item="{ element }">
				<CurriculumSection
					:section="element"
					:position="publishedPosition(element)"
					:expandedItem="expandedItem"
					:isBusy="isBusy"
					@rename-section="onRenameSection"
					@update-objective="onUpdateObjective"
					@toggle-published="onToggleSection"
					@delete="onDeleteSection"
					@add-item="onAddItem"
					@rename-item="onRenameItem"
					@toggle-item-published="onToggleItem"
					@toggle-expanded="onToggleExpanded"
					@delete-item="onDeleteItem"
					@update-item="onUpdateItem"
					@edit-content="onEditContent"
					@reorder-items="onReorderItems"
					@refresh="refresh"
				/>
			</template>
		</Draggable>

		<div v-if="addingSection" class="space-y-3 rounded-md border border-dashed p-4">
			<FormControl
				ref="sectionTitleInput"
				v-model="newSection.title"
				variant="outline"
				:label="__('Section title')"
				:placeholder="__('e.g. Getting started')"
				@keydown.enter.prevent="submitSection"
			/>
			<FormControl
				v-model="newSection.objective"
				variant="outline"
				:label="__('What will students be able to do?')"
				:placeholder="__('Optional, but it keeps the section focused')"
			/>
			<div class="flex items-center justify-end gap-2">
				<Button :label="__('Cancel')" @click="addingSection = false" />
				<Button
					variant="solid"
					:disabled="!newSection.title.trim()"
					:loading="isBusy('section:new')"
					:label="__('Add section')"
					@click="submitSection"
				/>
			</div>
		</div>
		<Button v-else variant="outline" :label="__('Section')" @click="openAddSection">
			<template #prefix>
				<span class="lucide-plus size-4" />
			</template>
		</Button>
	</div>
</template>

<script setup lang="ts">
/**
 * The course structure editor: sections, lectures and practice activities,
 * with their order and draft state.
 *
 * This was the "Curriculum" step of a standalone setup wizard that has since
 * been folded into the course tabs. It is the only outline editor now — the
 * wizard's copy and the editor tab's chapter sidebar used to manage the same
 * chapters and lessons from two places.
 */
import { computed, getCurrentInstance, nextTick, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Button, FormControl, createResource } from 'frappe-ui'
import Draggable from 'vuedraggable'
import SkeletonLoader from '@/components/SkeletonLoader.vue'
import CurriculumSection from '@/components/Curriculum/CurriculumSection.vue'
import { useCurriculum } from '@/composables/useCurriculum'
import { formatVideoLength } from '@/utils/courseCreation'
import type {
	CourseCreationStatus,
	CurriculumItem,
	CurriculumItemType,
	CurriculumSection as Section,
	Resource,
} from '@/types'

// Mirrors MIN_LECTURES in lms/lms/course_creation.py; copy only — the server
// is what actually gates submission.
const MIN_LECTURES = 5

interface DialogAction {
	label: string
	theme?: string
	variant?: string
	onClick: (close: () => void) => void
}
type DialogFn = (opts: {
	title: string
	message: string
	actions: DialogAction[]
}) => void

const props = defineProps<{ courseName: string }>()
// Structural changes move the setup checklist's ticks, so the page above is
// told to refetch rather than each surface polling on its own.
const emit = defineEmits<{ changed: [] }>()

const router = useRouter()
const app = getCurrentInstance()!
const { $dialog } = app.appContext.config.globalProperties as {
	$dialog: DialogFn
}

const courseName = computed(() => props.courseName)

// Lecture counts and total video length are computed server-side from the
// lessons' blocks, which this component never loads.
const status = createResource({
	url: 'lms.lms.course_creation.get_course_creation_status',
	makeParams: () => ({ course: props.courseName }),
	auto: true,
}) as Resource<CourseCreationStatus | null>
const expandedItem = ref('')
const addingSection = ref(false)
const sectionTitleInput = ref<{ $el?: HTMLElement } | null>(null)
const newSection = reactive({ title: '', objective: '' })

const curriculum = useCurriculum(courseName, () => {
	void status.reload()
	emit('changed')
})
const { resource, sections, isBusy } = curriculum

const allItems = computed<CurriculumItem[]>(() =>
	sections.value.flatMap((section) => section.items)
)
const lectureCount = computed(
	() => allItems.value.filter((item) => item.item_type === 'Lecture').length
)
const practiceCount = computed(
	() => allItems.value.filter((item) => item.item_type !== 'Lecture').length
)
const draftCount = computed(
	() => allItems.value.filter((item) => !item.is_published).length
)

// Sections are numbered the way a learner sees them, so a draft section sitting
// between two live ones does not push the visible numbering out of step.
const publishedPositions = computed(() => {
	const map: Record<string, number> = {}
	let counter = 0
	for (const section of sections.value) {
		if (section.is_published) counter += 1
		map[section.name] = counter || 1
	}
	return map
})
function publishedPosition(section: Section): number {
	return publishedPositions.value[section.name] ?? 1
}

function refresh() {
	void resource.reload()
	void status.reload()
}

async function openAddSection() {
	addingSection.value = true
	newSection.title = ''
	newSection.objective = ''
	await nextTick()
	sectionTitleInput.value?.$el?.querySelector('input')?.focus()
}

async function submitSection() {
	if (!newSection.title.trim()) return
	await curriculum.addSection(newSection.title.trim(), newSection.objective.trim())
	addingSection.value = false
}

function onRenameSection({ section, title }: { section: Section; title: string }) {
	void curriculum.updateSection(section.name, title, section.learning_objective)
}

function onUpdateObjective({
	section,
	objective,
}: {
	section: Section
	objective: string
}) {
	void curriculum.updateSection(section.name, section.title, objective)
}

function onToggleSection(section: Section) {
	void curriculum.setSectionPublished(section.name, !section.is_published)
}

function onDeleteSection(section: Section) {
	$dialog({
		title: __('Delete section'),
		message: __(
			'Deleting "{0}" also deletes its {1} item(s) and their content. This cannot be undone.'
		).format(section.title, section.items.length),
		actions: [
			{
				label: __('Delete'),
				theme: 'red',
				variant: 'solid',
				onClick(close) {
					void curriculum.deleteSection(section.name)
					close()
				},
			},
		],
	})
}

function onReorderSections(next: Section[]) {
	// Optimistic: apply locally so the drag does not snap back, then let the
	// server's answer replace it.
	resource.data = next
	void curriculum.reorderSections(next.map((section) => section.name))
}

async function onAddItem({
	section,
	itemType,
	title,
	description,
}: {
	section: Section
	itemType: CurriculumItemType
	title: string
	description: string
}) {
	const result = await curriculum.addItem(section.name, itemType, title, description)
	// Open the new item straight away: adding one is always followed by filling
	// it in, and a collapsed row would hide the work that comes next.
	if (result?.lesson) expandedItem.value = result.lesson
}

function onRenameItem({ item, title }: { item: CurriculumItem; title: string }) {
	void curriculum.updateItem(item.name, { title })
}

function onUpdateItem({
	lesson,
	values,
}: {
	lesson: string
	values: Record<string, unknown>
}) {
	void curriculum.updateItem(lesson, values)
}

function onToggleItem(item: CurriculumItem) {
	void curriculum.setItemPublished(item.name, !item.is_published)
}

function onToggleExpanded(item: CurriculumItem) {
	expandedItem.value = expandedItem.value === item.name ? '' : item.name
}

function onDeleteItem(item: CurriculumItem) {
	$dialog({
		title: __('Delete {0}').format(__(item.item_type)),
		message: __('Delete "{0}"? This cannot be undone.').format(item.title),
		actions: [
			{
				label: __('Delete'),
				theme: 'red',
				variant: 'solid',
				onClick(close) {
					void curriculum.deleteItem(item.name)
					close()
				},
			},
		],
	})
}

function onReorderItems({
	section,
	items,
}: {
	section: Section
	items: CurriculumItem[]
}) {
	// Only the moved row needs telling: the server renumbers the rest. Find it
	// by comparing against the order the section had before the drop.
	const before = section.items.map((item) => item.name)
	const after = items.map((item) => item.name)
	const movedIndex = after.findIndex((name, index) => name !== before[index])
	if (movedIndex === -1) return
	void curriculum.moveItem(after[movedIndex], section.name, movedIndex)
}

/** Hand off to whichever editor owns this item type's real content. */
function onEditContent(item: CurriculumItem) {
	if (item.item_type === 'Assignment' && item.assignment) {
		router.push({
			name: 'CourseAssignmentEditor',
			params: { courseName: courseName.value, assignmentName: item.assignment },
		})
		return
	}
	if (item.item_type === 'Coding Exercise' && item.exercise) {
		router.push({
			name: 'CourseExerciseEditor',
			params: { courseName: courseName.value, exerciseName: item.exercise },
		})
		return
	}
	// A lecture's body is an EditorJS document, which the existing block editor
	// already owns; sending the author there beats rebuilding it here.
	const section = sections.value.find((s) =>
		s.items.some((i) => i.name === item.name)
	)
	if (!section) return
	const sectionIndex = sections.value.indexOf(section) + 1
	const itemIndex = section.items.findIndex((i) => i.name === item.name) + 1
	router.push({
		name: 'CourseDetail',
		params: { courseName: courseName.value },
		hash: '#editor',
		query: { view: 'lesson', editLesson: `${sectionIndex}-${itemIndex}` },
	})
}
</script>
