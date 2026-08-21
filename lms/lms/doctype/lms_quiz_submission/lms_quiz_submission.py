# Copyright (c) 2021, FOSS United and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.desk.doctype.notification_log.notification_log import make_notification_logs
from frappe.model.document import Document
from frappe.utils import cint


class LMSQuizSubmission(Document):
	def validate(self):
		# Only a new attempt can exceed the attempt limit. Re-checking on update
		# counted the row being saved, so an evaluator marking the only submission
		# of a one-attempt quiz was refused with the learner's own error.
		if self.is_new():
			self.validate_if_max_attempts_exceeded()
		self.validate_marks()
		self.set_percentage()

	def on_update(self):
		self.notify_member()

	def validate_if_max_attempts_exceeded(self):
		max_attempts = frappe.db.get_value("LMS Quiz", self.quiz, ["max_attempts"])
		if max_attempts == 0:
			return

		current_user_submission_count = frappe.db.count(
			self.doctype, filters={"quiz": self.quiz, "member": self.member}
		)
		if current_user_submission_count >= max_attempts:
			frappe.throw(
				_("You have exceeded the maximum number of attempts ({0}) for this quiz").format(
					max_attempts
				),
				MaximumAttemptsExceededError,
			)

	def validate_marks(self):
		self.score = 0
		for row in self.result:
			if cint(row.marks) > cint(row.marks_out_of):
				frappe.throw(
					_(
						"Marks for question number {0} cannot be greater than the marks allotted for that question."
					).format(row.idx)
				)
			else:
				self.score += cint(row.marks)

	def set_percentage(self):
		# Written unconditionally: an evaluator awarding zero has to move a stale
		# percentage back down to 0, not leave the previous one standing.
		self.percentage = (cint(self.score) / cint(self.score_out_of)) * 100 if self.score_out_of else 0

	def notify_member(self):
		if self.evaluation_status == "Evaluated" and self.has_value_changed("evaluation_status"):
			self.notify_evaluation_complete()
			return

		if self.score != 0 and self.has_value_changed("score"):
			notification = frappe._dict(
				{
					"subject": _("You have got a score of {0} for the quiz {1}").format(
						(frappe.bold(self.score)), frappe.bold(self.quiz_title)
					),
					"email_content": _(
						"There has been an update on your submission. You have got a score of {0} for the quiz {1}"
					).format(frappe.bold(self.score), frappe.bold(self.quiz_title)),
					"document_type": self.doctype,
					"document_name": self.name,
					"for_user": self.member,
					"from_user": frappe.session.user,
					"type": "Alert",
					"link": "",
				}
			)

			make_notification_logs(notification, [self.member])

	def notify_evaluation_complete(self):
		"""Tell the learner their subjective submission has been marked.

		notify_member's own guard skips a score of zero, which is a legitimate
		result here — and the learner has been waiting on this one, so silence is
		the wrong answer.
		"""
		subject = _("Your submission for {0} has been evaluated").format(frappe.bold(self.quiz_title))
		notification = frappe._dict(
			{
				"subject": subject,
				"email_content": _("You scored {0} out of {1} for the quiz {2}.").format(
					frappe.bold(self.score),
					frappe.bold(self.score_out_of),
					frappe.bold(self.quiz_title),
				),
				"document_type": self.doctype,
				"document_name": self.name,
				"for_user": self.member,
				"from_user": frappe.session.user,
				"type": "Alert",
				"link": "",
			}
		)
		make_notification_logs(notification, [self.member])


class MaximumAttemptsExceededError(frappe.DuplicateEntryError):
	pass
