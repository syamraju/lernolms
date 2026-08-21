"""Whitelisted endpoints for the student calendar.

Two features live here, and they are deliberately separate:

* **Events** — a student organises a discussion and invites people they share a
  course with. Anyone enrolled can create one.
* **Appointments** — an instructor publishes weekly office hours per course and
  a student books a one-to-one slot from them. The slot is exclusive: once
  taken it disappears for everyone else.

The exclusivity guarantee is *not* implemented here. `get_available_slots`
subtracts booked slots so the UI does not offer them, but that is a courtesy —
the authority is `LMSAppointment.validate_slot_is_free`, which runs under a row
lock and rejects a race that this module's read cannot see. Never move that
check up here.
"""

import json

import frappe
from frappe import _
from frappe.utils import (
	add_days,
	cint,
	get_datetime,
	get_system_timezone,
	get_time,
	getdate,
	now_datetime,
)

from lms.lms.doctype.lms_student_event.lms_student_event import course_members
from lms.lms.utils import has_moderator_role

# How far ahead a student may book. Longer than this and an instructor's
# schedule is a guess rather than a commitment.
BOOKING_HORIZON_DAYS = 60

# Neither is a person: Guest is the anonymous pseudo-user and Administrator is
# the bootstrap account. Both can appear in enrolment tables on a seeded site.
BUILTIN_ACCOUNTS = {"Guest", "Administrator"}


def _require_login():
	if frappe.session.user == "Guest":
		frappe.throw(_("Please sign in to continue."), frappe.AuthenticationError)


def _parse(payload):
	"""Accept either a JSON string or an already-decoded dict.

	frappe hands `dict` through when the client posts JSON, and a string when it
	posts form-encoded; both reach whitelisted methods in practice.
	"""
	if isinstance(payload, str):
		return json.loads(payload)
	return payload or {}


def _enrolled_courses(member: str = None) -> list:
	return frappe.get_all(
		"LMS Enrollment",
		filters={"member": member or frappe.session.user},
		pluck="course",
		limit_page_length=0,
	)


def _taught_courses(instructor: str = None) -> list:
	return frappe.get_all(
		"Course Instructor",
		filters={"instructor": instructor or frappe.session.user, "parenttype": "LMS Course"},
		pluck="parent",
		limit_page_length=0,
	)


def _minutes(value) -> int:
	"""A Time as minutes past midnight, so slot arithmetic is plain integers."""
	parsed = get_time(value)
	return parsed.hour * 60 + parsed.minute


def _clock(minutes: int) -> str:
	return f"{minutes // 60:02d}:{minutes % 60:02d}:00"


# ---------------------------------------------------------------- events


@frappe.whitelist()
def get_event_invitees(course: str = None, search: str = None) -> list:
	"""Who the caller may invite to an event.

	Scoped to people they actually share a course with — a student may not
	enumerate the whole user table through this. With `course` given it is that
	course's members; without one it is the union across everything they are
	enrolled in or teach.
	"""
	_require_login()
	me = frappe.session.user

	if course:
		mine = set(_enrolled_courses()) | set(_taught_courses())
		if course not in mine and not has_moderator_role():
			frappe.throw(_("You are not part of that course."))
		courses = [course]
	else:
		courses = list(set(_enrolled_courses()) | set(_taught_courses()))

	if not courses:
		return []

	instructors = set()
	people = set()
	for row in courses:
		for instructor in frappe.get_all(
			"Course Instructor",
			filters={"parent": row, "parenttype": "LMS Course"},
			pluck="instructor",
			limit_page_length=0,
		):
			instructors.add(instructor)
			people.add(instructor)
		for member in frappe.get_all(
			"LMS Enrollment", filters={"course": row}, pluck="member", limit_page_length=0
		):
			people.add(member)

	people.discard(me)
	# Frappe's two built-in accounts are not people. Guest in particular reaches
	# this list through demo enrolments, and inviting it would attach the
	# anonymous pseudo-user to a real event.
	people -= BUILTIN_ACCOUNTS
	if not people:
		return []

	filters = {"name": ["in", list(people)], "enabled": 1}
	if search:
		# `like` on both columns rather than an or_filter: get_all's or_filters
		# would also OR away the `name in` restriction above.
		matches = set(
			frappe.get_all(
				"User",
				filters={**filters, "full_name": ["like", f"%{search}%"]},
				pluck="name",
				limit_page_length=0,
			)
		) | set(
			frappe.get_all(
				"User",
				filters={**filters, "name": ["like", f"%{search}%"]},
				pluck="name",
				limit_page_length=0,
			)
		)
		if not matches:
			return []
		filters["name"] = ["in", list(matches)]

	users = frappe.get_all(
		"User",
		filters=filters,
		fields=["name", "full_name", "user_image"],
		order_by="full_name asc",
		limit_page_length=50,
	)
	for user in users:
		user.participant_role = "Instructor" if user.name in instructors else "Student"
	return users


