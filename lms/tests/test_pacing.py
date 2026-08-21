# Copyright (c) 2026, FOSS United and Contributors
# See license.txt

from frappe.tests.utils import FrappeTestCase

from lms.lms.pacing import COMPLETE_PROGRESS, DUE_SOON_DAYS, compute_due_date, pacing_state


class TestComputeDueDate(FrappeTestCase):
	def test_adds_the_allowance_to_the_start_date(self):
		self.assertEqual(compute_due_date("2026-08-01", 30), "2026-08-31")

	def test_no_allowance_means_no_deadline(self):
		self.assertIsNone(compute_due_date("2026-08-01", 0))
		self.assertIsNone(compute_due_date("2026-08-01", None))

	# A negative allowance is a typo, not an instruction to backdate every
	# learner's deadline before they have opened the course.
	def test_a_negative_allowance_is_treated_as_none(self):
		self.assertIsNone(compute_due_date("2026-08-01", -5))

	def test_no_start_date_means_no_deadline(self):
		self.assertIsNone(compute_due_date(None, 30))


class TestPacingState(FrappeTestCase):
	def test_no_due_date_reports_no_deadline(self):
		state = pacing_state(None, progress=10, on_date="2026-08-21")
		self.assertEqual(state["status"], "No deadline")
		self.assertFalse(state["is_overdue"])
		self.assertIsNone(state["days_left"])

	def test_counts_the_days_remaining(self):
		state = pacing_state("2026-09-01", progress=10, on_date="2026-08-21")
		self.assertEqual(state["days_left"], 11)
		self.assertEqual(state["status"], "On track")
		self.assertFalse(state["is_overdue"])

	def test_the_last_week_is_due_soon(self):
		state = pacing_state("2026-08-28", progress=10, on_date="2026-08-21")
		self.assertEqual(state["days_left"], DUE_SOON_DAYS)
		self.assertEqual(state["status"], "Due soon")

	def test_the_due_date_itself_is_not_yet_overdue(self):
		state = pacing_state("2026-08-21", progress=10, on_date="2026-08-21")
		self.assertEqual(state["days_left"], 0)
		self.assertFalse(state["is_overdue"])

	def test_past_the_date_is_overdue_and_counts_backwards(self):
		state = pacing_state("2026-08-11", progress=10, on_date="2026-08-21")
		self.assertEqual(state["days_left"], -10)
		self.assertTrue(state["is_overdue"])
		self.assertEqual(state["status"], "Overdue")

	# Someone who finished late has finished. Reporting them overdue every time
	# they open the page is both useless and wrong.
	def test_a_finished_course_is_never_overdue(self):
		state = pacing_state("2026-08-11", progress=COMPLETE_PROGRESS, on_date="2026-08-21")
		self.assertFalse(state["is_overdue"])
		self.assertEqual(state["status"], "Completed")

	def test_completion_is_reported_without_a_deadline_too(self):
		state = pacing_state(None, progress=COMPLETE_PROGRESS, on_date="2026-08-21")
		self.assertEqual(state["status"], "Completed")
