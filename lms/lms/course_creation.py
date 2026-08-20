"""Server side of the guided course creation flow.

The flow is a wizard (course type → title → category → time commitment) that
drops the author into a single-purpose editing shell with a checklist rail. The
rail's tick marks and the "Submit for Review" gate both come from
`get_course_creation_status`, so the sidebar and the blocker dialog can never
disagree about what is still missing — they read the same computation.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, flt, now

from lms.lms.utils import can_modify_course, has_moderator_role

# Submission thresholds. Mirrored in the "why can't I submit" dialog, so they
# live in one place rather than being re-typed into the copy on the client.
MIN_LECTURES = 5
MIN_VIDEO_SECONDS = 30 * 60
MIN_OBJECTIVES = 4
MIN_DESCRIPTION_WORDS = 50

OBJECTIVE_FIELDS = ("learning_objectives", "requirements", "intended_learners")

# EditorJS stores an uploaded file as an `upload` block tagged with the file's
# extension, so "does this lecture have a video" is a question about its blocks
# rather than about a field on the lesson.
VIDEO_EXTENSIONS = ("mp4", "mov", "avi", "mkv", "webm")


def is_video_block(block: dict) -> bool:
	if block.get("type") != "upload":
		return False
	file_type = (block.get("data") or {}).get("file_type") or ""
	return file_type.lower() in VIDEO_EXTENSIONS


def enforce_course_access(course: str) -> None:
	"""Raise unless the session user may edit this course."""
	if not frappe.db.exists("LMS Course", course):
		frappe.throw(_("Course {0} does not exist.").format(course), frappe.DoesNotExistError)
	if not can_modify_course(course):
		frappe.throw(_("You are not permitted to edit this course."), frappe.PermissionError)


def strip_html_to_words(value: str | None) -> list[str]:
	if not value:
		return []
	from frappe.utils import strip_html_tags

	return [word for word in strip_html_tags(value).split() if word.strip()]


@frappe.whitelist()
def create_course_draft(
	title: str,
	course_type: str = "Course",
	category: str | None = None,
	time_commitment: str | None = None,
) -> str:
	"""Create the skeleton course the wizard hands off to the editing shell.

	Only the four wizard answers are written; description, objectives and
	pricing are filled in afterwards from the rail. That works because
	`description` and `short_introduction` are mandatory only once the course
	is published (`mandatory_depends_on` on LMS Course) — a draft is allowed to
	be incomplete, and every save between steps would fail otherwise.
	"""
	frappe.only_for(["Moderator", "Course Creator"])

	title = (title or "").strip()
	if not title:
		frappe.throw(_("A course title is required."))

	course = frappe.new_doc("LMS Course")
	course.title = title
	course.course_type = course_type if course_type in ("Course", "Practice Test") else "Course"
	course.status = "In Progress"
	course.published = 0
	if category:
		course.category = category
	if time_commitment:
		course.time_commitment = time_commitment
	course.append("instructors", {"instructor": frappe.session.user, "is_visible": 1, "can_manage_course": 1})
	course.insert()
	return course.name


def get_video_stats(course: str) -> dict:
	"""Lecture count and total recorded video length for a course.

	`video_duration` is written by the curriculum editor when a video is
	attached there. A lecture whose video was dropped into the body from the
	block editor has no recorded length, so it would silently under-report the
	course total. `lectures_without_duration` counts exactly those — a lecture
	that *has* a video but no measured length — and never a lecture that simply
	has no video yet, which is not a gap but an empty lecture.
	"""
	empty = {"lectures": 0, "video_seconds": 0.0, "lectures_without_duration": 0}

	chapters = frappe.get_all("Course Chapter", filters={"course": course}, pluck="name")
	if not chapters:
		return empty

	lesson_names = frappe.get_all(
		"Lesson Reference", filters={"parent": ["in", chapters]}, pluck="lesson"
	)
	if not lesson_names:
		return empty

	from lms.lms.utils import get_editorjs_blocks

	rows = frappe.get_all(
		"Course Lesson",
		filters={"name": ["in", lesson_names]},
		fields=["name", "video_duration", "content"],
	)
	total = 0.0
	unmeasured = 0
	for row in rows:
		duration = flt(row.video_duration)
		total += duration
		if duration:
			continue
		if any(is_video_block(block) for block in get_editorjs_blocks(row.content)):
			unmeasured += 1

	return {
		"lectures": len(rows),
		"video_seconds": total,
		"lectures_without_duration": unmeasured,
	}


def count_rows(doc, fieldname: str) -> int:
	return len([row for row in (doc.get(fieldname) or []) if (row.objective or "").strip()])


@frappe.whitelist()
def get_course_creation_status(course: str) -> dict:
	"""Completion state for every step of the rail, plus submission blockers.

	Returned as plain data so the sidebar ticks, the header's "N min of video
	content uploaded" readout and the blocker dialog all render from one fetch.
	"""
	enforce_course_access(course)
	doc = frappe.get_doc("LMS Course", course)
	stats = get_video_stats(course)

	objectives = count_rows(doc, "learning_objectives")
	requirements = count_rows(doc, "requirements")
	learners = count_rows(doc, "intended_learners")
	description_words = len(strip_html_to_words(doc.description))

	steps = {
		"intended-learners": objectives >= MIN_OBJECTIVES and requirements > 0 and learners > 0,
		"structure": bool(doc.primary_topic),
		"test-video": bool(doc.test_video),
		"film-edit": bool(doc.test_video),
		"curriculum": stats["lectures"] >= MIN_LECTURES,
		"captions": bool(doc.captions_enabled),
		"accessibility": bool(doc.captions_enabled),
		"landing-page": bool(doc.title and doc.short_introduction and doc.image)
		and description_words >= MIN_DESCRIPTION_WORDS,
		"pricing": bool(doc.paid_course) is False or flt(doc.course_price) > 0,
		"promotions": True,
		"messages": bool(doc.welcome_message or doc.congratulations_message),
	}

	blockers = []
	if stats["lectures"] < MIN_LECTURES:
		blockers.append(
			{
				"step": "curriculum",
				"message": _("Have at least {0} lectures (currently {1})").format(
					MIN_LECTURES, stats["lectures"]
				),
			}
		)
	if stats["video_seconds"] < MIN_VIDEO_SECONDS:
		blockers.append(
			{
				"step": "curriculum",
				"message": _("Have at least {0} minutes of video content (currently {1})").format(
					MIN_VIDEO_SECONDS // 60, int(stats["video_seconds"] // 60)
				),
			}
		)
	if objectives < MIN_OBJECTIVES:
		blockers.append(
			{
				"step": "intended-learners",
				"message": _("Enter at least {0} learning objectives (currently {1})").format(
					MIN_OBJECTIVES, objectives
				),
			}
		)
	if description_words < MIN_DESCRIPTION_WORDS:
		blockers.append(
			{
				"step": "landing-page",
				"message": _("Write a course description of at least {0} words (currently {1})").format(
					MIN_DESCRIPTION_WORDS, description_words
				),
			}
		)
	if not doc.image:
		blockers.append({"step": "landing-page", "message": _("Upload a course image")})

	return {
		"course": doc.name,
		"title": doc.title,
		"status": doc.status,
		"published": cint(doc.published),
		"steps": steps,
		"blockers": blockers,
		"can_submit": not blockers and doc.status == "In Progress",
		"lectures": stats["lectures"],
		"video_seconds": stats["video_seconds"],
		"lectures_without_duration": stats["lectures_without_duration"],
		"objectives": objectives,
		"requirements": requirements,
		"intended_learners": learners,
		"description_words": description_words,
	}


@frappe.whitelist()
def submit_course_for_review(course: str) -> dict:
	"""Move a draft to 'Under Review' once every blocker is cleared."""
	status = get_course_creation_status(course)
	if status["blockers"]:
		frappe.throw(
			_("This course is not ready for review yet: {0}").format(
				"; ".join(blocker["message"] for blocker in status["blockers"])
			)
		)
	if status["status"] != "In Progress":
		frappe.throw(_("This course has already been submitted."))

	frappe.db.set_value(
		"LMS Course", course, {"status": "Under Review", "submitted_on": now()}, update_modified=False
	)
	return get_course_creation_status(course)


@frappe.whitelist()
def withdraw_course_submission(course: str) -> dict:
	"""Pull a course back out of review so the author can keep editing it."""
	enforce_course_access(course)
	if frappe.db.get_value("LMS Course", course, "status") != "Under Review":
		frappe.throw(_("This course is not awaiting review."))
	frappe.db.set_value(
		"LMS Course", course, {"status": "In Progress", "submitted_on": None}, update_modified=False
	)
	return get_course_creation_status(course)


PERMISSION_FIELDS = (
	"is_visible",
	"can_manage_course",
	"can_manage_captions",
	"can_view_performance",
	"can_manage_qa",
	"can_manage_assignments",
	"can_manage_reviews",
)


def clean_permissions(permissions) -> dict:
	if isinstance(permissions, str):
		permissions = frappe.parse_json(permissions)
	permissions = permissions or {}
	return {field: 1 if permissions.get(field) else 0 for field in PERMISSION_FIELDS}


@frappe.whitelist()
def get_course_instructors(course: str) -> list[dict]:
	"""Instructor rows with their per-area permissions, for the settings table."""
	enforce_course_access(course)
	rows = frappe.get_all(
		"Course Instructor",
		filters={"parent": course, "parenttype": "LMS Course"},
		fields=["name", "instructor", "invitation_status", *PERMISSION_FIELDS],
		order_by="idx asc",
	)
	users = {
		user.name: user
		for user in frappe.get_all(
			"User",
			filters={"name": ["in", [row.instructor for row in rows] or [""]]},
			fields=["name", "full_name", "user_image"],
		)
	}
	for row in rows:
		user = users.get(row.instructor)
		row["full_name"] = user.full_name if user else row.instructor
		row["user_image"] = user.user_image if user else None
	return rows


@frappe.whitelist()
def add_course_instructor(course: str, email: str, permissions=None) -> list[dict]:
	"""Invite a user as a co-instructor with an explicit permission set."""
	enforce_course_access(course)
	email = (email or "").strip().lower()
	if not email:
		frappe.throw(_("An email address is required."))
	if not frappe.db.exists("User", email):
		frappe.throw(_("No user found with the email {0}.").format(email))
	if frappe.db.exists(
		"Course Instructor", {"parent": course, "parenttype": "LMS Course", "instructor": email}
	):
		frappe.throw(_("{0} is already an instructor on this course.").format(email))

	doc = frappe.get_doc("LMS Course", course)
	doc.append("instructors", {"instructor": email, "invitation_status": "Pending", **clean_permissions(permissions)})
	doc.save(ignore_permissions=True)
	return get_course_instructors(course)


@frappe.whitelist()
def update_instructor_permissions(course: str, row: str, permissions=None) -> list[dict]:
	"""Rewrite one instructor row's permission checkboxes."""
	enforce_course_access(course)
	if not frappe.db.exists("Course Instructor", {"name": row, "parent": course}):
		frappe.throw(_("That instructor is not on this course."))
	frappe.db.set_value("Course Instructor", row, clean_permissions(permissions))
	return get_course_instructors(course)


