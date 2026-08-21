# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from lms.lms.batch_access import assert_batch_moderator


class LMSBatchInviteLink(Document):
	def validate(self):
		"""A link is a delegation of the batch's front door, so minting one
		requires the same standing as opening it by hand."""
		assert_batch_moderator(self.batch)

		if self.max_uses and self.max_uses < 0:
			frappe.throw(_("Max uses cannot be negative."))

	def on_trash(self):
		assert_batch_moderator(self.batch)


def has_permission(doc, ptype="read", user=None):
	from lms.lms.batch_access import is_batch_moderator

	return bool(is_batch_moderator(doc.batch, user))


def get_permission_query_conditions(user=None):
	"""Only a moderator of the batch sees its links.

	Mirrors LMS Batch's own query rather than reusing it: an invite link is an
	administrative object, so published-ness — which opens the batch listing to
	everyone — must not open this.
	"""
	user = user or frappe.session.user
	if user == "Administrator":
		return ""

	from lms.lms.batch_access import is_super

	if is_super(user):
		return ""

	escaped = frappe.db.escape(user)
	return f"""(`tabLMS Batch Invite Link`.batch in (
		select name from `tabLMS Batch` where owner = {escaped}
		union
		select parent from `tabBatch Moderator`
		where parenttype = 'LMS Batch' and moderator = {escaped}
	))"""
