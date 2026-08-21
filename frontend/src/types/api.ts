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
		is_evaluator?: boolean
		is_student?: boolean
		is_system_manager?: boolean
	}
}

/** One course waiting on a review, from `lms.lms.course_review.get_review_queue`. */
export interface CourseReviewItem {
	name: string
	title: string
	image?: string | null
	submitted_on?: string | null
	category?: string | null
	course_type?: string | null
	lessons: number
	instructors: { name: string; full_name: string; user_image?: string | null }[]
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
	/** What a reviewer asked for when they sent the course back, if they did. */
	review_feedback?: string | null
	submitted_on?: string | null
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
	/**
	 * The certificate's readiness. Reported here but never in `blockers`: it
	 * gates the instructor handoff, which happens long before a course is
	 * submitted for review.
	 */
	certificate: CertificateReadiness
}

export interface CertificateReadiness {
	exists: boolean
	is_complete: boolean
	missing: { code: string; message: string }[]
}

/**
 * What the Settings tab provides to the course-authoring sections mounted
 * inside it.
 *
 * These sections used to be steps of a standalone creation wizard, each with
 * its own copy of the course document. They now share the Settings tab's one
 * resource, which is what stopped two surfaces racing to save the same fields.
 */
export interface CourseManageContext {
	resource: Resource<LMSCourse | null>
	status: Resource<CourseCreationStatus | null>
	isDirty: Ref<boolean>
	/** Queue an autosave; sections call this after mutating `resource.doc`. */
	markDirty: () => void
	/** Save now and resolve once the write lands. */
	save: () => Promise<void>
	/** Scroll a sibling section of the Settings tab into view, by its id. */
	focusSection: (id: string) => void
}

export type CurriculumItemType =
	| 'Lecture'
	| 'Quiz'
	| 'Assignment'
	| 'Coding Exercise'

export type ResourceType =
	| 'Downloadable File'
	| 'External Resource'
	| 'Source Code'

export interface LessonResourceRow {
	name: string
	resource_type: ResourceType
	title: string
	file?: string | null
	url?: string | null
}

/** One row in a section — a lecture, quiz, assignment or coding exercise. */
export interface CurriculumItem {
	name: string
	title: string
	item_type: CurriculumItemType
	is_published: 0 | 1
	duration_minutes?: number | null
	video_duration?: number | null
	description?: string | null
	include_in_preview?: 0 | 1
	/** Set only on the matching item_type; the backing document's name. */
	quiz?: string | null
	assignment?: string | null
	exercise?: string | null
	/**
	 * The linked activity came from the library, so this item does not own it:
	 * renaming or deleting the item leaves the quiz alone.
	 */
	is_shared_activity?: 0 | 1
	/** Shape of the linked quiz, for describing a row without opening it. */
	quiz_summary?: QuizSummary | null
	idx: number
	resources: LessonResourceRow[]
	has_video: boolean
}

/** A quiz as the curriculum row and the library picker describe it. */
export interface QuizSummary {
	name: string
	title: string
	passing_percentage: number
	max_attempts?: number | null
	question_count: number
	quiz_type?: QuizType
	/** Set when the quiz already belongs to a course rather than the library. */
	course?: string | null
	course_title?: string | null
	owner?: string
	modified?: string
}

export interface CurriculumSection {
	name: string
	title: string
	learning_objective?: string | null
	is_published: 0 | 1
	is_scorm_package?: 0 | 1
	idx: number
	items: CurriculumItem[]
}

/**
 * How a quiz is marked. An `Objective` quiz carries its own answer key and is
 * scored on submit; a `Subjective` one holds work an evaluator has to read, and
 * waits in their queue until they do.
 */
export type QuizType = 'Objective' | 'Subjective'

export interface QuizAnswer {
	index?: number
	option: string
	is_correct: 0 | 1 | boolean
	explanation?: string | null
}

export interface QuizQuestion {
	name: string
	question: string
	type: string
	multiple: 0 | 1
	answers: QuizAnswer[]
	/** What this question is worth on this quiz. */
	marks: number
}

export interface QuizDetail {
	name: string
	title: string
	quiz_type: QuizType
	/** Subjective only: hold the lesson open until an evaluator has marked it. */
	block_progress_until_evaluated: 0 | 1
	passing_percentage: number
	total_marks: number
	max_attempts?: number
	show_answers: 0 | 1
	shuffle_questions: 0 | 1
	questions: QuizQuestion[]
}

/** A quiz on the current lesson the student has not passed yet. */
export interface PendingQuiz {
	quiz: string
	title: string
	passing_percentage: number
	/** The student's best attempt so far, or null if they have not tried. */
	best_percentage: number | null
	attempts: number
	max_attempts: number
	/**
	 * Handed in and sitting with an evaluator. The student has nothing left to do
	 * here, so the page says so rather than telling them to attempt it.
	 */
	awaiting_evaluation?: boolean
}

/** One submission in an evaluator's queue. */
export interface EvaluationQueueRow {
	name: string
	quiz: string
	quiz_title: string
	course: string | null
	member: string
	member_name: string
	score: number
	score_out_of: number
	percentage: number
	passing_percentage: number
	evaluation_status: 'Pending' | 'Evaluated'
	evaluator?: string | null
	evaluated_on?: string | null
	creation: string
}

/** One answer inside a submission being reviewed. */
export interface EvaluationAnswer {
	/** The child row's name — what `save_evaluation` addresses marks to. */
	row: string
	question: string
	answer: string
	marks: number
	marks_out_of: number
	evaluator_feedback?: string | null
}

export interface EvaluationDetail {
	name: string
	quiz: string
	quiz_title: string
	quiz_type: QuizType
	course: string | null
	course_title: string | null
	member: string
	member_name: string
	submitted_on: string
	score: number
	score_out_of: number
	percentage: number
	passing_percentage: number
	evaluation_status: 'Not Required' | 'Pending' | 'Evaluated'
	evaluator?: string | null
	evaluated_on?: string | null
	evaluator_comment?: string | null
	/** The quiz holds the learner's lesson open until this is marked. */
	blocks_progress: boolean
	answers: EvaluationAnswer[]
}

/** An evaluator and the work a moderator has assigned them. */
export interface EvaluatorAssignment {
	name: string
	evaluator: string
	full_name?: string | null
	user_image?: string | null
	courses: { course: string; course_title?: string | null }[]
	programs: { program: string; program_title?: string | null }[]
}

/** Where an enrollment stands against the course's completion deadline. */
export interface CoursePacing {
	enrolled: boolean
	deadline_days: number
	due_date: string | null
	/** Whole days; negative once the due date has passed. */
	days_left: number | null
	is_overdue: boolean
	status:
		| 'No deadline'
		| 'Not enrolled'
		| 'On track'
		| 'Due soon'
		| 'Overdue'
		| 'Completed'
	progress?: number
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
