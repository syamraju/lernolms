[← API index](./README.md)

# Calls & direct messages

In-app audio/video calls ("huddles") that hang off a conversation, and the 1:1
message threads they can hang off.

| Endpoint | Guest | Writes |
| --- | --- | --- |
| [`get_config`](#get_config) | no | — |
| [`join`](#join) | no | yes |
| [`leave`](#leave) | no | yes |
| [`heartbeat`](#heartbeat) | no | yes |
| [`signal`](#signal) | no | — |
| [`set_flags`](#set_flags) | no | yes |
| [`get_active`](#get_active) | no | — |
| [`ring`](#ring) | no | — |
| [`get_messages`](#get_messages) | no | — |
| [`get_conversations`](#get_conversations) | no | — |
| [`get_thread`](#get_thread) | no | — |
| [`get_people`](#get_people) | no | — |
| [`send_message`](#send_message) | no | yes |
| [`start_dm`](#start_dm) | no | — |
| [`mark_read`](#mark_read) | no | yes |

---

## Conversations

Everything here is addressed by a **conversation id**, `"<kind>:<key>"`:

| Id | Who is in it |
| --- | --- |
| `batch:<LMS Batch>` | Batch members, instructors and moderators |
| `channel:<LMS Chat Channel>` | The channel's audience, per `lms.lms.chat` |
| `dm:<user-a>\|<user-b>` | Exactly the two people named — emails lowercased and sorted |
| `class:<LMS Live Class>` | The live class's batch |

The audience is computed in `lms.lms.conversation.audience` and is the *same*
list used for both the access check and the "a call started here" broadcast, so
the set that can join and the set that gets told can never disagree.

A DM id is derived, not allocated: both ends sort the two emails and arrive at
the same string without asking a server who started it.

---

## How a call works

Media is **peer-to-peer mesh** — one `RTCPeerConnection` per pair, no media
server. The endpoints below own three things and nothing else:

* **the roster** — who is in the call and their mute/camera/screen flags, held
  in Redis, not a doctype. A huddle lives for minutes, is written on every
  toggle, and is worthless once it ends.
* **the relay** — SDP and ICE forwarded verbatim between two named peers. The
  server never parses or rewrites a payload.
* **access** — answered once per call, from the conversation's audience.

Because it is a mesh, a call is capped at **8 participants**
(`lms.lms.huddle.MAX_PARTICIPANTS`). Past that, each joiner costs every other
participant another upstream.

### Client responsibilities

1. `join` with a self-generated `peer_id`. Generate a new one per tab; the
   roster is keyed by *person*, so a second tab takes over the seat.
2. Offer to a peer only when your own email sorts **before** theirs
   (lowercased). Both ends see the same roster event, so a first-past-the-post
   rule makes both offer and glare.
3. `heartbeat` every ~20s. A peer that stops beating for
   `PEER_TTL` (45s) is pruned — this is what ends a call whose last participant
   closed their laptop without leaving.
4. `leave` on hang-up, and best-effort on page unload.

### Realtime events

Delivered over Frappe's socket, addressed per user:

| Event | Sent to | Meaning |
| --- | --- | --- |
| `lms_huddle_signal` | one peer | A forwarded `offer` / `answer` / `ice` frame. Check `to_peer` matches your own — a stale tab of yours will see frames that are not for it. |
| `lms_huddle_roster` | everyone in the call | The roster changed. Reconcile connections against it. |
| `lms_huddle_lifecycle` | the whole conversation | A call started or ended here. Drives the badge, not the roster. |
| `lms_huddle_ring` | the people being rung | Someone is calling you. |
| `lms_direct_message` | both people in a DM | A new message. |

### TURN

`get_config` returns STUN servers by default, which gets most pairs connected.
A relay for the rest (symmetric NAT, corporate networks) is configured per-site
in `site_config.json` rather than shipped, because it needs credentials:

```json
{
  "huddle_turn_url": "turn:turn.example.com:3478",
  "huddle_turn_username": "…",
  "huddle_turn_credential": "…"
}
```

---

## `get_config`

`lms.lms.huddle.get_config` — **Guest: no**

ICE servers and the timings the client should pace itself by.

**Returns** `{ice_servers: [...], heartbeat_interval: 20, max_participants: 8}`

---

## `join`

`lms.lms.huddle.join` — **Guest: no** · **Writes**

Start the call if there isn't one, or take a seat in the one there is. There is
only ever one call per conversation, so two people pressing the button at the
same moment land in the same room.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `conversation` | `str` | yes | Conversation id. |
| `peer_id` | `str` | yes | Client-generated, one per tab. |
| `video` | `int` | no | `1` if joining with the camera on. Default `0`. |

**Returns** `{huddle: {...roster}, self: {user, peer_id}}`

**Errors** `PermissionError` if the caller is not in the conversation;
`ValidationError` if the call is already at `MAX_PARTICIPANTS` (someone already
in it may always rejoin).

---

## `leave`

`lms.lms.huddle.leave` — **Guest: no** · **Writes**

Give up the seat. Ends the huddle when it empties the room, which posts a
"Huddle ended (Nm Ns)" system message into a DM thread.

Passing `peer_id` is optional but recommended: without it, a stale tab's leave
can evict the tab that replaced it.

---

## `heartbeat`

`lms.lms.huddle.heartbeat` — **Guest: no** · **Writes**

Keep the seat, prune lapsed peers, and return the current roster. Doubles as
the reconciliation path — a client that missed a realtime frame while
backgrounded is corrected here within one interval.

**Returns** `{huddle: {...} | null, evicted?: true}`. `evicted` means another
tab of yours holds the seat now; stop your media rather than fighting for it.

---

## `signal`

`lms.lms.huddle.signal` — **Guest: no**

Forward one SDP or ICE frame to one peer, verbatim.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `conversation` | `str` | yes | Conversation id. |
| `to_user` | `str` | yes | Recipient. |
| `to_peer` | `str` | yes | Recipient's current `peer_id`. |
| `kind` | `str` | yes | `offer`, `answer` or `ice`. Anything else is refused. |
| `payload` | `dict` | yes | Passed through untouched. |

**Returns** `{delivered: bool}` — `false` (not an error) when the peer left or
reloaded into a new `peer_id`. The roster event that follows drives a fresh
negotiation.

---

## `set_flags`

`lms.lms.huddle.set_flags` — **Guest: no** · **Writes**

Record a mic/camera/screen toggle. The media needs no server involvement; this
exists so the roster a late joiner receives already reflects who muted before
they arrived. Omitted flags are left alone.

---

## `get_active`

`lms.lms.huddle.get_active` — **Guest: no**

Which of these conversations have a live call — the badge query for a chat
sidebar. Batched deliberately: twenty threads asking twenty times would make
opening the page the most expensive thing the page does.

Conversations the caller cannot see are skipped rather than raising, so one bad
id does not blank the other nineteen badges.

**Returns** `{conversation: {active, participant_count, participants: [...]}}`

---

## `ring`

`lms.lms.huddle.ring` — **Guest: no**

Make someone's client ring. `users` defaults to everyone else in the
conversation and is always filtered through the audience, so this cannot page a
stranger. There is no missed-call record: a ring nobody was at the keyboard for
is a message's job.

---

## `get_messages`

`lms.lms.direct_message.get_messages` — **Guest: no**

One page of a thread, oldest-first. Page backwards with `before` (a creation
timestamp). `limit` is capped at 100.

Bodies are **plain text** and are stored verbatim. Render them as text nodes.

---

## `get_conversations`

`lms.lms.direct_message.get_conversations` — **Guest: no**

Every DM thread the caller is part of, most recent first, with the other
person, the last message and an unread count. Threads are derived from messages
rather than stored, so there is no membership row to fall out of step.

---

## `get_thread`

`lms.lms.direct_message.get_thread` — **Guest: no**

Title, kind and (for a DM) the other person, for a conversation the client was
*handed* rather than listed — a deep link from a calendar entry, a reminder
mail or a ring.

---

## `get_people`

`lms.lms.direct_message.get_people` — **Guest: no**

People the caller may start a DM with: everyone they share a batch with,
optionally narrowed by `search`. Scoped to shared batches rather than the whole
user table — "who can I message" should not double as a site directory.

---

## `send_message`

`lms.lms.direct_message.send_message` — **Guest: no** · **Writes**

Post to a thread and push it to everyone in it. `content` is trimmed, must be
non-empty, and is capped at 4000 characters.

---

## `start_dm`

`lms.lms.direct_message.start_dm` — **Guest: no**

Resolve and authorize the thread id for a person, **without** posting. Opening
a DM writes nothing: a thread you opened and closed without typing is not a
conversation.

---

## `mark_read`

`lms.lms.direct_message.mark_read` — **Guest: no** · **Writes**

Stamp the caller's read cursor for a conversation.

---

## Live classes in-app

`LMS Live Class` accepts **`Learno Huddle`** as a `conferencing_provider`
alongside Zoom and Google Meet. Unlike the other two it needs no account, no
token and no calendar — the room *is* the class, addressed as
`class:<name>` — which makes it the provider a batch can use on day one.

Create one with
[`create_huddle_live_class`](./batches.md) (`lms.lms.doctype.lms_batch.lms_batch.create_huddle_live_class`);
its `join_url` is derived from the class name and deep-links into the chats
page with `?c=class:<name>&call=1`.
