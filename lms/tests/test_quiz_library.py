# Copyright (c) 2026, FOSS United and Contributors
# See license.txt

import frappe

from lms.lms.curriculum import (
	add_curriculum_item,
	delete_curriculum_item,
	enforce_quiz_access,
	list_quiz_library,
	set_item_quiz,
	update_curriculum_item,
	update_quiz_settings,
	upsert_section,
)
from lms.lms.test_helpers import BaseTestUtils


class TestQuizLibrary(BaseTestUtils):
	"""Placing a quiz that already exists, instead of minting an empty one.

	The rule underneath every test here: a placement borrows the quiz, it does
	not own it. One course must never be able to rename, hide or destroy a quiz
	another course is using.
	"""

	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		frappe.reload_doctype("Course Lesson")

	def setUp(self):
		super().setUp()
		# Fixtures are built as Administrator, then each test picks the actor it
		# is about. Building them as a restricted user makes a permission failure
		# in setUp look like a failure of the rule under test.
		frappe.set_user("Administrator")

		self.author = self._create_user_with_exact_roles(
			"lib-author@example.com", "Lib", "Author", ["Course Creator", "Moderator"]
		)
		# No authoring role at all. A Course Creator is deliberately NOT a
		# stranger here: the standalone library is shared staff-wide, which is
		# what the Quizzes page has always shown them.
		self.stranger = self._create_user_with_exact_roles(
			"lib-stranger@example.com", "Lib", "Stranger", ["LMS Student"]
		)

		self.questions = self._create_quiz_questions()
		# Unique per run: _create_quiz reuses a quiz with the same title, and a
		# leftover from an earlier run would be reused with the wrong shape.
		self.library_quiz = self._create_quiz(title=f"Library Quiz {frappe.generate_hash(length=8)}")
		# A library quiz belongs to nobody's course; that is what makes it
		# reusable and what the picker exists to reach.
		frappe.db.set_value("LMS Quiz", self.library_quiz.name, "course", None)
		self.library_quiz.reload()

		self.course = self._create_course(title="Library Course", instructor=self.author.email)
		frappe.set_user(self.author.email)
		self.chapter = upsert_section(self.course.name, "Section One")[0]["name"]

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def _place(self, title=None):
		"""Add a Quiz item that reuses the library quiz."""
		result = add_curriculum_item(self.chapter, "Quiz", title, quiz=self.library_quiz.name)
		return result["lesson"]

	def _lesson(self, lesson):
		return frappe.db.get_value(
			"Course Lesson", lesson, ["title", "quiz", "is_shared_activity"], as_dict=True
		)

	# -- placing ----------------------------------------------------------

	def test_placing_links_the_quiz_rather_than_copying_it(self):
		row = self._lesson(self._place())
		self.assertEqual(row.quiz, self.library_quiz.name)
		self.assertEqual(row.is_shared_activity, 1)

	# The author picked it from a list showing that name; anything else on the
	# row reads as the wrong quiz.
	def test_an_unnamed_placement_takes_the_quizs_own_name(self):
		self.assertEqual(self._lesson(self._place()).title, self.library_quiz.title)

	def test_a_named_placement_keeps_the_authors_label(self):
		self.assertEqual(self._lesson(self._place("End of section check")).title, "End of section check")

	def test_a_new_quiz_item_owns_its_quiz(self):
		lesson = add_curriculum_item(self.chapter, "Quiz", "Fresh quiz")["lesson"]
		row = self._lesson(lesson)
		self.assertEqual(row.is_shared_activity, 0)
		self.assertNotEqual(row.quiz, self.library_quiz.name)

	def test_only_a_quiz_item_can_be_linked_to_a_quiz(self):
		with self.assertRaises(frappe.ValidationError):
			add_curriculum_item(self.chapter, "Lecture", "A lecture", quiz=self.library_quiz.name)

	# -- the borrowed quiz is left alone ----------------------------------

	def test_renaming_the_placement_does_not_rename_the_library_quiz(self):
		lesson = self._place()
		update_curriculum_item(lesson, title="Renamed placement")
		self.assertEqual(
			frappe.db.get_value("LMS Quiz", self.library_quiz.name, "title"),
			self.library_quiz.title,
		)
		self.assertEqual(self._lesson(lesson).title, "Renamed placement")

	def test_deleting_the_placement_leaves_the_library_quiz_standing(self):
		lesson = self._place()
		delete_curriculum_item(lesson)
		self.assertTrue(frappe.db.exists("LMS Quiz", self.library_quiz.name))

	def test_deleting_an_owned_quiz_item_takes_its_quiz_with_it(self):
		lesson = add_curriculum_item(self.chapter, "Quiz", "Fresh quiz")["lesson"]
		own = self._lesson(lesson).quiz
		delete_curriculum_item(lesson)
		self.assertFalse(frappe.db.exists("LMS Quiz", own))

	# -- swapping ---------------------------------------------------------

	def test_detaching_gives_the_item_a_quiz_of_its_own(self):
		lesson = self._place()
		set_item_quiz(lesson, None)
		row = self._lesson(lesson)
		self.assertEqual(row.is_shared_activity, 0)
		self.assertNotEqual(row.quiz, self.library_quiz.name)
		self.assertTrue(frappe.db.exists("LMS Quiz", self.library_quiz.name))

	# An empty quiz exists only because the item did; leaving it behind would
	# fill the author's quiz list with blanks every time they changed their mind.
	def test_swapping_away_from_an_empty_owned_quiz_deletes_it(self):
		lesson = add_curriculum_item(self.chapter, "Quiz", "Fresh quiz")["lesson"]
		own = self._lesson(lesson).quiz
		set_item_quiz(lesson, self.library_quiz.name)
		self.assertFalse(frappe.db.exists("LMS Quiz", own))
		self.assertEqual(self._lesson(lesson).quiz, self.library_quiz.name)

	# A swap in one course is not permission to destroy written work.
	def test_swapping_away_from_a_quiz_with_questions_keeps_it(self):
		lesson = add_curriculum_item(self.chapter, "Quiz", "Fresh quiz")["lesson"]
		own = self._lesson(lesson).quiz
		owned = frappe.get_doc("LMS Quiz", own)
		owned.append("questions", {"question": self.questions[0].name, "marks": 1})
		owned.save()

		set_item_quiz(lesson, self.library_quiz.name)
		self.assertTrue(frappe.db.exists("LMS Quiz", own))
		self.assertIsNone(frappe.db.get_value("LMS Quiz", own, "lesson"))

	def test_a_lecture_item_cannot_be_given_a_quiz(self):
		lesson = add_curriculum_item(self.chapter, "Lecture", "A lecture")["lesson"]
		with self.assertRaises(frappe.ValidationError):
			set_item_quiz(lesson, self.library_quiz.name)

	# -- access -----------------------------------------------------------

	# A standalone quiz has no course to check against, so authorship stands in
	# for it. Without this, every quiz on the site was editable by anyone who
	# could reach the endpoint.
	def test_a_stranger_cannot_place_a_standalone_quiz(self):
		frappe.set_user(self.stranger.email)
		with self.assertRaises(frappe.PermissionError):
			enforce_quiz_access(self.library_quiz.name)

	def test_the_owner_can_place_their_own_standalone_quiz(self):
		frappe.set_user(self.author.email)
		self.assertEqual(enforce_quiz_access(self.library_quiz.name), self.library_quiz.name)

	def test_a_quiz_that_does_not_exist_is_reported_as_missing(self):
		with self.assertRaises(frappe.DoesNotExistError):
			enforce_quiz_access("no-such-quiz")

	# -- the listing ------------------------------------------------------

	def test_the_library_lists_a_placeable_quiz_with_its_shape(self):
		rows = list_quiz_library(course=self.course.name)
		row = next((r for r in rows if r["name"] == self.library_quiz.name), None)
		self.assertIsNotNone(row)
		self.assertEqual(row["question_count"], len(self.questions))
		self.assertEqual(row["passing_percentage"], 70)

	def test_the_library_hides_a_quiz_this_user_may_not_place(self):
		frappe.set_user(self.stranger.email)
		rows = list_quiz_library()
		self.assertNotIn(self.library_quiz.name, [r["name"] for r in rows])

	def test_the_library_search_narrows_by_title(self):
		rows = list_quiz_library(search=self.library_quiz.title)
		self.assertIn(self.library_quiz.name, [r["name"] for r in rows])
		self.assertEqual([], list_quiz_library(search="no-such-quiz-title"))

	# -- the pass mark ----------------------------------------------------

	def test_the_pass_mark_is_settable(self):
		update_quiz_settings(self.library_quiz.name, passing_percentage=65)
		self.assertEqual(frappe.db.get_value("LMS Quiz", self.library_quiz.name, "passing_percentage"), 65)

	def test_an_out_of_range_pass_mark_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			update_quiz_settings(self.library_quiz.name, passing_percentage=500)
		with self.assertRaises(frappe.ValidationError):
			update_quiz_settings(self.library_quiz.name, passing_percentage=-1)

	def test_negative_attempts_are_refused(self):
		with self.assertRaises(frappe.ValidationError):
			update_quiz_settings(self.library_quiz.name, max_attempts=-3)

	def test_a_stranger_cannot_change_the_pass_mark(self):
		frappe.set_user(self.stranger.email)
		with self.assertRaises(frappe.PermissionError):
			update_quiz_settings(self.library_quiz.name, passing_percentage=10)
