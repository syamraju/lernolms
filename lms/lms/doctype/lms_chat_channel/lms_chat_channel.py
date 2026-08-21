# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class LMSChatChannel(Document):
	def validate(self):
		self.validate_depth()
		self.validate_parent_batch()
		self.validate_course()

	def validate_depth(self):
		"""Channels and sub-channels. Two levels, not a tree.

		Unbounded nesting turns every permission check and every unread rollup
		into a recursive walk, for no gain a topic sub-channel does not already
		give. The cap is enforced here rather than assumed by the UI.
		"""
		if not self.parent_channel:
			return

		if self.parent_channel == self.name:
			frappe.throw(_("A channel cannot be its own parent."))

		grandparent = frappe.db.get_value("LMS Chat Channel", self.parent_channel, "parent_channel")
		if grandparent:
			frappe.throw(_("A sub-channel cannot hold sub-channels of its own."))

	def validate_parent_batch(self):
		"""A sub-channel belongs to the same batch as its parent.

		Without this a channel could be re-parented across cohorts, which would
		hand every member of one batch a channel scoped to another — the access
		rules read `batch` off the channel and would have no way to notice.
		"""
		if not self.parent_channel:
			return

		parent_batch = frappe.db.get_value("LMS Chat Channel", self.parent_channel, "batch")
		if parent_batch != self.batch:
			frappe.throw(_("A sub-channel must belong to the same batch as its parent channel."))

	def validate_course(self):
		if self.channel_type != "Course":
			self.course = None
			return

		if not self.course:
			frappe.throw(_("A course channel must name a course."))

	def on_trash(self):
		"""Deleting a channel takes its sub-channels and messages with it.

		Reached from `lms.lms.chat.delete_channel`, which is moderator-gated, and
		from `lms.lms.chat.remove_channels_for`, the on_trash hook that clears a
		batch's or a course's channels when the record they belong to is deleted.

		Archiving is the ordinary path and the one the curriculum hooks use: a
		course dropped from a batch keeps its channel, because the course still
		exists and the discussion is still about something. This runs when the
		batch or course itself is going.
		"""
		for child in frappe.get_all("LMS Chat Channel", filters={"parent_channel": self.name}, pluck="name"):
			frappe.delete_doc("LMS Chat Channel", child, ignore_permissions=True, force=True)

		frappe.db.delete("LMS Chat Message", {"channel": self.name})
		frappe.db.delete("LMS Chat Read State", {"channel": self.name})


def has_permission(doc, ptype="read", user=None):
	from lms.lms.chat import can_access_channel, can_moderate_channel

	if ptype in ("read", "select", "print"):
		return can_access_channel(doc, user)
	return can_moderate_channel(doc, user)


def get_permission_query_conditions(user=None):
	"""Channels of batches the user is attached to.

	Published-ness deliberately does not appear: seeing a cohort advertised is not
	being in it, and a channel is the inside of the cohort. The audience filter is
	applied on top of this in `lms.lms.chat.get_channel_tree` — SQL that reproduced
	the whole staff/student split would be a second copy of the access rules.
	"""
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
	return f"`tabLMS Chat Channel`.batch in ({joined})"
