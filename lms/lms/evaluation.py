# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

"""Evaluator review of subjective quiz submissions.

An objective quiz carries its own answer key, so it is scored the instant it is
submitted. A subjective one — a coding exercise, a written argument — has no key
to score against, so its submissions queue here until a person reads them.

Who may read which submission comes from the assignment a Moderator makes on the
Course Evaluator record: a list of courses, plus programs that stand in for every
course inside them. An evaluator's queue is exactly the submissions from those
courses; nothing else is visible to them.
"""

import contextlib

import frappe
from frappe import _
from frappe.utils import cint, now

from lms.lms.doctype.course_lesson.course_lesson import save_progress
from lms.lms.utils import has_moderator_role

QUEUE_MAX_LIMIT = 100
QUEUE_DEFAULT_LIMIT = 20

# The states a submission can be in from an evaluator's point of view. "Not Required"
# is an objective quiz's submission and never reaches this module.
REVIEWABLE_STATUSES = ("Pending", "Evaluated")


def evaluator_courses(evaluator: str | None = None) -> set[str]:
	"""Courses this evaluator has been assigned, directly or through a program."""
	evaluator = evaluator or frappe.session.user
	if not evaluator or evaluator == "Guest":
		return set()
	if not frappe.db.exists("Course Evaluator", evaluator):
		return set()

	courses = set(
		frappe.get_all(
			"LMS Evaluator Course",
			filters={"parent": evaluator, "parenttype": "Course Evaluator"},
			pluck="course",
		)
	)

	programs = frappe.get_all(
		"LMS Evaluator Program",
		filters={"parent": evaluator, "parenttype": "Course Evaluator"},
		pluck="program",
	)
	if programs:
		# A program assignment is shorthand for its courses. Expanding it here rather
		# than storing the courses means adding a course to a program reaches every
		# evaluator on it without anyone re-assigning anything.
		courses |= set(
			frappe.get_all(
				"LMS Program Course",
				filters={"parent": ("in", programs), "parenttype": "LMS Program"},
				pluck="course",
			)
		)

	courses.discard(None)
	return courses


def instructor_courses(user: str | None = None) -> set[str]:
	"""Courses the user teaches. An instructor marks their own course's work."""
	user = user or frappe.session.user
	return set(
		frappe.get_all(
			"Course Instructor",
			filters={"instructor": user, "parenttype": "LMS Course"},
			pluck="parent",
		)
	)


def reviewable_courses(user: str | None = None) -> set[str] | None:
	"""Courses whose submissions the user may mark. `None` means every course.

	A Moderator is unrestricted — they are the ones who hand out the assignments in
	the first place, and a submission from a quiz with no course at all (a quiz used
	only through a batch) has no scope to fall into, so somebody has to be able to
	reach it.
	"""
	if has_moderator_role(user):
		return None
	return evaluator_courses(user) | instructor_courses(user)


def can_evaluate(course: str | None, user: str | None = None) -> bool:
	scope = reviewable_courses(user)
	if scope is None:
		return True
	return bool(course) and course in scope


def enforce_evaluation_access(submission: str) -> frappe._dict:
	"""Raise unless the session user may mark this submission. Returns its header row."""
	row = frappe.db.get_value(
		"LMS Quiz Submission",
		submission,
		["name", "quiz", "course", "member", "evaluation_status"],
		as_dict=True,
	)
	if not row:
		frappe.throw(_("Submission {0} does not exist.").format(submission), frappe.DoesNotExistError)
	if not can_evaluate(row.course):
		frappe.throw(
			_("You are not assigned to the course this submission belongs to."),
			frappe.PermissionError,
		)
	return row


@contextlib.contextmanager
def _acting_as(user: str):
	"""Run a block as another user, then put the session back.

	Course progress is written from the learner's own session — `save_progress` reads
	`frappe.session.user` throughout. When an evaluator's mark is what finally
	completes a lesson, the write still belongs to the learner, so the session is
	borrowed for exactly that call.
	"""
	original = frappe.session.user
	frappe.set_user(user)
	try:
		yield
	finally:
		frappe.set_user(original)


