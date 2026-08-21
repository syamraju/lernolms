# Copyright (c) 2026, Frappe and Contributors
# For license information, please see license.txt

"""Who is attached to a batch, and what that entitles them to.

The batch is the unit of scope in this LMS: a moderator's reach, a chat
channel's audience and a calendar's contents are all answered by "which batch?",
never by "which role?" alone. Every one of those questions resolves here, so
there is exactly one place that decides them.

Design notes live in ``docs/design/batches.md``. The two that shape this module:

**Three of the four attachments are derived, not stored.** Only moderators and
students are rows. Instructors and evaluators are read out of the batch's
curriculum on every request, because adding a course to a batch must pull that
course's staff into the batch — a stored copy drifts the moment the curriculum
changes, and stale staff means stale chat access.

**Read and administer are different questions.** ``can_read_batch`` is broad:
published batches are public listings and a moderator must not see less of the
catalogue than a guest does. ``is_batch_moderator`` is the narrow one, and it is
what every administrative surface gates on.
"""

from __future__ import annotations

import frappe
from frappe import _

from lms.lms.utils import guest_access_allowed

# Roles that see every batch regardless of attachment. Deliberately not
# "Moderator": scoping Moderator to their own batches is the point of this
# module, and a role that bypasses it would make the rest of it decorative.
SUPER_ROLES = ("System Manager",)

READ_PTYPES = ("read", "select", "print", "email", "export", "report")


def is_super(user: str | None = None) -> bool:
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	return bool(set(frappe.get_roles(user)) & set(SUPER_ROLES))


# --- moderators -------------------------------------------------------------


def batch_moderators(batch: str) -> set[str]:
	"""Users who administer ``batch``: the listed moderators plus its creator.

	The creator is unioned in rather than trusted to be present. ``validate``
	keeps the row there, but this function is a permission check and must not
	depend on a validation that a direct ``db_set`` could have stepped around.
	"""
	rows = set(
		frappe.get_all(
			"Batch Moderator",
			filters={"parent": batch, "parenttype": "LMS Batch"},
			pluck="moderator",
		)
	)
	owner = frappe.db.get_value("LMS Batch", batch, "owner")
	if owner:
		rows.add(owner)
	return rows


def is_batch_moderator(batch: str, user: str | None = None) -> bool:
	user = user or frappe.session.user
	if is_super(user):
		return True
	if not batch:
		return False
	return user in batch_moderators(batch)


def moderated_batches(user: str | None = None) -> list[str]:
	"""Every batch ``user`` administers. Empty for a super role — they are not
	scoped, so an empty list here must never be read as "sees nothing"; callers
	check :func:`is_super` first."""
	user = user or frappe.session.user
	names = set(
		frappe.get_all(
			"Batch Moderator",
			filters={"moderator": user, "parenttype": "LMS Batch"},
			pluck="parent",
		)
	)
	names |= set(frappe.get_all("LMS Batch", filters={"owner": user}, pluck="name"))
	return sorted(names)


def assert_batch_moderator(batch: str, user: str | None = None) -> None:
	if not is_batch_moderator(batch, user):
		frappe.throw(
			_("You do not moderate this batch."),
			frappe.PermissionError,
		)


# --- derived staff ----------------------------------------------------------


def batch_courses(batch: str) -> list[str]:
	return frappe.get_all(
		"Batch Course",
		filters={"parent": batch, "parenttype": "LMS Batch"},
		pluck="course",
	)


def batch_instructors(batch: str) -> set[str]:
	"""Instructors of every course in the curriculum, plus the batch's own list.

	``LMS Batch.instructors`` survives alongside the derived set because a batch
	with no courses — a seminar or live-class-only cohort — derives nothing and
	still needs someone to run it. Union, never one instead of the other.
	"""
	direct = set(
		frappe.get_all(
			"Course Instructor",
			filters={"parent": batch, "parenttype": "LMS Batch"},
			pluck="instructor",
		)
	)
	courses = batch_courses(batch)
	if not courses:
		return direct
	derived = set(
		frappe.get_all(
			"Course Instructor",
			filters={"parent": ["in", courses], "parenttype": "LMS Course"},
			pluck="instructor",
		)
	)
	return direct | derived


def batch_evaluators(batch: str) -> set[str]:
	"""Evaluators of every course in the curriculum.

	``LMS Course.evaluator`` is a single-valued Link to ``Course Evaluator``,
	whose name *is* the user (``autoname: field:evaluator``). One course yields at
	most one evaluator; a batch yields the set over its courses.
	"""
	courses = batch_courses(batch)
	if not courses:
		return set()
	names = frappe.get_all(
		"LMS Course",
		filters={"name": ["in", courses], "evaluator": ["is", "set"]},
		pluck="evaluator",
	)
	if not names:
		return set()
	return set(frappe.get_all("Course Evaluator", filters={"name": ["in", names]}, pluck="evaluator"))


