# Copyright (c) 2026, Frappe and Contributors
# For license information, please see license.txt

"""What is scheduled in a batch, and when.

No new storage: every source already exists. What was missing was a batch-level
*view* of them — the timetable was reachable only through the Settings tab, and
live classes, evaluations and appointments were each somewhere else.

Every entry carries ``kind``, which is what the grid colours and routes on. That
is the same contract ``lms.lms.student_api.get_calendar_events`` already uses, so
the student calendar and this one render from one shape.
"""

from __future__ import annotations

from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import add_to_date, get_time, getdate

from lms.lms.batch_access import (
	assert_batch_member,
	batch_students,
	is_batch_moderator,
	visible_batches,
)

KINDS = (
	"timetable",
	"live_class",
	"evaluation",
	"appointment",
	"batch_start",
	"batch_end",
)


def _entry(kind: str, title: str, date, **extra) -> dict:
	return {"kind": kind, "title": title, "date": getdate(date), **extra}


@frappe.whitelist()
def get_batch_calendar(batch: str, start: str, end: str) -> list[dict]:
	"""Everything scheduled in ``batch`` between ``start`` and ``end`` (dates).

	Readable by any member of the batch. Published-ness does not open it: seeing a
	cohort advertised is not being in it, and this is the cohort's working
	schedule.
	"""
	assert_batch_member(batch)

	events: list[dict] = []
	events += _timetable_entries(batch, start, end)
	events += _live_classes(batch, start, end)
	events += _evaluations(batch, start, end)
	events += _batch_markers(batch, start, end)

	# Appointments are 1:1 and belong to the two people in them. A moderator sees
	# the batch's staff appointments because scheduling conflicts are their
	# problem; a student sees only their own.
	events += _appointments(batch, start, end)

	events.sort(key=lambda e: (e["date"], e.get("start_time") or timedelta(0)))
	return events


def _timetable_entries(batch: str, start: str, end: str) -> list[dict]:
	rows = frappe.get_all(
		"LMS Batch Timetable",
		filters={"parent": batch, "parenttype": "LMS Batch", "date": ["between", [start, end]]},
		fields=[
			"name",
			"reference_doctype",
			"reference_docname",
			"date",
			"start_time",
			"end_time",
			"milestone",
		],
		order_by="date asc",
	)
	out = []
	for row in rows:
		title = (
			frappe.db.get_value(row.reference_doctype, row.reference_docname, "title")
			or row.reference_docname
		)
		out.append(
			_entry(
				"timetable",
				title,
				row.date,
				start_time=row.start_time,
				end_time=row.end_time,
				milestone=bool(row.milestone),
				reference_doctype=row.reference_doctype,
				reference_docname=row.reference_docname,
			)
		)
	return out


def _live_classes(batch: str, start: str, end: str) -> list[dict]:
	rows = frappe.get_all(
		"LMS Live Class",
		filters={"batch_name": batch, "date": ["between", [start, end]]},
		fields=["name", "title", "description", "date", "time", "duration", "join_url"],
		order_by="date asc, time asc",
	)
	out = []
	for row in rows:
		end_time = None
		if row.time is not None and row.duration:
			end_time = row.time + timedelta(minutes=row.duration)
		out.append(
			_entry(
				"live_class",
				row.title,
				row.date,
				start_time=row.time,
				end_time=end_time,
				duration=row.duration,
				description=row.description,
				url=row.join_url,
				reference_doctype="LMS Live Class",
				reference_docname=row.name,
			)
		)
	return out


