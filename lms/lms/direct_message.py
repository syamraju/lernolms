"""Direct messages: a thread between two people.

Deliberately separate from `lms.lms.chat`, which owns the batch channel tree.
That store is channel-scoped -- every message links to an `LMS Chat Channel`
that belongs to a cohort -- and a DM belongs to no cohort. Forcing one into the
other would mean either a channel per pair of users or a nullable channel link
that half the access rules have to special-case.

This is what a 1:1 call hangs off: you ring a person, and the ring, the call,
and the "call ended" line all need somewhere to land.

Messages are plain text on the wire and plain text on the page. The client
renders them as text nodes, never as HTML, so there is no sanitizer to get
wrong and no markup a sender can smuggle through.
"""

import json

import frappe
from frappe import _
from frappe.utils import cint, now_datetime

from lms.lms.conversation import (
	LIKE_ESCAPE,
	assert_access,
	audience,
	batch_audience,
	dm_id,
	dm_like_patterns,
	dm_peer,
	parse,
	user_card,
)
from lms.lms.conversation import title as conversation_title

EVENT_MESSAGE = "lms_direct_message"

MESSAGE_DOCTYPE = "LMS Direct Message"
READ_STATE_DOCTYPE = "LMS Direct Message Read State"

# Long enough for anything anyone types into a chat box, short enough that the
# field is not an upload channel.
MAX_MESSAGE_LENGTH = 4000

PAGE_SIZE = 50


# --- reading ------------------------------------------------------------------


@frappe.whitelist()
def get_messages(conversation: str, before: str | None = None, limit: int | str = PAGE_SIZE) -> list:
	"""One page of a thread, newest last.

	Paged backwards from `before` (a creation timestamp) because that is how a
	chat scrolls: you open at the bottom and walk into the past.
	"""
	assert_access(conversation)

	limit = min(cint(limit) or PAGE_SIZE, 100)
	filters = {"conversation": conversation}
	if before:
		filters["creation"] = ["<", before]

	rows = frappe.get_all(
		MESSAGE_DOCTYPE,
		filters=filters,
		fields=["name", "conversation", "sender", "content", "message_type", "creation"],
		order_by="creation desc",
		limit_page_length=limit,
		ignore_permissions=True,
	)

	cards = {u: user_card(u) for u in {r.sender for r in rows}}
	for row in rows:
		row.update({k: v for k, v in cards[row.sender].items() if k != "user"})

	# Fetched newest-first for the LIMIT, handed back oldest-first for the view.
	return list(reversed(rows))


@frappe.whitelist()
def get_conversations() -> list:
	"""Every DM thread the caller is part of, most recent first.

	Threads are derived from messages rather than stored: a DM with no messages
	is not a thread anyone needs listed, and deriving it means there is no
	membership row that can fall out of step with the id.
	"""
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Please sign in to continue."), frappe.AuthenticationError)

	# The id sorts its two emails, so the caller is on one side or the other.
	# Raw SQL rather than the query builder because pypika's `.like()` emits no
	# ESCAPE clause, and without one an address containing `_` matches other
	# people's threads -- the same hole the permission hook has to avoid.
	first, second = dm_like_patterns(user)
	rows = frappe.db.sql(
		f"""
		SELECT DISTINCT conversation
		FROM `tab{MESSAGE_DOCTYPE}`
		WHERE conversation LIKE %(first)s ESCAPE '{LIKE_ESCAPE}'
		   OR conversation LIKE %(second)s ESCAPE '{LIKE_ESCAPE}'
		""",
		{"first": first, "second": second},
		as_dict=True,
	)

	conversations = [r["conversation"] for r in rows]
	if not conversations:
		return []

	last_read = _read_states(user, conversations)

	out = []
	for conversation in conversations:
		peer = dm_peer(conversation, user)
		if not peer:
			continue

		latest = frappe.get_all(
			MESSAGE_DOCTYPE,
			filters={"conversation": conversation},
			fields=["content", "sender", "message_type", "creation"],
			order_by="creation desc",
			limit_page_length=1,
			ignore_permissions=True,
		)

		out.append(
			{
				"conversation": conversation,
				"kind": "dm",
				"peer": user_card(peer),
				"last_message": latest[0] if latest else None,
				"unread": _unread_count(conversation, user, last_read.get(conversation)),
			}
		)

	out.sort(key=lambda c: (c["last_message"] or {}).get("creation") or "", reverse=True)
	return out


@frappe.whitelist()
def get_thread(conversation: str) -> dict:
	"""Enough to render a thread header for a conversation the client was handed
	rather than one it listed.

	A deep link -- from a calendar entry, a reminder mail, a ring -- can name a
	thread the sidebar has never heard of. Without this the page would have to
	either refuse the link or show an untitled room.
	"""
	assert_access(conversation)
	kind, _key = parse(conversation)
	peer = dm_peer(conversation) if kind == "dm" else None

	return {
		"conversation": conversation,
		"kind": kind,
		"title": conversation_title(conversation),
		"peer": user_card(peer) if peer else None,
	}


