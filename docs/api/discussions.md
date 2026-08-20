[← API index](./README.md)

# Discussions, announcements & notifications

| Endpoint | Guest | Writes |
| --- | --- | --- |
| [`get_discussion_topics`](#get_discussion_topics) | no | yes* |
| [`get_discussion_replies`](#get_discussion_replies) | no | — |
| [`get_announcements`](#get_announcements) | no | — |
| [`get_notifications`](#get_notifications) | no | — |

\* `get_discussion_topics` creates a topic when called with `single_thread=1` and
none exists.

---

## `get_discussion_topics`

`lms.lms.utils.get_discussion_topics` — **Guest: no** · *Requires `can_access_topic`*

Discussion topics attached to a document — a lesson, a batch, anything with
discussions enabled.

Two modes:

- **Threaded (default)** — every topic on the document, newest first, each with an
  author and an answer count.
- **Single thread** (`single_thread=1`) — the document has exactly one conversation.
  Returns the existing topic's name, **or creates one and returns that** if none
  exists yet. This is the only write path in this file.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `doctype` | `str` | yes | Reference doctype, e.g. `"Course Lesson"`. |
| `docname` | `str` | yes | Reference docname. |
| `single_thread` | `bool` | no | Default `false`. See above. |

**Returns — threaded:**

```json
[{
  "name": "topic-0031", "title": "Why does this loop terminate?",
  "owner": "asha@example.com", "creation": "…", "modified": "…",
  "user": { "full_name": "Asha K", "user_image": "/files/a.png" },
  "reply_count": 4
}]
```

`reply_count` is the number of **answers**, which is one fewer than the stored reply
count — a topic's first reply is the question body itself.

Reply counts are fetched in one grouped query for the whole page, not per topic.

**Returns — single thread:** `{ "name": "topic-0031" }`.

Throws when the caller may not access the referenced document.

---

## `get_discussion_replies`

`lms.lms.utils.get_discussion_replies` — **Guest: no** · *Requires `can_access_topic` on the topic's reference document*

All replies in a topic, oldest first (so the first element is the question body).

**Parameters** — `topic` (`str`, required — `Discussion Topic` name).

**Returns**

```json
[{
  "name": "reply-0101", "owner": "asha@example.com",
  "creation": "…", "modified": "…",
  "reply": "<p>Because the counter reaches zero.</p>",
  "user": { "full_name": "Asha K", "user_image": "/files/a.png" }
}]
```

Permission is resolved through the topic's reference document, not the topic itself —
losing access to the lesson loses access to its discussion.

**Posting** a topic or reply is not a custom endpoint; insert `Discussion Topic` /
`Discussion Reply` through the [generic REST API](./rest.md).

---

## `get_announcements`

`lms.lms.api.get_announcements` — **Guest: no** · *Enrolled batch students, or Moderator / Batch Evaluator*

Announcement emails sent to a batch, newest first. Backed by the `Communication`
doctype with `reference_doctype = "LMS Batch"`.

**Parameters** — `batch` (`str`, required).

**Returns**

```json
[{
  "subject": "Week 2 materials are up",
  "content": "<p>…</p>",
  "recipients": "batch-2026-03@example.com",
  "cc": null,
  "communication_date": "2026-03-09 09:00:00.000000",
  "sender": "instructor@example.com",
  "sender_full_name": "R. Iyer",
  "image": "/files/r.png"
}]
```

Anyone who is neither enrolled in the batch nor a batch admin gets a
`PermissionError`.

---

## `get_notifications`

`lms.lms.api.get_notifications` — **Guest: no**

The session user's notification log, newest first, capped at **50** rows.

**Always scoped to the session user** — there is no parameter that can widen it, so
no IDOR surface. The only client input honoured is the read flag.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `filters` | `dict` | no | Only `read` is read: truthy → unread-excluded (`read = 1`), falsy → unread only (`read = 0`). Omit the key entirely to get both. |

**Returns**

```json
[{
  "name": "nl-0091", "subject": "Your evaluation is tomorrow",
  "from_user": "eval@example.com", "link": "/lms/batches/batch-2026-03",
  "read": 0, "type": "Alert", "creation": "2026-08-20 17:00:00.000000",
  "from_user_details": { "name": "eval@example.com", "full_name": "E. Rao", "user_image": "/files/e.png" }
}]
```

`from_user_details` is `{}` for system-generated notifications with no sender.
Sender details are batch-fetched in one query for the whole page.

**Marking as read** uses the core Frappe endpoints, which remain reachable even
under `block_endpoints`:

```
/api/method/frappe.desk.doctype.notification_log.notification_log.mark_as_read
/api/method/frappe.desk.doctype.notification_log.notification_log.mark_all_as_read
```
