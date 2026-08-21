# Copyright (c) 2026, Frappe and Contributors
# For license information, please see license.txt

"""The roster: who appears in a batch, how they are labelled, and who may act.

The load-bearing case is the last class here — a moderator locked out of a batch
must not be able to enumerate its students through the site-wide members
endpoint, or scoping batches was theatre.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from lms.lms.batch_people import get_batch_people, get_my_people, remove_from_batch
from lms.lms.test_batch_access import _batch, _user


class PeopleTestCase(FrappeTestCase):
	def setUp(self):
		self.moderator = _user(self.mod_email, ["Moderator"])
		self.batch = _batch(self.batch_title, self.moderator)
		frappe.set_user(self.moderator)

	def tearDown(self):
		frappe.set_user("Administrator")

	def _enrol(self, email, batch=None):
		user = _user(email, ["LMS Student"])
		frappe.set_user(self.moderator)
		frappe.get_doc(
			{"doctype": "LMS Batch Enrollment", "batch": batch or self.batch, "member": user}
		).insert(ignore_permissions=True)
		return user

	def _by_user(self, rows):
		return {row["user"]: row for row in rows}


class TestTheRoster(PeopleTestCase):
	mod_email = "people-roster-mod@example.com"
	batch_title = "People Roster Cohort"

	def test_students_and_the_moderator_both_appear(self):
		student = self._enrol("people-roster-student@example.com")
		rows = self._by_user(get_batch_people(self.batch))

		self.assertEqual(rows[student]["relation"], "student")
		self.assertEqual(rows[self.moderator]["relation"], "moderator")

	def test_the_strongest_attachment_wins(self):
		"""A moderator who is also enrolled reads as a moderator, matching
		batch_relation — otherwise the same person is labelled two ways depending
		on which list is consulted."""
		frappe.get_doc(
			{"doctype": "LMS Batch Enrollment", "batch": self.batch, "member": self.moderator}
		).insert(ignore_permissions=True)

		rows = self._by_user(get_batch_people(self.batch))
		self.assertEqual(rows[self.moderator]["relation"], "moderator")

	def test_the_roster_reads_top_down(self):
		self._enrol("people-roster-order@example.com")
		relations = [row["relation"] for row in get_batch_people(self.batch)]
		self.assertEqual(relations, sorted(relations, key=lambda r: {"moderator": 0, "instructor": 1, "evaluator": 2, "student": 3}[r]))

	def test_a_student_does_not_see_administrative_columns(self):
		"""'Why can this person not get in' is not a question one student gets to
		ask about another."""
		student = self._enrol("people-roster-nosy@example.com")
		other = self._enrol("people-roster-other@example.com")

		frappe.set_user(student)
		rows = self._by_user(get_batch_people(self.batch))

		self.assertIn(other, rows)
		self.assertNotIn("must_reset_password", rows[other])
		self.assertNotIn("last_active", rows[other])

	def test_a_moderator_sees_whether_an_invitation_is_outstanding(self):
		student = self._enrol("people-roster-pending@example.com")
		frappe.db.set_value("User", student, "must_reset_password", 1)

		frappe.set_user(self.moderator)
		rows = self._by_user(get_batch_people(self.batch))
		self.assertTrue(rows[student]["must_reset_password"])


class TestRemoval(PeopleTestCase):
	mod_email = "people-remove-mod@example.com"
	batch_title = "People Remove Cohort"

	def test_a_moderator_can_unenrol_a_student(self):
		student = self._enrol("people-remove-student@example.com")
		remove_from_batch(self.batch, student)

		self.assertFalse(
			frappe.db.exists("LMS Batch Enrollment", {"batch": self.batch, "member": student})
		)

	def test_removing_somebody_who_is_not_enrolled_says_so(self):
		stranger = _user("people-remove-stranger@example.com", ["LMS Student"])
		frappe.set_user(self.moderator)

		with self.assertRaises(frappe.DoesNotExistError):
			remove_from_batch(self.batch, stranger)

	def test_a_student_cannot_unenrol_anybody(self):
		student = self._enrol("people-remove-actor@example.com")
		victim = self._enrol("people-remove-victim@example.com")

		frappe.set_user(student)
		with self.assertRaises(frappe.PermissionError):
			remove_from_batch(self.batch, victim)

	def test_a_moderator_of_another_batch_cannot_unenrol(self):
		student = self._enrol("people-remove-guarded@example.com")
		outsider = _user("people-remove-outsider@example.com", ["Moderator"])

		frappe.set_user(outsider)
		with self.assertRaises(frappe.PermissionError):
			remove_from_batch(self.batch, student)


class TestCrossBatchRoster(PeopleTestCase):
	mod_email = "people-cross-mod@example.com"
	batch_title = "People Cross Cohort"

	def test_one_person_in_two_batches_is_listed_once(self):
		second = _batch("People Cross Second", self.moderator)
		student = self._enrol("people-cross-student@example.com")
		frappe.get_doc(
			{"doctype": "LMS Batch Enrollment", "batch": second, "member": student}
		).insert(ignore_permissions=True)

		frappe.set_user(self.moderator)
		rows = [row for row in get_my_people() if row["user"] == student]

		self.assertEqual(len(rows), 1)
		self.assertEqual(
			{entry["batch"] for entry in rows[0]["batches"]}, {self.batch, second}
		)

	def test_a_batch_the_caller_only_studies_in_is_not_included(self):
		"""get_my_people is the moderator's roster. Being a student somewhere does
		not put that cohort's classmates on your list."""
		other_mod = _user("people-cross-othermod@example.com", ["Moderator"])
		other = _batch("People Cross Other", other_mod)
		classmate = _user("people-cross-classmate@example.com", ["LMS Student"])

		# Enrol as that batch's own moderator: a closed batch refuses enrollments
		# pushed by somebody who does not run it, which is the rule under test in
		# test_batch_invite and would fail here for the right reason.
		frappe.set_user(other_mod)
		for member in (self.moderator, classmate):
			frappe.get_doc(
				{"doctype": "LMS Batch Enrollment", "batch": other, "member": member}
			).insert(ignore_permissions=True)

		frappe.set_user(self.moderator)
		self.assertNotIn(classmate, {row["user"] for row in get_my_people()})


class TestTheSiteWideDoorIsShut(PeopleTestCase):
	mod_email = "people-door-mod@example.com"
	batch_title = "People Door Cohort"

	def test_a_moderator_cannot_enumerate_the_whole_site(self):
		"""Scoping batches while leaving get_members open to Moderator would have
		been theatre: a moderator locked out of a batch could still have listed
		its students through Settings."""
		from lms.lms.api import get_members

		frappe.set_user(self.moderator)
		with self.assertRaises(frappe.PermissionError):
			get_members()

	def test_a_system_manager_still_can(self):
		from lms.lms.api import get_members

		frappe.set_user("Administrator")
		self.assertIsNotNone(get_members())
