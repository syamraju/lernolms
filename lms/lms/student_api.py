"""Whitelisted endpoints the student experience needs.

These live in their own module rather than in `lms.lms.api` for one reason:
every function here answers a question about *the signed-in student* and takes
no doctype-wide arguments. Keeping them apart makes the permission story easy
to check — none of them accept a `member` parameter, so none of them can be
pointed at somebody else's record.

The read paths reuse `lms.lms.utils` wherever a helper already exists, so a
change to how courses are filtered or how the outline is built reaches the
student app for free.
"""

import json
from collections import Counter

import frappe
from frappe import _
from frappe.utils import cint

from lms.lms.utils import (
	PRIVILEGED_ROLES,
	get_chapters,
	get_course_details,
	get_courses,
	get_editorjs_blocks,
	get_membership,
	guest_access_allowed,
)

# The card's "New Course" flag and the dashboard's "recently added" row both
# key off this window.
NEW_COURSE_DAYS = 30

# Anything at or above this counts as done, matching the progress bar the
# course pages already render.
COMPLETE_AT = 100


def _require_login():
	"""Guard for the endpoints that are meaningless without a session.

	`guest_access_allowed` governs whether a *guest* may browse the catalogue;
	it is not an authentication check. Endpoints that read the caller's own
	enrolments need the stronger one.
	"""
	if frappe.session.user == "Guest":
		frappe.throw(_("Please sign in to continue."), frappe.AuthenticationError)


def _chapter_counts(course_names: list) -> dict:
	"""How many chapters each of `course_names` has, in one query.

	The card shows a chapter count and the list can hold 24 cards, so this is
	deliberately not `len(get_chapters(course))` per row — that is one query per
	course plus one per chapter.
	"""
	if not course_names:
		return {}

	# Counted in Python rather than with a GROUP BY: frappe v16 rejects a SQL
	# function passed as a string in `fields`, and its dict form gives the column
	# a driver-dependent key that would have to be guessed at. A course has a
	# handful of chapters and a page holds at most a couple of dozen courses, so
	# this reads a few hundred rows — still the one query the roll-up is for.
	rows = frappe.get_all(
		"Chapter Reference",
		filters={"parent": ["in", course_names], "parenttype": "LMS Course"},
		pluck="parent",
		limit_page_length=0,
	)
	return dict(Counter(rows))


def _pacing_by_course(course_names: list) -> dict:
	"""Deadline state for the signed-in student's enrollments in these courses.

	One query for the whole page rather than one per card: deciding where an
	enrollment stands is pure arithmetic, so the only cost worth avoiding is the
	round trip.
	"""
	if not course_names or frappe.session.user == "Guest":
		return {}

	from lms.lms.pacing import compute_due_date, deadline_days, pacing_state

	rows = frappe.get_all(
		"LMS Enrollment",
		filters={"member": frappe.session.user, "course": ("in", course_names)},
		fields=["course", "due_date", "progress", "creation"],
		limit_page_length=0,
	)

	pacing = {}
	for row in rows:
		# An enrollment made before the course had a deadline carries no stored
		# date. Deriving one keeps the setting meaningful for a cohort already in
		# flight instead of applying only to whoever enrolls next.
		due_date = row.due_date or compute_due_date(row.creation, deadline_days(row.course))
		pacing[row.course] = pacing_state(due_date, row.progress)
	return pacing


def _scope_to_visible_courses(filters: dict | None) -> dict:
	"""Hide unpublished courses from the learner-facing catalogue.

	`get_courses` applies whatever publish state the caller asks for, which is right
	for the admin list -- it has explicit Published / Unpublished / Created tabs. The
	student shell sends no publish filter at all for its "Explore courses" view, so a
	draft an author has not released was listed to learners, with a live Enroll button
	that could only ever fail (`enroll` refuses: "This course is not open for
	enrolment.").

	Only the unscoped view is narrowed. `enrolled` and `created` already restrict to
	rows the caller has a relationship with, and forcing `published` on top of those
	would hide a learner's own in-progress course the moment its author unpublished
	it -- which is how the one enrolled course on the dev site would have vanished
	from "Continue learning".
	"""
	filters = dict(filters or {})

	# `enrolled` and `created` restrict to rows the caller already has a
	# relationship with, so publish state adds nothing and forcing it would hide
	# a learner's own in-progress course the moment its author unpublished it.
	if filters.get("enrolled") or filters.get("created"):
		return filters

	# A caller-supplied `published` used to be honoured here too, and it is not
	# the same kind of thing at all: those two scope to the caller, a publish
	# flag scopes nothing and is entirely caller-controlled. Because this
	# endpoint is `allow_guest=True`, that let an UNAUTHENTICATED request ask
	# for `published: 0` and receive every unreleased course on the site --
	# titles, slugs and metadata for work nobody had chosen to release. The
	# default path was always correct, which is why it went unnoticed; the
	# escape hatch was one query parameter.
	#
	# Staff keep the ability to ask, because the authoring surfaces legitimately
	# list unreleased work. PRIVILEGED_ROLES is the app's own definition of who
	# those are -- restating it here is how the two copies drift apart.
	if "published" in filters and _may_see_unpublished():
		return filters

	filters["published"] = 1
	return filters