def staffed_batches(user: str | None = None) -> list[str]:
	"""Batches ``user`` is derived onto as instructor or evaluator.

	The reverse of :func:`batch_instructors` / :func:`batch_evaluators`: from the
	user to the courses they staff, then to the batches those courses are in.
	"""
	user = user or frappe.session.user

	courses = set(
		frappe.get_all(
			"Course Instructor",
			filters={"instructor": user, "parenttype": "LMS Course"},
			pluck="parent",
		)
	)
	if frappe.db.exists("Course Evaluator", {"evaluator": user}):
		evaluator_name = frappe.db.get_value("Course Evaluator", {"evaluator": user}, "name")
		courses |= set(frappe.get_all("LMS Course", filters={"evaluator": evaluator_name}, pluck="name"))

	names = set(
		frappe.get_all(
			"Course Instructor",
			filters={"instructor": user, "parenttype": "LMS Batch"},
			pluck="parent",
		)
	)
	if courses:
		names |= set(
			frappe.get_all(
				"Batch Course",
				filters={"course": ["in", sorted(courses)], "parenttype": "LMS Batch"},
				pluck="parent",
			)
		)
	return sorted(names)


# --- students ---------------------------------------------------------------


def is_batch_student(batch: str, user: str | None = None) -> bool:
	user = user or frappe.session.user
	return bool(frappe.db.exists("LMS Batch Enrollment", {"batch": batch, "member": user}))


def batch_students(batch: str) -> set[str]:
	return set(frappe.get_all("LMS Batch Enrollment", filters={"batch": batch}, pluck="member"))


# --- the composite answer ---------------------------------------------------

#: Ordered most- to least-privileged. :func:`batch_relation` returns the first
#: that applies, so a moderator who is also enrolled reads as a moderator.
RELATIONS = ("moderator", "instructor", "evaluator", "student")


def batch_relation(batch: str, user: str | None = None) -> str | None:
	"""How ``user`` is attached to ``batch``, or None. Super roles report
	"moderator": their reach is a superset of one, and every caller that
	branches on this wants them on the administrative side of it."""
	user = user or frappe.session.user
	if is_batch_moderator(batch, user):
		return "moderator"
	if user in batch_instructors(batch):
		return "instructor"
	if user in batch_evaluators(batch):
		return "evaluator"
	if is_batch_student(batch, user):
		return "student"
	return None


def is_batch_staff(batch: str, user: str | None = None) -> bool:
	return batch_relation(batch, user) in ("moderator", "instructor", "evaluator")


def can_read_batch(batch: str, user: str | None = None) -> bool:
	"""Read access. Broader than administration on purpose — a published batch is
	a public listing, so this stays true for anyone the catalogue is open to."""
	user = user or frappe.session.user
	if user == "Guest" and not guest_access_allowed():
		return False
	if is_super(user):
		return True
	if batch_relation(batch, user):
		return True
	return bool(frappe.db.get_value("LMS Batch", batch, "published"))


def assert_batch_access(batch: str, user: str | None = None) -> None:
	if not can_read_batch(batch, user):
		frappe.throw(_("You do not have access to this batch."), frappe.PermissionError)


def assert_batch_member(batch: str, user: str | None = None) -> None:
	"""Gate for the *inside* of a batch — calendar, chats, roster.

	Published-ness does not open these. Being able to see a cohort advertised is
	not being in it, and every surface that shows what a cohort is *doing* uses
	this rather than :func:`can_read_batch`.
	"""
	user = user or frappe.session.user
	if is_super(user):
		return
	if not batch_relation(batch, user):
		frappe.throw(_("You are not a member of this batch."), frappe.PermissionError)


def visible_batches(user: str | None = None) -> list[str]:
	"""Every batch ``user`` is attached to, in any capacity. The backing list for
	the cross-batch surfaces: a moderator with six cohorts needs one chat
	sidebar and one calendar, not six tabs."""
	user = user or frappe.session.user
	if is_super(user):
		return frappe.get_all("LMS Batch", pluck="name")
	names = set(moderated_batches(user)) | set(staffed_batches(user))
	names |= set(frappe.get_all("LMS Batch Enrollment", filters={"member": user}, pluck="batch"))
	return sorted(names)