@frappe.whitelist()
def create_event(payload: dict | str) -> dict:
	"""Create an event owned by the caller and return it in calendar shape."""
	_require_login()
	data = _parse(payload)

	doc = frappe.new_doc("LMS Student Event")
	doc.update(
		{
			"title": data.get("title"),
			"course": data.get("course") or None,
			"event_type": data.get("event_type") or "Discussion",
			"date": data.get("date"),
			"start_time": data.get("start_time"),
			"end_time": data.get("end_time"),
			"all_day": cint(data.get("all_day")),
			"description": data.get("description"),
			"meet_link": data.get("meet_link"),
			"repeat_enabled": cint(data.get("repeat_enabled")),
			"repeat_every": cint(data.get("repeat_every")) or 1,
			"repeat_unit": data.get("repeat_unit") or "Weeks",
			"repeat_on": data.get("repeat_on"),
			"repeat_ends": data.get("repeat_ends") or "Never",
			"repeat_until": data.get("repeat_until") or None,
			"repeat_count": cint(data.get("repeat_count")) or 0,
		}
	)

	_apply_participants(doc, data.get("participants") or [])
	doc.insert()
	return {"name": doc.name}


@frappe.whitelist()
def update_event(name: str, payload: dict | str) -> dict:
	"""Edit an event the caller owns."""
	_require_login()
	doc = _own_event(name)
	data = _parse(payload)

	editable = (
		"title",
		"course",
		"event_type",
		"date",
		"start_time",
		"end_time",
		"description",
		"meet_link",
		"repeat_unit",
		"repeat_on",
		"repeat_ends",
		"repeat_until",
	)
	for field in editable:
		if field in data:
			doc.set(field, data.get(field) or None)

	for field in ("all_day", "repeat_enabled", "repeat_every", "repeat_count"):
		if field in data:
			doc.set(field, cint(data.get(field)))

	if "participants" in data:
		doc.participants = []
		_apply_participants(doc, data.get("participants") or [])

	doc.save()
	return {"name": doc.name}


@frappe.whitelist()
def delete_event(name: str) -> None:
	_require_login()
	_own_event(name).delete()


def _own_event(name: str):
	doc = frappe.get_doc("LMS Student Event", name)
	if doc.owner != frappe.session.user and not has_moderator_role():
		frappe.throw(_("You can only change events you created."), frappe.PermissionError)
	return doc


def _apply_participants(doc, participants: list) -> None:
	"""Attach invitees, resolving each one's role against the event's course.

	The role is stored rather than looked up on read so the invitation list still
	reads correctly after someone's enrolment changes.
	"""
	if not participants:
		return

	course = doc.course
	instructors = set()
	if course:
		instructors = set(
			frappe.get_all(
				"Course Instructor",
				filters={"parent": course, "parenttype": "LMS Course"},
				pluck="instructor",
				limit_page_length=0,
			)
		)
	else:
		# No course to scope against, so the organiser may only invite people
		# they share some course with. Same rule get_event_invitees applies.
		reachable = set()
		for row in set(_enrolled_courses()) | set(_taught_courses()):
			reachable |= set(course_members(row))
		for entry in participants:
			user = entry.get("participant") if isinstance(entry, dict) else entry
			if user not in reachable:
				frappe.throw(_("You do not share a course with {0}.").format(user))

	for entry in participants:
		user = entry.get("participant") if isinstance(entry, dict) else entry
		if not user:
			continue
		doc.append(
			"participants",
			{
				"participant": user,
				"participant_role": "Instructor" if user in instructors else "Student",
			},
		)


# ------------------------------------------------------- availability (instructor)


@frappe.whitelist()
def get_my_courses_for_availability() -> list:
	"""Courses the caller teaches, each with the availability they have set (if any)."""
	_require_login()
	courses = _taught_courses()
	if not courses:
		return []

	rows = frappe.get_all(
		"LMS Course",
		filters={"name": ["in", courses]},
		fields=["name", "title"],
		order_by="title asc",
		limit_page_length=0,
	)

	existing = {
		row.course: row
		for row in frappe.get_all(
			"LMS Instructor Availability",
			filters={"instructor": frappe.session.user, "course": ["in", courses]},
			fields=["name", "course", "slot_duration", "published", "unavailable_from", "unavailable_to"],
			limit_page_length=0,
		)
	}

	for row in rows:
		found = existing.get(row.name)
		row.availability = found
		row.schedule = (
			frappe.get_all(
				"LMS Availability Slot",
				filters={"parent": found.name, "parenttype": "LMS Instructor Availability"},
				fields=["name", "day", "start_time", "end_time"],
				order_by="idx asc",
			)
			if found
			else []
		)
	return rows