def _may_see_unpublished() -> bool:
	"""Whether this caller may ask for courses that have not been released."""
	if frappe.session.user == "Guest":
		return False

	return bool(set(frappe.get_roles()) & PRIVILEGED_ROLES)


@frappe.whitelist(allow_guest=True)
def get_student_courses(filters: dict | str = None, start: int = 0, limit_page_length=None) -> list:
	"""`lms.lms.utils.get_courses` plus the two fields the student card needs.

	Kept as a wrapper rather than a change to `get_courses` because the admin
	list does not render either field, and the chapter roll-up is a query the
	admin list should not pay for.
	"""
	if isinstance(filters, str):
		filters = json.loads(filters)

	filters = _scope_to_visible_courses(filters)

	courses = get_courses(filters=filters, start=start, limit_page_length=limit_page_length)
	if not courses:
		return []

	course_names = [course.name for course in courses]
	counts = _chapter_counts(course_names)
	pacing = _pacing_by_course(course_names)
	for course in courses:
		course.chapters_count = counts.get(course.name, 0)
		# `get_enrollment_details` attaches `membership` only when one exists, so
		# a plain read of `.progress` would be a KeyError on an unenrolled row.
		course.progress = cint((course.get("membership") or {}).get("progress"))
		course.pacing = pacing.get(course.name)

	return courses


@frappe.whitelist()
def get_enrollment_summary() -> dict:
	"""The three counts in the student header: pending, enrolled, completed.

	Computed from LMS Enrollment rather than from the course list, because the
	header's numbers describe the student's whole shelf and the list below it is
	a filtered, paged window onto part of it.
	"""
	_require_login()

	rows = frappe.get_all(
		"LMS Enrollment",
		filters={"member": frappe.session.user},
		fields=["progress"],
		limit_page_length=0,
	)

	completed = sum(1 for row in rows if cint(row.progress) >= COMPLETE_AT)
	return {
		"enrolled": len(rows),
		"completed": completed,
		"pending": len(rows) - completed,
	}


@frappe.whitelist()
def enroll(course: str) -> dict:
	"""Enroll the signed-in user in `course` and hand back the fresh membership.

	Deliberately does not accept a member: the row is always for the caller.
	Every eligibility rule (self-learning disabled, paid course, duplicate) is
	enforced by LMSEnrollment's own `before_insert`, so this adds no checks of
	its own beyond refusing an unpublished course — it only removes the need for
	the client to hand-assemble a doc and then re-read it.
	"""
	_require_login()

	existing = get_membership(course)
	if existing:
		return existing

	if not frappe.db.get_value("LMS Course", course, "published"):
		frappe.throw(_("This course is not open for enrolment."))

	frappe.get_doc(
		{
			"doctype": "LMS Enrollment",
			"course": course,
			"member": frappe.session.user,
		}
	).insert(ignore_permissions=False)

	return get_membership(course)


def _materials_from_content(content: str) -> list:
	"""Pull the downloadable files out of one lesson's EditorJS content.

	Only `upload` blocks carry a real file: images pasted as `image` blocks are
	inline artwork, and `embed` blocks are remote players. Both would be noise
	in a materials list, so neither is collected.
	"""
	files = []
	for block in get_editorjs_blocks(content):
		if block.get("type") != "upload":
			continue
		data = block.get("data") or {}
		file_url = data.get("file_url")
		if not file_url:
			continue
		files.append(
			{
				"file_url": file_url,
				"file_type": data.get("file_type") or "",
				"file_name": data.get("file_name") or file_url.rsplit("/", 1)[-1],
			}
		)
	return files


def _file_sizes(file_urls: list) -> dict:
	"""File sizes for the URLs, in one query. Missing rows simply have no size."""
	if not file_urls:
		return {}

	rows = frappe.get_all(
		"File",
		filters={"file_url": ["in", file_urls]},
		fields=["file_url", "file_size"],
		limit_page_length=0,
	)
	return {row.file_url: cint(row.file_size) for row in rows}


