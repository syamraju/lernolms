"""Huddles: in-app audio/video calls that hang off a chat conversation.

A huddle is a *facet of a conversation*, not a separate object a user has to
manage: someone hits the call button in a thread, everyone else in that thread
sees "Huddle active — Join", and it ends by itself when the last person leaves.
That is the Slack/Teams shape, and it is the one the frontend is built to.

Media is peer-to-peer mesh. This module never touches media -- it owns three
things only:

  * **the roster** -- who is in the call right now, and their mute/camera/screen
    flags. Kept in Redis, not in a doctype: a huddle lives for minutes, is
    written on every toggle, and is worthless once it ends. A doctype would buy
    durability nobody wants and pay for it with table churn.
  * **the relay** -- SDP offers/answers and ICE candidates forwarded verbatim
    between two peers over Frappe's realtime socket. Payloads are never
    inspected or rewritten here; the browsers own that contract.
  * **access** -- whether the caller may be in this conversation at all,
    answered once per call from the LMS's own membership tables.

Conversation ids, membership and access all come from `lms.lms.conversation`:
this module is kind-agnostic, so a new conversation kind gains calls for free.
"""

import json
import time

import frappe
from frappe import _
from frappe.utils import cint

from lms.lms.direct_message import post_system_message
from lms.lms.conversation import assert_access, audience, can_access, parse, user_card

# --- storage -----------------------------------------------------------------

CACHE_PREFIX = "lms_huddle"

# A huddle key outlives any plausible call but not the day, so a process that
# dies mid-call cannot strand a "call in progress" badge forever.
HUDDLE_TTL = 4 * 60 * 60

# A peer that has not heartbeated in this long is treated as gone. Generous
# enough to survive a laptop sleeping through a GC pause, short enough that a
# closed tab does not haunt the roster for a whole minute.
PEER_TTL = 45

# The client heartbeats at half this, so one dropped beat is not a disconnect.
HEARTBEAT_INTERVAL = 20

# Mesh, not SFU: every added peer costs every other peer another upstream. This
# is the point past which the call degrades for everyone rather than for the
# joiner, so it is refused rather than allowed to spoil the room.
MAX_PARTICIPANTS = 8

# --- realtime event names (mirrored in frontend/src/composables/useHuddle.ts) --

EVENT_SIGNAL = "lms_huddle_signal"
EVENT_ROSTER = "lms_huddle_roster"
EVENT_LIFECYCLE = "lms_huddle_lifecycle"
EVENT_RING = "lms_huddle_ring"

# Relayed verbatim, but only these three: the relay is not a general-purpose
# message bus between browsers.
SIGNAL_KINDS = ("offer", "answer", "ice")


def _key(conversation: str) -> str:
	return f"{CACHE_PREFIX}:{conversation}"


def _lock_key(conversation: str) -> str:
	return f"{CACHE_PREFIX}:lock:{conversation}"


class _RosterLock:
	"""SET NX EX around a read-modify-write of one huddle's roster.

	Two people hitting Join in the same instant otherwise race and one of them
	is silently dropped from the roster -- a peer nobody offers to, sitting in a
	call that looks empty to them. `frappe.cache()` is a redis.Redis subclass,
	so the atomic primitive is right there.
	"""

	def __init__(self, conversation: str, timeout: float = 3.0):
		# make_key() by hand: the atomic SET NX below is a raw redis call, and
		# raw calls skip the per-site prefixing that set_value() does for us.
		self.name = frappe.cache().make_key(_lock_key(conversation))
		self.timeout = timeout
		self.held = False

	def __enter__(self):
		deadline = time.monotonic() + self.timeout
		while time.monotonic() < deadline:
			if frappe.cache().set(self.name, b"1", nx=True, ex=5):
				self.held = True
				return self
			time.sleep(0.02)
		# Proceeding unlocked beats failing the join: the worst case is the race
		# above, which the next heartbeat repairs, and blocking a call on a
		# stuck lock is worse than a rare re-announce.
		return self

	def __exit__(self, *exc):
		if self.held:
			frappe.cache().delete(self.name)
		return False


def _read(conversation: str) -> dict | None:
	raw = frappe.cache().get_value(_key(conversation))
	if not raw:
		return None
	if isinstance(raw, bytes):
		raw = raw.decode("utf-8")
	try:
		return json.loads(raw)
	except (ValueError, TypeError):
		return None


def _write(conversation: str, huddle: dict) -> None:
	frappe.cache().set_value(_key(conversation), json.dumps(huddle), expires_in_sec=HUDDLE_TTL)


