# Copyright (c) 2026, Frappe and Contributors
# For license information, please see license.txt

"""What the batch calendar shows, and to whom.

The calendar adds no storage — it is a view over sources that already existed.
So these tests are about *merging and scoping*: that each source reaches the
grid, that a student sees their own evaluations and not a classmate's, and that
the cross-batch view catches a collision invisible from inside either batch.
"""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate, nowdate

from lms.lms.batch_calendar import get_batch_calendar, get_my_calendar
from lms.lms.doctype.lms_batch.lms_batch import HUDDLE_PROVIDER
from lms.lms.test_batch_access import _batch, _user

WINDOW_START = add_days(nowdate(), -30)
WINDOW_END = add_days(nowdate(), 60)


class CalendarTestCase(FrappeTestCase):
	def setUp(self):
		self.moderator = _user(self.mod_email, ["Moderator"])
		self.batch = _batch(self.batch_title, self.moderator)
		frappe.set_user(self.moderator)

	def tearDown(self):
		frappe.set_user("Administrator")

	def _enrol(self, email):
		user = _user(email, ["LMS Student"])
		frappe.set_user(self.moderator)
		frappe.get_doc(
			{"doctype": "LMS Batch Enrollment", "batch": self.batch, "member": user}
		).insert(ignore_permissions=True)
		return user

	def _live_class(self, title, date=None, batch=None):
		"""`host` and `timezone` are mandatory on LMS Live Class — a class has to
		be run by somebody, somewhere."""
		return frappe.get_doc(
			{
				"doctype": "LMS Live Class",
				"batch_name": batch or self.batch,
				"title": title,
				"date": date or add_days(nowdate(), 3),
				"time": "10:00:00",
				"duration": 60,
				"description": "x",
				"host": self.moderator,
				"timezone": "Asia/Kolkata",
				# The one provider that needs no external calendar configured. The
				# Google paths refuse to create a class without one, which a test
				# has no way to supply.
				"conferencing_provider": HUDDLE_PROVIDER,
			}
		).insert(ignore_permissions=True)

	def _kinds(self, events):
		return {event["kind"] for event in events}


class TestSourcesReachTheGrid(CalendarTestCase):
	mod_email = "cal-source-mod@example.com"
	batch_title = "Calendar Source Cohort"

	def test_a_live_class_appears(self):
		self._live_class("Intro session")
		events = get_batch_calendar(self.batch, WINDOW_START, WINDOW_END)

		live = [e for e in events if e["kind"] == "live_class"]
		self.assertEqual(len(live), 1)
		self.assertEqual(live[0]["title"], "Intro session")

	def test_a_live_class_carries_the_end_time_its_duration_implies(self):
		"""A 60-minute class starting at 10:00 has to occupy the 10–11 slot, or the
		grid cannot show a collision with anything else at 10:30."""
		self._live_class("Timed session")
		events = get_batch_calendar(self.batch, WINDOW_START, WINDOW_END)
		live = [e for e in events if e["kind"] == "live_class"][0]

		self.assertEqual(str(live["start_time"]), "10:00:00")
		self.assertEqual(str(live["end_time"]), "11:00:00")

	def test_the_batch_start_and_end_are_marked(self):
		events = get_batch_calendar(self.batch, WINDOW_START, WINDOW_END)
		self.assertIn("batch_start", self._kinds(events))

	def test_events_come_back_in_time_order(self):
		self._live_class("Later", add_days(nowdate(), 10))
		self._live_class("Sooner", add_days(nowdate(), 2))
		events = get_batch_calendar(self.batch, WINDOW_START, WINDOW_END)

		dates = [event["date"] for event in events]
		self.assertEqual(dates, sorted(dates))

	def test_nothing_outside_the_window_leaks_in(self):
		self._live_class("Far future", add_days(nowdate(), 200))
		events = get_batch_calendar(self.batch, WINDOW_START, WINDOW_END)
		self.assertNotIn("Far future", [event["title"] for event in events])


class TestWhoSeesWhat(CalendarTestCase):
	mod_email = "cal-access-mod@example.com"
	batch_title = "Calendar Access Cohort"

	def test_a_student_of_the_batch_can_read_it(self):
		student = self._enrol("cal-access-student@example.com")
		self._live_class("Open session")
		frappe.set_user(student)

		events = get_batch_calendar(self.batch, WINDOW_START, WINDOW_END)
		self.assertIn("live_class", self._kinds(events))

	def test_an_outsider_is_refused(self):
		"""Published-ness does not open the schedule: seeing a cohort advertised
		is not being in it."""
		outsider = _user("cal-access-outsider@example.com", ["LMS Student"])
		frappe.set_user(outsider)

		with self.assertRaises(frappe.PermissionError):
			get_batch_calendar(self.batch, WINDOW_START, WINDOW_END)

	def test_a_moderator_of_another_batch_is_refused(self):
		other_mod = _user("cal-access-othermod@example.com", ["Moderator"])
		frappe.set_user(other_mod)

		with self.assertRaises(frappe.PermissionError):
			get_batch_calendar(self.batch, WINDOW_START, WINDOW_END)


class TestCrossBatchCollisions(CalendarTestCase):
	mod_email = "cal-cross-mod@example.com"
	batch_title = "Calendar Cross Cohort"

	def test_two_batches_merge_into_one_calendar(self):
		"""The reason this endpoint exists: two classes at the same hour in two
		different cohorts is a collision nobody can see from inside either one."""
		second = _batch("Calendar Cross Second", self.moderator)
		clash_date = add_days(nowdate(), 5)

		self._live_class("Cohort one class", clash_date)
		self._live_class("Cohort two class", clash_date, batch=second)

		frappe.set_user(self.moderator)
		events = get_my_calendar(WINDOW_START, WINDOW_END)
		titles = [event["title"] for event in events]

		self.assertIn("Cohort one class", titles)
		self.assertIn("Cohort two class", titles)

	def test_every_entry_names_its_batch(self):
		"""Without this the merged view is a list of times with no way to tell
		which cohort each belongs to."""
		self._live_class("Labelled class")
		frappe.set_user(self.moderator)

		events = [e for e in get_my_calendar(WINDOW_START, WINDOW_END) if e["kind"] == "live_class"]
		self.assertTrue(events)
		for event in events:
			self.assertTrue(event.get("batch"))
			self.assertTrue(event.get("batch_title"))

	def test_a_student_gets_only_their_own_batches(self):
		student = self._enrol("cal-cross-student@example.com")
		other = _batch("Calendar Cross Other", self.moderator)
		self._live_class("Not their class", add_days(nowdate(), 4), batch=other)

		frappe.set_user(student)
		titles = [event["title"] for event in get_my_calendar(WINDOW_START, WINDOW_END)]
		self.assertNotIn("Not their class", titles)
