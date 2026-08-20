import type { Ref } from 'vue'
import type { LMSCourse } from './lms/LMSCourse'
import type { LMSBatch } from './lms/LMSBatch'

export interface Resource<T = unknown> {
	data: T
	loading: boolean
	error: unknown
	doc?: T
	hasNextPage?: boolean
	reload(): Promise<T>
	fetch(): Promise<T>
	next?(): void
	// Promise, not void: frappe-ui's submit resolves or REJECTS, and typing it
	// away is what let bare `resource.submit(...)` statements spread unnoticed —
	// see utils/resource.ts.
	submit(params?: unknown, opts?: unknown): Promise<T>
	update(opts: unknown): void
	setValue: { submit(values: unknown, opts?: unknown): Promise<T> }
}

export interface UserInfo {
	name: string
	full_name?: string
	first_name?: string
	last_name?: string
	email?: string
	username?: string
	user_image?: string
	open_to?: 'Work' | 'Hiring' | string
}

export interface SessionUser {
	data?: UserInfo & {
		is_moderator?: boolean
		is_instructor?: boolean
		is_student?: boolean
		is_system_manager?: boolean
	}
}

export interface CourseInstructorInfo extends UserInfo {
	instructor?: string
	bio?: string | null
}

export interface Membership {
	name?: string
	member?: string
	progress?: number
	current_lesson?: string
	purchased_certificate?: 0 | 1 | boolean
	certificate?: string
}

export interface CourseDetails extends Omit<
	LMSCourse,
	'instructors' | 'rating'
> {
	price?: string
	current_lesson?: string
	instructors: CourseInstructorInfo[]
	membership?: Membership | null
	rating?: string
	rating_count?: number
	quiz_count?: number
}

export interface BatchDetails extends Omit<LMSBatch, 'instructors'> {
	instructors: string[]
	students?: string[]
	batch_details_raw?: string
}

export interface CourseReviewInfo {
	name: string
	creation: string
	rating: number
	review?: string
	owner_details: UserInfo
}

export interface OutlineLesson {
	name: string
	title: string
	number: string
	icon?: string
	is_complete?: boolean
	locked?: 0 | 1
}

export interface OutlineChapter {
	name: string
	title: string
	idx: number
	is_scorm_package?: 0 | 1
	scorm_package?: { file_name: string; file_size: number } | null
	lessons?: OutlineLesson[]
}

export interface CertificationInfo {
	certificate?: { name: string; template: string } | null
	membership?: {
		purchased_certificate?: 0 | 1
		certificate?: string
	} | null
	paid_certificate?: 0 | 1
}

export interface ChapterDetailInput {
	name?: string
	title?: string
	is_scorm_package?: 0 | 1
	/**
	 * build_outline expands this into the File's details only while that File row
	 * still exists; once it is deleted the raw Course Chapter.scorm_package
	 * DOCNAME comes through instead. Declaring only the object shape made every
	 * consumer assume `.file_name` was there.
	 */
	scorm_package?:
		| string
		| { name?: string; file_name?: string; file_size?: number }
		| null
}

export interface CourseFormMeta {
	description: string
	keywords: string
}

export interface CourseFormContext {
	resource: Resource<LMSCourse | null>
	instructors: Ref<string[]>
	relatedCourses: Ref<string[]>
	meta: CourseFormMeta
	markDirty: () => void
}

/** One unmet requirement standing between a draft and "Under Review". */
export interface CourseSubmitBlocker {
	/** Rail step the author has to visit to clear it. */
	step: string
	message: string
}

/** Shape of `lms.lms.course_creation.get_course_creation_status`. */
export interface CourseCreationStatus {
	course: string
	title: string
	status: 'In Progress' | 'Under Review' | 'Approved'
	published: 0 | 1
	/** Rail step key → whether that step reads as done. */
	steps: Record<string, boolean>
	blockers: CourseSubmitBlocker[]
	can_submit: boolean
	lectures: number
	video_seconds: number
	/** Lectures whose video length was never recorded, so it can be disclosed. */
	lectures_without_duration: number
	objectives: number
	requirements: number
	intended_learners: number
	description_words: number
}

/** What the manage shell provides to every step body. */
export interface CourseManageContext {
	resource: Resource<LMSCourse | null>
	status: Resource<CourseCreationStatus | null>
	isDirty: Ref<boolean>
	/** Queue an autosave; steps call this after mutating `resource.doc`. */
	markDirty: () => void
	/** Save now and resolve once the write lands. */
	save: () => Promise<void>
	goToStep: (key: string) => void
}

export interface CourseInstructorRow {
	name: string
	instructor: string
	full_name: string
	user_image?: string | null
	invitation_status?: 'Accepted' | 'Pending'
	is_visible: 0 | 1
	can_manage_course: 0 | 1
	can_manage_captions: 0 | 1
	can_view_performance: 0 | 1
	can_manage_qa: 0 | 1
	can_manage_assignments: 0 | 1
	can_manage_reviews: 0 | 1
}