@frappe.whitelist()
def save_availability(payload: dict | str) -> dict:
	"""Create or replace the caller's availability for one course."""
	_require_login()
	data = _parse(payload)

	course = data.get("course")
	if not course:
		frappe.throw(_("Pick a course."))

	existing = frappe.db.get_value(
		"LMS Instructor Availability",
		{"instructor": frappe.session.user, "course": course},
		"name",
	)
	doc = (
		frappe.get_doc("LMS Instructor Availability", existing)
		if existing
		else frappe.new_doc("LMS Instructor Availability")
	)

	doc.update(
		{
			"instructor": frappe.session.user,
			"course": course,
			"slot_duration": cint(data.get("slot_duration")) or 30,
			"published": cint(data.get("published", 1)),
			"unavailable_from": data.get("unavailable_from") or None,
			"unavailable_to": data.get("unavailable_to") or None,
		}
	)

	doc.schedule = []
	for row in data.get("schedule") or []:
		doc.append(
			"schedule",
			{
				"day": row.get("day"),
				"start_time": row.get("start_time"),
				"end_time": row.get("end_time"),
			},
		)

	doc.save()
	return {"name": doc.name}


@frappe.whitelist()
def delete_availability(course: str) -> None:
	"""Stop taking appointments for a course. Booked appointments are untouched."""
	_require_login()
	name = frappe.db.get_value(
		"LMS Instructor Availability", {"instructor": frappe.session.user, "course": course}, "name"
	)
	if name:
		frappe.delete_doc("LMS Instructor Availability", name)


# ------------------------------------------------------- booking (student)


@frappe.whitelist()
def get_bookable_courses() -> list:
	"""Courses the caller is enrolled in that have at least one instructor taking appointments.

	This is the first step of the booking popup, so a course that would lead to
	an empty instructor list is not offered at all.
	"""
	_require_login()
	courses = _enrolled_courses()
	if not courses:
		return []

	open_courses = frappe.get_all(
		"LMS Instructor Availability",
		filters={"course": ["in", courses], "published": 1},
		pluck="course",
		limit_page_length=0,
	)
	if not open_courses:
		return []

	return frappe.get_all(
		"LMS Course",
		filters={"name": ["in", list(set(open_courses))]},
		fields=["name", "title", "image"],
		order_by="title asc",
		limit_page_length=0,
	)


@frappe.whitelist()
def get_bookable_instructors(course: str) -> list:
	"""The course's instructors who are taking appointments, in the card shape the popup renders."""
	_require_login()

	if course not in _enrolled_courses():
		frappe.throw(_("You are not enrolled in that course."))

	rows = frappe.get_all(
		"LMS Instructor Availability",
		filters={"course": course, "published": 1},
		fields=["name", "instructor", "slot_duration"],
		limit_page_length=0,
	)
	if not rows:
		return []

	by_instructor = {row.instructor: row for row in rows}
	people = frappe.get_all(
		"User",
		filters={"name": ["in", list(by_instructor)], "enabled": 1},
		fields=["name", "full_name", "user_image", "bio"],
		order_by="full_name asc",
		limit_page_length=0,
	)
	for person in people:
		person.slot_duration = by_instructor[person.name].slot_duration
	return people


