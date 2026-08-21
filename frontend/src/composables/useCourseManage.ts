import { computed, inject } from 'vue'
import type { ComputedRef } from 'vue'
import type { CourseManageContext } from '@/types'
import type { LMSCourse } from '@/types/lms/LMSCourse'

interface UseCourseManage extends CourseManageContext {
	/**
	 * The loaded course document.
	 *
	 * Non-nullable by contract: `CourseForm` renders a skeleton until
	 * `resource.doc` exists and only then mounts its sections, so every section
	 * can bind straight to `doc.title` without a `?.` on every line. The cast
	 * is the single place that assumption is written down.
	 */
	doc: ComputedRef<LMSCourse>
}

/**
 * Reach the Settings tab's shared course doc, save plumbing and status.
 *
 * Every authoring section is mounted by `CourseForm.vue`, so the injection is
 * always satisfied in the app. Throwing on a miss turns a mis-mounted section
 * into an immediate, named error instead of a cascade of undefined reads.
 */
export function useCourseManage(): UseCourseManage {
	const context = inject<CourseManageContext | null>('courseManage', null)
	if (!context) {
		throw new Error(
			'useCourseManage() must be called inside the course Settings tab.'
		)
	}
	return {
		...context,
		doc: computed(() => context.resource.doc as LMSCourse),
	}
}
