import { computed, ref } from 'vue'
import type { Ref } from 'vue'
import { call, createResource, toast } from 'frappe-ui'
import { errorMessage } from '@/utils/courseCreation'
import type { CurriculumSection, QuizType, Resource } from '@/types'

/**
 * The curriculum tree plus every mutation the builder performs on it.
 *
 * Each endpoint returns the whole tree, so mutations end with a plain
 * assignment rather than a refetch — one round trip per action, and the server
 * stays the authority on ordering and on the publish cascades it enforces.
 */
export function useCurriculum(courseName: Ref<string>, onChanged?: () => void) {
	const busy = ref('')

	const resource = createResource({
		url: 'lms.lms.curriculum.get_curriculum',
		makeParams: () => ({ course: courseName.value, for_author: true }),
		auto: true,
	}) as Resource<CurriculumSection[] | null>

	const sections = computed<CurriculumSection[]>(() => resource.data ?? [])

	/**
	 * Run one mutation.
	 *
	 * `key` marks which control is mid-flight so only that button spins.
	 * Failures are surfaced and swallowed: every caller is a click handler, and
	 * an unhandled rejection out of one is a console error nobody reads.
	 */
	async function mutate<T = CurriculumSection[]>(
		key: string,
		method: string,
		params: Record<string, unknown>,
		fallback: string,
	): Promise<T | null> {
		busy.value = key
		try {
			const result = await call(`lms.lms.curriculum.${method}`, params)
			// Most endpoints hand back the tree; the ones that return something
			// else (an item name, a resource list) are read by the caller.
			if (Array.isArray(result)) {
				resource.data = result as CurriculumSection[]
			} else if (
				result &&
				Array.isArray((result as { curriculum?: unknown }).curriculum)
			) {
				resource.data = (
					result as { curriculum: CurriculumSection[] }
				).curriculum
			}
			onChanged?.()
			return result as T
		} catch (error) {
			toast.error(errorMessage(error, fallback))
			return null
		} finally {
			busy.value = ''
		}
	}

	const isBusy = (key: string) => busy.value === key

	return {
		resource,
		sections,
		busy,
		isBusy,
		mutate,

		addSection: (title: string, learningObjective?: string) =>
			mutate(
				'section:new',
				'upsert_section',
				{
					course: courseName.value,
					title,
					learning_objective: learningObjective || null,
				},
				__('Could not add the section'),
			),

		updateSection: (
			name: string,
			title: string,
			learningObjective?: string | null,
		) =>
			mutate(
				`section:${name}`,
				'upsert_section',
				{
					course: courseName.value,
					name,
					title,
					learning_objective: learningObjective || null,
				},
				__('Could not update the section'),
			),

		setSectionPublished: (chapter: string, published: boolean) =>
			mutate(
				`section-pub:${chapter}`,
				'set_section_published',
				{
					chapter,
					published: published ? 1 : 0,
				},
				__('Could not change the section visibility'),
			),

		deleteSection: (chapter: string) =>
			mutate(
				`section-del:${chapter}`,
				'delete_section',
				{ chapter },
				__('Could not delete the section'),
			),

		reorderSections: (order: string[]) =>
			mutate(
				'section:order',
				'reorder_sections',
				{
					course: courseName.value,
					order,
				},
				__('Could not reorder the sections'),
			),

		addItem: (
			chapter: string,
			itemType: string,
			title: string,
			description?: string,
			quiz?: string | null,
			quizType?: QuizType,
		) =>
			mutate<{ lesson: string; curriculum: CurriculumSection[] }>(
				`item:new:${chapter}`,
				'add_curriculum_item',
				{
					chapter,
					item_type: itemType,
					title,
					description: description || null,
					// Naming a quiz places the one that already exists; without it
					// the server mints an empty quiz for this item to own.
					quiz: quiz || null,
					// Ignored unless a new quiz is being minted: a placed quiz keeps
					// whatever type it was written as.
					quiz_type: quizType || 'Objective',
				},
				__('Could not add the item'),
			),

		setItemQuiz: (lesson: string, quiz: string | null) =>
			mutate(
				`item-quiz:${lesson}`,
				'set_item_quiz',
				{ lesson, quiz: quiz || null },
				__('Could not change the quiz'),
			),

		updateItem: (lesson: string, values: Record<string, unknown>) =>
			mutate(
				`item:${lesson}`,
				'update_curriculum_item',
				{ lesson, ...values },
				__('Could not update the item'),
			),

		setItemPublished: (lesson: string, published: boolean) =>
			mutate(
				`item-pub:${lesson}`,
				'set_item_published',
				{
					lesson,
					published: published ? 1 : 0,
				},
				__('Could not change the item visibility'),
			),

		deleteItem: (lesson: string) =>
			mutate(
				`item-del:${lesson}`,
				'delete_curriculum_item',
				{ lesson },
				__('Could not delete the item'),
			),

		moveItem: (lesson: string, targetChapter: string, idx: number) =>
			mutate(
				`item-move:${lesson}`,
				'move_curriculum_item',
				{
					lesson,
					target_chapter: targetChapter,
					idx,
				},
				__('Could not move the item'),
			),
	}
}