@frappe.whitelist()
def remove_course_instructor(course: str, row: str) -> list[dict]:
	"""Drop a co-instructor, keeping at least one instructor on the course."""
	enforce_course_access(course)
	doc = frappe.get_doc("LMS Course", course)
	remaining = [instructor for instructor in doc.instructors if instructor.name != row]
	if len(remaining) == len(doc.instructors):
		frappe.throw(_("That instructor is not on this course."))
	if not remaining:
		frappe.throw(_("A course must keep at least one instructor."))
	doc.instructors = remaining
	doc.save(ignore_permissions=True)
	return get_course_instructors(course)


@frappe.whitelist()
def set_lesson_video_duration(lesson: str, duration: float) -> float:
	"""Record a lecture's video length, measured client side on upload."""
	course = frappe.db.get_value("Course Lesson", lesson, "course")
	if not course:
		frappe.throw(_("Lesson {0} does not exist.").format(lesson), frappe.DoesNotExistError)
	enforce_course_access(course)
	value = max(flt(duration), 0)
	frappe.db.set_value("Course Lesson", lesson, "video_duration", value, update_modified=False)
	return value


@frappe.whitelist()
def set_lecture_video(lesson: str, file_url: str, file_type: str, duration: float = 0) -> dict:
	"""Attach (or replace) the video on a lecture from the curriculum editor.

	Lesson bodies are EditorJS documents that authors also edit block by block
	in the lesson editor. Rather than overwrite that, this swaps the file on the
	first existing video block and only appends a new one when the lecture has
	no video yet — so attaching a video from the curriculum never destroys prose
	written elsewhere.
	"""
	import json

	from lms.lms.utils import get_editorjs_blocks

	course = frappe.db.get_value("Course Lesson", lesson, "course")
	if not course:
		frappe.throw(_("Lesson {0} does not exist.").format(lesson), frappe.DoesNotExistError)
	enforce_course_access(course)

	if (file_type or "").lower() not in VIDEO_EXTENSIONS:
		frappe.throw(_("{0} is not a supported video format.").format(file_type))

	doc = frappe.get_doc("Course Lesson", lesson)
	blocks = get_editorjs_blocks(doc.content)
	replaced = False
	for block in blocks:
		if is_video_block(block):
			block.setdefault("data", {})
			block["data"]["file_url"] = file_url
			block["data"]["file_type"] = file_type
			replaced = True
			break

	if not replaced:
		blocks.append({"type": "upload", "data": {"file_url": file_url, "file_type": file_type}})

	doc.content = json.dumps({"blocks": blocks})
	doc.video_duration = max(flt(duration), 0)
	doc.save(ignore_permissions=True)
	return {"lesson": lesson, "video_duration": doc.video_duration, "replaced": replaced}