def _evaluations(batch: str, start: str, end: str) -> list[dict]:
	"""Evaluation slots booked by this batch's students.

	A student sees only their own — whose certification interview is when is not
	cohort business. Staff see the batch's, because that is the schedule they run.
	"""
	if is_batch_moderator(batch):
		members = sorted(batch_students(batch))
	else:
		members = [frappe.session.user]
	if not members:
		return []

	# Scoped by `batch_name` as well as by person: filtering on the member alone
	# would pull that student's evaluations for *other* cohorts into this batch's
	# calendar.
	rows = frappe.get_all(
		"LMS Certificate Request",
		filters={
			"batch_name": batch,
			"member": ["in", members],
			"date": ["between", [start, end]],
		},
		fields=[
			"name",
			"member",
			"member_name",
			"course",
			"date",
			"start_time",
			"end_time",
			"google_meet_link",
		],
		order_by="date asc, start_time asc",
	)
	return [
		_entry(
			"evaluation",
			_("Evaluation: {0}").format(frappe.db.get_value("LMS Course", row.course, "title") or row.course),
			row.date,
			start_time=row.start_time,
			end_time=row.end_time,
			member=row.member,
			member_name=row.member_name,
			url=row.google_meet_link,
			reference_doctype="LMS Certificate Request",
			reference_docname=row.name,
		)
		for row in rows
	]


def _appointments(batch: str, start: str, end: str) -> list[dict]:
	"""1:1 appointments involving this batch's people.

	`LMS Appointment` has no batch column — it is course-scoped — so this filters
	by the people rather than by the batch, which is why a moderator's view is
	built from the roster and everyone else's is just themselves.
	"""
	if not frappe.db.exists("DocType", "LMS Appointment"):
		return []

	user = frappe.session.user
	if is_batch_moderator(batch):
		members = sorted(batch_students(batch) | {user})
	else:
		members = [user]

	rows = frappe.get_all(
		"LMS Appointment",
		filters={
			"date": ["between", [start, end]],
			"status": ["!=", "Cancelled"],
		},
		# The learner column here is `student`, not `member` — LMS Batch Enrollment
		# uses `member` and the two doctypes do not share a vocabulary.
		or_filters={"student": ["in", members], "instructor": ["in", members]},
		fields=[
			"name",
			"student",
			"student_name",
			"instructor",
			"course",
			"date",
			"start_time",
			"end_time",
			"topic",
		],
		order_by="date asc, start_time asc",
	)
	return [
		_entry(
			"appointment",
			row.topic or _("Appointment"),
			row.date,
			start_time=row.start_time,
			end_time=row.end_time,
			member=row.student,
			member_name=row.student_name,
			instructor=row.instructor,
			course=row.course,
			reference_doctype="LMS Appointment",
			reference_docname=row.name,
		)
		for row in rows
	]


def _batch_markers(batch: str, start: str, end: str) -> list[dict]:
	row = frappe.db.get_value(
		"LMS Batch", batch, ["title", "start_date", "end_date", "start_time", "end_time"], as_dict=True
	)
	if not row:
		return []

	window = (getdate(start), getdate(end))
	out = []
	if row.start_date and window[0] <= getdate(row.start_date) <= window[1]:
		out.append(
			_entry(
				"batch_start",
				_("{0} starts").format(row.title),
				row.start_date,
				start_time=row.start_time,
				end_time=row.end_time,
			)
		)
	if row.end_date and window[0] <= getdate(row.end_date) <= window[1]:
		out.append(_entry("batch_end", _("{0} ends").format(row.title), row.end_date))
	return out


@frappe.whitelist()
def get_my_calendar(start: str, end: str) -> list[dict]:
	"""The cross-batch schedule: every batch the caller is attached to, merged.

	A moderator running six cohorts needs one calendar, not six. Two live classes
	at the same hour in two different batches is the collision this exists to
	surface, and it is invisible from inside either one.
	"""
	batches = visible_batches()
	if not batches:
		return []

	titles = {
		row.name: row.title
		for row in frappe.get_all("LMS Batch", filters={"name": ["in", batches]}, fields=["name", "title"])
	}

	events = []
	for batch in batches:
		try:
			for event in get_batch_calendar(batch, start, end):
				event["batch"] = batch
				event["batch_title"] = titles.get(batch, batch)
				events.append(event)
		except frappe.PermissionError:
			continue

	events.sort(key=lambda e: (e["date"], e.get("start_time") or timedelta(0)))
	return events
