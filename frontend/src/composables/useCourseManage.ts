import { computed, inject } from 'vue'
import type { ComputedRef } from 'vue'
import type { CourseManageContext } from '@/types'
import type { LMSCourse } from '@/types/lms/LMSCourse'

interface UseCourseManage extends CourseManageContext {
	/**
	 * The loaded course document.
	 *
	 * Non-nullable by contract: `CourseManage` renders a skeleton until
	 * `resource.doc` exists and only then mounts a step body, so every step can
	 * bind straight to `doc.title` without a `?.` on every line. The cast is
	 * the single place that assumption is written down.
	 */
	doc: ComputedRef<LMSCourse>
}

/**
 * Reach the manage shell's shared course doc, save plumbing and status.
 *
 * Every step body is mounted by `CourseManage.vue`, so the injection is always
 * satisfied in the app. Throwing on a miss turns a mis-mounted step into an
 * immediate, named error instead of a cascade of undefined reads.
 */
export function useCourseManage(): UseCourseManage {
	const context = inject<CourseManageContext | null>('courseManage', null)
	if (!context) {
		throw new Error(
			'useCourseManage() must be called inside the course manage shell.'
		)
	}
	return {
		...context,
		doc: computed(() => context.resource.doc as LMSCourse),
	}
}