@frappe.whitelist()
def rename_lecture(lesson: str, title: str) -> str:
	"""Rename a lecture inline from the curriculum list."""
	course = frappe.db.get_value("Course Lesson", lesson, "course")
	if not course:
		frappe.throw(_("Lesson {0} does not exist.").format(lesson), frappe.DoesNotExistError)
	enforce_course_access(course)
	title = (title or "").strip()
	if not title:
		frappe.throw(_("A lecture title is required."))
	frappe.db.set_value("Course Lesson", lesson, "title", title)
	return title


@frappe.whitelist()
def get_curriculum(course: str) -> list[dict]:
	"""The curriculum tree — sections with their lectures and video lengths."""
	enforce_course_access(course)
	chapters = frappe.get_all(
		"Chapter Reference",
		filters={"parent": course, "parenttype": "LMS Course"},
		fields=["chapter", "idx"],
		order_by="idx asc",
	)
	sections = []
	for row in chapters:
		chapter = frappe.db.get_value("Course Chapter", row.chapter, ["name", "title"], as_dict=True)
		if not chapter:
			continue
		lesson_rows = frappe.get_all(
			"Lesson Reference", filters={"parent": chapter.name}, fields=["lesson", "idx"], order_by="idx asc"
		)
		lessons = []
		for lesson_row in lesson_rows:
			lesson = frappe.db.get_value(
				"Course Lesson",
				lesson_row.lesson,
				["name", "title", "video_duration", "include_in_preview"],
				as_dict=True,
			)
			if lesson:
				lessons.append(lesson)
		sections.append({"name": chapter.name, "title": chapter.title, "idx": row.idx, "lessons": lessons})
	return sections


@frappe.whitelist()
def get_caption_status(course: str) -> dict:
	"""Per-lecture caption state for the Captions step."""
	enforce_course_access(course)
	doc = frappe.get_doc("LMS Course", course)
	sections = get_curriculum(course)
	total = sum(len(section["lessons"]) for section in sections)
	return {
		"enabled": cint(doc.captions_enabled),
		"language": doc.captions_language or "English (US)",
		"total": total,
		# Captions are generated after publish, so nothing is captioned while
		# the course is still a draft. Reported explicitly rather than left for
		# the client to infer from `published`.
		"captioned": 0 if not cint(doc.published) else 0,
		"sections": sections,
	}


@frappe.whitelist()
def moderate_course(course: str, action: str) -> dict:
	"""Approve or send back a course awaiting review. Moderators only."""
	if not has_moderator_role():
		frappe.throw(_("Only a moderator can review courses."), frappe.PermissionError)
	if action not in ("approve", "reject"):
		frappe.throw(_("Unknown review action {0}.").format(action))

	if action == "approve":
		frappe.db.set_value("LMS Course", course, {"status": "Approved", "published": 1})
	else:
		frappe.db.set_value("LMS Course", course, {"status": "In Progress", "submitted_on": None})
	return get_course_creation_status(course)