def _clear(conversation: str) -> None:
	frappe.cache().delete_value(_key(conversation))


# --- roster ------------------------------------------------------------------


def _now() -> float:
	return time.time()


def _prune(huddle: dict) -> dict:
	"""Drop peers whose heartbeat has lapsed.

	A closed laptop lid sends no `leave`, so without this every abandoned call
	stays "active" and the thread shows a Join button into an empty room.
	"""
	cutoff = _now() - PEER_TTL
	live = {u: p for u, p in huddle.get("participants", {}).items() if p.get("seen_at", 0) >= cutoff}
	return {**huddle, "participants": live}


def _public(huddle: dict) -> dict:
	"""The roster shape the client consumes. `seen_at` stays server-side."""
	return {
		"id": huddle["id"],
		"conversation": huddle["conversation"],
		"started_by": huddle["started_by"],
		"started_at": huddle["started_at"],
		"participants": [
			{
				"user": p["user"],
				"full_name": p["full_name"],
				"avatar": p.get("avatar"),
				"peer_id": p["peer_id"],
				"joined_at": p["joined_at"],
				"muted": bool(p.get("muted")),
				"video": bool(p.get("video")),
				"screensharing": bool(p.get("screensharing")),
			}
			for p in sorted(huddle.get("participants", {}).values(), key=lambda p: p["joined_at"])
		],
	}


def _publish_roster(huddle: dict) -> None:
	"""Tell the people *in* the call that the roster moved.

	Addressed per-user rather than to a room: Frappe's doc rooms require a
	subscription that a cache-backed huddle has no document to hang off, and a
	live roster is a handful of people anyway.
	"""
	payload = _public(huddle)
	for user in huddle.get("participants", {}):
		frappe.publish_realtime(EVENT_ROSTER, payload, user=user)


def _publish_lifecycle(conversation: str, people: list, huddle: dict | None) -> None:
	"""Tell the whole thread that a call started or ended -- the badge, not the
	roster. Sent to people who are *not* in the call, which is the point."""
	payload = {
		"conversation": conversation,
		"active": bool(huddle and huddle.get("participants")),
		"participant_count": len(huddle.get("participants", {})) if huddle else 0,
		"started_by": huddle.get("started_by") if huddle else None,
	}
	for user in people:
		frappe.publish_realtime(EVENT_LIFECYCLE, payload, user=user)


# --- announcements ------------------------------------------------------------

HUDDLE_STARTED = "\U0001f3a7 Huddle started"


def _ended_body(duration: float) -> str:
	"""\"Huddle ended (3m 12s)\" -- the duration is the whole point of the
	message, since by the time you read it the call is gone."""
	total = max(0, int(duration))
	minutes, seconds = divmod(total, 60)
	return f"Huddle ended ({minutes}m {seconds}s)" if minutes else f"Huddle ended ({seconds}s)"


def _announce(conversation: str, body: str) -> None:
	"""Leave a trace of the call in the thread -- but only where the thread is
	this app's message store.

	Only a DM is backed by `lms.lms.direct_message`. A batch channel's history
	lives in `lms.lms.chat`'s own message store and a batch thread's in LMS
	Discussion, so a system message written here would land in a table neither
	of them reads. Those calls announce themselves live instead, through the
	lifecycle badge, and leave no history behind.
	"""
	kind, _key = parse(conversation)
	if kind != "dm":
		return

	post_system_message(conversation, body)


# --- api ---------------------------------------------------------------------


@frappe.whitelist()
def get_config() -> dict:
	"""ICE servers + the timings the client paces itself by.

	STUN alone gets most pairs connected; a TURN relay is what rescues the rest
	(symmetric NAT, corporate networks). TURN is configured per-site rather than
	shipped, because it needs credentials nobody should be reading out of source.
	"""
	ice = [{"urls": ["stun:stun.l.google.com:19302", "stun:stun1.l.google.com:19302"]}]

	turn_url = frappe.conf.get("huddle_turn_url")
	if turn_url:
		ice.append(
			{
				"urls": turn_url if isinstance(turn_url, list) else [turn_url],
				"username": frappe.conf.get("huddle_turn_username"),
				"credential": frappe.conf.get("huddle_turn_credential"),
			}
		)

	return {
		"ice_servers": ice,
		"heartbeat_interval": HEARTBEAT_INTERVAL,
		"max_participants": MAX_PARTICIPANTS,
	}


