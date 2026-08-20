# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, get_system_timezone, get_time


class LMSInstructorAvailability(Document):
	"""An instructor's open hours for one-to-one appointments on one course.

	One row per (instructor, course). The weekly `schedule` windows are not
	themselves bookable — `lms.lms.calendar_api` divides each window into
	`slot_duration` chunks and offers the chunks that no appointment has taken.
	"""

	def before_insert(self):
		if not self.timezone:
			self.timezone = get_system_timezone()

	def validate(self):
		self.validate_instructor_teaches_course()
		self.validate_slot_duration()
		self.validate_schedule()
		self.validate_unavailability()
		self.validate_uniqueness()

	def validate_instructor_teaches_course(self):
		"""Only a course's own instructors may publish hours against it.

		Checked here rather than only in the API so the rule holds for a row
		created from the desk too.
		"""
		if frappe.db.exists(
			"Course Instructor", {"parent": self.course, "parenttype": "LMS Course", "instructor": self.instructor}
		):
			return

		# A moderator setting someone else up is legitimate; anything else is not.
		from lms.lms.utils import has_moderator_role

		if has_moderator_role():
			return

		frappe.throw(_("{0} does not teach this course.").format(self.instructor))

	def validate_slot_duration(self):
		duration = cint(self.slot_duration)
		# 5 minutes is the floor because the slot list is rendered in full: a
		# 1-minute duration over an 8-hour window is 480 rows in a popover.
		if duration < 5 or duration > 480:
			frappe.throw(_("Slot duration must be between 5 and 480 minutes."))
		if duration % 5:
			frappe.throw(_("Slot duration must be a multiple of 5 minutes."))

	def validate_schedule(self):
		if not self.schedule:
			frappe.throw(_("Add at least one weekly window before publishing your availability."))

		seen = []
		for row in self.schedule:
			start = get_time(row.start_time)
			end = get_time(row.end_time)

			if start >= end:
				frappe.throw(
					_("Row {0}: the end time must be after the start time.").format(row.idx)
				)

			# A window shorter than one slot can never be booked, which reads as
			# "my availability does not work" rather than as a mistake.
			minutes = (end.hour * 60 + end.minute) - (start.hour * 60 + start.minute)
			if minutes < cint(self.slot_duration):
				frappe.throw(
					_("Row {0}: this window is shorter than one {1}-minute slot.").format(
						row.idx, self.slot_duration
					)
				)

			for other_day, other_start, other_end, other_idx in seen:
				if other_day != row.day:
					continue
				if start < other_end and other_start < end:
					frappe.throw(
						_("Row {0} overlaps row {1} on {2}.").format(row.idx, other_idx, row.day)
					)

			seen.append((row.day, start, end, row.idx))

	def validate_unavailability(self):
		if self.unavailable_from and self.unavailable_to:
			if self.unavailable_from > self.unavailable_to:
				frappe.throw(_("The unavailability window ends before it starts."))

	def validate_uniqueness(self):
		existing = frappe.db.exists(
			"LMS Instructor Availability",
			{
				"instructor": self.instructor,
				"course": self.course,
				"name": ["!=", self.name],
			},
		)
		if existing:
			frappe.throw(_("You already have availability set for this course."))
