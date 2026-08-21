"""What a "conversation" is, and who is allowed in one.

Chat threads and huddles are two views of the same thing, so the membership
rule lives here rather than in either of them: a person who can read a thread
can join its call, and a person who cannot, cannot. Splitting that rule across
two modules is how the two drift apart and one of them becomes a hole.

A conversation id is ``"<kind>:<key>"``:

  * ``batch:<LMS Batch>``        -- the batch discussion thread
  * ``channel:<LMS Chat Channel>`` -- one channel of a batch's channel tree
  * ``dm:<user-a>|<user-b>``     -- a direct 1:1 thread, emails sorted
  * ``class:<LMS Live Class>``   -- a scheduled live session

New kinds need a branch in `audience` and nothing else. Everything downstream --
messages, rosters, signalling, badges -- is written against the id alone.
"""

import frappe
from frappe import _

KINDS = ("batch", "channel", "dm", "class")


def parse(conversation: str) -> tuple[str, str]:
	"""Split ``"<kind>:<key>"``, rejecting anything not of a known kind.

	Partitions on the FIRST colon: a doc name may legitimately contain one.
	"""
	if not conversation or ":" not in conversation:
		frappe.throw(_("Invalid conversation."))

	kind, _sep, key = conversation.partition(":")
	if kind not in KINDS or not key:
		frappe.throw(_("Invalid conversation."))

	return kind, key


def dm_id(user_a: str, user_b: str) -> str:
	"""The canonical id for a 1:1 thread.

	Sorted, so both ends derive the same id without asking who started it -- the
	same trick the mesh uses to agree on an offer initiator without a coin toss.
	"""
	pair = sorted([(user_a or "").strip().lower(), (user_b or "").strip().lower()])
	if not all(pair) or pair[0] == pair[1]:
		frappe.throw(_("A direct message needs two different people."))
	return f"dm:{pair[0]}|{pair[1]}"


def dm_peer(conversation: str, user: str | None = None) -> str | None:
	"""The other person in a DM, or None if this isn't one."""
	kind, key = parse(conversation)
	if kind != "dm":
		return None

	user = (user or frappe.session.user).strip().lower()
	return next((u for u in key.split("|") if u != user), None)


def batch_audience(batch: str) -> list:
	if not frappe.db.exists("LMS Batch", batch):
		frappe.throw(_("Batch not found."), frappe.DoesNotExistError)

	members = frappe.get_all(
		"LMS Batch Enrollment", filters={"batch": batch}, pluck="member", limit_page_length=0
	)
	instructors = frappe.get_all(
		"Course Instructor",
		filters={"parenttype": "LMS Batch", "parent": batch},
		pluck="instructor",
		limit_page_length=0,
	)
	moderators = frappe.get_all(
		"Batch Moderator", filters={"parent": batch}, pluck="moderator", limit_page_length=0
	)
	return list({u for u in (members + instructors + moderators) if u})


# The character that escapes the others in our LIKE patterns. Any character
# would do; `!` is chosen because it cannot appear unquoted in an email address,
# so the doubling below is effectively never exercised.
LIKE_ESCAPE = "!"


def like_literal(value: str) -> str:
	"""Make `value` match itself literally inside a LIKE pattern.

	`_` matches any single character in SQL LIKE, and underscores are legal and
	common in email local parts. Without this, the scoping pattern for
	`a_b@x.com` also matches `axb@x.com`, so anyone who can self-register an
	address that LIKE-matches their target reads that target's private threads
	through the very query condition meant to stop them. `%` is legal too, in a
	quoted local part, and is the same bug with a wider blast radius.

	`frappe.db.escape` does not help here: it quotes, it does not neutralise
	LIKE metacharacters. Callers must pair this with `ESCAPE '!'`.
	"""
	return (
		value.replace(LIKE_ESCAPE, LIKE_ESCAPE * 2)
		.replace("%", f"{LIKE_ESCAPE}%")
		.replace("_", f"{LIKE_ESCAPE}_")
	)


def dm_like_patterns(user: str) -> tuple[str, str]:
	"""The two patterns matching every DM id this person is a party to.

	Two rather than one because the id sorts its pair, so the caller is either
	the first address or the second. The wildcards around the escaped address
	are deliberately NOT escaped -- they are ours.
	"""
	safe = like_literal(user.strip().lower())
	return f"dm:{safe}|%", f"dm:%|{safe}"


def batches_of(user: str) -> set:
	"""Every batch a person is attached to, in any capacity."""
	enrolled = frappe.get_all(
		"LMS Batch Enrollment", filters={"member": user}, pluck="batch", limit_page_length=0
	)
	instructing = frappe.get_all(
		"Course Instructor",
		filters={"parenttype": "LMS Batch", "instructor": user},
		pluck="parent",
		limit_page_length=0,
	)
	moderating = frappe.get_all(
		"Batch Moderator", filters={"moderator": user}, pluck="parent", limit_page_length=0
	)
	return {b for b in (*enrolled, *instructing, *moderating) if b}


