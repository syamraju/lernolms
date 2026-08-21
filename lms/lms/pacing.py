"""Course deadlines: how long a learner has, and when they have fallen behind.

A course may set `completion_deadline_days`. From that, every enrollment gets a
`due_date` — the day by which the learner is expected to have finished. Passing
it does not revoke anything: the enrollment is simply reported as overdue, so
the learner and the instructor can both see it.

The deadline is stored on the enrollment rather than derived on every read
because it is the learner's own clock: it starts when *they* enrolled, and
raising the course's allowance later should not silently move the date of
someone already past it. `refresh_due_dates` is the one place that rewrites
stored dates, and it only ever touches learners who are still working.

The two functions that decide anything — `compute_due_date` and `pacing_state`
— take plain values and return plain values, so the rules can be tested without
a course, an enrollment or a session user.
"""

from __future__ import annotations

import frappe
from frappe.utils import add_days, cint, date_diff, flt, getdate, nowdate

# Progress at which a learner is done and the deadline stops mattering.
COMPLETE_PROGRESS = 100

# How close to the due date counts as "due soon". A learner who reads it on a
# Monday still has the working week to act on it.
DUE_SOON_DAYS = 7


def deadline_days(course: str) -> int:
	"""The course's allowance in days, or 0 when it has no deadline."""
	if not course:
		return 0
	return cint(frappe.db.get_value("LMS Course", course, "completion_deadline_days"))


def compute_due_date(started_on, days: int) -> str | None:
	"""The day a learner who started on `started_on` is expected to finish.

	Returns None when the course sets no deadline, which is what an enrollment
	with no due date means everywhere else in this module.
	"""
	days = cint(days)
	if days <= 0 or not started_on:
		return None
	return str(add_days(getdate(started_on), days))


def pacing_state(due_date, progress, on_date=None) -> dict:
	"""How an enrollment stands against its deadline on a given day.

	`days_left` counts whole days and goes negative once the date has passed, so
	a caller can say "3 days left" and "2 days overdue" from the one number.

	A finished course is never overdue. Someone who completed the work late has
	completed it, and telling them otherwise every time they open the page is
	both useless and wrong.
	"""
	on_date = getdate(on_date or nowdate())
	completed = flt(progress) >= COMPLETE_PROGRESS

	if not due_date:
		return {
			"due_date": None,
			"days_left": None,
			"is_overdue": False,
			"status": "Completed" if completed else "No deadline",
		}

	due = getdate(due_date)
	days_left = date_diff(due, on_date)

	if completed:
		status = "Completed"
	elif days_left < 0:
		status = "Overdue"
	elif days_left <= DUE_SOON_DAYS:
		status = "Due soon"
	else:
		status = "On track"

	return {
		"due_date": str(due),
		"days_left": days_left,
		"is_overdue": status == "Overdue",
		"status": status,
	}


def set_enrollment_due_date(enrollment) -> None:
	"""Stamp a new enrollment with its deadline. Called from before_insert."""
	if enrollment.due_date:
		return
	days = deadline_days(enrollment.course)
	if not days:
		return
	# A brand new document has no creation timestamp yet, so the clock starts
	# today — which is the same day the row is about to be written.
	enrollment.due_date = compute_due_date(enrollment.get("creation") or nowdate(), days)


def refresh_due_dates(course: str) -> int:
	"""Re-stamp the deadline on enrollments of `course` that are still in progress.

	Run when the course's allowance changes. Learners who already finished keep
	whatever date they had: rewriting history for work that is done serves
	nobody, and clearing the deadline on a course that dropped it is handled by
	the `days == 0` branch below.
	"""
	days = deadline_days(course)
	enrollments = frappe.get_all(
		"LMS Enrollment",
		filters={"course": course, "progress": ("<", COMPLETE_PROGRESS)},
		fields=["name", "creation", "due_date"],
	)

	changed = 0
	for enrollment in enrollments:
		due_date = compute_due_date(enrollment.creation, days)
		if str(enrollment.due_date or "") == str(due_date or ""):
			continue
		frappe.db.set_value("LMS Enrollment", enrollment.name, "due_date", due_date, update_modified=False)
		changed += 1
	return changed


@frappe.whitelist()
def get_course_pacing(course: str, member: str | None = None) -> dict:
	"""The deadline picture for one learner on one course.

	Defaults to the session user. Reading someone else's pacing is limited to
	people who can already see the course's roster, so a student cannot poll for
	who in their cohort is behind.
	"""
	member = member or frappe.session.user
	if member != frappe.session.user:
		from lms.lms.utils import can_modify_course

		if not can_modify_course(course):
			raise frappe.PermissionError

	enrollment = frappe.db.get_value(
		"LMS Enrollment",
		{"course": course, "member": member},
		["name", "due_date", "progress", "creation"],
		as_dict=True,
	)
	days = deadline_days(course)
	if not enrollment:
		return {
			"enrolled": False,
			"deadline_days": days,
			"due_date": None,
			"days_left": None,
			"is_overdue": False,
			"status": "No deadline" if not days else "Not enrolled",
		}

	# Enrollments created before the course had a deadline carry no stored date.
	# Deriving one here means turning the setting on works for the cohort already
	# in flight, without a migration pass over every course.
	due_date = enrollment.due_date or compute_due_date(enrollment.creation, days)
	state = pacing_state(due_date, enrollment.progress)
	state.update({"enrolled": True, "deadline_days": days, "progress": flt(enrollment.progress)})
	return state
