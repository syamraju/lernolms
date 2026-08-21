# Copyright (c) 2026, Frappe and Contributors
# For license information, please see license.txt

"""Batch chat: a two-level channel tree per cohort.

    LMS Batch "March Cohort"
    ├── # announcements      staff post, everyone reads
    ├── # general            everyone
    │   ├── # python-basics  one per course in the curriculum
    │   └── # sql-fundamentals
    └── # staff-room         moderators + instructors + evaluators

**Access is derived, never synced.** Nothing is written when a student enrols or
a course is added: membership *is* the roster query, answered by
`lms.lms.batch_access`. A sync table would be a second source of truth that goes
stale the moment an enrollment is deleted directly — and stale chat membership
means a removed student keeps reading.

**Depth is capped at two**, in `LMSChatChannel.validate_depth`. Channels and
sub-channels is what the product needs; unbounded nesting makes every permission
check and every unread rollup a recursive walk for no gain.

Not built on Raven: `lms/raven_provider.py` bridges cohorts into Raven channels,
but `raven_integration` is an optional out-of-tree app that may be absent, and
its channels are workspace-scoped rather than nested under a batch. Both coexist;
this module does not touch that one.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

from lms.lms.batch_access import (
	assert_batch_member,
	assert_batch_moderator,
	batch_relation,
	is_batch_moderator,
	is_super,
	visible_batches,
)

#: Seeded on every new batch. `key` is not stored — it only distinguishes the
#: rows here — but the ordering is, via `creation`.
DEFAULT_CHANNELS = (
	{
		"title": "announcements",
		"channel_type": "Announcement",
		"audience": "Everyone",
		"post_permission": "Staff",
		"description": "Batch-wide notices from the people running this cohort.",
	},
	{
		"title": "general",
		"channel_type": "Discussion",
		"audience": "Everyone",
		"post_permission": "Everyone",
		"description": "Everything else.",
	},
	{
		"title": "staff-room",
		"channel_type": "Discussion",
		"audience": "Staff",
		"post_permission": "Staff",
		"description": "Moderators, instructors and evaluators only.",
	},
)

STAFF_RELATIONS = ("moderator", "instructor", "evaluator")


# --- access -----------------------------------------------------------------


def can_access_channel(channel, user: str | None = None) -> bool:
	"""Whether ``user`` may read ``channel``.

	``channel`` is a doc or a name. The audience field narrows the batch's own
	membership; it never widens it, so somebody outside the cohort is refused
	before audience is even consulted.
	"""
	user = user or frappe.session.user
	if is_super(user):
		return True

	if isinstance(channel, str):
		channel = frappe.db.get_value(
			"LMS Chat Channel", channel, ["name", "batch", "audience"], as_dict=True
		)
	if not channel:
		return False

	relation = batch_relation(channel.batch, user)
	if not relation:
		return False
	if relation == "moderator":
		return True

	audience = channel.audience or "Everyone"
	if audience == "Everyone":
		return True
	if audience == "Staff":
		return relation in STAFF_RELATIONS
	if audience == "Students":
		return relation == "student"
	return False


def can_moderate_channel(channel, user: str | None = None) -> bool:
	if isinstance(channel, str):
		channel = frappe.db.get_value("LMS Chat Channel", channel, ["name", "batch"], as_dict=True)
	if not channel:
		return False
	return bool(is_batch_moderator(channel.batch, user))


def can_post(channel, user: str | None = None) -> bool:
	"""Reading is not posting, and an archived channel is nobody's soapbox."""
	user = user or frappe.session.user

	if isinstance(channel, str):
		channel = frappe.db.get_value(
			"LMS Chat Channel",
			channel,
			["name", "batch", "audience", "post_permission", "is_archived"],
			as_dict=True,
		)
	if not channel:
		return False

	if not can_access_channel(channel, user):
		return False

	if cint(channel.is_archived):
		# Read-only for everyone but a moderator, who may still need to close a
		# thread out or answer a last question.
		return bool(is_batch_moderator(channel.batch, user))

	if (channel.post_permission or "Everyone") == "Staff":
		relation = batch_relation(channel.batch, user)
		return relation in STAFF_RELATIONS or is_super(user)

	return True