@frappe.whitelist()
def list_evaluation_queue(
	status: str = "Pending",
	course: str | None = None,
	search: str | None = None,
	limit: int = QUEUE_DEFAULT_LIMIT,
	start: int = 0,
) -> dict:
	"""Subjective submissions waiting on the session user, newest first."""
	if status not in REVIEWABLE_STATUSES:
		frappe.throw(_("Unknown evaluation status {0}.").format(status), frappe.ValidationError)

	scope = reviewable_courses()
	if scope is not None and not scope:
		return {"submissions": [], "total": 0, "courses": [], "pending_count": 0}

	filters = {"evaluation_status": status}
	if scope is not None:
		filters["course"] = ("in", sorted(scope))
	if course:
		if not can_evaluate(course):
			frappe.throw(_("You are not assigned to that course."), frappe.PermissionError)
		filters["course"] = course

	or_filters = {}
	if search and search.strip():
		term = f"%{search.strip()}%"
		or_filters = {"member_name": ("like", term), "quiz_title": ("like", term)}

	limit = max(1, min(cint(limit) or QUEUE_DEFAULT_LIMIT, QUEUE_MAX_LIMIT))

	fields = [
		"name",
		"quiz",
		"quiz_title",
		"course",
		"member",
		"member_name",
		"score",
		"score_out_of",
		"percentage",
		"passing_percentage",
		"evaluation_status",
		"evaluator",
		"evaluated_on",
		"creation",
	]
	submissions = frappe.get_all(
		"LMS Quiz Submission",
		filters=filters,
		or_filters=or_filters,
		fields=fields,
		order_by="creation asc" if status == "Pending" else "evaluated_on desc",
		limit_start=cint(start),
		limit_page_length=limit,
	)

	pending_filters = dict(filters)
	pending_filters["evaluation_status"] = "Pending"

	return {
		"submissions": submissions,
		"total": frappe.db.count("LMS Quiz Submission", filters),
		"courses": _queue_courses(scope),
		"pending_count": frappe.db.count("LMS Quiz Submission", pending_filters),
	}


def _queue_courses(scope: set[str] | None) -> list[dict]:
	"""The courses to offer as a filter — only those that actually have work in them."""
	filters = {"evaluation_status": ("in", REVIEWABLE_STATUSES)}
	if scope is not None:
		filters["course"] = ("in", sorted(scope))

	names = {
		row.course
		for row in frappe.get_all("LMS Quiz Submission", filters=filters, fields=["course"])
		if row.course
	}
	if not names:
		return []
	return frappe.get_all(
		"LMS Course", filters={"name": ("in", sorted(names))}, fields=["name", "title"], order_by="title asc"
	)


@frappe.whitelist()
def get_evaluation(submission: str) -> dict:
	"""One submission, expanded for review."""
	header = enforce_evaluation_access(submission)
	doc = frappe.get_doc("LMS Quiz Submission", header.name)

	quiz = (
		frappe.db.get_value(
			"LMS Quiz",
			doc.quiz,
			["title", "quiz_type", "passing_percentage", "block_progress_until_evaluated"],
			as_dict=True,
		)
		or frappe._dict()
	)

	return {
		"name": doc.name,
		"quiz": doc.quiz,
		"quiz_title": doc.quiz_title,
		"quiz_type": quiz.get("quiz_type") or "Objective",
		"course": doc.course,
		"course_title": frappe.db.get_value("LMS Course", doc.course, "title") if doc.course else None,
		"member": doc.member,
		"member_name": doc.member_name,
		"submitted_on": doc.creation,
		"score": cint(doc.score),
		"score_out_of": cint(doc.score_out_of),
		"percentage": cint(doc.percentage),
		"passing_percentage": cint(doc.passing_percentage),
		"evaluation_status": doc.evaluation_status,
		"evaluator": doc.evaluator,
		"evaluated_on": doc.evaluated_on,
		"evaluator_comment": doc.evaluator_comment,
		"blocks_progress": bool(cint(quiz.get("block_progress_until_evaluated"))),
		"answers": [
			{
				"row": row.name,
				"question": row.question,
				"answer": row.answer,
				"marks": cint(row.marks),
				"marks_out_of": cint(row.marks_out_of),
				"evaluator_feedback": row.evaluator_feedback,
			}
			for row in doc.result
		],
	}


@frappe.whitelist()
def save_evaluation(
	submission: str,
	marks: list | str | None = None,
	comment: str | None = None,
	finalize: bool = True,
) -> dict:
	"""Record an evaluator's marks against a submission.

	`finalize` false saves the marks without releasing them — an evaluator part-way
	through a long answer keeps their work without the learner being told the result
	is final. True moves the submission to Evaluated, notifies the learner, and
	unlocks the lesson if the quiz was holding it.
	"""
	header = enforce_evaluation_access(submission)
	doc = frappe.get_doc("LMS Quiz Submission", header.name)

	if isinstance(marks, str):
		marks = frappe.parse_json(marks)
	marks = marks or []

	rows = {row.name: row for row in doc.result}
	for entry in marks:
		if not isinstance(entry, dict):
			frappe.throw(_("Invalid marks submitted."), frappe.ValidationError)
		row = rows.get(entry.get("row"))
		if not row:
			frappe.throw(_("That question is not part of this submission."), frappe.ValidationError)

		awarded = cint(entry.get("marks"))
		if awarded < 0:
			frappe.throw(_("Marks cannot be negative."), frappe.ValidationError)
		if awarded > cint(row.marks_out_of):
			frappe.throw(
				_("Question {0} is out of {1} marks. You awarded {2}.").format(
					row.idx, cint(row.marks_out_of), awarded
				),
				frappe.ValidationError,
			)
		row.marks = awarded
		row.evaluator_feedback = (entry.get("evaluator_feedback") or "").strip() or None

	if comment is not None:
		doc.evaluator_comment = (comment or "").strip() or None

	if finalize:
		doc.evaluation_status = "Evaluated"
		doc.evaluator = frappe.session.user
		doc.evaluated_on = now()

	# The submission's own validate() recomputes score and percentage from the rows,
	# so neither is set here — the two must not be able to drift apart.
	doc.save(ignore_permissions=True)

	if finalize:
		release_progress_after_evaluation(doc)

	return get_evaluation(doc.name)


