# Copyright (c) 2026, FOSS United and Contributors
# See license.txt

"""`get_all_users` must not be a site-wide address book.

`User.name` IS the email address and `frappe.get_all` has no default limit, so
before this guard any holder of Course Creator or Batch Evaluator -- roles an
authoring user is given without an administrator's involvement -- could read
every enabled account's email from one call.
"""

import frappe

from lms.lms.api import get_all_users
from lms.lms.test_helpers import BaseTestUtils

# Fixed rather than randomised, and never torn down. Frappe throttles `User`
# creation site-wide (60/hour in core), so a suite that mints and deletes an
# account per test spends that budget on behalf of every other suite.
INSTRUCTOR = "dir-instructor@fixtures.test"
CLASSMATE = "dir-classmate@fixtures.test"
OUTSIDER = "dir-outsider@fixtures.test"
OTHER_INSTRUCTOR = "dir-other-instructor@fixtures.test"
COURSE_STUDENT = "dir-course-student@fixtures.test"
FAR_STUDENT = "dir-far-student@fixtures.test"


class TestUserDirectoryScope(BaseTestUtils):
	def setUp(self):
		super().setUp()
		# `_create_user_with_exact_roles`, not `_create_user`: a reused account
		# keeps whatever roles it was born with, and "an instructor cannot see
		# this person" must not pass or fail on the history of the site.
		make = self._create_user_with_exact_roles

		# Batch A: the instructor teaches it and one student is enrolled.
		self.instructor = make(INSTRUCTOR, "Ida", "Instructor", ["Course Creator"]).name
		self.classmate = make(CLASSMATE, "Cal", "Classmate", ["LMS Student"]).name
		# Batch B: a different cohort the instructor has nothing to do with.
		self.outsider = make(OUTSIDER, "Otto", "Outsider", ["LMS Student"]).name
		self.other_instructor = make(OTHER_INSTRUCTOR, "Ivo", "Other", ["Course Creator"]).name
		# Course-only, no batch anywhere near them.
		self.course_student = make(COURSE_STUDENT, "Cora", "Coursemate", ["LMS Student"]).name
		self.far_student = make(FAR_STUDENT, "Fay", "Faraway", ["LMS Student"]).name
		# Accounts outlive the test; the batches and enrolments do not, so a
		# leftover membership can never quietly widen the audience under test.
		self.cleanup_items = [i for i in self.cleanup_items if i[0] != "User"]

		course_a = self._create_course(title="Dir Course A", instructor=self.instructor)
		batch_a = self._create_batch(
			course_a.name,
			instructor=self.instructor,
			title="Dir Batch A",
			evaluator=self._create_evaluator(self.instructor).name,
		)
		self._create_batch_enrollment(self.classmate, batch_a.name)

		course_b = self._create_course(title="Dir Course B", instructor=self.other_instructor)
		batch_b = self._create_batch(
			course_b.name,
			instructor=self.other_instructor,
			title="Dir Batch B",
			evaluator=self._create_evaluator(self.other_instructor).name,
		)
		self._create_batch_enrollment(self.outsider, batch_b.name)

		# A course with no batch at all -- the shape a lesson discussion runs on,
		# and the one batch-only scoping would have left the picker empty for.
		course_c = self._create_course(title="Dir Course C", instructor=self.instructor)
		self._create_enrollment(self.course_student, course_c.name)
		course_d = self._create_course(title="Dir Course D", instructor=self.other_instructor)
		self._create_enrollment(self.far_student, course_d.name)

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def _as(self, user):
		frappe.set_user(user)
		return get_all_users()

	def test_an_instructor_sees_the_people_in_their_own_batch(self):
		self.assertIn(self.classmate, self._as(self.instructor))

	def test_an_instructor_does_not_see_a_student_from_another_batch(self):
		# The whole point: `outsider` is an enabled account the caller shares
		# nothing with, and their email is not the caller's to read.
		self.assertNotIn(self.outsider, self._as(self.instructor))

	def test_an_instructor_does_not_see_an_unrelated_instructor(self):
		self.assertNotIn(self.other_instructor, self._as(self.instructor))

	def test_an_instructor_sees_students_of_a_course_that_has_no_batch(self):
		# `Discussions.vue` mounts against `Course Lesson` as well as `LMS Batch`,
		# so a course-only site must still have a working mention picker.
		self.assertIn(self.course_student, self._as(self.instructor))

	def test_an_instructor_does_not_see_a_student_of_someone_elses_course(self):
		self.assertNotIn(self.far_student, self._as(self.instructor))

	def test_the_caller_is_still_offered(self):
		# A mention picker that cannot name its own user would be a silent
		# change to what the picker used to offer.
		self.assertIn(self.instructor, self._as(self.instructor))

	def test_the_built_in_accounts_are_never_people(self):
		listing = self._as(self.instructor)
		self.assertNotIn("Guest", listing)
		self.assertNotIn("Administrator", listing)

	def test_a_system_manager_keeps_the_site_wide_directory(self):
		# Administering the user table is that role's job, and it cannot be
		# self-assigned -- so the wide list stays available to exactly it.
		listing = self._as("Administrator")
		self.assertIn(self.outsider, listing)
		self.assertIn(self.classmate, listing)

	def test_a_student_is_still_refused_outright(self):
		frappe.set_user(self.classmate)
		with self.assertRaises(frappe.PermissionError):
			get_all_users()

	def test_every_entry_still_carries_what_the_picker_renders(self):
		for email, row in self._as(self.instructor).items():
			self.assertEqual(row.name, email)
			self.assertIn("full_name", row)
			self.assertIn("user_image", row)
