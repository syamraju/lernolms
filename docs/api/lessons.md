[← API index](./README.md)

# Lessons, chapters & content

Reading and authoring `Course Lesson` / `Course Chapter`, tracking progress, and
serving gated media.

| Endpoint | Guest | Writes |
| --- | --- | --- |
| [`get_lesson`](#get_lesson) | yes | — |
| [`get_lesson_creation_details`](#get_lesson_creation_details) | no | — |
| [`create_lesson`](#create_lesson) | no | yes |
| [`delete_lesson`](#delete_lesson) | no | yes |
| [`update_lesson_index`](#update_lesson_index) | no | yes |
| [`upsert_chapter`](#upsert_chapter) | no | yes |
| [`delete_chapter`](#delete_chapter) | no | yes |
| [`update_chapter_index`](#update_chapter_index) | no | yes |
| [`save_progress`](#save_progress) | no | yes |
| [`mark_lesson_progress`](#mark_lesson_progress) | no | yes |
| [`track_video_watch_duration`](#track_video_watch_duration) | no | yes |
| [`serve_resource`](#serve_resource) | yes | — |

---

## `get_lesson`

`lms.lms.utils.get_lesson` — **Guest: yes**

The full lesson payload the player renders: body, media, neighbours, progress,
instructor material and membership — addressed by **position**, not by name.

This endpoint returns one of **four different shapes** depending on access. Branch
on the marker keys before reading anything else.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `course` | `str` | yes | `LMS Course` name. |
| `chapter` | `int` | yes | 1-based chapter index within the course. |
| `lesson` | `int` | yes | 1-based lesson index within the chapter. |

**Returns — 1. Locked** (course enforces completion order and this lesson is gated):

```json
{ "locked": 1, "title": "Recursion", "course_title": "Intro to Python", "redirect_to": "2-3" }
```

`redirect_to` is the `"<chapter>-<lesson>"` index the student may actually open.

**Returns — 2. SCORM chapter** (playback is handled by the SCORM runtime):

```json
{ "is_scorm_package": true, "chapter_name": "chapter-0007" }
```

**Returns — 3. No preview** (lesson exists but the caller may not read it):

```json
{ "no_preview": 1, "title": "Recursion", "course_title": "Intro to Python", "disable_self_learning": 0 }
```

**Returns — 4. Full lesson:**

| Field | Type | Notes |
| --- | --- | --- |
| `name`, `title`, `creation` | | Lesson identity. |
| `body`, `content` | `str` | Lesson content. Private media URLs are rewritten to `serve_resource` **for every caller**, not just guests. |
| `include_in_preview` | `bool` | Visible without enrollment. |
| `youtube`, `file_type`, `question`, `quiz_id` | | Embedded media / assessment references. |
| `instructor_notes`, `instructor_content` | `str` \| `null` | **Nulled for non-instructors.** Never leaked to students or preview guests. |
| `chapter_title`, `course_title` | `str` | Context. |
| `next`, `prev` | `str` \| `null` | Neighbouring lesson indices. |
| `progress` | `number` | Caller's completion. `0` for guests. |
| `membership` | `object` \| `false` | Enrollment row. |
| `icon` | `str` | Derived from the content type. |
| `instructors` | `array` | Course instructors. |
| `paid_certificate`, `disable_self_learning` | | From the parent course. |
| `videos` | `array` | Video sources for watch tracking. |

Returns `{}` when guest access is off. An out-of-range `chapter` or `lesson` index
returns the gate-redirect shape rather than a 404.

---

## `get_lesson_creation_details`

`lms.lms.utils.get_lesson_creation_details` — **Guest: no** · *Roles: Moderator, Course Creator*

The editor's payload for a lesson slot — including instructor-only fields, which
`get_lesson` withholds. Also answers for an **empty** slot, so it backs "create
lesson here" as well as "edit this lesson".

**Parameters** — `course` (`str`), `chapter` (`int`, 1-based), `lesson` (`int`, 1-based).

**Returns**

```json
{
  "course_title": "Intro to Python",
  "chapter": { "name": "chapter-0002", "title": "Control flow" },
  "lesson": {
    "name": "lesson-0011", "title": "Loops", "include_in_preview": 0,
    "body": "…", "content": "…",
    "instructor_notes": "…", "instructor_content": "…",
    "youtube": "", "quiz_id": null
  }
}
```

`lesson` is `null` when the slot is empty.

---

## `create_lesson`

`lms.lms.api.create_lesson` — **Guest: no** · **Writes** · *Requires `can_modify_course`*

Appends a draft **"Untitled lesson"** to a chapter. The `Course Lesson` and its
`Lesson Reference` row are inserted in one request that rolls back together, so a
failure never leaves an orphan lesson outside the outline.

**Parameters** — `chapter` (`str`, required — `Course Chapter` name).

**Returns** — `str`, the new lesson's docname.

Throws on an invalid chapter; raises `PermissionError` without course-modify rights.

---

## `delete_lesson`

`lms.lms.api.delete_lesson` — **Guest: no** · **Writes** · *Requires `can_modify_course`*

Removes a lesson from its chapter, renumbers the remaining lessons, and cleans up
everything that pointed at it: course progress rows, video watch durations, and all
discussion topics and replies (which would otherwise block the delete with a
`LinkExistsError`).

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `lesson` | `str` | yes | `Course Lesson` name. |
| `chapter` | `str` | yes | Owning `Course Chapter` name. |

**Returns** — `null`.

---

## `update_lesson_index`

`lms.lms.api.update_lesson_index` — **Guest: no** · **Writes** · *Requires `can_modify_course`*

Reorders a lesson within its chapter, or moves it to a different chapter. Both
source and target chapters are renumbered.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `lesson` | `str` | yes | Lesson being moved. |
| `sourceChapter` | `str` | yes | Chapter it is leaving (or staying in). |
| `targetChapter` | `str` | yes | Chapter it is landing in. Same as source for a pure reorder. |
| `idx` | `int` | yes | Destination position. |

Note the camelCase parameter names — they are the wire names.

**Returns** — `null`.

---

## `upsert_chapter`

`lms.lms.api.upsert_chapter` — **Guest: no** · **Writes** · *Requires `can_modify_course`*

Creates or updates a chapter, including SCORM package handling. Pass `name` to
update; omit it to create.

On create, the `Chapter Reference` linking the chapter into the course outline is
written server-side in the same request as the chapter itself.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `title` | `str` | yes | Chapter title. |
| `course` | `str` | yes | Owning `LMS Course`. |
| `is_scorm_package` | `bool` | yes | Whether this chapter wraps a SCORM package. |
| `scorm_package` | `dict` | conditional | Required when `is_scorm_package` is true. Must carry a `name` — the `File` docname of the uploaded package. |
| `name` | `str` | no | Existing `Course Chapter` to update. Omit to create. |

**SCORM behaviour**

On a new package the zip is extracted and the chapter records
`scorm_package_path`, `manifest_file` and `launch_file`. If the `File` row was
deleted but the extraction still exists on disk, the save is allowed through and
keeps the existing extraction — `scorm_package` is cleared rather than rewritten,
so a chapter whose package File went missing can still be renamed.

A SCORM chapter with no lessons automatically gets one lesson created, titled after
the chapter.

**Returns** — the saved `Course Chapter` document.

---

## `delete_chapter`

`lms.lms.api.delete_chapter` — **Guest: no** · **Writes** · *Requires `can_modify_course`*

Deletes a chapter, every lesson inside it, and each lesson's dependants:
discussion topics and replies, course progress, video watch durations, and any
back-references. Extracted SCORM package files are removed from disk. Remaining
chapters in the course are renumbered.

**Parameters** — `chapter` (`str`, required).

**Returns** — `null`.

---

## `update_chapter_index`

`lms.lms.api.update_chapter_index` — **Guest: no** · **Writes** · *Requires `can_modify_course`*

Moves a chapter to a new position in the course outline and renumbers the rest.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `chapter` | `str` | yes | `Course Chapter` name. |
| `course` | `str` | yes | Owning `LMS Course`. |
| `idx` | `int` | yes | 0-based insertion position; stored indices are then written 1-based. |

**Returns** — `null`.

---

## `save_progress`

`lms.lms.doctype.course_lesson.course_lesson.save_progress` — **Guest: no** · **Writes**

Marks a lesson complete for the session user and advances the enrollment's
`current_lesson` pointer. The two enrollment writes are batched into a single
`on_update`, so downstream hooks fire once per request.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `lesson` | `str` | yes | `Course Lesson` name. |
| `course` | `str` | yes | `LMS Course` name. |
| `scorm_details` | `dict` | no | SCORM runtime state, when the lesson is a SCORM package. |

**Returns** — the updated progress value.

---

## `mark_lesson_progress`

`lms.lms.api.mark_lesson_progress` — **Guest: no** · **Writes**

Same effect as `save_progress`, addressed by **position** instead of docname —
useful when the client is already working in `chapter`/`lesson` index terms.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `course` | `str` | yes | `LMS Course` name. |
| `chapter_number` | `int` | yes | 1-based chapter index. |
| `lesson_number` | `int` | yes | 1-based lesson index. |

**Returns** — `null`.

---

## `track_video_watch_duration`

`lms.lms.api.track_video_watch_duration` — **Guest: no** · **Writes**

Records how long the caller has watched each video in a lesson. Stored durations
only ever move **forward** — a shorter reported time is ignored, so seeking back or
a stale beacon cannot reduce recorded progress.

Gated by `can_access_lesson`; a caller without lesson access gets a `PermissionError`.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `lesson` | `str` | yes | `Course Lesson` name. |
| `videos` | `list` | yes | Array of `{"source": "<video source>", "watch_time": <seconds>}`. Accepts a JSON-encoded string. |

**Returns** — `null`.

**Example**

```bash
curl -s -X POST "$SITE/api/method/lms.lms.api.track_video_watch_duration" \
  -H 'Content-Type: application/json' \
  -d '{"lesson":"lesson-0011","videos":[{"source":"dQw4w9WgXcQ","watch_time":184.5}]}'
```

---

## `serve_resource`

`lms.lms.doctype.course_lesson.course_lesson.serve_resource` — **Guest: yes**

Access-gated streaming of **private** lesson media. Frappe's native
`/private/files/` route requires a `Course Lesson` read role-perm that LMS students
and guests do not hold, and hard-refuses Guest outright — so all private lesson
media is served here instead, and `get_lesson` rewrites embedded URLs to point at
this endpoint for every caller.

**Parameters** — `file_url` (`str`, required). Percent-encoding is decoded before
matching, so `%20` resolves and `%2e%2e` traversal is still caught.

**Returns** — the raw file bytes (not the JSON envelope).

**Security model**

1. `file_url` must contain no `..` after decoding.
2. A `File` row with that exact `file_url` and `is_private = 1` must exist.
3. The file must be referenced by at least one lesson — resolved from lesson content
   (the source of truth) and from File attachments.
4. The caller must pass `can_access_lesson` for **at least one** referencing lesson,
   honouring instructor-only visibility.

Every failure raises a bare `PermissionError` and is logged — the responses are
indistinguishable, so the endpoint cannot be used to probe which files exist.
