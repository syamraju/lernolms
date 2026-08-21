# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class LMSChatReadState(Document):
	def validate(self):
		"""Read state is per-person and nobody edits somebody else's.

		This table carries unread badges only. It is deliberately *not* the access
		list — access is derived from the batch roster on every request, so a row
		here grants nothing.
		"""
		if self.user != frappe.session.user and frappe.session.user != "Administrator":
			frappe.throw(_("You can only update your own read state."), frappe.PermissionError)
