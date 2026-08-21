# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

"""Row scoping for direct messages.

The whitelisted API in `lms.lms.direct_message` calls `assert_access` and then
reads with `ignore_permissions=True`, so none of this is on the app's own path.
It exists because `/api/resource/LMS Direct Message` and
`frappe.client.get_list` are a SECOND door onto the same rows, and the app's
access checks do not run on that door. Without the two functions below -- and
without hooks.py naming them -- a role grant on this doctype is a grant over
every private thread on the site.

The scope is derived from the conversation id rather than a membership table:
a DM id is `dm:<a>|<b>` with the two emails sorted, so "am I in this thread" is
answerable in SQL without a join.
"""

import frappe
from frappe.model.document import Document

from lms.lms.conversation import LIKE_ESCAPE, dm_like_patterns


class LMSDirectMessage(Document):
	pass


def get_permission_query_conditions(user: str | None = None) -> str:
	"""Restrict list/report queries to threads the caller is part of."""
	# The shared definition, not a local one. Two notions of "super user" inside
	# one permission layer is a drift waiting to happen, and this one also
	# covers Administrator explicitly rather than relying on its role list.
	from lms.lms.batch_access import is_super

	user = user or frappe.session.user
	if is_super(user):
		return ""

	# Guest has no threads, and LIKE 'dm:guest|%' would be a lie rather than a
	# refusal, so say so explicitly. Compared against frappe's literal session
	# value, the same way the read-state hook does it.
	if user == "Guest":
		return "1 = 0"

	first, second = dm_like_patterns(user)
	# ESCAPE is not optional here: without it `_` in an address is a wildcard
	# and this condition widens access instead of narrowing it.
	#
	# One caveat this function cannot enforce for itself: frappe.db.escape
	# doubles every `%`, and the doubling is undone by MySQLdb's `query % args`
	# only on a call that passes args. get_list always does, which is the only
	# caller of a permission query condition -- but the correctness of the `%`
	# branch is therefore a property of the CALLER, not of the string returned
	# here. The `_` branch, which is the exploitable one (Frappe will not let
	# anyone register an address containing `%`), needs no such help: escape()
	# does not touch underscores, so `a!_b@x.com` reaches MySQL intact.
	return (
		f"(`tabLMS Direct Message`.conversation LIKE {frappe.db.escape(first)} ESCAPE '{LIKE_ESCAPE}'"
		f" OR `tabLMS Direct Message`.conversation LIKE {frappe.db.escape(second)} ESCAPE '{LIKE_ESCAPE}')"
	)


def has_permission(doc, ptype: str | None = None, user: str | None = None) -> bool:
	"""Single-document access: you must be one of the two people in the id."""
	from lms.lms.batch_access import is_super

	user = user or frappe.session.user
	if is_super(user):
		return True
	if user == "Guest":
		return False

	conversation = (doc.get("conversation") if hasattr(doc, "get") else None) or ""
	if not conversation.startswith("dm:"):
		return False

	# The id's addresses are lowercased at construction, so the comparison has
	# to be too -- but only here, not on the `user` used for the Guest check.
	return user.strip().lower() in conversation[len("dm:") :].split("|")
