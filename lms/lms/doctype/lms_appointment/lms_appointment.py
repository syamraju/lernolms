# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, get_system_timezone, get_time, getdate, now_datetime


class LMSAppointment(Document):
	"""One booked one-to-one session between a student and a course instructor.

	The rule that matters here is exclusivity: once a slot is taken it must not
	be bookable again. That is enforced in `validate_slot_is_free` under a row
	lock taken in `before_insert`, not by a unique index — a unique index cannot
	express "unique among rows that are not Cancelled", and cancelling has to
	release the slot.
	"""

	def before_insert(self):
		# Serialise every booking attempt for this instructor+course pair before
		# anything reads the existing appointments. Two students clicking the
		# same slot at the same moment otherwise both read "free" and both
		# insert. Locking the availability row (the parent of the slot) is the
		# same trick LMS Enrollment uses against its course row.
		frappe.db.get_value(
			"LMS Instructor Availability",
			{"instructor": self.instructor, "course": self.course},
			"name",
			for_update=True,
		)

		if not self.timezone:
			self.timezone = get_system_timezone()

	def validate(self):
		self.set_day()
		self.validate_times()

		# The three checks below answer "may this slot be taken?", which is a
		# question about the booking, not about the row. Re-running them on every
		# save would make an appointment impossible to cancel or complete once the
		# instructor edited their hours, withdrew them, or the student's enrolment
		# ended — all of which happen after a booking is already made. Gate them on
		# the slot actually moving, so a reschedule is still held to the same rules.
		if self.is_new() or self.slot_has_changed():
			self.validate_not_in_the_past()
			self.validate_student_is_enrolled()
			self.validate_within_availability()

		# Not gated: two live appointments must never overlap, whatever moved.
		self.validate_slot_is_free()

	def slot_has_changed(self) -> bool:
		return any(
			self.has_value_changed(field)
			for field in ("course", "instructor", "student", "date", "start_time", "end_time")
		)

	def set_day(self):
		self.day = getdate(self.date).strftime("%A")

	def validate_times(self):
		if get_time(self.start_time) >= get_time(self.end_time):
			frappe.throw(_("The appointment ends before it starts."))

	def validate_not_in_the_past(self):
		# Only reached for a new or rescheduled booking — an appointment that has
		# since passed must stay saveable so its status can be moved to Completed
		# or Cancelled. `validate` is what draws that line.
		starts_at = get_datetime(f"{getdate(self.date)} {self.start_time}")
		if starts_at < now_datetime():
			frappe.throw(_("That slot is in the past."))

	def validate_student_is_enrolled(self):
		if self.student == self.instructor:
			frappe.throw(_("An instructor cannot book an appointment with themselves."))

		if frappe.db.exists("LMS Enrollment", {"course": self.course, "member": self.student}):
			return

		frappe.throw(_("You must be enrolled in this course to book an appointment."))

	def validate_within_availability(self):
		"""The slot must sit inside a published weekly window for this instructor.

		Without this a crafted request could book any time at all — the slot list
		the UI renders is a convenience, never the authority.
		"""
		availability = frappe.db.get_value(
			"LMS Instructor Availability",
			{"instructor": self.instructor, "course": self.course},
			["name", "published", "unavailable_from", "unavailable_to"],
			as_dict=True,
		)
		if not availability:
			frappe.throw(_("This instructor is not taking appointments for this course."))

		if not availability.published:
			frappe.throw(_("This instructor has paused appointments for this course."))

		booked_on = getdate(self.date)
		if availability.unavailable_from and availability.unavailable_to:
			if availability.unavailable_from <= booked_on <= availability.unavailable_to:
				frappe.throw(_("The instructor is unavailable on that date."))

		start = get_time(self.start_time)
		end = get_time(self.end_time)

		windows = frappe.get_all(
			"LMS Availability Slot",
			filters={"parent": availability.name, "parenttype": "LMS Instructor Availability", "day": self.day},
			fields=["start_time", "end_time"],
		)
		for window in windows:
			if get_time(window.start_time) <= start and end <= get_time(window.end_time):
				return

		frappe.throw(_("That time is outside the instructor's available hours."))

	def validate_slot_is_free(self):
		"""No other live appointment may overlap this one for this instructor.

		Overlap rather than an exact start match: the slot grid makes exact
		matches the normal case, but a changed `slot_duration` can leave an old
		appointment straddling two new slots, and double-booking a human is
		wrong either way.
		"""
		start = get_time(self.start_time)
		end = get_time(self.end_time)

		same_day = frappe.get_all(
			"LMS Appointment",
			filters={
				"instructor": self.instructor,
				"date": self.date,
				"status": ["!=", "Cancelled"],
				"name": ["!=", self.name],
			},
			fields=["start_time", "end_time"],
		)
		for other in same_day:
			if start < get_time(other.end_time) and get_time(other.start_time) < end:
				frappe.throw(_("That slot has just been taken. Please pick another one."))