@frappe.whitelist(allow_guest=True)
def get_course_materials(course: str) -> list:
	"""Every downloadable file in `course`, grouped by chapter.

	Access mirrors the course detail page exactly: `get_course_details` already
	returns `{}` for a course the caller may not see, so a caller who cannot
	open the course gets an empty list here rather than a file listing.
	"""
	if not guest_access_allowed():
		return []

	if not get_course_details(course):
		return []

	grouped = []
	pending_urls = []

	for chapter in get_chapters(course):
		lesson_names = frappe.get_all(
			"Lesson Reference",
			filters={"parent": chapter.name},
			pluck="lesson",
			order_by="idx",
		)
		if not lesson_names:
			continue

		lessons = frappe.get_all(
			"Course Lesson",
			filters={"name": ["in", lesson_names]},
			fields=["name", "title", "content"],
		)
		by_name = {lesson.name: lesson for lesson in lessons}

		files = []
		# Iterate `lesson_names` rather than `lessons` so the files come back in
		# the order the chapter lists its lessons, not the order the DB returns.
		for lesson_name in lesson_names:
			lesson = by_name.get(lesson_name)
			if not lesson:
				continue
			for item in _materials_from_content(lesson.content):
				item["lesson"] = lesson.name
				item["lesson_title"] = lesson.title
				files.append(item)
				pending_urls.append(item["file_url"])

		if files:
			grouped.append(
				{
					"chapter": chapter.name,
					"chapter_title": chapter.title,
					"idx": chapter.idx,
					"files": files,
				}
			)

	sizes = _file_sizes(list(set(pending_urls)))
	for group in grouped:
		for item in group["files"]:
			item["file_size"] = sizes.get(item["file_url"], 0)

	return grouped


@frappe.whitelist()
def get_my_materials() -> list:
	"""The materials shelf: every course the student is enrolled in, with files.

	Courses with no downloadable file are dropped rather than shown empty — an
	empty course row tells the student nothing they can act on.
	"""
	_require_login()

	enrolled = frappe.get_all(
		"LMS Enrollment",
		filters={"member": frappe.session.user},
		pluck="course",
		limit_page_length=0,
	)
	if not enrolled:
		return []

	titles = dict(
		frappe.get_all(
			"LMS Course",
			filters={"name": ["in", enrolled]},
			fields=["name", "title"],
			as_list=True,
			limit_page_length=0,
		)
	)

	shelf = []
	for course in enrolled:
		chapters = get_course_materials(course)
		if not chapters:
			continue
		shelf.append(
			{
				"course": course,
				"course_title": titles.get(course, course),
				"chapters": chapters,
				"count": sum(len(chapter["files"]) for chapter in chapters),
			}
		)

	return shelf


@frappe.whitelist()
def get_my_batches() -> list:
	"""The batches the student is actually enrolled in.

	Deliberately not `lms.lms.api.get_my_batches`: that one falls back to the
	next four *published upcoming* batches when the student has none, which is
	right for a marketing row on the home page and wrong for anything that reads
	as "your batches" — a discussion list built on it would offer threads the
	student is not a member of.
	"""
	_require_login()

	names = frappe.get_all(
		"LMS Batch Enrollment",
		filters={"member": frappe.session.user},
		pluck="batch",
		order_by="creation desc",
		limit_page_length=0,
	)
	if not names:
		return []

	return frappe.get_all(
		"LMS Batch",
		filters={"name": ["in", names]},
		fields=["name", "title", "start_date", "end_date", "start_time"],
		order_by="start_date desc",
		limit_page_length=0,
	)