@frappe.whitelist()
def join(conversation: str, peer_id: str, video: int | str = 0) -> dict:
	"""Start the call if there isn't one, or take a seat in the one there is.

	One call per conversation, always: two people pressing the button at the
	same moment land in the same room rather than in two rooms of one.
	"""
	assert_access(conversation)
	if not peer_id:
		frappe.throw(_("Missing peer id."))

	user = frappe.session.user
	kind, _key = parse(conversation)

	with _RosterLock(conversation):
		huddle = _prune(_read(conversation) or {})
		fresh = not huddle.get("participants")

		if fresh:
			huddle = {
				"id": frappe.generate_hash(length=12),
				"conversation": conversation,
				"kind": kind,
				"started_by": user,
				"started_at": _now(),
				"participants": {},
			}

		participants = dict(huddle.get("participants", {}))
		if user not in participants and len(participants) >= MAX_PARTICIPANTS:
			frappe.throw(
				_("This call is full ({0} people).").format(MAX_PARTICIPANTS),
				frappe.ValidationError,
			)

		card = user_card(user)
		existing = participants.get(user)
		# A rejoin from a second tab replaces the row rather than adding one --
		# the roster is keyed by person, so the newest tab wins the seat and the
		# old one stops being offered to.
		participants[user] = {
			**card,
			"peer_id": peer_id,
			"joined_at": existing["joined_at"] if existing else _now(),
			"seen_at": _now(),
			"muted": bool(existing.get("muted")) if existing else False,
			"video": bool(cint(video)),
			"screensharing": False,
		}
		huddle = {**huddle, "participants": participants}
		_write(conversation, huddle)

	_publish_roster(huddle)
	if fresh:
		_publish_lifecycle(conversation, audience(conversation), huddle)
		_announce(conversation, HUDDLE_STARTED)

	return {"huddle": _public(huddle), "self": {"user": user, "peer_id": peer_id}}


@frappe.whitelist()
def leave(conversation: str, peer_id: str | None = None) -> dict:
	"""Give up the seat. Ends the huddle when it empties the room."""
	assert_access(conversation)
	user = frappe.session.user

	with _RosterLock(conversation):
		huddle = _read(conversation)
		if not huddle:
			return {"huddle": None}

		participants = dict(_prune(huddle).get("participants", {}))
		seat = participants.get(user)
		# A stale tab's leave must not evict the tab that replaced it.
		if seat and (not peer_id or seat.get("peer_id") == peer_id):
			participants.pop(user, None)

		huddle = {**huddle, "participants": participants}
		if participants:
			_write(conversation, huddle)
		else:
			_clear(conversation)

	_publish_roster(huddle)
	if not huddle["participants"]:
		_publish_lifecycle(conversation, audience(conversation), None)
		_announce(conversation, _ended_body(_now() - huddle.get("started_at", _now())))

	return {"huddle": _public(huddle) if huddle["participants"] else None}


@frappe.whitelist()
def heartbeat(conversation: str, peer_id: str) -> dict:
	"""Keep the seat, and collect whatever the roster looks like now.

	Doubles as the reconciliation path: a client that missed a realtime frame
	while backgrounded is corrected here within one interval, so the mesh never
	drifts from the server's idea of who is present.
	"""
	assert_access(conversation)
	user = frappe.session.user

	with _RosterLock(conversation):
		huddle = _read(conversation)
		if not huddle:
			return {"huddle": None}

		pruned = _prune(huddle)
		before = set(pruned.get("participants", {}))
		participants = dict(pruned.get("participants", {}))
		seat = participants.get(user)
		if not seat or seat.get("peer_id") != peer_id:
			# Someone else's tab holds this seat now; report the truth rather
			# than stealing it back.
			huddle = {**huddle, "participants": participants}
			if participants:
				_write(conversation, huddle)
			else:
				_clear(conversation)
			return {"huddle": _public(huddle) if participants else None, "evicted": True}

		participants[user] = {**seat, "seen_at": _now()}
		huddle = {**huddle, "participants": participants}
		if participants:
			_write(conversation, huddle)
		else:
			_clear(conversation)

	# Only announce when the prune actually removed someone -- a heartbeat that
	# changes nothing must not cost every peer a re-render.
	if before - set(huddle["participants"]):
		_publish_roster(huddle)
		if not huddle["participants"]:
			_publish_lifecycle(conversation, audience(conversation), None)
			_announce(conversation, _ended_body(_now() - huddle.get("started_at", _now())))

	return {"huddle": _public(huddle) if huddle["participants"] else None}