def dm_allowed(pair: list) -> bool:
	"""Whether these two people may hold a direct thread at all.

	Being *named in the id* is not enough. Anyone can compose
	``dm:<someone>|<me>`` for any address on the site, so without this the guard
	would let a stranger open a thread with -- and ring, and call -- any user
	whose email they could guess, while `get_people` was still telling the UI
	that only batchmates are reachable. A rule the UI applies and the API does
	not is not a rule.

	Sharing a batch is the relationship the LMS actually has. An existing thread
	also qualifies, so a conversation does not become unreadable to the two
	people in it the moment their cohort ends.
	"""
	a, b = pair
	if batches_of(a) & batches_of(b):
		return True

	return bool(frappe.db.exists("LMS Direct Message", {"conversation": dm_id(a, b)}))


def channel_audience(channel: str) -> list:
	"""Who may read one channel of a batch's channel tree.

	Delegates the rule to `lms.lms.chat` rather than restating it: a channel's
	audience narrows its batch's membership, and a second copy of that rule here
	would be the copy that goes stale when the first one changes. The cost is a
	membership check per batch member, paid only when a call starts or ends.
	"""
	from lms.lms.chat import can_access_channel

	row = frappe.db.get_value(
		"LMS Chat Channel", channel, ["name", "batch", "audience"], as_dict=True
	)
	if not row:
		frappe.throw(_("Channel not found."), frappe.DoesNotExistError)

	return [u for u in batch_audience(row.batch) if can_access_channel(row, u)]


def audience(conversation: str) -> list:
	"""Everyone entitled to see this conversation.

	Deliberately one function for two jobs -- the join guard and the address
	list for "a call started here" badges. If they were two lists they would
	eventually disagree, and the disagreement would read as either a leak or a
	notification nobody can act on.
	"""
	kind, key = parse(conversation)

	if kind == "batch":
		return batch_audience(key)

	if kind == "channel":
		return channel_audience(key)

	if kind == "class":
		batch = frappe.db.get_value("LMS Live Class", key, "batch_name")
		if not batch:
			frappe.throw(_("Live class not found."), frappe.DoesNotExistError)
		return batch_audience(batch)

	# dm: the two people named in the id, and nobody else -- there is no
	# membership table to consult, because the id *is* the membership.
	return [u for u in key.split("|") if u]


def assert_access(conversation: str) -> list:
	"""Guard + audience in one call, so no caller can guard without also
	learning who to tell."""
	if frappe.session.user == "Guest":
		frappe.throw(_("Please sign in to continue."), frappe.AuthenticationError)

	kind, _key = parse(conversation)
	people = audience(conversation)

	if frappe.session.user in people:
		# A DM needs a reason to exist beyond one party having typed the other's
		# address into the id.
		if kind == "dm" and not dm_allowed(people):
			frappe.throw(
				_("You can only message people you share a batch with."), frappe.PermissionError
			)
		return people

	# Staff can drop into a shared conversation to help -- their presence shows
	# in the roster and the thread, so it is not a silent read. A DM is NOT such
	# a conversation: two people's private thread is not a room to walk into,
	# and a Moderator role should not be a licence to read it.
	roles = frappe.get_roles()
	if kind != "dm" and ("Moderator" in roles or "System Manager" in roles):
		return list({*people, frappe.session.user})

	frappe.throw(_("You do not have access to this conversation."), frappe.PermissionError)


def can_access(conversation: str) -> bool:
	"""The non-throwing form, for batched lookups where one bad id in a list of
	twenty must not fail the other nineteen."""
	try:
		assert_access(conversation)
		return True
	except (
		frappe.PermissionError,
		frappe.DoesNotExistError,
		frappe.ValidationError,
		frappe.AuthenticationError,
	):
		return False


def user_card(user: str) -> dict:
	"""The minimum a client needs to render a person: who, name, face."""
	full_name, avatar = frappe.db.get_value("User", user, ["full_name", "user_image"]) or (user, None)
	return {"user": user, "full_name": full_name or user, "avatar": avatar}


def title(conversation: str, viewer: str | None = None) -> str:
	"""A human label for the thread, from the viewer's side of it."""
	kind, key = parse(conversation)

	if kind == "batch":
		return frappe.db.get_value("LMS Batch", key, "title") or key

	if kind == "channel":
		return frappe.db.get_value("LMS Chat Channel", key, "title") or key

	if kind == "class":
		return frappe.db.get_value("LMS Live Class", key, "title") or key

	peer = dm_peer(conversation, viewer)
	return (frappe.db.get_value("User", peer, "full_name") if peer else None) or peer or key
