# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class LMSChatMessage(Document):
	def validate(self):
		self.validate_sender()
		self.validate_can_post()
		self.validate_reply_target()
		self.validate_content()

	def validate_sender(self):
		"""Nobody posts as somebody else.

		Set rather than checked on insert, so a forged `sender` in the payload is
		overwritten instead of rejected; on update it is pinned, so an edit cannot
		reassign authorship.
		"""
		if self.is_new():
			self.sender = frappe.session.user
			return

		before = self.get_doc_before_save()
		if before and before.sender != self.sender:
			frappe.throw(_("The author of a message cannot be changed."))

	def validate_can_post(self):
		from lms.lms.chat import assert_can_post

		if self.is_new():
			assert_can_post(self.channel)

	def validate_reply_target(self):
		if not self.reply_to:
			return

		target_channel = frappe.db.get_value("LMS Chat Message", self.reply_to, "channel")
		if target_channel != self.channel:
			frappe.throw(_("A reply must stay in the channel of the message it answers."))

	def validate_content(self):
		if self.is_deleted:
			return
		if not (self.content or "").strip() and not self.attachment:
			frappe.throw(_("A message needs either text or an attachment."))

	def before_save(self):
		if not self.is_new() and self.has_value_changed("content"):
			self.edited_at = now_datetime()


def has_permission(doc, ptype="read", user=None):
	from lms.lms.chat import can_access_channel, can_moderate_channel

	user = user or frappe.session.user
	channel = frappe.get_cached_doc("LMS Chat Channel", doc.channel)

	if ptype in ("read", "select", "print"):
		return can_access_channel(channel, user)

	# Your own message, or a moderator's cleanup.
	return doc.sender == user or can_moderate_channel(channel, user)


def get_permission_query_conditions(user=None):
	user = user or frappe.session.user
	if user == "Administrator":
		return ""

	from lms.lms.batch_access import is_super, visible_batches

	if is_super(user):
		return ""

	batches = visible_batches(user)
	if not batches:
		return "1 = 0"

	joined = ", ".join(frappe.db.escape(b) for b in batches)
	return f"""`tabLMS Chat Message`.channel in (
		select name from `tabLMS Chat Channel` where batch in ({joined})
	)"""