def release_progress_after_evaluation(submission) -> None:
	"""Complete the learner's lesson if this mark is what it was waiting for.

	Only quizzes set to block progress reach this: for every other subjective quiz
	the lesson already closed when the work was handed in.
	"""
	quiz = frappe.db.get_value(
		"LMS Quiz",
		submission.quiz,
		["lesson", "course", "passing_percentage", "block_progress_until_evaluated"],
		as_dict=True,
	)
	if not quiz or not quiz.lesson or not quiz.course:
		return
	if not cint(quiz.block_progress_until_evaluated):
		return
	if cint(submission.percentage) < cint(quiz.passing_percentage):
		return

	from lms.lms.permissions import get_locked_lessons

	with _acting_as(submission.member):
		# A lesson the learner cannot reach yet is not theirs to complete; the mark is
		# still recorded, and the lesson closes on its own once they get there.
		if quiz.lesson in get_locked_lessons(quiz.course):
			return
		save_progress(quiz.lesson, quiz.course)


# ---------------------------------------------------------------------------
# Assignment — who evaluates what. Moderators only.
# ---------------------------------------------------------------------------


def enforce_moderator() -> None:
	if not has_moderator_role():
		frappe.throw(_("Only a moderator can assign evaluators."), frappe.PermissionError)


@frappe.whitelist()
def list_evaluators() -> list[dict]:
	"""Every evaluator with the courses and programs they have been given."""
	enforce_moderator()

	evaluators = frappe.get_all(
		"Course Evaluator",
		fields=["name", "evaluator", "full_name", "user_image"],
		order_by="full_name asc",
	)
	for row in evaluators:
		row["courses"] = frappe.get_all(
			"LMS Evaluator Course",
			filters={"parent": row["name"], "parenttype": "Course Evaluator"},
			fields=["course", "course_title"],
			order_by="idx asc",
		)
		row["programs"] = frappe.get_all(
			"LMS Evaluator Program",
			filters={"parent": row["name"], "parenttype": "Course Evaluator"},
			fields=["program", "program_title"],
			order_by="idx asc",
		)
	return evaluators


@frappe.whitelist()
def set_evaluator_assignments(
	evaluator: str, courses: list | str | None = None, programs: list | str | None = None
) -> list[dict]:
	"""Replace an evaluator's course and program assignments wholesale."""
	enforce_moderator()

	if not frappe.db.exists("Course Evaluator", evaluator):
		frappe.throw(_("{0} is not an evaluator.").format(evaluator), frappe.DoesNotExistError)

	if isinstance(courses, str):
		courses = frappe.parse_json(courses)
	if isinstance(programs, str):
		programs = frappe.parse_json(programs)

	doc = frappe.get_doc("Course Evaluator", evaluator)
	doc.courses = []
	doc.programs = []

	# dict.fromkeys rather than a set: the order the moderator picked them in is the
	# order they read back, and a name repeated in the payload is still one row.
	for course in dict.fromkeys(courses or []):
		if not frappe.db.exists("LMS Course", course):
			frappe.throw(_("Course {0} does not exist.").format(course), frappe.DoesNotExistError)
		doc.append("courses", {"course": course})

	for program in dict.fromkeys(programs or []):
		if not frappe.db.exists("LMS Program", program):
			frappe.throw(_("Program {0} does not exist.").format(program), frappe.DoesNotExistError)
		doc.append("programs", {"program": program})

	doc.save(ignore_permissions=True)
	return list_evaluators()


@frappe.whitelist()
def get_course_evaluators(course: str) -> list[dict]:
	"""Who can mark this course's subjective work, for the course's own settings page."""
	from lms.lms.utils import can_modify_course

	if not can_modify_course(course):
		frappe.throw(_("You are not permitted to view this course."), frappe.PermissionError)

	direct = frappe.get_all(
		"LMS Evaluator Course",
		filters={"course": course, "parenttype": "Course Evaluator"},
		pluck="parent",
	)

	programs = frappe.get_all(
		"LMS Program Course", filters={"course": course, "parenttype": "LMS Program"}, pluck="parent"
	)
	via_program = (
		frappe.get_all(
			"LMS Evaluator Program",
			filters={"program": ("in", programs), "parenttype": "Course Evaluator"},
			pluck="parent",
		)
		if programs
		else []
	)

	names = sorted(set(direct) | set(via_program))
	if not names:
		return []

	evaluators = frappe.get_all(
		"Course Evaluator",
		filters={"name": ("in", names)},
		fields=["name", "evaluator", "full_name", "user_image"],
		order_by="full_name asc",
	)
	direct_set = set(direct)
	for row in evaluators:
		row["via"] = "course" if row["name"] in direct_set else "program"
	return evaluators