@frappe.whitelist()
def get_available_slots(course: str, instructor: str, date_from: str = None, date_to: str = None) -> list:
	"""Free slots for one instructor on one course, grouped by date.

	Advisory only — see this module's docstring. A slot listed here can still be
	taken between the read and the booking, which is exactly the case
	`LMSAppointment` is written to reject.
	"""
	_require_login()

	if course not in _enrolled_courses():
		frappe.throw(_("You are not enrolled in that course."))

	availability = frappe.db.get_value(
		"LMS Instructor Availability",
		{"instructor": instructor, "course": course, "published": 1},
		["name", "slot_duration", "unavailable_from", "unavailable_to", "timezone"],
		as_dict=True,
	)
	if not availability:
		return []

	today = getdate()
	start = max(getdate(date_from), today) if date_from else today
	horizon = add_days(today, BOOKING_HORIZON_DAYS)
	end = min(getdate(date_to), horizon) if date_to else horizon
	if start > end:
		return []

	windows = {}
	for row in frappe.get_all(
		"LMS Availability Slot",
		filters={"parent": availability.name, "parenttype": "LMS Instructor Availability"},
		fields=["day", "start_time", "end_time"],
		order_by="idx asc",
	):
		windows.setdefault(row.day, []).append((_minutes(row.start_time), _minutes(row.end_time)))

	if not windows:
		return []

	# Every live appointment in range, in one read rather than one per day.
	taken = {}
	for row in frappe.get_all(
		"LMS Appointment",
		filters={
			"instructor": instructor,
			"date": ["between", [start, end]],
			"status": ["!=", "Cancelled"],
		},
		fields=["date", "start_time", "end_time"],
		limit_page_length=0,
	):
		taken.setdefault(str(getdate(row.date)), []).append(
			(_minutes(row.start_time), _minutes(row.end_time))
		)

	duration = cint(availability.slot_duration) or 30
	now = now_datetime()
	days = []
	cursor = start

	while cursor <= end:
		iso = str(cursor)
		if _is_unavailable(availability, cursor):
			cursor = add_days(cursor, 1)
			continue

		slots = []
		for window_start, window_end in windows.get(cursor.strftime("%A"), []):
			at = window_start
			while at + duration <= window_end:
				slot_end = at + duration

				# A slot earlier today is not bookable, and the doctype would
				# reject it anyway — leaving it visible only invites a failure.
				if get_datetime(f"{iso} {_clock(at)}") <= now:
					at = slot_end
					continue

				if not any(
					at < other_end and other_start < slot_end
					for other_start, other_end in taken.get(iso, [])
				):
					slots.append({"start_time": _clock(at), "end_time": _clock(slot_end)})

				at = slot_end

		if slots:
			days.append({"date": iso, "day": cursor.strftime("%A"), "slots": slots})

		cursor = add_days(cursor, 1)

	return days


def _is_unavailable(availability, day) -> bool:
	if not availability.unavailable_from or not availability.unavailable_to:
		return False
	return getdate(availability.unavailable_from) <= day <= getdate(availability.unavailable_to)


@frappe.whitelist()
def book_appointment(payload: dict | str) -> dict:
	"""Book a one-to-one slot for the caller.

	Everything that decides whether the booking is legal lives in
	`LMSAppointment.validate`; this only assembles the document. The student is
	always the caller, so a crafted request cannot book on someone else's behalf.
	"""
	_require_login()
	data = _parse(payload)

	topic = (data.get("topic") or "").strip()
	if not topic:
		frappe.throw(_("Describe what you would like to go over."))

	doc = frappe.get_doc(
		{
			"doctype": "LMS Appointment",
			"course": data.get("course"),
			"instructor": data.get("instructor"),
			"student": frappe.session.user,
			"date": data.get("date"),
			"start_time": data.get("start_time"),
			"end_time": data.get("end_time"),
			"topic": topic,
			"status": "Upcoming",
			"timezone": get_system_timezone(),
		}
	)
	doc.insert()

	return {
		"name": doc.name,
		"date": str(doc.date),
		"start_time": str(doc.start_time),
		"end_time": str(doc.end_time),
		"instructor_name": doc.instructor_name,
		"course_title": doc.course_title,
	}


@frappe.whitelist()
def cancel_appointment(name: str) -> None:
	"""Cancel an appointment, freeing the slot for someone else.

	Either side may cancel; nobody else can. The row is kept rather than deleted
	so the history survives, and `Cancelled` is what makes the slot bookable
	again.
	"""
	_require_login()
	doc = frappe.get_doc("LMS Appointment", name)

	if frappe.session.user not in (doc.student, doc.instructor) and not has_moderator_role():
		frappe.throw(_("You can only cancel your own appointments."), frappe.PermissionError)

	doc.status = "Cancelled"
	doc.save(ignore_permissions=True)


@frappe.whitelist()
def get_my_appointments(upcoming_only: int = 1) -> list:
	"""Appointments the caller is on, as student or as instructor."""
	_require_login()
	me = frappe.session.user

	filters = {"status": ["!=", "Cancelled"]} if cint(upcoming_only) else {}
	if cint(upcoming_only):
		filters["date"] = [">=", getdate()]

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

	# Two reads rather than an or_filter, so the status/date filters above are
	# not ORed away along with the ownership test.
	mine = frappe.get_all(
		"LMS Appointment", filters={**filters, "student": me}, fields=fields, limit_page_length=0
	)
	teaching = frappe.get_all(
		"LMS Appointment", filters={**filters, "instructor": me}, fields=fields, limit_page_length=0
	)

	seen = {}
	for row in mine + teaching:
		row.role = "instructor" if row.instructor == me else "student"
		seen[row.name] = row

	return sorted(seen.values(), key=lambda row: (str(row.date), str(row.start_time)))
