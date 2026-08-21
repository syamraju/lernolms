# Copyright (c) 2026, Frappe and Contributors
# For license information, please see license.txt

"""The batch scoping rules, exercised as use cases.

Each test names the situation it protects rather than the function it calls:
these are the operational structure from ``docs/design/batches.md``, and a
refactor that keeps the functions but breaks the situations has broken the
feature.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from lms.lms.batch_access import (
	batch_evaluators,
	batch_instructors,
	batch_relation,
	can_read_batch,
	is_batch_moderator,
	moderated_batches,
	staffed_batches,
	visible_batches,
)


def _user(email: str, roles: list[str] | None = None) -> str:
	if frappe.db.exists("User", email):
		frappe.delete_doc("User", email, force=True, ignore_permissions=True)
	doc = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": email.split("@")[0],
			"send_welcome_email": 0,
		}
	)
	doc.insert(ignore_permissions=True)
	for role in roles or []:
		doc.append("roles", {"role": role})
	if roles:
		doc.save(ignore_permissions=True)
	return doc.name


def _batch(title: str, owner: str, **kwargs) -> str:
	"""A minimally valid LMS Batch. `instructors` is mandatory on the doctype, so
	a batch cannot be created with an empty staff list — the owner stands in."""
	instructors = kwargs.pop("instructors", [{"instructor": owner}])
	doc = frappe.get_doc(
		{
			"doctype": "LMS Batch",
			"title": title,
			"start_date": "2026-09-01",
			"end_date": "2026-10-01",
			"start_time": "10:00:00",
			"end_time": "12:00:00",
			"timezone": "Asia/Kolkata",
			"description": title,
			"batch_details": f"<p>{title}</p>",
			"instructors": instructors,
			"published": kwargs.pop("published", 0),
			**kwargs,
		}
	)
	# Inserted *as* the owner rather than stamped afterwards. `owner` is written by
	# set_user_and_timestamp() from the session, and `before_insert` seeds the
	# moderators row from it — patching `owner` after the fact leaves the row
	# naming whoever ran the test instead of the batch's creator.
	original = frappe.session.user
	frappe.set_user(owner)
	try:
		doc.insert(ignore_permissions=True)
	finally:
		frappe.set_user(original)
	return doc.name


class TestBatchModeratorScoping(FrappeTestCase):
	"""A moderator reaches their own batches and no others."""

	def setUp(self):
		self.alice = _user("scope-alice@example.com", ["Moderator"])
		self.bob = _user("scope-bob@example.com", ["Moderator"])
		self.alice_batch = _batch("Alice Cohort", self.alice)
		self.bob_batch = _batch("Bob Cohort", self.bob)

	def test_creator_is_a_moderator_without_being_added(self):
		self.assertTrue(is_batch_moderator(self.alice_batch, self.alice))

	def test_moderator_role_alone_does_not_reach_another_batch(self):
		"""The regression this whole change exists for: holding `Moderator`
		used to mean every batch on the site."""
		self.assertTrue("Moderator" in frappe.get_roles(self.bob))
		self.assertFalse(is_batch_moderator(self.alice_batch, self.bob))

	def test_moderated_batches_lists_only_own(self):
		self.assertIn(self.alice_batch, moderated_batches(self.alice))
		self.assertNotIn(self.bob_batch, moderated_batches(self.alice))
		self.assertIn(self.bob_batch, moderated_batches(self.bob))
		self.assertNotIn(self.alice_batch, moderated_batches(self.bob))

	def test_added_moderator_reaches_the_batch(self):
		doc = frappe.get_doc("LMS Batch", self.alice_batch)
		doc.append("moderators", {"moderator": self.bob})
		doc.save(ignore_permissions=True)

		self.assertTrue(is_batch_moderator(self.alice_batch, self.bob))
		self.assertIn(self.alice_batch, moderated_batches(self.bob))
		self.assertIn(self.bob_batch, moderated_batches(self.bob))

	def test_one_moderator_holds_many_batches(self):
		second = _batch("Alice Second Cohort", self.alice)
		held = moderated_batches(self.alice)
		self.assertIn(self.alice_batch, held)
		self.assertIn(second, held)
		self.assertNotIn(self.bob_batch, held)


class TestCreatorCannotBeRemoved(FrappeTestCase):
	"""Equal rights for all moderators; the creator is the one immovable row."""

	def setUp(self):
		self.creator = _user("immovable-creator@example.com", ["Moderator"])
		self.peer = _user("immovable-peer@example.com", ["Moderator"])
		self.batch = _batch("Immovable Cohort", self.creator)
		doc = frappe.get_doc("LMS Batch", self.batch)
		doc.append("moderators", {"moderator": self.peer})
		doc.save(ignore_permissions=True)

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_peer_can_be_removed(self):
		frappe.set_user(self.peer)
		doc = frappe.get_doc("LMS Batch", self.batch)
		doc.moderators = [row for row in doc.moderators if row.moderator != self.peer]
		doc.save(ignore_permissions=True)
		self.assertFalse(is_batch_moderator(self.batch, self.peer))

	def test_creator_cannot_be_removed(self):
		"""As a peer, not as Administrator.

		System Manager is exempt from this rule — that exemption is the escape
		hatch for a creator who has left the organisation — and the test suite runs
		as Administrator, so asserting this as the default user would pass
		vacuously no matter what validate_moderators did.
		"""
		frappe.set_user(self.peer)
		doc = frappe.get_doc("LMS Batch", self.batch)
		doc.moderators = [row for row in doc.moderators if row.moderator != self.creator]
		with self.assertRaises(frappe.ValidationError):
			doc.save(ignore_permissions=True)

	def test_a_super_role_may_remove_the_creator_row(self):
		"""The escape hatch, asserted rather than assumed."""
		doc = frappe.get_doc("LMS Batch", self.batch)
		doc.moderators = [row for row in doc.moderators if row.moderator != self.creator]
		doc.save(ignore_permissions=True)  # session user is Administrator

	def test_creator_stays_a_moderator_even_if_the_row_is_gone(self):
		"""batch_moderators unions the owner in rather than trusting validate.

		A permission check must not depend on a validation a direct db write can
		step around, so the row is deleted underneath the doc here on purpose.
		"""
		frappe.db.delete(
			"Batch Moderator",
			{"parent": self.batch, "parenttype": "LMS Batch", "moderator": self.creator},
		)
		self.assertTrue(is_batch_moderator(self.batch, self.creator))

	def test_duplicate_moderator_rows_are_rejected(self):
		frappe.set_user(self.peer)
		doc = frappe.get_doc("LMS Batch", self.batch)
		doc.append("moderators", {"moderator": self.peer})
		with self.assertRaises(frappe.ValidationError):
			doc.save(ignore_permissions=True)


class TestDerivedStaff(FrappeTestCase):
	"""Instructors and evaluators come from the curriculum, not from a copy."""

	def setUp(self):
		self.owner = _user("derive-owner@example.com", ["Moderator"])
		self.instructor = _user("derive-instructor@example.com", ["Course Creator"])
		self.evaluator = _user("derive-evaluator@example.com", ["Batch Evaluator"])

		if not frappe.db.exists("Course Evaluator", self.evaluator):
			frappe.get_doc({"doctype": "Course Evaluator", "evaluator": self.evaluator}).insert(
				ignore_permissions=True
			)

		course = frappe.get_doc(
			{
				"doctype": "LMS Course",
				"title": "Derived Staff Course",
				"short_introduction": "x",
				"description": "x",
				"evaluator": self.evaluator,
			}
		)
		course.append("instructors", {"instructor": self.instructor})
		course.insert(ignore_permissions=True)
		self.course = course.name

		self.batch = _batch("Derived Cohort", self.owner)

	def test_batch_with_no_courses_derives_nobody(self):
		"""`instructors` is mandatory on LMS Batch, so the owner is always in the
		direct list. The claim is that nothing is *derived* without a curriculum."""
		self.assertNotIn(self.instructor, batch_instructors(self.batch))
		self.assertEqual(batch_evaluators(self.batch), set())

	def test_adding_a_course_pulls_its_staff_onto_the_batch(self):
		"""The reason staff is derived rather than stored: nobody edits a second
		list, and the two cannot drift."""
		doc = frappe.get_doc("LMS Batch", self.batch)
		doc.append("courses", {"course": self.course})
		doc.save(ignore_permissions=True)

		self.assertIn(self.instructor, batch_instructors(self.batch))
		self.assertIn(self.evaluator, batch_evaluators(self.batch))
		self.assertEqual(batch_relation(self.batch, self.instructor), "instructor")
		self.assertEqual(batch_relation(self.batch, self.evaluator), "evaluator")

	def test_staffed_batches_is_the_reverse_lookup(self):
		doc = frappe.get_doc("LMS Batch", self.batch)
		doc.append("courses", {"course": self.course})
		doc.save(ignore_permissions=True)

		self.assertIn(self.batch, staffed_batches(self.instructor))
		self.assertIn(self.batch, staffed_batches(self.evaluator))

	def test_direct_batch_instructor_survives_alongside_derived(self):
		"""A seminar batch has no courses and still needs someone to run it."""
		doc = frappe.get_doc("LMS Batch", self.batch)
		doc.append("instructors", {"instructor": self.instructor})
		doc.save(ignore_permissions=True)

		self.assertIn(self.instructor, batch_instructors(self.batch))
		self.assertIn(self.batch, staffed_batches(self.instructor))


class TestBatchReadVersusAdminister(FrappeTestCase):
	"""Read is broad; administering is narrow."""

	def setUp(self):
		self.owner = _user("visible-owner@example.com", ["Moderator"])
		self.outsider = _user("visible-outsider@example.com", ["Moderator"])
		self.student = _user("visible-student@example.com", ["LMS Student"])
		self.published = _batch("Published Cohort", self.owner, published=1, allow_self_enrollment=1)
		self.private = _batch("Private Cohort", self.owner)

	def test_a_published_batch_is_readable_by_anyone(self):
		"""A moderator must not see less of the catalogue than a guest does."""
		self.assertTrue(can_read_batch(self.published, self.outsider))
		self.assertTrue(can_read_batch(self.published, self.student))

	def test_an_unpublished_batch_is_not_readable_by_an_outsider(self):
		self.assertFalse(can_read_batch(self.private, self.outsider))
		self.assertFalse(can_read_batch(self.private, self.student))

	def test_reading_a_published_batch_is_not_moderating_it(self):
		self.assertTrue(can_read_batch(self.published, self.outsider))
		self.assertFalse(is_batch_moderator(self.published, self.outsider))

	def test_visible_batches_unions_every_attachment(self):
		frappe.get_doc(
			{"doctype": "LMS Batch Enrollment", "batch": self.published, "member": self.student}
		).insert(ignore_permissions=True)
		self.assertIn(self.published, visible_batches(self.student))
		self.assertNotIn(self.private, visible_batches(self.student))
		owned = visible_batches(self.owner)
		self.assertIn(self.published, owned)
		self.assertIn(self.private, owned)
		self.assertNotIn(self.private, visible_batches(self.outsider))