def assert_channel_access(channel) -> None:
	if not can_access_channel(channel):
		frappe.throw(_("You do not have access to this channel."), frappe.PermissionError)


def assert_can_post(channel) -> None:
	if not can_post(channel):
		frappe.throw(_("You cannot post in this channel."), frappe.PermissionError)


# --- seeding ----------------------------------------------------------------


def seed_default_channels(batch: str) -> None:
	"""Create the three standing channels for a new batch. Idempotent."""
	for spec in DEFAULT_CHANNELS:
		if frappe.db.exists("LMS Chat Channel", {"batch": batch, "title": spec["title"], "parent_channel": ["is", "not set"]}):
			continue
		frappe.get_doc({"doctype": "LMS Chat Channel", "batch": batch, **spec}).insert(
			ignore_permissions=True
		)


def general_channel(batch: str) -> str | None:
	return frappe.db.get_value(
		"LMS Chat Channel",
		{"batch": batch, "title": "general", "parent_channel": ["is", "not set"]},
		"name",
	)


def sync_course_channels(doc, method=None) -> None:
	"""Keep one sub-channel per course in the batch's curriculum.

	Hooked on LMS Batch's on_update. Courses added get a channel; courses removed
	get theirs **archived, not deleted** — dropping a course from a curriculum
	must not destroy the discussion that happened in it.
	"""
	if doc.doctype != "LMS Batch":
		return

	seed_default_channels(doc.name)
	parent = general_channel(doc.name)
	if not parent:
		return

	wanted = {row.course for row in (doc.courses or [])}
	existing = {
		row.course: row
		for row in frappe.get_all(
			"LMS Chat Channel",
			filters={"batch": doc.name, "channel_type": "Course"},
			fields=["name", "course", "is_archived"],
		)
		if row.course
	}

	for course in wanted - set(existing):
		title = frappe.db.get_value("LMS Course", course, "title") or course
		frappe.get_doc(
			{
				"doctype": "LMS Chat Channel",
				"batch": doc.name,
				"parent_channel": parent,
				"title": title,
				"channel_type": "Course",
				"course": course,
				"audience": "Everyone",
				"post_permission": "Everyone",
			}
		).insert(ignore_permissions=True)

	for course, row in existing.items():
		# Re-adding a course un-archives its old channel, which is the point of
		# archiving instead of deleting: the history comes back with it.
		should_archive = course not in wanted
		if bool(cint(row.is_archived)) != should_archive:
			frappe.db.set_value("LMS Chat Channel", row.name, "is_archived", int(should_archive))


# --- reads ------------------------------------------------------------------


def _channel_summary(row, unread: int) -> dict:
	return {
		"name": row.name,
		"title": row.title,
		"description": row.description,
		"channel_type": row.channel_type,
		"audience": row.audience,
		"post_permission": row.post_permission,
		"course": row.course,
		"is_archived": bool(cint(row.is_archived)),
		"unread": unread,
		"children": [],
	}


@frappe.whitelist()
def get_channel_tree(batch: str) -> list[dict]:
	"""The channel tree for one batch, filtered to what the caller may read.

	Each channel carries its message count, last message and unread count — which
	is what makes this the admin's answer to "what channels exist and what is
	being discussed in them", rather than a list of names.
	"""
	assert_batch_member(batch)
	user = frappe.session.user

	rows = frappe.get_all(
		"LMS Chat Channel",
		filters={"batch": batch},
		fields=[
			"name",
			# `batch` is what can_access_channel resolves the roster from. Leaving it
			# out does not raise — the row just carries None and every caller is
			# refused, which reads as "this cohort has no channels".
			"batch",
			"title",
			"description",
			"channel_type",
			"audience",
			"post_permission",
			"course",
			"is_archived",
			"parent_channel",
		],
		order_by="creation asc",
	)
	visible = [row for row in rows if can_access_channel(row, user)]
	if not visible:
		return []

	names = [row.name for row in visible]
	stats = _channel_stats(names)
	read_state = {
		row.channel: row.last_read_at
		for row in frappe.get_all(
			"LMS Chat Read State",
			filters={"channel": ["in", names], "user": user},
			fields=["channel", "last_read_at"],
		)
	}

	nodes = {}
	for row in visible:
		stat = stats.get(row.name, {})
		node = _channel_summary(row, _unread_count(row.name, read_state.get(row.name)))
		node.update(
			{
				"message_count": stat.get("count", 0),
				"last_message_at": stat.get("last_at"),
				"last_message_by": stat.get("last_by"),
				"last_message_preview": stat.get("preview"),
			}
		)
		nodes[row.name] = node

	tree = []
	for row in visible:
		node = nodes[row.name]
		parent = nodes.get(row.parent_channel) if row.parent_channel else None
		if parent:
			parent["children"].append(node)
		else:
			tree.append(node)
	return tree


