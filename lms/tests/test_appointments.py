# Copyright (c) 2026, FOSS United and Contributors
# See license.txt

import frappe
from frappe.utils import add_days, getdate

from lms.lms.calendar_api import (
	book_appointment,
	cancel_appointment,
	get_available_slots,
	get_bookable_courses,
	get_bookable_instructors,
	get_my_appointments,
	save_availability,
)
from lms.lms.test_helpers import BaseTestUtils

# The window every test books against. 10:00–12:00 in 30-minute slots is four
# slots: 10:00, 10:30, 11:00 and 11:30.
WINDOW_START = "10:00:00"
WINDOW_END = "12:00:00"
SLOT_MINUTES = 30


class TestAppointments(BaseTestUtils):
	"""Booking a one-to-one against an instructor's published hours.

	The rule the whole feature rests on is exclusivity: a slot that one student
	takes must stop being available to everyone else, and must come back if the
	booking is cancelled. `LMSAppointment` is the authority — `calendar_api`
	only subtracts booked slots so the UI does not offer them — so these tests
	go through the API the way the popup does, and assert on what the controller
	allows rather than on what the list happened to show.
	"""

	USERS = {
		"instructor": ("appointment-instructor@example.com", ["Course Creator"]),
		"student": ("appointment-student@example.com", ["LMS Student"]),
		"classmate": ("appointment-classmate@example.com", ["LMS Student"]),
		"stranger": ("appointment-stranger@example.com", ["LMS Student"]),
	}

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		# frappe refuses more than 60 new Users an hour. These fixtures have
		# stable names and are reused across runs, so the quota only matters the
		# first time a site sees them.
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
			title=f"Appointment Course {suffix}", instructor=self.instructor.email
		)
		self._create_enrollment(self.student.email, self.course.name)
		self._create_enrollment(self.classmate.email, self.course.name)

		# A week out: always in the future, and always the same weekday as today
		# so the published window matches whatever day the suite runs on.
		self.date = add_days(getdate(), 7)
		self.day = self.date.strftime("%A")
		self._publish(WINDOW_START, WINDOW_END)

	def tearDown(self):
		# Before the base class deletes this test's fixtures: the test itself
		# left the session as a student, who may not delete a course.
		frappe.set_user("Administrator")
		super().tearDown()
		frappe.set_user(self.original_user)

	def _publish(self, start=WINDOW_START, end=WINDOW_END, **overrides):
		"""Publish the instructor's hours through the endpoint the modal uses."""
		frappe.set_user(self.instructor.email)
		payload = {
			"course": self.course.name,
			"slot_duration": SLOT_MINUTES,
			"published": 1,
			"schedule": [{"day": self.day, "start_time": start, "end_time": end}],
		}
		payload.update(overrides)
		result = save_availability(payload)
		self.cleanup_items.append(("LMS Instructor Availability", result["name"]))
		frappe.set_user("Administrator")
		return result["name"]

	def _book(self, user=None, start="10:00:00", end="10:30:00", date=None, instructor=None):
		frappe.set_user(user or self.student.email)
		result = book_appointment(
			{
				"course": self.course.name,
				"instructor": instructor or self.instructor.email,
				"date": str(date or self.date),
				"start_time": start,
				"end_time": end,
				"topic": "Stuck on chapter two",
			}
		)
		self.cleanup_items.append(("LMS Appointment", result["name"]))
		return result

	# --- booking ---------------------------------------------------------

	def test_a_student_books_a_published_slot(self):
		booked = self._book()

		doc = frappe.get_doc("LMS Appointment", booked["name"])
		self.assertEqual(doc.student, self.student.email)
		self.assertEqual(doc.instructor, self.instructor.email)
		self.assertEqual(doc.status, "Upcoming")
		# Derived on save; the availability check reads it rather than the date.
		self.assertEqual(doc.day, self.day)

	def test_a_slot_outside_the_published_window_is_rejected(self):
		with self.assertRaises(frappe.ValidationError):
			self._book(start="13:00:00", end="13:30:00")

	def test_a_paused_instructor_takes_no_bookings(self):
		self._publish(published=0)

		with self.assertRaises(frappe.ValidationError):
			self._book()

	def test_a_date_inside_the_time_off_window_is_rejected(self):
		self._publish(
			unavailable_from=str(add_days(self.date, -1)),
			unavailable_to=str(add_days(self.date, 1)),
		)

		with self.assertRaises(frappe.ValidationError):
			self._book()

	def test_a_slot_in_the_past_is_rejected(self):
		# Same weekday, so it sits inside the published window and only the
		# past-date rule can be what turns it down.
		with self.assertRaises(frappe.ValidationError):
			self._book(date=add_days(getdate(), -7))

	def test_a_student_who_is_not_enrolled_cannot_book(self):
		with self.assertRaises(frappe.ValidationError):
			self._book(user=self.stranger.email)

	def test_an_instructor_cannot_book_with_themselves(self):
		with self.assertRaises(frappe.ValidationError):
			self._book(user=self.instructor.email)

	# --- exclusivity -----------------------------------------------------

	def test_the_same_slot_cannot_be_taken_twice(self):
		self._book()

		with self.assertRaises(frappe.ValidationError):
			self._book(user=self.classmate.email)

	def test_a_slot_that_only_overlaps_is_also_rejected(self):
		"""Not just an exact start match: a changed slot_duration can leave an
		old appointment straddling two new slots, and double-booking a human is
		wrong either way."""
		self._book(start="10:00:00", end="10:30:00")

		with self.assertRaises(frappe.ValidationError):
			self._book(user=self.classmate.email, start="10:15:00", end="10:45:00")

	def test_cancelling_frees_the_slot_for_someone_else(self):
		booked = self._book()

		frappe.set_user(self.student.email)
		cancel_appointment(booked["name"])

		self.assertEqual(frappe.db.get_value("LMS Appointment", booked["name"], "status"), "Cancelled")
		# The row is kept rather than deleted, so this proves Cancelled is what
		# releases the slot rather than the row's absence.
		self._book(user=self.classmate.email)

	def test_nobody_outside_the_booking_may_cancel_it(self):
		booked = self._book()

		frappe.set_user(self.stranger.email)
		with self.assertRaises(frappe.PermissionError):
			cancel_appointment(booked["name"])

	def test_the_instructor_may_cancel_too(self):
		booked = self._book()

		frappe.set_user(self.instructor.email)
		cancel_appointment(booked["name"])

		self.assertEqual(frappe.db.get_value("LMS Appointment", booked["name"], "status"), "Cancelled")

	# --- a booking outlives the hours it was made against ----------------

	def test_a_booking_can_still_be_cancelled_after_the_hours_are_withdrawn(self):
		"""Regression: the availability rules used to run on every save, so an
		instructor who stopped taking appointments left both sides unable to
		cancel what was already booked."""
		booked = self._book()

		frappe.set_user(self.instructor.email)
		frappe.delete_doc(
			"LMS Instructor Availability",
			frappe.db.get_value(
				"LMS Instructor Availability",
				{"instructor": self.instructor.email, "course": self.course.name},
				"name",
			),
			ignore_permissions=True,
		)

		frappe.set_user(self.student.email)
		cancel_appointment(booked["name"])
		self.assertEqual(frappe.db.get_value("LMS Appointment", booked["name"], "status"), "Cancelled")

	def test_a_booking_can_be_completed_after_the_window_moves(self):
		booked = self._book()
		self._publish("15:00:00", "17:00:00")

		doc = frappe.get_doc("LMS Appointment", booked["name"])
		doc.status = "Completed"
		doc.save(ignore_permissions=True)

		self.assertEqual(frappe.db.get_value("LMS Appointment", booked["name"], "status"), "Completed")

	def test_rescheduling_is_still_held_to_the_published_hours(self):
		"""The gate is "did the slot move", not "is this a new row" — moving an
		existing booking outside the window must still fail."""
		booked = self._book()

		doc = frappe.get_doc("LMS Appointment", booked["name"])
		doc.start_time = "13:00:00"
		doc.end_time = "13:30:00"
		with self.assertRaises(frappe.ValidationError):
			doc.save(ignore_permissions=True)

	# --- what the popup reads --------------------------------------------

	def test_the_slot_list_drops_what_has_been_booked(self):
		frappe.set_user(self.student.email)
		before = self._slots_on(self.date)
		self.assertIn("10:00:00", before)

		self._book()

		frappe.set_user(self.student.email)
		after = self._slots_on(self.date)
		self.assertNotIn("10:00:00", after)
		self.assertEqual(len(after), len(before) - 1)

	def test_the_slot_list_is_refused_to_someone_not_enrolled(self):
		frappe.set_user(self.stranger.email)
		with self.assertRaises(frappe.ValidationError):
			get_available_slots(self.course.name, self.instructor.email)

	def test_only_courses_with_published_hours_are_offered(self):
		frappe.set_user(self.student.email)
		self.assertIn(self.course.name, [row.name for row in get_bookable_courses()])

		self._publish(published=0)

		frappe.set_user(self.student.email)
		self.assertNotIn(self.course.name, [row.name for row in get_bookable_courses()])

	def test_the_instructor_list_carries_the_slot_length(self):
		frappe.set_user(self.student.email)
		people = get_bookable_instructors(self.course.name)

		self.assertEqual([row.name for row in people], [self.instructor.email])
		self.assertEqual(people[0].slot_duration, SLOT_MINUTES)

	def test_both_sides_see_the_appointment_on_their_calendar(self):
		booked = self._book()

		frappe.set_user(self.student.email)
		mine = {row.name: row.role for row in get_my_appointments()}
		self.assertEqual(mine.get(booked["name"]), "student")

		frappe.set_user(self.instructor.email)
		theirs = {row.name: row.role for row in get_my_appointments()}
		self.assertEqual(theirs.get(booked["name"]), "instructor")

	def _slots_on(self, date):
		days = get_available_slots(self.course.name, self.instructor.email)
		for day in days:
			if day["date"] == str(date):
				return [slot["start_time"] for slot in day["slots"]]
		return []