@frappe.whitelist()
def get_people(search: str | None = None, limit: int | str = 25) -> list:
	"""People the caller may start a DM with: everyone they share a batch with.

	Scoped to shared batches rather than the whole user table on purpose --
	"who can I message" should not double as a directory of every account on
	the site.
	"""
	user = frappe.session.user
	if user == "Guest":
		frappe.throw(_("Please sign in to continue."), frappe.AuthenticationError)

	enrolled = frappe.get_all(
		"LMS Batch Enrollment", filters={"member": user}, pluck="batch", limit_page_length=0
	)
	instructing = frappe.get_all(
		"Course Instructor",
		filters={"parenttype": "LMS Batch", "instructor": user},
		pluck="parent",
		limit_page_length=0,
	)

	people = set()
	for batch in {*enrolled, *instructing}:
		people.update(batch_audience(batch))
	people.discard(user)
	if not people:
		return []

	filters = {"name": ["in", list(people)], "enabled": 1}
	or_filters = {"full_name": ["like", f"%{search}%"], "name": ["like", f"%{search}%"]} if search else None

	return frappe.get_all(
		"User",
		filters=filters,
		or_filters=or_filters,
		fields=["name as user", "full_name", "user_image as avatar"],
		order_by="full_name asc",
		limit_page_length=min(cint(limit) or 25, 100),
		ignore_permissions=True,
	)


def _read_states(user: str, conversations: list) -> dict:
	rows = frappe.get_all(
		READ_STATE_DOCTYPE,
		filters={"member": user, "conversation": ["in", conversations]},
		fields=["conversation", "last_read_at"],
		limit_page_length=0,
		ignore_permissions=True,
	)
	# A duplicate pair can exist if two tabs marked read at once; the later
	# timestamp is the true one, so fold rather than assume uniqueness.
	out = {}
	for row in rows:
		current = out.get(row.conversation)
		if not current or (row.last_read_at and row.last_read_at > current):
			out[row.conversation] = row.last_read_at
	return out


def _unread_count(conversation: str, user: str, last_read_at) -> int:
	filters = {"conversation": conversation, "sender": ["!=", user]}
	if last_read_at:
		filters["creation"] = [">", last_read_at]
	return frappe.db.count(MESSAGE_DOCTYPE, filters)


# --- writing ------------------------------------------------------------------


@frappe.whitelist()
def send_message(conversation: str, content: str) -> dict:
	"""Post to a thread and push it to everyone in it."""
	people = assert_access(conversation)

	content = (content or "").strip()
	if not content:
		frappe.throw(_("Write something first."))
	if len(content) > MAX_MESSAGE_LENGTH:
		frappe.throw(_("That message is too long ({0} characters max).").format(MAX_MESSAGE_LENGTH))

	message = _insert(conversation, frappe.session.user, content, "Message")
	# The sender has read what they just wrote; not marking it leaves them with
	# an unread badge on their own message.
	mark_read(conversation)
	_publish(message, people)
	return message


@frappe.whitelist()
def start_dm(user: str) -> dict:
	"""Resolve (and authorize) the thread id for a person, without posting.

	Opening a DM should not write anything -- a thread you opened and closed
	without typing is not a conversation, and listing it as one is noise.
	"""
	conversation = dm_id(frappe.session.user, user)
	assert_access(conversation)
	return {"conversation": conversation, "peer": user_card(dm_peer(conversation))}


@frappe.whitelist()
def mark_read(conversation: str) -> dict:
	assert_access(conversation)

	user = frappe.session.user
	name = frappe.db.get_value(READ_STATE_DOCTYPE, {"member": user, "conversation": conversation})
	if name:
		frappe.db.set_value(READ_STATE_DOCTYPE, name, "last_read_at", now_datetime())
	else:
		frappe.get_doc(
			{
				"doctype": READ_STATE_DOCTYPE,
				"member": user,
				"conversation": conversation,
				"last_read_at": now_datetime(),
			}
		).insert(ignore_permissions=True)

	return {"conversation": conversation, "unread": 0}


def post_system_message(conversation: str, content: str) -> dict | None:
	"""The call's way of leaving a trace in the thread.

	Not whitelisted: "the app said this" is a claim only the app gets to make.
	Best-effort -- a call must not fail because its announcement did.
	"""
	try:
		people = audience(conversation)
		message = _insert(conversation, frappe.session.user, content, "System")
		_publish(message, people)
		return message
	except Exception:
		frappe.log_error(title="Huddle system message failed", message=frappe.get_traceback())
		return None


def _insert(conversation: str, sender: str, content: str, message_type: str) -> dict:
	doc = frappe.get_doc(
		{
			"doctype": MESSAGE_DOCTYPE,
			"conversation": conversation,
			"sender": sender,
			"content": content,
			"message_type": message_type,
		}
	).insert(ignore_permissions=True)

	return {
		"name": doc.name,
		"conversation": conversation,
		"sender": sender,
		"content": content,
		"message_type": message_type,
		"creation": doc.creation,
		**{k: v for k, v in user_card(sender).items() if k != "user"},
	}


def _publish(message: dict, people: list) -> None:
	"""Addressed per person rather than to a doc room: there is no document to
	subscribe to, and a DM's audience is two."""
	for user in people:
		frappe.publish_realtime(EVENT_MESSAGE, message, user=user, after_commit=True)
