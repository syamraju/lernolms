# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, add_months, cint, get_time, getdate

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# A repeating event is expanded on read, never stored as N rows. This bounds how
# far that expansion will go for an event that says "Never" ends.
MAX_OCCURRENCES = 200


class LMSStudentEvent(Document):
	"""A student-organised event — a discussion, a study group, a call.

	Recurrence is stored as a rule, not as rows: `calendar_api.expand_event`
	generates the occurrences that fall inside the window being displayed. That
	keeps "edit the series" a single-row update and stops an event that never
	ends from writing unbounded rows.
	"""

	def validate(self):
		self.validate_times()
		self.validate_repeat()
		self.validate_participants()

	def validate_times(self):
		if self.all_day:
			# The times are meaningless for an all-day event and would otherwise
			# survive a toggle and reappear if it were toggled back.
			self.start_time = None
			self.end_time = None
			return

		if not self.start_time or not self.end_time:
			frappe.throw(_("Set a start and end time, or mark this an all-day event."))

		if get_time(self.start_time) >= get_time(self.end_time):
			frappe.throw(_("The event ends before it starts."))

	def validate_repeat(self):
		if not self.repeat_enabled:
			return

		if cint(self.repeat_every) < 1:
			frappe.throw(_("A repeating event must repeat at least every 1 unit."))

		if self.repeat_ends == "On Date":
			if not self.repeat_until:
				frappe.throw(_("Pick the date the repeat ends on."))
			if getdate(self.repeat_until) < getdate(self.date):
				frappe.throw(_("The repeat ends before the event starts."))

		if self.repeat_ends == "After" and cint(self.repeat_count) < 1:
			frappe.throw(_("Set how many times the event repeats."))

		for day in self.repeat_on_days():
			if day not in WEEKDAYS:
				frappe.throw(_("{0} is not a day of the week.").format(day))

	def repeat_on_days(self) -> list:
		return [day.strip() for day in (self.repeat_on or "").split(",") if day.strip()]

	def validate_participants(self):
		"""Everyone invited must be reachable from the event's course.

		Without a course there is nothing to scope against, so an event with no
		course may only invite people the organiser already shares a course with;
		that check lives in the API, which knows the caller. Here we only enforce
		the course-scoped case and reject duplicates.
		"""
		seen = set()
		for row in self.participants:
			if row.participant in seen:
				frappe.throw(_("{0} is invited twice.").format(row.participant))
			seen.add(row.participant)

		if not self.course or not self.participants:
			return

		allowed = set(course_members(self.course))
		for row in self.participants:
			if row.participant not in allowed:
				frappe.throw(
					_("{0} is not part of {1}.").format(row.participant, self.course_title or self.course)
				)

	def occurrences(self, window_start, window_end) -> list:
		"""Every date this event falls on between `window_start` and `window_end`.

		Returns dates, not documents — the caller pairs each with this event's
		own fields to build a calendar entry.
		"""
		window_start = getdate(window_start)
		window_end = getdate(window_end)
		first = getdate(self.date)

		if not self.repeat_enabled:
			return [first] if window_start <= first <= window_end else []

		every = max(cint(self.repeat_every), 1)
		unit = self.repeat_unit or "Weeks"
		days = self.repeat_on_days()
		limit = cint(self.repeat_count) if self.repeat_ends == "After" else MAX_OCCURRENCES
		until = getdate(self.repeat_until) if self.repeat_ends == "On Date" else None

		found = []
		emitted = 0
		cursor = first

		while emitted < min(limit, MAX_OCCURRENCES) and cursor <= window_end:
			if until and cursor > until:
				break

			# A weekly repeat with named days emits one date per named day inside
			# the cursor's week; every other shape emits the cursor itself.
			if unit == "Weeks" and days:
				week_start = add_days(cursor, -cursor.weekday())
				for offset, name in enumerate(WEEKDAYS):
					if name not in days:
						continue
					candidate = add_days(week_start, offset)
					if candidate < first:
						continue
					if until and candidate > until:
						continue
					if window_start <= candidate <= window_end:
						found.append(candidate)
					emitted += 1
					if emitted >= min(limit, MAX_OCCURRENCES):
						break
			else:
				if window_start <= cursor <= window_end:
					found.append(cursor)
				emitted += 1

			if unit == "Days":
				cursor = add_days(cursor, every)
			elif unit == "Months":
				cursor = add_months(cursor, every)
			else:
				cursor = add_days(cursor, 7 * every)

		return sorted(set(found))


def course_members(course: str) -> list:
	"""Everyone a course-scoped event may invite: its students and its instructors."""
	students = frappe.get_all(
		"LMS Enrollment", filters={"course": course}, pluck="member", limit_page_length=0
	)
	instructors = frappe.get_all(
		"Course Instructor",
		filters={"parent": course, "parenttype": "LMS Course"},
		pluck="instructor",
		limit_page_length=0,
	)
	return list(set(students) | set(instructors))