@frappe.whitelist()
def signal(conversation: str, to_user: str, to_peer: str, kind: str, payload: str | dict) -> dict:
	"""Forward one SDP/ICE frame to one peer, verbatim.

	Nothing here parses or rewrites the payload: the offer/answer contract lives
	between the two browsers, and a server that "helpfully" normalizes SDP is a
	server that breaks codecs it has never heard of.
	"""
	assert_access(conversation)

	if kind not in SIGNAL_KINDS:
		frappe.throw(_("Unknown signal."))

	huddle = _read(conversation)
	if not huddle:
		return {"delivered": False}

	participants = _prune(huddle).get("participants", {})
	if frappe.session.user not in participants:
		frappe.throw(_("You are not in this call."), frappe.PermissionError)

	target = participants.get(to_user)
	if not target or target.get("peer_id") != to_peer:
		# The peer left, or reloaded into a new peer id. Dropping the frame is
		# correct: the roster event that follows will drive a fresh negotiation.
		return {"delivered": False}

	if isinstance(payload, str):
		try:
			payload = json.loads(payload)
		except (ValueError, TypeError):
			frappe.throw(_("Malformed signal payload."))

	frappe.publish_realtime(
		EVENT_SIGNAL,
		{
			"conversation": conversation,
			"kind": kind,
			"from_user": frappe.session.user,
			"from_peer": participants[frappe.session.user]["peer_id"],
			"to_peer": to_peer,
			"payload": payload,
		},
		user=to_user,
	)
	return {"delivered": True}


@frappe.whitelist()
def set_flags(
	conversation: str,
	peer_id: str,
	muted: int | str | None = None,
	video: int | str | None = None,
	screensharing: int | str | None = None,
) -> dict:
	"""Record a mic/camera/screen toggle so late joiners render it correctly.

	The media itself needs no server involvement -- a muted track is muted in
	the browser. This exists so the roster a third person joins into already
	shows the two people who muted before they arrived.
	"""
	assert_access(conversation)
	user = frappe.session.user

	with _RosterLock(conversation):
		huddle = _read(conversation)
		if not huddle:
			return {"huddle": None}

		participants = dict(_prune(huddle).get("participants", {}))
		seat = participants.get(user)
		if not seat or seat.get("peer_id") != peer_id:
			return {"huddle": _public({**huddle, "participants": participants})}

		updated = {**seat, "seen_at": _now()}
		if muted is not None:
			updated["muted"] = bool(cint(muted))
		if video is not None:
			updated["video"] = bool(cint(video))
		if screensharing is not None:
			updated["screensharing"] = bool(cint(screensharing))

		participants[user] = updated
		huddle = {**huddle, "participants": participants}
		_write(conversation, huddle)

	_publish_roster(huddle)
	return {"huddle": _public(huddle)}


@frappe.whitelist()
def get_active(conversations: str | list) -> dict:
	"""Which of these threads have a live call -- the badge query for a chat list.

	Batched on purpose: a sidebar of twenty threads asking twenty times would
	make opening the page the most expensive thing the page does.
	"""
	if isinstance(conversations, str):
		try:
			conversations = json.loads(conversations)
		except (ValueError, TypeError):
			conversations = [conversations]

	out = {}
	for conversation in conversations or []:
		if not can_access(conversation):
			continue

		huddle = _prune(_read(conversation) or {})
		if not huddle.get("participants"):
			continue

		out[conversation] = {
			"active": True,
			"participant_count": len(huddle["participants"]),
			"participants": [
				{"user": p["user"], "full_name": p["full_name"], "avatar": p.get("avatar")}
				for p in huddle["participants"].values()
			],
		}

	return out


@frappe.whitelist()
def ring(conversation: str, users: str | list | None = None) -> dict:
	"""Make someone's client ring for this call.

	The realtime ping is the whole mechanism -- there is no missed-call record,
	because a call you were not at the keyboard for is a chat message's job, and
	the caller can send one.
	"""
	people = assert_access(conversation)
	caller = frappe.session.user

	if isinstance(users, str):
		try:
			users = json.loads(users)
		except (ValueError, TypeError):
			users = [users]

	# Ringing defaults to "everyone else in the thread"; an explicit list is
	# still filtered through the audience so this cannot page a stranger.
	targets = [u for u in (users or people) if u != caller and u in people]

	huddle = _prune(_read(conversation) or {})
	payload = {
		"conversation": conversation,
		"from": user_card(caller),
		"participant_count": len(huddle.get("participants", {})),
	}
	for user in targets:
		frappe.publish_realtime(EVENT_RING, payload, user=user)

	return {"rang": targets}
