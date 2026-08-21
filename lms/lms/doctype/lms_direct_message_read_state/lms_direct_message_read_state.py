# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

"""Row scoping for DM read cursors.

Same reasoning as `lms_direct_message`: the app reads these with
`ignore_permissions=True`, so this exists solely to close the generic REST door.
A read cursor is less sensitive than a message, but it still says who has been
talking to whom and when they last looked, which is nobody else's business.

Scoped on `member` rather than on the conversation id: a read state belongs to
exactly one person by construction.
"""

import frappe
from frappe.model.document import Document


class LMSDirectMessageReadState(Document):
	pass


def get_permission_query_conditions(user: str | None = None) -> str:
	# The shared definition, matching the message hook and the chat doctypes.
	from lms.lms.batch_access import is_super

	user = user or frappe.session.user
	if is_super(user):
		return ""
	if user == "Guest":
		return "1 = 0"

	return f"(`tabLMS Direct Message Read State`.member = {frappe.db.escape(user)})"


def has_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
	from lms.lms.batch_access import is_super

	user = user or frappe.session.user
	if is_super(user):
		return True
	if user == "Guest":
		return False

	return (doc.get("member") if hasattr(doc, "get") else None) == user
