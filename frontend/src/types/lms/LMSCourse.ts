import { ChapterReference } from './ChapterReference'
import { CourseInstructor } from './CourseInstructor'
import { LMSCourseObjective } from './LMSCourseObjective'
import { RelatedCourses } from './RelatedCourses'

export interface LMSCourse {
	creation: string
	name: string
	modified: string
	owner: string
	modified_by: string
	docstatus: 0 | 1 | 2
	parent?: string
	parentfield?: string
	parenttype?: string
	idx?: number
	/**	Title : Data	*/
	title: string
	/**	Description : Text Editor	*/
	description: string
	/**	Published : Check	*/
	published?: 0 | 1
	/**	Video Embed Link : Data	*/
	video_link?: string
	/**	Short Introduction : Small Text	*/
	short_introduction: string
	/**	Disable Self Learning : Check	*/
	disable_self_learning?: 0 | 1
	/**	Enforce Lesson Completion : Check	*/
	enforce_lesson_completion?: 0 | 1
	/**	Preview Image : Attach Image	*/
	image?: string
	/**	Tags : Data	*/
	tags?: string
	/**	Upcoming : Check	*/
	upcoming?: 0 | 1
	/**	Chapters : Table - Chapter Reference	*/
	chapters?: ChapterReference[]
	/**	Instructors : Table MultiSelect - Course Instructor	*/
	instructors: CourseInstructor[]
	/**	Completion Certificate : Check	*/
	enable_certification?: 0 | 1
	/**	Related Courses : Table - Related Courses	*/
	related_courses?: RelatedCourses[]
	/**	Status : Select	*/
	status?: 'In Progress' | 'Under Review' | 'Approved'
	/**	Currency : Link - Currency	*/
	currency?: string
	/**	Paid Course : Check	*/
	paid_course?: 0 | 1
	/**	Amount : Currency	*/
	course_price?: number
	/**	Amount (USD) : Currency - If you set an amount here, then the USD equivalent setting will not get applied.	*/
	amount_usd?: number
	/**	Published On : Date	*/
	published_on?: string
	/**	Featured : Check	*/
	featured?: 0 | 1
	/**	Category : Link - LMS Category	*/
	category?: string
	/**	Enrollments : Int	*/
	enrollments?: number
	/**	Lessons : Int	*/
	lessons?: number
	/**	Rating : Data	*/
	rating?: string
	/**	Paid Certificate : Check	*/
	paid_certificate?: 0 | 1
	/**	Evaluator : Link - Course Evaluator	*/
	evaluator?: string
	/**	Color : Select	*/
	card_gradient?:
		| 'Red'
		| 'Blue'
		| 'Green'
		| 'Amber'
		| 'Cyan'
		| 'Orange'
		| 'Pink'
		| 'Purple'
		| 'Teal'
		| 'Violet'
		| 'Yellow'
		| 'Gray'
	/**	Timezone : Data	*/
	timezone?: string
	/**	Notification Sent : Check	*/
	notification_sent?: 0 | 1

	/* ---- Guided course creation ---- */

	/**	Course Type : Select	*/
	course_type?: 'Course' | 'Practice Test'
	/**	Time Commitment : Select	*/
	time_commitment?:
		| ''
		| '0-2 hours per week'
		| '2-4 hours per week'
		| '5+ hours per week'
		| 'Not decided yet'
	/**	Test Video : Attach	*/
	test_video?: string
	/**	Test Video Feedback Areas : Small Text	*/
	test_video_feedback?: string
	/**	What will students learn : Table - LMS Course Objective	*/
	learning_objectives?: LMSCourseObjective[]
	/**	Requirements or prerequisites : Table - LMS Course Objective	*/
	requirements?: LMSCourseObjective[]
	/**	Who this course is for : Table - LMS Course Objective	*/
	intended_learners?: LMSCourseObjective[]
	/**	Course Subtitle : Data	*/
	subtitle?: string
	/**	Language : Data	*/
	language?: string
	/**	Level : Select	*/
	level?:
		| 'All Levels'
		| 'Beginner Level'
		| 'Intermediate Level'
		| 'Expert Level'
	/**	Primarily Taught : Data	*/
	primary_topic?: string
	/**	Promotional Video : Attach	*/
	promo_video?: string
	/**	Welcome Message : Text Editor	*/
	welcome_message?: string
	/**	Congratulations Message : Text Editor	*/
	congratulations_message?: string
	/**	Enrollment (Privacy) : Select	*/
	enrollment_privacy?:
		| 'Public'
		| 'Private (Invite Only)'
		| 'Private (Password Protected)'
	/**	Enrollment Password : Password	*/
	enrollment_password?: string
	/**	Auto-generate Captions : Check	*/
	captions_enabled?: 0 | 1
	/**	Captions Language : Data	*/
	captions_language?: string
	/**	Daily Q&A digest : Check	*/
	daily_qa_digest?: 0 | 1
	/**	Lecture ready emails : Check	*/
	lecture_ready_emails?: 0 | 1
	/**	Submitted for Review On : Datetime	*/
	submitted_on?: string
}