def _channel_stats(names: list[str]) -> dict:
	"""Message count and last message per channel, in two queries rather than 2N."""
	if not names:
		return {}

	counts = frappe.db.sql(
		"""
		select channel, count(*) as count, max(creation) as last_at
		from `tabLMS Chat Message`
		where channel in %(names)s and is_deleted = 0
		group by channel
		""",
		{"names": names},
		as_dict=True,
	)
	stats = {row.channel: {"count": row.count, "last_at": row.last_at} for row in counts}

	latest = frappe.db.sql(
		"""
		select m.channel, m.sender, m.content, m.creation
		from `tabLMS Chat Message` m
		join (
			select channel, max(creation) as creation
			from `tabLMS Chat Message`
			where channel in %(names)s and is_deleted = 0
			group by channel
		) newest on newest.channel = m.channel and newest.creation = m.creation
		""",
		{"names": names},
		as_dict=True,
	)
	for row in latest:
		entry = stats.setdefault(row.channel, {"count": 0, "last_at": row.creation})
		entry["last_by"] = row.sender
		entry["preview"] = frappe.utils.strip_html(row.content or "")[:140]
	return stats


def _unread_count(channel: str, last_read_at) -> int:
	filters = {"channel": channel, "is_deleted": 0, "sender": ["!=", frappe.session.user]}
	if last_read_at:
		filters["creation"] = [">", last_read_at]
	return frappe.db.count("LMS Chat Message", filters)


@frappe.whitelist()
def get_my_channels() -> list[dict]:
	"""Every batch the caller belongs to, each with its channel tree.

	The cross-batch sidebar: a moderator with six cohorts gets one list with
	unread rolling up per batch, not six tabs to poll.
	"""
	batches = visible_batches()
	if not batches:
		return []

	titles = {
		row.name: row.title
		for row in frappe.get_all(
			"LMS Batch", filters={"name": ["in", batches]}, fields=["name", "title"]
		)
	}

	out = []
	for batch in batches:
		try:
			tree = get_channel_tree(batch)
		except frappe.PermissionError:
			continue
		if not tree:
			continue
		out.append(
			{
				"batch": batch,
				"title": titles.get(batch, batch),
				"relation": batch_relation(batch),
				"channels": tree,
				"unread": sum(_tree_unread(node) for node in tree),
			}
		)
	return out


def _tree_unread(node: dict) -> int:
	return cint(node.get("unread")) + sum(_tree_unread(child) for child in node.get("children", []))


