# Copyright (c) 2026, Frappe and Contributors
# For license information, please see license.txt

"""The roster of a batch — every person attached to it, and how.

This is the moderator's replacement for site-wide user visibility. A moderator
used to reach every user on the site through ``lms.lms.api.get_members``
(``frappe.only_for(["Moderator"])``, unfiltered); that endpoint is now System
Manager only, and this is what a moderator gets instead. Scoping batches while
leaving that door open would have been theatre — a moderator locked out of a
batch could still have enumerated its students through Settings.
"""

from __future__ import annotations

import frappe
from frappe import _

from lms.lms.batch_access import (
	assert_batch_member,
	assert_batch_moderator,
	batch_evaluators,
	batch_instructors,
	batch_moderators,
	is_batch_moderator,
	visible_batches,
)

PERSON_FIELDS = ["name", "full_name", "user_image", "username", "enabled", "last_active"]

#: Ordered as the roster should read: who runs it, who teaches it, then who takes it.
RELATION_ORDER = {"moderator": 0, "instructor": 1, "evaluator": 2, "student": 3}


def _people(emails: set[str]) -> dict[str, dict]:
	if not emails:
		return {}
	rows = frappe.get_all(
		"User",
		filters={"name": ["in", sorted(emails)]},
		fields=PERSON_FIELDS,
	)
	return {row.name: row for row in rows}


@frappe.whitelist()
def get_batch_people(batch: str) -> list[dict]:
	"""Everyone attached to ``batch``, each with their relation to it.

	Readable by any member of the batch — an instructor needs to know who is in
	the room. The administrative details (whether an invitation is still
	outstanding, when someone last signed in) are added only for a moderator,
	because they are the answer to "why can this person not get in", which is not
	a question a fellow student gets to ask about somebody else.
	"""
	assert_batch_member(batch)
	moderator_view = is_batch_moderator(batch)

	relations: dict[str, str] = {}
	# Assigned least- to most-privileged so the strongest attachment wins: a
	# moderator who is also enrolled reads as a moderator, matching batch_relation.
	for member in frappe.get_all("LMS Batch Enrollment", filters={"batch": batch}, pluck="member"):
		relations[member] = "student"
	for user in batch_evaluators(batch):
		relations[user] = "evaluator"
	for user in batch_instructors(batch):
		relations[user] = "instructor"
	for user in batch_moderators(batch):
		relations[user] = "moderator"

	people = _people(set(relations))
	enrollments = {
		row.member: row
		for row in frappe.get_all(
			"LMS Batch Enrollment",
			filters={"batch": batch},
			fields=["member", "name", "creation", "payment", "confirmation_email_sent"],
		)
	}

	rows = []
	for email, relation in relations.items():
		person = people.get(email)
		if not person:
			# A Course Instructor or Batch Moderator row can outlive the User it
			# names. Skipping keeps a deleted account from rendering as a blank row.
			continue
		row = {
			"user": email,
			"full_name": person.full_name or email,
			"user_image": person.user_image,
			"username": person.username,
			"relation": relation,
			"enrolled_on": enrollments.get(email, {}).get("creation"),
		}
		if moderator_view:
			row.update(
				{
					"enabled": bool(person.enabled),
					"last_active": person.last_active,
					"never_signed_in": not person.last_active,
					"must_reset_password": bool(frappe.db.get_value("User", email, "must_reset_password")),
					"enrollment": enrollments.get(email, {}).get("name"),
					"confirmation_email_sent": bool(
						enrollments.get(email, {}).get("confirmation_email_sent")
					),
				}
			)
		rows.append(row)

	rows.sort(key=lambda r: (RELATION_ORDER.get(r["relation"], 9), (r["full_name"] or "").lower()))
	return rows


@frappe.whitelist()
def get_my_people() -> list[dict]:
	"""The cross-batch roster: every person in every batch the caller moderates,
	deduplicated, each carrying the batches they appear in.

	A moderator with six cohorts has one list of people, not six. A student
	enrolled in two of those cohorts is one person listed once.
	"""
	batches = [b for b in visible_batches() if is_batch_moderator(b)]
	if not batches:
		return []

	titles = {
		row.name: row.title
		for row in frappe.get_all("LMS Batch", filters={"name": ["in", batches]}, fields=["name", "title"])
	}

	merged: dict[str, dict] = {}
	for batch in batches:
		for row in get_batch_people(batch):
			entry = merged.setdefault(
				row["user"],
				{**row, "batches": []},
			)
			entry["batches"].append(
				{"batch": batch, "title": titles.get(batch, batch), "relation": row["relation"]}
			)
			# Across batches keep the strongest relation, same rule as within one.
			if RELATION_ORDER.get(row["relation"], 9) < RELATION_ORDER.get(entry["relation"], 9):
				entry["relation"] = row["relation"]

	rows = list(merged.values())
	rows.sort(key=lambda r: (RELATION_ORDER.get(r["relation"], 9), (r["full_name"] or "").lower()))
	return rows


@frappe.whitelist()
def remove_from_batch(batch: str, user: str) -> None:
	"""Unenroll a student. Moderators of this batch only.

	Only students: instructors and evaluators are derived from the curriculum, so
	there is no row here to delete — removing them means changing the courses in
	the batch or the staff on those courses, which is a different action in a
	different place.
	"""
	assert_batch_moderator(batch)

	enrollment = frappe.db.exists("LMS Batch Enrollment", {"batch": batch, "member": user})
	if not enrollment:
		frappe.throw(
			_("{0} is not enrolled in this batch.").format(user),
			frappe.DoesNotExistError,
		)

	frappe.delete_doc("LMS Batch Enrollment", enrollment, ignore_permissions=True)