@frappe.whitelist()
def get_calendar_events(start: str, end: str) -> list:
	"""Everything on the student's calendar between `start` and `end` (dates).

	Five sources, flattened into one shape the calendar can render without
	knowing where each entry came from:

	  * live classes on the batches the student belongs to,
	  * evaluation slots the student has booked,
	  * batches' own start dates, so an upcoming cohort is visible before its
	    first class exists,
	  * events the student organised or was invited to (recurrence expanded),
	  * one-to-one appointments, as student or as instructor.

	Every entry carries `kind`, which is what the UI colours and routes on.
	"""
	_require_login()

	member = frappe.session.user
	batches = frappe.get_all(
		"LMS Batch Enrollment",
		filters={"member": member},
		pluck="batch",
		limit_page_length=0,
	)

	events = []

	if batches:
		classes = frappe.get_all(
			"LMS Live Class",
			filters={"batch_name": ["in", batches], "date": ["between", [start, end]]},
			fields=["title", "description", "date", "time", "duration", "join_url", "batch_name"],
			order_by="date asc, time asc",
			limit_page_length=0,
		)
		for row in classes:
			events.append(
				{
					"kind": "live_class",
					"title": row.title,
					"description": row.description,
					"date": row.date,
					"time": row.time,
					"duration": row.duration,
					"url": row.join_url,
					"context": row.batch_name,
				}
			)

	evaluations = frappe.get_all(
		"LMS Certificate Request",
		filters={"member": member, "date": ["between", [start, end]]},
		fields=["name", "course", "date", "start_time", "end_time", "google_meet_link"],
		order_by="date asc, start_time asc",
		limit_page_length=0,
	)
	for row in evaluations:
		events.append(
			{
				"kind": "evaluation",
				"title": _("Evaluation: {0}").format(
					frappe.db.get_value("LMS Course", row.course, "title") or row.course
				),
				"description": "",
				"date": row.date,
				"time": row.start_time,
				"end_time": row.end_time,
				"url": row.google_meet_link,
				"context": row.course,
			}
		)

	if batches:
		upcoming = frappe.get_all(
			"LMS Batch",
			filters={"name": ["in", batches], "start_date": ["between", [start, end]]},
			fields=["name", "title", "start_date", "start_time"],
			limit_page_length=0,
		)
		for row in upcoming:
			events.append(
				{
					"kind": "batch_start",
					"title": _("{0} begins").format(row.title),
					"description": "",
					"date": row.start_date,
					"time": row.start_time,
					"url": None,
					"context": row.name,
				}
			)

	events.extend(_student_events(member, start, end))
	events.extend(_appointments(member, start, end))

	events.sort(key=lambda event: (str(event["date"]), str(event.get("time") or "")))
	return events


def _student_events(member: str, start: str, end: str) -> list:
	"""Events the member organised or was invited to, expanded over the window.

	Recurrence is stored as a rule, so an event contributes one entry per date it
	actually lands on inside `[start, end]` — see
	`LMSStudentEvent.occurrences`.
	"""
	invited_to = frappe.get_all(
		"LMS Event Participant",
		filters={"participant": member, "parenttype": "LMS Student Event"},
		pluck="parent",
		limit_page_length=0,
	)
	mine = frappe.get_all("LMS Student Event", filters={"owner": member}, pluck="name", limit_page_length=0)

	names = list(set(invited_to) | set(mine))
	if not names:
		return []

	rows = []
	for name in names:
		doc = frappe.get_cached_doc("LMS Student Event", name)
		for day in doc.occurrences(start, end):
			rows.append(
				{
					"kind": "event",
					"name": doc.name,
					"title": doc.title,
					"description": doc.description or "",
					"date": day,
					"time": None if doc.all_day else doc.start_time,
					"end_time": None if doc.all_day else doc.end_time,
					"all_day": bool(doc.all_day),
					"url": doc.meet_link,
					"context": doc.course,
					"is_owner": doc.owner == member,
					"participants": [
						{
							"participant": row.participant,
							"full_name": row.full_name,
							"user_image": row.user_image,
							"participant_role": row.participant_role,
						}
						for row in doc.participants
					],
				}
			)
	return rows


def _appointments(member: str, start: str, end: str) -> list:
	"""One-to-one sessions the member is on, as student or as instructor."""
	fields = [
		"name",
		"course",
		"course_title",
		"instructor",
		"instructor_name",
		"student",
		"student_name",
		"date",
		"start_time",
		"end_time",
		"topic",
		"status",
		"meet_link",
	]
	window = {"date": ["between", [start, end]], "status": ["!=", "Cancelled"]}

	# Two reads rather than an or_filter: or_filters would OR away the date and
	# status restrictions along with the ownership test.
	rows = frappe.get_all(
		"LMS Appointment", filters={**window, "student": member}, fields=fields, limit_page_length=0
	) + frappe.get_all(
		"LMS Appointment", filters={**window, "instructor": member}, fields=fields, limit_page_length=0
	)

	seen = {}
	for row in rows:
		as_instructor = row.instructor == member
		seen[row.name] = {
			"kind": "appointment",
			"name": row.name,
			"title": _("1:1 with {0}").format(row.student_name if as_instructor else row.instructor_name),
			"description": row.topic,
			"date": row.date,
			"time": row.start_time,
			"end_time": row.end_time,
			"url": row.meet_link,
			"context": row.course,
			"course_title": row.course_title,
			"role": "instructor" if as_instructor else "student",
			"status": row.status,
		}
	return list(seen.values())