@frappe.whitelist()
def get_messages(channel: str, limit: int = 50, before: str = None) -> list[dict]:
	"""One page of a channel's history, oldest-first within the page.

	Paged backwards from `before` so opening a channel loads the tail rather than
	the beginning of a cohort's entire conversation.
	"""
	assert_channel_access(channel)

	filters = {"channel": channel}
	if before:
		filters["creation"] = ["<", before]

	rows = frappe.get_all(
		"LMS Chat Message",
		filters=filters,
		fields=["name", "sender", "content", "attachment", "reply_to", "edited_at", "is_deleted", "creation"],
		order_by="creation desc",
		limit_page_length=min(cint(limit) or 50, 100),
	)

	senders = {row.sender for row in rows}
	people = {
		row.name: row
		for row in frappe.get_all(
			"User", filters={"name": ["in", list(senders)]}, fields=["name", "full_name", "user_image"]
		)
	} if senders else {}

	out = []
	for row in reversed(rows):
		person = people.get(row.sender)
		out.append(
			{
				"name": row.name,
				"sender": row.sender,
				"sender_name": (person.full_name if person else None) or row.sender,
				"sender_image": person.user_image if person else None,
				# A deleted message keeps its row so replies under it still have a
				# parent; the body is dropped here rather than served and hidden.
				"content": None if cint(row.is_deleted) else row.content,
				"attachment": None if cint(row.is_deleted) else row.attachment,
				"is_deleted": bool(cint(row.is_deleted)),
				"reply_to": row.reply_to,
				"edited_at": row.edited_at,
				"creation": row.creation,
			}
		)
	return out


# --- writes -----------------------------------------------------------------


@frappe.whitelist()
def post_message(channel: str, content: str, reply_to: str = None, attachment: str = None) -> dict:
	assert_can_post(channel)

	doc = frappe.get_doc(
		{
			"doctype": "LMS Chat Message",
			"channel": channel,
			"content": content,
			"reply_to": reply_to,
			"attachment": attachment,
		}
	).insert(ignore_permissions=True)

	mark_read(channel)
	return {"name": doc.name, "creation": doc.creation}


@frappe.whitelist()
def delete_message(message: str) -> None:
	"""Soft delete. The row stays so replies under it keep a parent."""
	row = frappe.db.get_value("LMS Chat Message", message, ["name", "channel", "sender"], as_dict=True)
	if not row:
		frappe.throw(_("That message does not exist."), frappe.DoesNotExistError)

	if row.sender != frappe.session.user and not can_moderate_channel(row.channel):
		frappe.throw(_("You cannot delete this message."), frappe.PermissionError)

	frappe.db.set_value("LMS Chat Message", message, {"is_deleted": 1, "content": ""})


@frappe.whitelist()
def mark_read(channel: str) -> None:
	assert_channel_access(channel)

	existing = frappe.db.exists(
		"LMS Chat Read State", {"channel": channel, "user": frappe.session.user}
	)
	if existing:
		frappe.db.set_value("LMS Chat Read State", existing, "last_read_at", now_datetime())
		return

	frappe.get_doc(
		{
			"doctype": "LMS Chat Read State",
			"channel": channel,
			"user": frappe.session.user,
			"last_read_at": now_datetime(),
		}
	).insert(ignore_permissions=True)


@frappe.whitelist()
def create_channel(
	batch: str,
	title: str,
	parent_channel: str = None,
	audience: str = "Everyone",
	post_permission: str = "Everyone",
	description: str = None,
	channel_type: str = "Discussion",
) -> dict:
	assert_batch_moderator(batch)

	doc = frappe.get_doc(
		{
			"doctype": "LMS Chat Channel",
			"batch": batch,
			"title": title,
			"parent_channel": parent_channel,
			"audience": audience,
			"post_permission": post_permission,
			"description": description,
			"channel_type": channel_type,
		}
	).insert(ignore_permissions=True)
	return {"name": doc.name}


@frappe.whitelist()
def update_channel(channel: str, **values) -> None:
	doc = frappe.get_doc("LMS Chat Channel", channel)
	assert_batch_moderator(doc.batch)

	allowed = {"title", "description", "audience", "post_permission", "is_archived"}
	for key, value in (values or {}).items():
		if key in allowed:
			doc.set(key, value)
	doc.save(ignore_permissions=True)


@frappe.whitelist()
def delete_channel(channel: str) -> None:
	"""Hard delete, with its sub-channels and messages.

	Archiving is the ordinary path and what the curriculum hooks use. This exists
	for a channel created by mistake.
	"""
	doc = frappe.get_doc("LMS Chat Channel", channel)
	assert_batch_moderator(doc.batch)
	frappe.delete_doc("LMS Chat Channel", channel, ignore_permissions=True)
