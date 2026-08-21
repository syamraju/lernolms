# Copyright (c) 2026, FOSS United and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from lms.lms.utils import compute_course_locks, compute_locked_sections


def rows(*sections) -> list:
	"""Ordered lesson rows for the sections given as ``(chapter, [lessons])``."""
	out = []
	for idx, (chapter, lessons) in enumerate(sections, start=1):
		for lesson in lessons:
			out.append(frappe._dict(name=lesson, chapter_name=chapter, chapter_idx=idx))
	return out


class TestComputeLockedSections(FrappeTestCase):
	# The whole point of the section rule: inside the portion in play, order is
	# the learner's business. The lesson rule would have locked L2 and L3 here.
	def test_the_first_section_is_open_in_any_order(self):
		locked = compute_locked_sections(rows(("C1", ["L1", "L2", "L3"])), set())
		self.assertEqual(locked, set())

	def test_a_later_section_waits_for_the_one_before_it(self):
		locked = compute_locked_sections(
			rows(("C1", ["L1", "L2"]), ("C2", ["L3", "L4"])), {"L1"}
		)
		self.assertEqual(locked, {"L3", "L4"})

	def test_finishing_a_section_opens_the_next(self):
		locked = compute_locked_sections(
			rows(("C1", ["L1", "L2"]), ("C2", ["L3", "L4"])), {"L1", "L2"}
		)
		self.assertEqual(locked, set())

	def test_everything_after_the_open_section_is_locked(self):
		locked = compute_locked_sections(
			rows(("C1", ["L1"]), ("C2", ["L2"]), ("C3", ["L3"])), set()
		)
		self.assertEqual(locked, {"L2", "L3"})

	# Switching the setting on mid-cohort must not take back work already done,
	# the same courtesy the lesson rule extends.
	def test_a_lesson_already_completed_stays_open(self):
		locked = compute_locked_sections(
			rows(("C1", ["L1"]), ("C2", ["L2", "L3"])), {"L3"}
		)
		self.assertEqual(locked, {"L2"})

	def test_all_complete_locks_nothing(self):
		locked = compute_locked_sections(
			rows(("C1", ["L1"]), ("C2", ["L2"])), {"L1", "L2"}
		)
		self.assertEqual(locked, set())

	def test_an_empty_course_locks_nothing(self):
		self.assertEqual(compute_locked_sections([], set()), set())

	# A chapter placed twice is two portions: completing its first placement
	# opens only the section that follows, not its own later placement.
	def test_a_chapter_placed_twice_is_two_portions(self):
		locked = compute_locked_sections(
			[
				frappe._dict(name="L1", chapter_name="C1", chapter_idx=1),
				frappe._dict(name="L2", chapter_name="C2", chapter_idx=2),
				frappe._dict(name="L3", chapter_name="C1", chapter_idx=3),
			],
			{"L1"},
		)
		self.assertEqual(locked, {"L3"})

	# The dead-end guard. The return value is a set of names, so a lesson
	# reachable from two sections would be locked by its later placement and take
	# its own first one with it — and with the opening lesson locked there is
	# nowhere left to send the learner.
	def test_one_lesson_placed_twice_does_not_lock_itself(self):
		locked = compute_locked_sections(
			[
				frappe._dict(name="L1", chapter_name="C1", chapter_idx=1),
				frappe._dict(name="L1", chapter_name="C1", chapter_idx=3),
			],
			set(),
		)
		self.assertEqual(locked, set())


class TestComputeCourseLocks(FrappeTestCase):
	"""The one entry point both the outline and the lesson gate go through."""

	def test_picks_the_lesson_rule_by_default(self):
		locked = compute_course_locks(rows(("C1", ["L1", "L2", "L3"])), set())
		self.assertEqual(locked, {"L2", "L3"})

	def test_picks_the_section_rule_when_asked(self):
		locked = compute_course_locks(rows(("C1", ["L1", "L2", "L3"])), set(), by_section=True)
		self.assertEqual(locked, set())
