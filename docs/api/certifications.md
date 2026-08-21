[← API index](./README.md)

# Certifications & evaluations

Certificates, the certified-members directory, evaluator schedules and the
evaluation booking pipeline.

| Endpoint | Guest | Writes |
| --- | --- | --- |
| [`create_certificate`](#create_certificate) | no | yes |
| [`save_certificate_details`](#save_certificate_details) | no | yes |
| [`get_certificates`](#get_certificates) | no | — |
| [`get_certified_participants`](#get_certified_participants) | no | — |
| [`get_count_of_certified_members`](#get_count_of_certified_members) | no | — |
| [`get_certification_categories`](#get_certification_categories) | no | — |
| [`get_evaluator_details`](#get_evaluator_details) | no | — |
| [`ensure_evaluator_calendar`](#ensure_evaluator_calendar) | no | yes |
| [`add_evaluator_slot`](#add_evaluator_slot) | no | yes |
| [`update_evaluator_slot`](#update_evaluator_slot) | no | yes |
| [`delete_evaluator_slot`](#delete_evaluator_slot) | no | yes |
| [`set_evaluator_unavailability`](#set_evaluator_unavailability) | no | yes |
| [`get_schedule`](#get_schedule) | no | — |
| [`save_evaluation_details`](#save_evaluation_details) | no | yes |
| [`cancel_evaluation`](#cancel_evaluation) | no | yes |
| [`setup_calendar_event`](#setup_calendar_event) | no | yes |
| [`get_admin_evals`](#get_admin_evals) | no | — |
| [`create_lms_certificate_evaluation`](#create_lms_certificate_evaluation) | no | — |
| [`create_lms_certificate`](#create_lms_certificate) | no | — |

> Certification status for the *current* user on a course is
> [`get_certification_details`](./courses.md#get_certification_details).

---

## `create_certificate`

`lms.lms.doctype.lms_certificate.lms_certificate.create_certificate` — **Guest: no** · **Writes**

Issues the session user's own certificate for a course, using the site's default
template and today's date.

**Idempotent** — if a certificate already exists it is returned unchanged rather
than reissued.

**Parameters** — `course` (`str`, required).

**Returns** — `{ "name": "cert-0091", "course": "intro-to-python", "template": "Default" }`
(existing), or the newly created `LMS Certificate` document.

Eligibility (course completion, purchased certificate, evaluation outcome) is
enforced by `validate_certification_eligibility` and surfaces as a `ValidationError`.

---

## `save_certificate_details`

`lms.lms.api.save_certificate_details` — **Guest: no** · **Writes** · *Roles: Batch Evaluator, Moderator*

Issues or updates a certificate **on a member's behalf** — the evaluator-facing
counterpart to `create_certificate`.

**Permission.** Moderators may act on any course/batch. A Batch Evaluator may act
only where they are the **assigned** evaluator for that course-and-batch pair;
otherwise `PermissionError`.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `member` | `str` | yes | Recipient. |
| `issue_date` | `str` | yes | `YYYY-MM-DD`. |
| `template` | `str` | yes | Certificate template name. |
| `course` | `str` | no | `LMS Course`. |
| `batch_name` | `str` | no | `LMS Batch`. |
| `expiry_date` | `str` | no | `YYYY-MM-DD`. |
| `published` | `bool` | no | Default `true`. Published certificates appear in the public directory. |

Upserts on the `(member, course)` pair.

**Returns** — the certificate docname.

---

## `get_certificates`

`lms.lms.certificates.get_certificates` — **Guest: no**

One person's certificates, for the profile tab and the course certificate page.

Use this rather than filtering `LMS Certificate` by `member` through the generic
list API: `member`, `verification_code` and `snapshot` all sit at **permlevel 1**
so that a signed-in student cannot enumerate every holder's email address and
code, and Frappe refuses a filter on a field the caller's roles cannot read.
(`snapshot` is on that list because the frozen design carries the verification
code as plain text whenever the certificate places the "Verification link" or
"Certificate ID" element.) None of the three is returned here.

Scoping matches the doctype's own rule — staff (Moderator, Course Creator, Batch
Evaluator) see every row, everyone else sees published ones.

**Parameters** — `member` (`str`, optional; defaults to the session user),
`course` (`str`, optional).

**Returns** — `[{name, course, course_title, batch_title, issue_date, template}, …]`,
newest issue date first.

---

## `get_certified_participants`

`lms.lms.api.get_certified_participants` — **Guest: no**

The certified-members directory. One row per member — their **most recent** issue
date, not one row per certificate. Only published certificates held by enabled
users are counted.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `filters` | `dict` | no | See the filter table below. |
| `start` | `int` | no | Offset. Default `0`. Alias: `limit_start`. |
| `page_length` | `int` | no | Page size. Default `40`. Alias: `limit_page_length`. |

**Filters** (unrecognised keys are ignored):

| Key | Effect |
| --- | --- |
| `category` | Substring match on the certificate's course **or** batch title. |
| `member_name` | Frappe-style `["like", "%asha%"]` pair; the second element is used as the pattern. |
| `open_to_work` | Restricts to users whose profile says `open_to = "Work"`. |
| `hiring` | Restricts to users whose profile says `open_to = "Hiring"`. |

**Returns** — array of participants, newest issue date first, with profile detail
merged in. The raw `member` key is removed from each row.

---

## `get_count_of_certified_members`

`lms.lms.api.get_count_of_certified_members` — **Guest: no**

Count matching the same `filters` `get_certified_participants` takes.

**Parameters** — `filters` (`dict`, optional).

**Returns** — `int`.

---

## `get_certification_categories`

`lms.lms.api.get_certification_categories` — **Guest: no**

Distinct filter options for the certified-members directory, drawn from published
certificates' course titles (falling back to batch title).

**Returns** — `[{"label": "Intro to Python", "value": "Intro to Python"}, …]`.

---

## `get_evaluator_details`

`lms.lms.api.get_evaluator_details` — **Guest: no** · *Own record, or Moderator*

An evaluator's weekly slots, unavailability window and Google Calendar link state.

**Access.** Your own record, or anyone's if you are a Moderator. A plain role check
would let any Batch Evaluator read every other evaluator's schedule; the profile
page's redirect is client-side and stops nobody calling this directly.

**Reading never writes.** If no `Course Evaluator` record exists, an unsaved draft
is returned — saving one would run `validate_evaluator_role` and *grant* the target
the Batch Evaluator role as a side effect of a page view. The record is created on
the first real write instead (see `add_evaluator_slot`).

**Parameters** — `evaluator` (`str`, required).

**Returns**

```json
{
  "slots": { "evaluator": "eval@example.com", "unavailable_from": null, "unavailable_to": null,
             "schedule": [{"name": "row-1", "day": "Monday", "start_time": "10:00:00", "end_time": "12:00:00"}] },
  "calendar": "gcal-001",
  "is_authorized": "…",
  "timezone": "Asia/Kolkata (+05:30)"
}
```

`calendar` and `is_authorized` are `null` when no Google Calendar is linked.
`timezone` is the **system** timezone — Evaluator Schedule stores bare wall-clock
times and the whole booking pipeline reads them as system time, so the editor has
to say so.

---

## `ensure_evaluator_calendar`

`lms.lms.api.ensure_evaluator_calendar` — **Guest: no** · **Writes** · *Roles: Batch Evaluator, Moderator*

Creates the **caller's own** Google Calendar record on demand, at the start of the
authorisation flow. Batch Evaluators are portal users without create permission on
`Google Calendar`, so it is provisioned on their behalf — for themselves only, and
only when they ask.

Idempotent, including under concurrent calls (a duplicate insert is rolled back to
a savepoint and the existing record returned).

**Returns** — the `Google Calendar` docname.

---

## `add_evaluator_slot`

`lms.lms.api.add_evaluator_slot` — **Guest: no** · **Writes** · *Own record, or Moderator*

Appends a weekly availability slot. **This is the call that creates the
`Course Evaluator` record**, and creating it is what makes the target an evaluator —
hence the ownership check runs first.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `evaluator` | `str` | yes | Evaluator user. |
| `day` | `str` | yes | `Monday` … `Sunday`. Anything else throws. |
| `start_time` | `str` | yes | `HH:mm:ss`, validated. |
| `end_time` | `str` | yes | `HH:mm:ss`, validated. |

**Returns** — the new schedule row's name.

---

## `update_evaluator_slot`

`lms.lms.api.update_evaluator_slot` — **Guest: no** · **Writes** · *Own record, or Moderator*

Changes one field of one slot.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `evaluator` | `str` | yes | |
| `slot` | `str` \| `int` | yes | Schedule row name or index. Must belong to this evaluator. |
| `fieldname` | `str` | yes | **Only `day`, `start_time` or `end_time`.** Anything else throws. |
| `value` | `str` | yes | Validated as a day name or a time, per `fieldname`. |

**Returns** — `null`.

---

## `delete_evaluator_slot`

`lms.lms.api.delete_evaluator_slot` — **Guest: no** · **Writes** · *Own record, or Moderator*

Removes a slot.

**Parameters** — `evaluator` (`str`), `slot` (`str` \| `int`).

**Returns** — `null`.

---

## `set_evaluator_unavailability`

`lms.lms.api.set_evaluator_unavailability` — **Guest: no** · **Writes** · *Own record, or Moderator*

Sets or clears one end of the evaluator's unavailability window.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `evaluator` | `str` | yes | |
| `fieldname` | `str` | yes | **Only `unavailable_from` or `unavailable_to`.** |
| `value` | `str` | no | `YYYY-MM-DD`. Omit or send `null` to clear. |

**Returns** — `null`.

---

## `get_schedule`

`lms.lms.doctype.course_evaluator.course_evaluator.get_schedule` — **Guest: no**

Bookable evaluation slots for a course (optionally within a batch), from today to
the end of the booking window. Already-booked slots are removed, and the remainder
is grouped by display date in the evaluation's display timezone.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `course` | `str` | yes | Determines the assigned evaluator. |
| `batch` | `str` | no | Narrows the evaluator and the schedule range. |

**Returns** — slots grouped by date, ready to render as a booking calendar.

---

## `save_evaluation_details`

`lms.lms.api.save_evaluation_details` — **Guest: no** · **Writes** · *Roles: Batch Evaluator, Moderator*

Records an evaluation outcome for a member on a course. Upserts on the
`(member, course)` pair.

**Permission.** Same rule as `save_certificate_details`: Moderators anywhere, a
Batch Evaluator only where they are the assigned evaluator.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `member` | `str` | yes | |
| `course` | `str` | yes | |
| `date_value` | `str` | yes | `YYYY-MM-DD`. |
| `start_time` | `str` | yes | `HH:mm:ss`. |
| `end_time` | `str` | yes | `HH:mm:ss`. |
| `status` | `str` | yes | Evaluation outcome. |
| `batch_name` | `str` | no | |
| `rating` | `float` | no | **Sent on a 0–5 scale; stored divided by 5** as a 0–1 fraction. Default `0`. |
| `summary` | `str` | no | Evaluator's notes. |

**Returns** — the `LMS Certificate Evaluation` docname.

---

## `cancel_evaluation`

`lms.lms.api.cancel_evaluation` — **Guest: no** · **Writes** · *The requesting member only*

Cancels the caller's own evaluation booking: sets the `LMS Certificate Request`
status to `Cancelled`, and tears down the matching calendar Event, its participants
and its Communication.

Ownership is checked **twice** — the submitted `member` must be the session user,
*and* the `LMS Certificate Request` must exist with that member. A mismatch is a
`PermissionError` either way.

**Parameters** — `evaluation` (`dict`, required). Must carry `name`, `member`,
`member_name` and `date`.

**Returns** — `null`.

---

## `setup_calendar_event`

`lms.lms.doctype.lms_certificate_request.lms_certificate_request.setup_calendar_event` — **Guest: no** · **Writes** · *The requesting member, or Moderator / Batch Evaluator*

Creates the Google Calendar event for a booked evaluation, adds both parties as
participants, and writes the meeting link back to the request.

No-ops silently if the evaluator has no **enabled** Google Calendar linked.

**Parameters** — `eval_name` (`str`, required — `LMS Certificate Request` name).

**Returns** — `null`.

---

## `get_admin_evals`

`lms.lms.api.get_admin_evals` — **Guest: no**

The next **4** upcoming evaluations assigned to the session user, status `Upcoming`,
dated today or later.

**Returns**

```json
[{
  "name": "cr-0031", "date": "2026-08-25", "start_time": "11:00:00", "timezone": "Asia/Kolkata",
  "course": "intro-to-python", "course_title": "Intro to Python",
  "evaluator": "eval@example.com", "google_meet_link": "https://meet.google.com/…",
  "member": "asha@example.com", "member_name": "Asha K"
}]
```

---

## `create_lms_certificate_evaluation`

`lms.lms.doctype.lms_certificate_request.lms_certificate_request.create_lms_certificate_evaluation` — **Guest: no** · *Roles: Moderator, Batch Evaluator, System Manager*

Frappe **document-mapper**: builds a draft `LMS Certificate Evaluation` from an
existing `LMS Certificate Request`, carrying the fields across.

**Parameters** — `source_name` (`str`, required), `target_doc` (`dict`, optional —
an existing draft to merge into).

**Returns** — the mapped, **unsaved** document. Persist it with
`frappe.client.insert` or by submitting it through the desk form.

---

## `create_lms_certificate`

`lms.lms.doctype.lms_certificate_evaluation.lms_certificate_evaluation.create_lms_certificate` — **Guest: no**

Document-mapper from `LMS Certificate Evaluation` to a draft `LMS Certificate`.

**Parameters** — `source_name` (`str`, required), `target_doc` (`dict`, optional).

**Returns** — the mapped, **unsaved** document.
