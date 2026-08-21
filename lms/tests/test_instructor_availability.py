# Copyright (c) 2026, FOSS United and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, getdate

from lms.lms.calendar_api import (
	delete_availability,
	get_bookable_instructors,
	get_my_courses_for_availability,
	save_availability,
)
from lms.lms.test_helpers import BaseTestUtils


class TestInstructorAvailability(BaseTestUtils):
	"""Publishing the weekly hours a student can book against.

	This is the booking-link half of the calendar: an instructor sets windows
	per weekday and a slot length, and `calendar_api` divides the windows into
	slots. What the tests below pin down is who may publish hours at all, and
	which schedules are refused before a student ever sees them — a window that
	cannot produce a slot reads to the instructor as "my availability is broken"
	rather than as a mistake they made.
	"""

	USERS = {
		"instructor": ("availability-owner@example.com", ["Course Creator"]),
		"other_instructor": ("availability-other@example.com", ["Course Creator"]),
		"student": ("availability-learner@example.com", ["LMS Student"]),
	}

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		original_in_import = frappe.flags.in_import
		frappe.flags.in_import = True
		try:
			for attr, (email, roles) in cls.USERS.items():
				if not frappe.db.exists("User", email):
					user = frappe.new_doc("User")
					user.update(
						{
							"email": email,
							"first_name": attr,
							"user_type": "Website User",
							"send_welcome_email": False,
						}
					)
					for role in roles:
						user.append("roles", {"role": role})
					user.insert(ignore_permissions=True)
				setattr(cls, attr, frappe._dict(email=email))
		finally:
			frappe.flags.in_import = original_in_import
		frappe.db.commit()

	def setUp(self):
		super().setUp()
		self.original_user = frappe.session.user
		frappe.set_user("Administrator")

		suffix = frappe.generate_hash(length=6)
		self.course = self._create_course(
			title=f"Availability Course {suffix}", instructor=self.instructor.email
		)
		self._create_enrollment(self.student.email, self.course.name)

	def tearDown(self):
		# Before the base class deletes this test's fixtures: the test itself
		# left the session as a student, who may not delete a course.
		frappe.set_user("Administrator")
		super().tearDown()
		frappe.set_user(self.original_user)

	def _save(self, user=None, **overrides):
		frappe.set_user(user or self.instructor.email)
		payload = {
			"course": self.course.name,
			"slot_duration": 30,
			"published": 1,
			"schedule": [{"day": "Monday", "start_time": "10:00:00", "end_time": "12:00:00"}],
		}
		payload.update(overrides)
		result = save_availability(payload)
		self.cleanup_items.append(("LMS Instructor Availability", result["name"]))
		return result["name"]

	# --- who may publish --------------------------------------------------

	def test_an_instructor_publishes_hours_for_their_own_course(self):
		name = self._save()

		doc = frappe.get_doc("LMS Instructor Availability", name)
		self.assertEqual(doc.instructor, self.instructor.email)
		self.assertEqual([row.day for row in doc.schedule], ["Monday"])

	def test_a_student_cannot_publish_hours_for_a_course_they_only_attend(self):
		"""Otherwise anyone enrolled could put themselves in the booking popup's
		instructor list, which reads it straight off this table.

		Stopped one layer earlier than the test below it: LMS Student has no
		create permission on the doctype at all, so the DocPerm check refuses it
		before `validate_instructor_teaches_course` is reached.
		"""
		with self.assertRaises(frappe.PermissionError):
			self._save(user=self.student.email)

	def test_someone_who_does_not_teach_the_course_cannot_publish_against_it(self):
		with self.assertRaises(frappe.ValidationError):
			self._save(user=self.other_instructor.email)

	def test_only_taught_courses_are_offered_to_configure(self):
		frappe.set_user(self.instructor.email)
		self.assertIn(self.course.name, [row.name for row in get_my_courses_for_availability()])

		frappe.set_user(self.student.email)
		self.assertEqual(get_my_courses_for_availability(), [])

	def test_saved_hours_come_back_with_the_course(self):
		"""The modal reloads the saved windows when the instructor switches
		course, so the schedule has to travel with the row."""
		self._save()

		frappe.set_user(self.instructor.email)
		row = next(r for r in get_my_courses_for_availability() if r.name == self.course.name)

		self.assertTrue(row.availability)
		self.assertEqual(row.availability.slot_duration, 30)
		# Time fields come back from the database as timedeltas; the JSON the
		# modal receives is their string form, which is what this compares.
		self.assertEqual([str(slot.start_time) for slot in row.schedule], ["10:00:00"])

	# --- what makes a schedule usable ------------------------------------

	def test_a_window_that_ends_before_it_starts_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			self._save(schedule=[{"day": "Monday", "start_time": "12:00:00", "end_time": "10:00:00"}])

	def test_a_window_shorter_than_one_slot_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			self._save(
				slot_duration=60,
				schedule=[{"day": "Monday", "start_time": "10:00:00", "end_time": "10:30:00"}],
			)

	def test_two_windows_on_the_same_day_may_not_overlap(self):
		with self.assertRaises(frappe.ValidationError):
			self._save(
				schedule=[
					{"day": "Monday", "start_time": "10:00:00", "end_time": "12:00:00"},
					{"day": "Monday", "start_time": "11:00:00", "end_time": "13:00:00"},
				]
			)

	def test_the_same_hours_on_different_days_are_fine(self):
		name = self._save(
			schedule=[
				{"day": "Monday", "start_time": "10:00:00", "end_time": "12:00:00"},
				{"day": "Tuesday", "start_time": "10:00:00", "end_time": "12:00:00"},
			]
		)

		self.assertEqual(len(frappe.get_doc("LMS Instructor Availability", name).schedule), 2)

	def test_an_empty_schedule_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			self._save(schedule=[])

	def test_a_slot_length_outside_the_allowed_range_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			self._save(slot_duration=3)

	def test_a_slot_length_that_is_not_a_multiple_of_five_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			self._save(slot_duration=32)

	def test_time_off_that_ends_before_it_starts_is_rejected(self):
		today = getdate()
		with self.assertRaises(frappe.ValidationError):
			self._save(
				unavailable_from=str(add_days(today, 5)),
				unavailable_to=str(add_days(today, 1)),
			)

	# --- one row per instructor and course --------------------------------

	def test_saving_again_replaces_the_hours_rather_than_adding_a_second_row(self):
		first = self._save()
		second = self._save(
			schedule=[{"day": "Friday", "start_time": "09:00:00", "end_time": "11:00:00"}]
		)

		self.assertEqual(first, second)
		self.assertEqual(
			frappe.db.count(
				"LMS Instructor Availability",
				{"instructor": self.instructor.email, "course": self.course.name},
			),
			1,
		)
		self.assertEqual(
			[row.day for row in frappe.get_doc("LMS Instructor Availability", second).schedule],
			["Friday"],
		)

	def test_withdrawing_hours_takes_the_instructor_out_of_the_booking_list(self):
		self._save()

		frappe.set_user(self.student.email)
		offered = [row.name for row in get_bookable_instructors(self.course.name)]
		self.assertEqual(offered, [self.instructor.email])

		frappe.set_user(self.instructor.email)
		delete_availability(self.course.name)

		frappe.set_user(self.student.email)
		self.assertEqual(get_bookable_instructors(self.course.name), [])
