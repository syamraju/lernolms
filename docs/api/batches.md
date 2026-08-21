[← API index](./README.md)

# Batches & live classes

Cohort-based learning: `LMS Batch`, enrollment, timetable, live classes and
instructor analytics.

| Endpoint | Guest | Writes |
| --- | --- | --- |
| [`get_batches`](#get_batches) | yes | — |
| [`get_batch_count`](#get_batch_count) | yes | — |
| [`get_batch_details`](#get_batch_details) | yes | — |
| [`get_batch_courses`](#get_batch_courses) | yes | — |
| [`get_batch_timetable`](#get_batch_timetable) | no | — |
| [`enroll_in_batch`](#enroll_in_batch) | no | yes |
| [`send_confirmation_email`](#send_confirmation_email) | no | yes |
| [`get_my_batches`](#get_my_batches) | no | — |
| [`get_created_batches`](#get_created_batches) | no | — |
| [`get_batch_student_progress`](#get_batch_student_progress) | no | — |
| [`get_batch_chart_data`](#get_batch_chart_data) | no | — |
| [`delete_batch`](#delete_batch) | no | yes |
| [`create_live_class`](#create_live_class) | no | yes |
| [`create_google_meet_live_class`](#create_google_meet_live_class) | no | yes |
| [`get_my_live_classes`](#get_my_live_classes) | no | — |
| [`get_admin_live_classes`](#get_admin_live_classes) | no | — |

---

## `get_batches`

`lms.lms.utils.get_batches` — **Guest: yes**

Paginated batch list.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `filters` | `dict` | no | Frappe filters, plus the `enrolled` pseudo-filter. |
| `start` | `int` | no | Row offset. Default `0`. |
| `order_by` | `str` | no | Default `"start_date"`. |
| `limit_page_length` | `int` \| `str` | no | Page size. Default `24`, clamped to `1–120`. |

`enrolled: 1` is rewritten server-side to "batches the session user has an
`LMS Batch Enrollment` for".

After the query, `filter_batches_based_on_start_time` applies the time-of-day part
of the Upcoming/Archived split in Python — the SQL filter only settles the *date*.

**Returns** — array of batch cards:

```json
[{
  "name": "batch-2026-03", "title": "March Cohort", "description": "…",
  "seat_count": 40, "paid_batch": 1,
  "amount": 4999, "amount_usd": 60, "currency": "INR",
  "start_date": "2026-03-01", "end_date": "2026-04-15",
  "start_time": "18:00:00", "end_time": "20:00:00",
  "timezone": "Asia/Kolkata", "published": 1, "category": "Programming"
}]
```

Card decoration (instructor list, formatted price, seats left) is added by
`get_batch_card_details`. `[]` for guests when guest access is off.

---

## `get_batch_count`

`lms.lms.utils.get_batch_count` — **Guest: yes**

Count matching the same `filters` `get_batches` takes. Implemented as two `COUNT`
queries — one total, one subtracting the rows the clock excludes — rather than by
fetching the rows, because the endpoint is open to guests and its cost must not
grow with the number of batches on the site.

**Parameters** — `filters` (`dict`, optional).

**Returns** — `int`.

---

## `get_batch_details`

`lms.lms.utils.get_batch_details` — **Guest: yes**

Full batch record with instructors, courses, assessments and enrollment window.

Returns `{}` when the batch is unpublished and the caller is neither an enrolled
student nor a batch admin, or when guest access is off.

**Parameters** — `batch` (`str`, required).

**Returns**

| Field | Type | Notes |
| --- | --- | --- |
| `name`, `title`, `description`, `batch_details`, `batch_details_raw` | | Identity and copy. |
| `start_date`, `end_date`, `start_time`, `end_time`, `timezone` | | Schedule. |
| `seat_count` | `int` | |
| `seats_left` | `int` | Present only when `seat_count` is set. |
| `published`, `category` | | |
| `paid_batch`, `amount`, `amount_usd`, `currency` | | Pricing. `amount`/`currency` are converted for the caller's region. |
| `price` | `str` | Formatted. Present only for paid batches still open for enrollment. |
| `evaluation`, `certification`, `evaluation_end_date` | | Assessment configuration. |
| `allow_self_enrollment` | `bool` | |
| `zoom_account`, `google_meet_account`, `conferencing_provider`, `video_link` | | Live-class wiring. |
| `instructors` | `array` | |
| `courses` | `array` | `{course, title, evaluator}` per `Batch Course`. |
| `assessments` | `array` | `{assessment_name, assessment_type}`. |
| `accept_enrollments` | `bool` | True while the batch has not started. Stays true on the start date until `start_time` passes. |
| `students` | `array` | **Batch admins see every member. An enrolled student sees only themselves. Everyone else gets no `students` key at all.** |

---

## `get_batch_courses`

`lms.lms.utils.get_batch_courses` — **Guest: yes**

Full course details for every course attached to a batch, each carrying the
`batch_course` link-row name. Courses the viewer cannot see are dropped.

**Parameters** — `batch` (`str`, required).

**Returns** — array of `get_course_details` objects, each with an extra
`batch_course` field.

---

## `get_batch_timetable`

`lms.lms.doctype.lms_batch.lms_batch.get_batch_timetable` — **Guest: no** · *Enrolled students or Moderator / Batch Evaluator*

The batch schedule: timetable rows plus, when the batch has `show_live_class` set,
its live classes merged into the same date-ordered list.

**Parameters** — `batch` (`str`, required).

**Returns**

```json
[{
  "name": "row-001", "idx": 1, "parent": "batch-2026-03",
  "reference_doctype": "LMS Quiz", "reference_docname": "quiz-basics",
  "date": "2026-03-04", "start_time": "18:00:00", "end_time": "19:00:00",
  "milestone": 0
}]
```

Enriched by `get_timetable_details` with the referenced document's title and type.

---

## `enroll_in_batch`

`lms.lms.utils.enroll_in_batch` — **Guest: no** · **Writes**

Enrolls the session user in a batch, optionally linking a completed payment.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `batch` | `str` | yes | `LMS Batch` name. Throws if it does not exist. |
| `payment_name` | `str` | no | `LMS Payment` docname for a paid batch. |

**Returns** — `null`. Enrollment rules (seat count, self-enrollment allowed,
enrollment window, duplicate guard) are enforced inside `create_enrollment`.

---

## `send_confirmation_email`

`lms.lms.doctype.lms_batch_enrollment.lms_batch_enrollment.send_confirmation_email` — **Guest: no** · **Writes** · *The enrolled member, or Moderator / Batch Evaluator*

Sends the enrollment confirmation email, once. No-ops if
`confirmation_email_sent` is already set, or if the site has no default outgoing
email account configured.

**Parameters** — `doc` (`dict`, required — the `LMS Batch Enrollment` document; a
JSON-encoded string is also accepted).

**Returns** — `null`.

---

## `get_my_batches`

`lms.lms.api.get_my_batches` — **Guest: no**

Home-screen batch rail: the session user's most recent batches, falling back to
upcoming batches when they have none.

**Returns** — array of `get_batch_details` objects.

---

## `get_created_batches`

`lms.lms.api.get_created_batches` — **Guest: no**

Up to **4** upcoming batches (start date today or later) the session user is a
listed instructor on, earliest first.

**Returns** — array of `get_batch_details` objects.

---

## `get_batch_student_progress`

`lms.lms.utils.get_batch_student_progress` — **Guest: no** · *Requires `can_modify_batch`*

One student's progress across everything in the batch — courses and assessments.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `member` | `str` | yes | User to report on. |
| `batch` | `str` | yes | `LMS Batch` name. |

**Returns** — the student's detail record with per-course and per-assessment
progress merged in.

---

## `get_batch_chart_data`

`lms.lms.utils.get_batch_chart_data` — **Guest: no** · *Requires `can_modify_batch`*

Completion and pass statistics for the batch dashboard: per-course completion
counts, assignment pass stats and quiz pass stats, concatenated into one series
array.

**Parameters** — `batch` (`str`, required). Throws if the batch does not exist.

**Returns** — array of chart data points.

---

## `delete_batch`

`lms.lms.api.delete_batch` — **Guest: no** · **Writes** · *Requires `can_modify_batch`*

Deletes a batch and its dependants: enrollments, batch-course rows, assessments,
timetable rows, feedback and every batch discussion.

**Parameters** — `batch` (`str`, required).

**Returns** — `null`.

---

## `create_live_class`

`lms.lms.doctype.lms_batch.lms_batch.create_live_class` — **Guest: no** · **Writes** · *Roles: Moderator, Batch Evaluator*

Creates a **Zoom** meeting via the Zoom API and records it as an `LMS Live Class`.
The meeting is created as a private meeting.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `batch_name` | `str` | yes | Owning `LMS Batch`. |
| `zoom_account` | `str` | yes | Configured Zoom account to host under. |
| `title` | `str` | yes | Meeting topic. |
| `duration` | `int` | yes | Minutes. |
| `date` | `str` | yes | `YYYY-MM-DD`. |
| `time` | `str` | yes | `HH:mm:ss`. |
| `timezone` | `str` | yes | IANA timezone, e.g. `Asia/Kolkata`. |
| `auto_recording` | `str` | yes | `"No Recording"`, `"Cloud"` or `"Local"`. `"No Recording"` maps to Zoom's `none`. |
| `description` | `str` | no | Meeting agenda. |

**Returns** — the saved `LMS Live Class` document, including `start_url` (host),
`join_url` (attendees), `meeting_id`, `uuid` and `password`.

Any non-`201` response from Zoom is surfaced as a `ValidationError` carrying
Zoom's own response text.

---

## `create_google_meet_live_class`

`lms.lms.doctype.lms_batch.lms_batch.create_google_meet_live_class` — **Guest: no** · **Writes** · *Roles: Moderator, Batch Evaluator*

Creates a **Google Meet** live class. Requires the named
`LMS Google Meet Settings` record to be enabled **and** to have a Google Calendar
configured — both are checked up front with distinct error messages.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `batch_name` | `str` | yes | Owning `LMS Batch`. |
| `google_meet_account` | `str` | yes | `LMS Google Meet Settings` name. |
| `title` | `str` | yes | |
| `duration` | `int` | yes | Minutes. |
| `date` | `str` | yes | `YYYY-MM-DD`. |
| `time` | `str` | yes | `HH:mm:ss`. |
| `timezone` | `str` | yes | IANA timezone. |
| `description` | `str` | no | |

**Returns** — the saved `LMS Live Class` document with
`conferencing_provider: "Google Meet"`.

---

## `get_my_live_classes`

`lms.lms.api.get_my_live_classes` — **Guest: no**

The next **2** live classes, today or later, across every batch the session user is
enrolled in.

**Returns**

```json
[{
  "name": "lc-001", "title": "Week 1 Q&A", "description": "…",
  "date": "2026-03-04", "time": "18:00:00", "duration": 60,
  "attendees": 0, "start_url": "…", "join_url": "…",
  "owner": "instructor@example.com", "course_title": "Intro to Python"
}]
```

---

## `get_admin_live_classes`

`lms.lms.api.get_admin_live_classes` — **Guest: no**

The next **4** upcoming live classes across every batch the session user teaches.
Same row shape as `get_my_live_classes`, without `course_title`.

---

## Batch moderation, chat and calendar

Added with the batch-scoping work. Design: [`docs/design/batches.md`](../design/batches.md).

**The rule these all share:** the batch is the unit of scope. Holding `Moderator`
says what someone can do; the `LMS Batch.moderators` table says *where*. Every
endpoint below resolves that through `lms.lms.batch_access`.

### Scope helpers — `lms.lms.batch_access`

Not whitelisted; used by everything else here.

| Function | Answers |
| --- | --- |
| `is_batch_moderator(batch, user)` | administers this batch (or is System Manager) |
| `moderated_batches(user)` | every batch they administer |
| `batch_instructors(batch)` | derived from `Batch Course` → `Course Instructor`, ∪ the batch's own list |
| `batch_evaluators(batch)` | derived from `Batch Course` → `LMS Course.evaluator` |
| `staffed_batches(user)` | the reverse of the two above |
| `batch_relation(batch, user)` | `moderator` \| `instructor` \| `evaluator` \| `student` \| `None` |
| `can_read_batch(batch, user)` | read — published batches included |
| `assert_batch_member(batch)` | the inside of a cohort; published-ness does **not** open it |
| `visible_batches(user)` | every batch they are attached to, in any capacity |

### People — `lms.lms.batch_people`

| Endpoint | Who |
| --- | --- |
| `get_batch_people(batch)` | any member; administrative columns for moderators only |
| `get_my_people()` | moderators — the union across their batches, deduplicated |
| `remove_from_batch(batch, user)` | moderators; students only (staff is derived, so there is no row) |

`lms.lms.api.get_members` (site-wide) is now **System Manager only**. It was
`Moderator`, unfiltered, which made batch scoping meaningless.

### Invitations — `lms.lms.batch_invite`

| Endpoint | Writes | Notes |
| --- | --- | --- |
| `preview_invitations(batch, emails)` | — | classifies every address: `existing` / `new` / `already_enrolled` / `invalid` / `no_seats`. Seats count against a running total. Also returns `mail_configured`. |
| `send_invitations(batch, emails)` | yes | per-address results; enqueues above 25 addresses |
| `reissue_password(batch, user)` | yes | target's roles must be **exactly** `{LMS Student}` and they must be enrolled here |
| `create_invite_link(batch, expires_in_days, max_uses)` | yes | raw token returned **once**; only its SHA-256 is stored |
| `get_invite_links(batch)` | — | moderators |
| `revoke_invite_link(name)` | yes | moderators |
| `describe_invite_link(token)` | — | public; returns `valid: false` rather than throwing |
| `join_with_link(token)` | yes | signed-in caller only; increments `uses` and enrolls under the batch row lock |

**Outgoing email is a precondition, checked once.** An invitation is a message;
if it cannot be delivered there is no invitation, and for a provisioned account
the temporary password exists *only* in that message. `send_invitations` and
`reissue_password` refuse up front when the site has no default outgoing Email
Account. `preview_invitations` deliberately does **not** refuse — a dry run
describes rather than blocks — and reports `mail_configured: false` instead, so
the dialog can say nothing would be delivered. Permission is checked before
configuration, so an outsider is refused for who they are rather than being told
this site's mail settings.

**One bad address costs one address.** `invite_many` wraps each address in a
savepoint and unwinds to it on failure. A bare `frappe.db.rollback()` there
discards everything uncommitted, including work the caller did before calling —
which, called inline, silently undid the caller's own changes.

A valid token is a per-request grant that satisfies
`LMSBatchEnrollment.validate_self_enrollment` for the token holder alone, so a
batch does not have to stand open to self-enrollment for its links to work.

### Provisioned accounts — `lms.lms.user`

| Endpoint | Notes |
| --- | --- |
| `must_reset_password()` | whether the caller still holds a generated password |
| `set_own_password(new_password)` | acts only on the caller; runs the site password policy; clears the flag |

`User.must_reset_password` (custom field) is set when an account is provisioned.
`on_login` sends such a session to `/set-password` and the router keeps it there.
The temporary password is written to one email and nowhere else — no endpoint
returns it and nothing logs it.

### Chat — `lms.lms.chat`

Two levels: channels and sub-channels. `LMSChatChannel.validate_depth` refuses a
third. Access is derived from the batch roster on every request, never synced.

| Endpoint | Notes |
| --- | --- |
| `get_channel_tree(batch)` | filtered to what the caller may read; carries message count, last message and unread |
| `get_my_channels()` | the cross-batch sidebar, unread rolling up per batch |
| `get_messages(channel, limit, before)` | paged backwards from `before` |
| `post_message(channel, content, reply_to, attachment)` | |
| `delete_message(message)` | soft — replies keep a parent |
| `mark_read(channel)` | |
| `create_channel` / `update_channel` / `delete_channel` | moderators |

| Audience | Who reads |
| --- | --- |
| `Everyone` | every member of the batch |
| `Staff` | moderators, instructors, evaluators |
| `Students` | enrolled students |

Seeded per batch: `# announcements` (staff post), `# general`, `# staff-room`,
plus one `Course` sub-channel per curriculum course. Dropping a course
**archives** its channel rather than deleting the discussion.

### Calendar — `lms.lms.batch_calendar`

No new storage. Every entry carries `kind`, matching
`lms.lms.student_api.get_calendar_events`.

| Endpoint | Notes |
| --- | --- |
| `get_batch_calendar(batch, start, end)` | any member |
| `get_my_calendar(start, end)` | every batch the caller is attached to, merged |

`kind` ∈ `timetable` · `live_class` · `evaluation` · `appointment` ·
`batch_start` · `batch_end`. Students see only their own evaluations and
appointments; moderators see the batch's.
