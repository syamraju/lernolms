"""Objective vs subjective quizzes, and the evaluator queue behind the latter.

Run with: bench execute lms.lms._run_module_tests.execute --args "['lms.lms.test_evaluation']"
"""

import json

import frappe
from frappe.utils import cint

from lms.lms.doctype.course_lesson.course_lesson import get_pending_quizzes
from lms.lms.doctype.lms_quiz.lms_quiz import submit_quiz
from lms.lms.evaluation import (
	evaluator_courses,
	get_evaluation,
	list_evaluation_queue,
	save_evaluation,
	set_evaluator_assignments,
)
from lms.lms.test_helpers import BaseTestUtils

EVALUATOR = "evaluator-quiz@example.com"
OTHER_EVALUATOR = "other-evaluator-quiz@example.com"
STUDENT = "student-quiz-eval@example.com"
MODERATOR = "moderator-quiz-eval@example.com"


class TestSubjectiveQuizzes(BaseTestUtils):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")

		self.moderator = self._create_user(MODERATOR, "Mod", "Erator", ["Moderator"])
		self.evaluator = self._create_user(EVALUATOR, "Eve", "Aluator", ["Batch Evaluator"])
		self.other = self._create_user(OTHER_EVALUATOR, "Otto", "Ther", ["Batch Evaluator"])
		self.student = self._create_user(STUDENT, "Stu", "Dent", ["LMS Student"])

		self.course = self._create_course(title="Subjective Quiz Course", instructor=MODERATOR)
		self.chapter = self._create_chapter("Section One", self.course.name)
		self.lesson = self._create_lesson("Lesson One", self.chapter.name, self.course.name)
		self._create_lesson_reference(self.chapter.name, self.lesson.name)
		self._create_chapter_reference(self.course.name, self.chapter.name)

		# can_access_quiz grants through course membership, and save_progress needs an
		# LMS Enrollment to write against, so the student has to actually be enrolled —
		# creating the User is not enough.
		self._create_enrollment(STUDENT, self.course.name)

		self.quiz = self._create_subjective_quiz()
		# Placing the quiz takes both links, and they point opposite ways:
		# get_lesson_quizzes (the lesson gate) reads Course Lesson.quiz, while the
		# progress writes read LMS Quiz.lesson/course. Setting only the latter left the
		# gate seeing an empty lesson.
		frappe.db.set_value(
			"Course Lesson", self.lesson.name, {"quiz": self.quiz.name, "item_type": "Quiz"}
		)

		self._register_evaluator(EVALUATOR, courses=[self.course.name])
		self._register_evaluator(OTHER_EVALUATOR)

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	# -- helpers -----------------------------------------------------------

	def _create_subjective_quiz(self, block_progress=0, title="Subjective Utility Quiz"):
		question = frappe.new_doc("LMS Question")
		question.update({"question": "Write a function that reverses a list.", "type": "Open Ended"})
		question.save()
		self.cleanup_items.append(("LMS Question", question.name))

		quiz = frappe.new_doc("LMS Quiz")
		quiz.update(
			{
				"title": title,
				"quiz_type": "Subjective",
				"passing_percentage": 60,
				"lesson": self.lesson.name,
				"course": self.course.name,
				"block_progress_until_evaluated": block_progress,
			}
		)
		quiz.append("questions", {"question": question.name, "marks": 10})
		quiz.save()
		self.cleanup_items.append(("LMS Quiz", quiz.name))
		self.question = question
		return quiz

	def _register_evaluator(self, user, courses=None, programs=None):
		if not frappe.db.exists("Course Evaluator", user):
			doc = frappe.new_doc("Course Evaluator")
			doc.evaluator = user
			doc.save(ignore_permissions=True)
			self.cleanup_items.append(("Course Evaluator", user))
		frappe.set_user(MODERATOR)
		set_evaluator_assignments(user, courses or [], programs or [])
		frappe.set_user("Administrator")

	def _submit_as_student(self, quiz=None, answer="def reverse(x): return x[::-1]"):
		quiz = quiz or self.quiz
		frappe.set_user(STUDENT)
		result = submit_quiz(
			quiz.name,
			json.dumps([{"question_name": self.question.name, "answer": [answer]}]),
		)
		frappe.set_user("Administrator")
		self.cleanup_items.append(("LMS Quiz Submission", result["submission"]))
		return result

	# -- quiz shape --------------------------------------------------------

	def test_objective_quiz_rejects_open_ended_questions(self):
		quiz = frappe.get_doc("LMS Quiz", self.quiz.name)
		quiz.quiz_type = "Objective"
		self.assertRaises(frappe.ValidationError, quiz.save)

	def test_subjective_quiz_rejects_auto_graded_questions(self):
		choice = frappe.new_doc("LMS Question")
		choice.update(
			{
				"question": "Pick one.",
				"type": "Choices",
				"option_1": "A",
				"is_correct_1": 1,
				"option_2": "B",
			}
		)
		choice.save()
		self.cleanup_items.append(("LMS Question", choice.name))

		quiz = frappe.get_doc("LMS Quiz", self.quiz.name)
		quiz.append("questions", {"question": choice.name, "marks": 1})
		self.assertRaises(frappe.ValidationError, quiz.save)

	def test_subjective_quiz_never_shows_answers(self):
		quiz = frappe.get_doc("LMS Quiz", self.quiz.name)
		quiz.show_answers = 1
		quiz.save()
		self.assertEqual(quiz.show_answers, 0)

	# -- submitting --------------------------------------------------------

	def test_submission_is_queued_rather_than_scored(self):
		result = self._submit_as_student()

		self.assertTrue(result["pending_evaluation"])
		# Neither passed nor failed: nobody has looked at it yet.
		self.assertIsNone(result["pass"])
		self.assertEqual(result["score"], 0)

		submission = frappe.get_doc("LMS Quiz Submission", result["submission"])
		self.assertEqual(submission.evaluation_status, "Pending")
		self.assertEqual(submission.course, self.course.name)

	def test_objective_submission_is_not_queued(self):
		self.questions = self._create_quiz_questions()
		objective = self._create_quiz(title="Objective Utility Quiz")
		# _create_quiz builds a quiz with no course, and can_access_quiz grants only
		# through a course or a batch assessment — so without this the enrolled
		# student is refused before the assertion is ever reached.
		frappe.db.set_value("LMS Quiz", objective.name, "course", self.course.name)

		frappe.set_user(STUDENT)
		result = submit_quiz(
			objective.name,
			json.dumps(
				[
					{"question_name": question.name, "answer": [question.option_1]}
					for question in self.questions
				]
			),
		)
		frappe.set_user("Administrator")
		self.cleanup_items.append(("LMS Quiz Submission", result["submission"]))

		self.assertFalse(result["pending_evaluation"])
		self.assertEqual(
			frappe.db.get_value("LMS Quiz Submission", result["submission"], "evaluation_status"),
			"Not Required",
		)

	def test_posted_marks_are_ignored(self):
		"""A student cannot mark their own subjective answer.

		process_results builds each stored row from scratch. It used to mutate the
		caller's dict and, on the open-ended branch, never assigned `marks` — so a
		posted value rode through into the submission and validate_marks() summed it,
		letting a student post full marks on a non-answer and pass instantly.
		"""
		frappe.set_user(STUDENT)
		result = submit_quiz(
			self.quiz.name,
			json.dumps(
				[
					{
						"question_name": self.question.name,
						"answer": ["not a real answer"],
						"marks": 10,
						"is_correct": 1,
						"evaluator_feedback": "Excellent work.",
					}
				]
			),
		)
		frappe.set_user("Administrator")
		self.cleanup_items.append(("LMS Quiz Submission", result["submission"]))

		submission = frappe.get_doc("LMS Quiz Submission", result["submission"])
		self.assertEqual(submission.score, 0)
		self.assertEqual(submission.percentage, 0)
		self.assertEqual(submission.evaluation_status, "Pending")

		row = submission.result[0]
		self.assertEqual(cint(row.marks), 0)
		self.assertEqual(cint(row.is_correct), 0)
		# The evaluator's own field is theirs alone; a student must not seed it.
		self.assertFalse(row.evaluator_feedback)

	# -- the lesson gate ---------------------------------------------------

	def test_unmarked_submission_does_not_block_by_default(self):
		frappe.set_user(STUDENT)
		self.assertEqual(len(get_pending_quizzes(self.lesson.name)), 1)
		frappe.set_user("Administrator")

		self._submit_as_student()

		frappe.set_user(STUDENT)
		# Handing the work in is the requirement when the author did not ask the
		# lesson to wait — there is no percentage yet to hold anyone to.
		self.assertEqual(get_pending_quizzes(self.lesson.name), [])
		frappe.set_user("Administrator")

	def test_blocking_quiz_waits_for_the_mark(self):
		frappe.db.set_value("LMS Quiz", self.quiz.name, "block_progress_until_evaluated", 1)
		result = self._submit_as_student()

		frappe.set_user(STUDENT)
		pending = get_pending_quizzes(self.lesson.name)
		frappe.set_user("Administrator")
		self.assertEqual(len(pending), 1)
		self.assertTrue(pending[0]["awaiting_evaluation"])

		frappe.set_user(EVALUATOR)
		save_evaluation(
			result["submission"],
			marks=[{"row": self._row_of(result["submission"]), "marks": 8}],
		)
		frappe.set_user("Administrator")

		frappe.set_user(STUDENT)
		self.assertEqual(get_pending_quizzes(self.lesson.name), [])
		frappe.set_user("Administrator")

	def test_failing_mark_stops_awaiting_and_reports_the_score(self):
		frappe.db.set_value("LMS Quiz", self.quiz.name, "block_progress_until_evaluated", 1)
		result = self._submit_as_student()

		frappe.set_user(EVALUATOR)
		save_evaluation(
			result["submission"],
			marks=[{"row": self._row_of(result["submission"]), "marks": 2}],
		)
		frappe.set_user("Administrator")

		frappe.set_user(STUDENT)
		pending = get_pending_quizzes(self.lesson.name)
		frappe.set_user("Administrator")
		self.assertEqual(len(pending), 1)
		# A mark exists, so the learner has a result to act on rather than a wait.
		self.assertFalse(pending[0]["awaiting_evaluation"])
		self.assertEqual(pending[0]["best_percentage"], 20)

	def _row_of(self, submission):
		return frappe.get_doc("LMS Quiz Submission", submission).result[0].name

	# -- marking -----------------------------------------------------------

	def test_marks_drive_the_score_and_percentage(self):
		result = self._submit_as_student()

		frappe.set_user(EVALUATOR)
		marked = save_evaluation(
			result["submission"],
			marks=[
				{
					"row": self._row_of(result["submission"]),
					"marks": 7,
					"evaluator_feedback": "Works, but O(n) space.",
				}
			],
			comment="Good first attempt.",
		)
		frappe.set_user("Administrator")

		self.assertEqual(marked["score"], 7)
		self.assertEqual(marked["score_out_of"], 10)
		self.assertEqual(marked["percentage"], 70)
		self.assertEqual(marked["evaluation_status"], "Evaluated")
		self.assertEqual(marked["evaluator"], EVALUATOR)
		self.assertEqual(marked["answers"][0]["evaluator_feedback"], "Works, but O(n) space.")

	def test_a_draft_does_not_release_the_result(self):
		result = self._submit_as_student()

		frappe.set_user(EVALUATOR)
		saved = save_evaluation(
			result["submission"],
			marks=[{"row": self._row_of(result["submission"]), "marks": 5}],
			finalize=False,
		)
		frappe.set_user("Administrator")

		self.assertEqual(saved["evaluation_status"], "Pending")
		self.assertEqual(saved["score"], 5)

	def test_marks_cannot_exceed_what_the_question_is_worth(self):
		result = self._submit_as_student()
		frappe.set_user(EVALUATOR)
		self.assertRaises(
			frappe.ValidationError,
			save_evaluation,
			result["submission"],
			marks=[{"row": self._row_of(result["submission"]), "marks": 11}],
		)
		frappe.set_user("Administrator")

	def test_marking_a_one_attempt_quiz_is_not_refused_as_a_retry(self):
		"""The attempt limit belongs to the learner, not to the evaluator's save."""
		frappe.db.set_value("LMS Quiz", self.quiz.name, "max_attempts", 1)
		result = self._submit_as_student()

		frappe.set_user(EVALUATOR)
		marked = save_evaluation(
			result["submission"],
			marks=[{"row": self._row_of(result["submission"]), "marks": 9}],
		)
		frappe.set_user("Administrator")
		self.assertEqual(marked["score"], 9)

	# -- who sees what -----------------------------------------------------

	def test_scope_covers_assigned_courses(self):
		self.assertEqual(evaluator_courses(EVALUATOR), {self.course.name})
		self.assertEqual(evaluator_courses(OTHER_EVALUATOR), set())

	def test_scope_expands_a_program_into_its_courses(self):
		program = frappe.new_doc("LMS Program")
		program.update({"title": "Utility Program"})
		program.append("program_courses", {"course": self.course.name})
		program.save(ignore_permissions=True)
		self.cleanup_items.append(("LMS Program", program.name))

		self._register_evaluator(OTHER_EVALUATOR, programs=[program.name])
		self.assertEqual(evaluator_courses(OTHER_EVALUATOR), {self.course.name})

	def test_queue_shows_only_assigned_work(self):
		result = self._submit_as_student()

		frappe.set_user(EVALUATOR)
		queue = list_evaluation_queue()
		frappe.set_user("Administrator")
		self.assertEqual([row.name for row in queue["submissions"]], [result["submission"]])
		self.assertEqual(queue["pending_count"], 1)

		frappe.set_user(OTHER_EVALUATOR)
		empty = list_evaluation_queue()
		frappe.set_user("Administrator")
		self.assertEqual(empty["submissions"], [])

	def test_unassigned_evaluator_cannot_open_a_submission(self):
		result = self._submit_as_student()
		frappe.set_user(OTHER_EVALUATOR)
		self.assertRaises(frappe.PermissionError, get_evaluation, result["submission"])
		self.assertRaises(frappe.PermissionError, save_evaluation, result["submission"])
		frappe.set_user("Administrator")

	def test_only_a_moderator_assigns_evaluators(self):
		frappe.set_user(EVALUATOR)
		self.assertRaises(
			frappe.PermissionError,
			set_evaluator_assignments,
			OTHER_EVALUATOR,
			[self.course.name],
		)
		frappe.set_user("Administrator")

	def test_assignments_replace_rather_than_accumulate(self):
		second = self._create_course(title="Second Subjective Course", instructor=MODERATOR)
		self._register_evaluator(EVALUATOR, courses=[second.name])
		self.assertEqual(evaluator_courses(EVALUATOR), {second.name})
