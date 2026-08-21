# Copyright (c) 2026, FOSS United and Contributors
# See license.txt

from unittest.mock import patch

import frappe

from lms.lms.course_creation import submit_course_for_review
from lms.lms.course_review import (
	can_review_courses,
	course_instructors,
	get_review_queue,
	get_review_state,
	review_course,
	reviewers,
)
from lms.lms.test_helpers import BaseTestUtils


class TestCourseReview(BaseTestUtils):
	"""The moderator → instructor → reviewer handoff.

	Approving a course publishes it, so every test here is really about one
	question: who can put a course in front of learners, and on what evidence.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# The worktree's new fields reach the test site's schema only via
		# reload_doctype; bench migrate cannot see this worktree.
		frappe.reload_doctype("LMS Course")

	def setUp(self):
		super().setUp()
		self.author = self._create_user_with_exact_roles(
			"review-author@example.com", "Rev", "Author", ["Course Creator"]
		)
		self.moderator = self._create_user_with_exact_roles(
			"review-mod@example.com", "Rev", "Mod", ["Course Creator", "Moderator"]
		)
		self.evaluator = self._create_user_with_exact_roles(
			"review-eval@example.com", "Rev", "Eval", ["Batch Evaluator"]
		)
		self.student = self._create_user_with_exact_roles(
			"review-student@example.com", "Rev", "Student", ["LMS Student"]
		)

		self.course = self._create_course(title="Review Course", instructor=self.author.email)
		self._submit()

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def _submit(self):
		"""Put the course in the queue, as submit_course_for_review would."""
		frappe.db.set_value(
			"LMS Course",
			self.course.name,
			{
				"status": "Under Review",
				"submitted_on": frappe.utils.now(),
				"published": 0,
				"review_feedback": None,
			},
		)

	def _status(self):
		return frappe.db.get_value(
			"LMS Course",
			self.course.name,
			["status", "published", "review_feedback", "submitted_on", "reviewed_by"],
			as_dict=True,
		)

	# -- who may review ---------------------------------------------------

	def test_a_moderator_may_review(self):
		frappe.set_user(self.moderator.email)
		self.assertTrue(can_review_courses())

	def test_an_evaluator_may_review(self):
		frappe.set_user(self.evaluator.email)
		self.assertTrue(can_review_courses())

	# The author builds the course; letting them approve it would make the
	# review a formality they can skip.
	def test_a_course_author_may_not_review(self):
		frappe.set_user(self.author.email)
		self.assertFalse(can_review_courses())
		with self.assertRaises(frappe.PermissionError):
			review_course(self.course.name, "approve")

	def test_a_student_may_not_review(self):
		frappe.set_user(self.student.email)
		with self.assertRaises(frappe.PermissionError):
			review_course(self.course.name, "approve")

	def test_a_student_may_not_read_the_queue(self):
		frappe.set_user(self.student.email)
		with self.assertRaises(frappe.PermissionError):
			get_review_queue()

	def test_the_reviewer_list_excludes_guest_and_administrator(self):
		frappe.set_user("Administrator")
		everyone = reviewers()
		self.assertNotIn("Administrator", everyone)
		self.assertNotIn("Guest", everyone)
		self.assertIn(self.evaluator.email, everyone)

	# Someone holding both roles would otherwise be notified twice per submission.
	def test_the_reviewer_list_is_deduped(self):
		frappe.set_user("Administrator")
		everyone = reviewers()
		self.assertEqual(len(everyone), len(set(everyone)))
		self.assertIn(self.moderator.email, everyone)

	# -- the queue --------------------------------------------------------

	def test_the_queue_holds_the_submitted_course(self):
		frappe.set_user(self.evaluator.email)
		queued = {row["name"] for row in get_review_queue()}
		self.assertIn(self.course.name, queued)

	def test_the_queue_names_the_instructors(self):
		frappe.set_user(self.evaluator.email)
		row = next(r for r in get_review_queue() if r["name"] == self.course.name)
		self.assertIn(self.author.email, [i["name"] for i in row["instructors"]])

	def test_an_approved_course_leaves_the_queue(self):
		frappe.set_user(self.moderator.email)
		review_course(self.course.name, "approve")
		self.assertNotIn(self.course.name, {row["name"] for row in get_review_queue()})

	# -- approving --------------------------------------------------------

	def test_approving_publishes(self):
		frappe.set_user(self.moderator.email)
		review_course(self.course.name, "approve")
		status = self._status()
		self.assertEqual(status.status, "Approved")
		self.assertEqual(status.published, 1)
		self.assertEqual(status.reviewed_by, self.moderator.email)

	def test_an_evaluator_can_publish_too(self):
		frappe.set_user(self.evaluator.email)
		review_course(self.course.name, "approve")
		self.assertEqual(self._status().published, 1)

	# -- sending back -----------------------------------------------------

	# "Sent back" with nothing attached leaves the instructor guessing at what
	# the reviewer objected to, which is the failure this step exists to avoid.
	def test_sending_back_without_a_reason_is_refused(self):
		frappe.set_user(self.moderator.email)
		with self.assertRaises(frappe.ValidationError):
			review_course(self.course.name, "reject")
		with self.assertRaises(frappe.ValidationError):
			review_course(self.course.name, "reject", "   ")
		# Refused, not half-applied.
		self.assertEqual(self._status().status, "Under Review")

	def test_sending_back_returns_the_course_with_its_reason(self):
		frappe.set_user(self.moderator.email)
		review_course(self.course.name, "reject", "Section 3 has no assessment.")
		status = self._status()
		self.assertEqual(status.status, "In Progress")
		self.assertEqual(status.published, 0)
		self.assertIsNone(status.submitted_on)
		self.assertEqual(status.review_feedback, "Section 3 has no assessment.")

	# The previous round's notes describe a version that no longer exists;
	# leaving them up would show the course as rejected while it sits in the queue.
	def test_resubmitting_clears_the_previous_notes(self):
		frappe.set_user(self.moderator.email)
		review_course(self.course.name, "reject", "Needs more lectures.")
		self.assertEqual(self._status().review_feedback, "Needs more lectures.")

		# The real endpoint, with its readiness gate stubbed: what is under test
		# is that resubmission wipes the notes, not what makes a course ready.
		# Building a submittable course here (5 lectures, 30 minutes of video, an
		# image) would test the thresholds instead.
		frappe.set_user(self.author.email)
		ready = {"blockers": [], "status": "In Progress"}
		with patch("lms.lms.course_creation.get_course_creation_status", return_value=ready):
			submit_course_for_review(self.course.name)

		status = self._status()
		self.assertEqual(status.status, "Under Review")
		self.assertIsNone(status.review_feedback)
		self.assertIsNotNone(status.submitted_on)

	def test_submitting_notifies_the_reviewers(self):
		frappe.set_user(self.moderator.email)
		review_course(self.course.name, "reject", "Needs more lectures.")

		frappe.set_user(self.author.email)
		ready = {"blockers": [], "status": "In Progress"}
		with patch("lms.lms.course_creation.get_course_creation_status", return_value=ready):
			submit_course_for_review(self.course.name)

		told = frappe.get_all(
			"Notification Log",
			filters={"document_type": "LMS Course", "document_name": self.course.name},
			pluck="for_user",
		)
		self.assertIn(self.evaluator.email, told)

	# Nobody needs telling about their own action, and a self-notification in the
	# bell reads as something to act on.
	def test_a_reviewer_is_not_notified_of_their_own_decision(self):
		frappe.set_user(self.moderator.email)
		review_course(self.course.name, "reject", "Needs more lectures.")
		told = frappe.get_all(
			"Notification Log",
			filters={"document_type": "LMS Course", "document_name": self.course.name},
			pluck="for_user",
		)
		self.assertIn(self.author.email, told)
		self.assertNotIn(self.moderator.email, told)

	def test_a_course_not_in_the_queue_cannot_be_reviewed(self):
		frappe.set_user(self.moderator.email)
		review_course(self.course.name, "approve")
		with self.assertRaises(frappe.ValidationError):
			review_course(self.course.name, "approve")

	# -- reading the state ------------------------------------------------

	# get_course_creation_status enforces edit access, so a reviewer who is
	# neither moderator-on-this-course nor instructor would be refused the answer
	# to the decision they just made. This is the reason get_review_state exists.
	def test_a_reviewer_can_read_the_state_without_edit_rights(self):
		frappe.set_user(self.evaluator.email)
		state = get_review_state(self.course.name)
		self.assertEqual(state["status"], "Under Review")
		self.assertTrue(state["can_review"])

	def test_an_instructor_can_read_the_state(self):
		frappe.set_user(self.author.email)
		state = get_review_state(self.course.name)
		self.assertEqual(state["name"], self.course.name)
		self.assertFalse(state["can_review"])

	def test_a_stranger_cannot_read_the_state(self):
		frappe.set_user(self.student.email)
		with self.assertRaises(frappe.PermissionError):
			get_review_state(self.course.name)

	def test_course_instructors_lists_the_author(self):
		frappe.set_user("Administrator")
		self.assertIn(self.author.email, course_instructors(self.course.name))
