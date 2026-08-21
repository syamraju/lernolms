# Copyright (c) 2025, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class LMSProgrammingExercise(Document):
	def validate(self):
		self.validate_test_cases()

	def validate_test_cases(self):
		"""An exercise needs test cases to be gradeable — but only once it is live.

		The curriculum builder creates the exercise first and the author fills
		in the problem, solution and cases across several sittings, so requiring
		them at insert would make the draft unsaveable. The guarantee that
		matters is unchanged: nothing reaches a learner without test cases,
		because publishing is what this now gates.
		"""
		if self.is_published and not self.test_cases:
			frappe.throw(_("Add at least one test case before publishing this coding exercise."))
