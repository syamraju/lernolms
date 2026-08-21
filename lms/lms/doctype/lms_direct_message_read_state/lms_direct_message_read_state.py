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


def _is_super(user: str | None = None) -> bool:
	"""Site administrators, who can already read the database directly.

	Deliberately a local definition: `lms.lms.batch_access.is_super` is the same
	rule and this should collapse into it the moment both live in the tree, but
	a permission hook must not import a module this commit does not ship. The
	literal "Administrator" check is not redundant with the role list -- it holds
	even on a site where somebody has stripped System Manager from that user.
	"""
	user = user or frappe.session.user
	if user == "Administrator":
		return True
	return "System Manager" in frappe.get_roles(user)


def get_permission_query_conditions(user: str | None = None) -> str:
	user = user or frappe.session.user
	if _is_super(user):
		return ""
	if user == "Guest":
		return "1 = 0"

	return f"(`tabLMS Direct Message Read State`.member = {frappe.db.escape(user)})"


def has_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
	user = user or frappe.session.user
	if _is_super(user):
		return True
	if user == "Guest":
		return False

	return (doc.get("member") if hasattr(doc, "get") else None) == user
