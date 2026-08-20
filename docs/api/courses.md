[← API index](./README.md)

# Courses

Discovery, detail, outline, categories, authoring and lifecycle for `LMS Course`.

| Endpoint | Guest | Writes |
| --- | --- | --- |
| [`get_courses`](#get_courses) | yes | — |
| [`get_course_count`](#get_course_count) | yes | — |
| [`get_course_details`](#get_course_details) | yes | — |
| [`get_course_outline`](#get_course_outline) | yes | — |
| [`get_course_categories`](#get_course_categories) | yes | — |
| [`get_related_courses`](#get_related_courses) | yes | — |
| [`get_reviews`](#get_reviews) | yes | — |
| [`get_my_courses`](#get_my_courses) | no | — |
| [`get_created_courses`](#get_created_courses) | no | — |
| [`get_certification_details`](#get_certification_details) | no | — |
| [`delete_course`](#delete_course) | no | yes |
| [`delete_category`](#delete_category) | no | yes |
| [`get_course_progress_distribution`](#get_course_progress_distribution) | no | — |
| [`get_lesson_completion_stats`](#get_lesson_completion_stats) | no | — |
| [`get_course_assessment_progress`](#get_course_assessment_progress) | no | — |
| [`export_course_as_zip`](#export_course_as_zip) | no | — |
| [`import_course_from_zip`](#import_course_from_zip) | no | yes |

---

## `get_courses`

`lms.lms.utils.get_courses` — **Guest: yes**

Paginated course list. Featured courses lead the sequence and are excluded from the
non-featured query behind them, so the two together form one list the caller pages
through without duplicates or short pages.

Returns `[]` (not an error) when the caller is a guest and guest access is off.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `filters` | `dict` | no | Frappe filters, plus the pseudo-filters below. Defaults to `{}`. |
| `start` | `int` | no | Row offset. Default `0`. |
| `limit_page_length` | `int` \| `str` | no | Page size. Default `24`, clamped to `1–120`. |

**Pseudo-filters** — rewritten server-side before the query runs:

| Key | Effect |
| --- | --- |
| `title` | Becomes an `or_filter` title/short-introduction search. |
| `enrolled` | Restricts to courses the session user is enrolled in. |
| `created` | Restricts to courses the session user is a Course Instructor on. |
| `live` | Adds `featured = 0` and prepends featured courses to the result. |
| `certification` | `or_filter` on `enable_certification = 1` OR `paid_certificate = 1`. |

Real filters pass through untouched — `published`, `category`, `upcoming`,
`status`, `paid_course`, etc.

**Returns** — array of course cards:

```json
[{
  "name": "intro-to-python",
  "title": "Intro to Python",
  "tags": "python,beginner",
  "image": "/files/py.png",
  "video_link": "dQw4w9WgXcQ",
  "card_gradient": "blue",
  "short_introduction": "Start writing Python today.",
  "description": "…",
  "published": 1,
  "upcoming": 0,
  "featured": 1,
  "disable_self_learning": 0,
  "published_on": "2026-01-14",
  "category": "Programming",
  "status": "Approved",
  "paid_course": 0,
  "paid_certificate": 1,
  "course_price": 0,
  "currency": "INR",
  "amount_usd": 0,
  "enable_certification": 1,
  "lessons": 24,
  "enrollments": 812,
  "rating": 4.6,
  "membership": { "name": "…", "progress": 42.0, "current_lesson": "…" }
}]
```

`membership` is `false` when the caller is not enrolled. Card decoration
(instructor avatars, formatted price) is added by `get_course_card_details`.

**Example**

```bash
curl -s -G "$SITE/api/method/lms.lms.utils.get_courses" \
  --data-urlencode 'filters={"published":1,"live":1,"title":"python"}' \
  --data-urlencode 'limit_page_length=12'
```

---

## `get_course_count`

`lms.lms.utils.get_course_count` — **Guest: yes**

How many courses the *same* `filters` argument `get_courses` takes actually match.
Exists because the tab pseudo-filters (`enrolled`, `created`, `live`) and the title
search are not plain fields, so `frappe.client.get_count` cannot answer this.

When `live` is set, featured rows are counted with a second query and added in.

**Parameters** — `filters` (`dict`, optional). Same semantics as `get_courses`.

**Returns** — `int`. `0` for guests when guest access is off.

---

## `get_course_details`

`lms.lms.utils.get_course_details` — **Guest: yes**

Full detail for one course, including instructors, content statistics, membership,
rating count and a resolvable "continue learning" pointer.

Returns `{}` — never an error — when the course is unpublished and the caller
neither owns it nor is enrolled, when guest access is off, or when the course no
longer exists.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `course` | `str` | yes | `LMS Course` name. |

**Returns** — the `get_courses` card fields, plus:

| Field | Type | Notes |
| --- | --- | --- |
| `instructors` | `array` | User rows for every Course Instructor. |
| `membership` | `object` \| `false` | Enrollment row: `name`, `current_lesson`, `progress`, `member`, `course`, `purchased_certificate`, `certificate`. |
| `rating_count` | `int` | Number of `LMS Course Review` rows. |
| `price` | `str` | Formatted price, present only for paid courses/certificates. |
| `current_lesson` | `str` | `"<chapter>-<lesson>"` index to resume at. **Never points at a locked lesson** — if the stored pointer is gated, the first lesson the student may actually open is substituted. |
| `is_instructor` | `bool` | Forced `false` for guests. |

Content statistics (lesson counts, durations) are merged in from
`get_course_content_stats`.

---

## `get_course_outline`

`lms.lms.utils.get_course_outline` — **Guest: yes**

The chapter → lesson tree for a course, optionally annotated with the caller's
completion state and lesson locking.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `course` | `str` | yes | `LMS Course` name. |
| `progress` | `bool` | no | Default `false`. When `true`, marks completed lessons and applies the course's lesson-completion enforcement so locked lessons are flagged. |

**Returns** — array of chapters, each with a nested `lessons` array. SCORM chapters
carry their extracted package/launch file references. `[]` when guest access is off
or the course has no chapters.

Set `progress=1` only for authenticated callers — it costs an extra query per
render and always resolves empty for guests.

---

## `get_course_categories`

`lms.lms.utils.get_course_categories` — **Guest: yes**

Every distinct category string used by a **published** course, unpaginated (the set
is bounded by the number of categories, not courses).

**Returns** — array of select options, sorted, with a leading blank:

```json
[{"label": "", "value": null},
 {"label": "Design", "value": "Design"},
 {"label": "Programming", "value": "Programming"}]
```

---

## `get_related_courses`

`lms.lms.utils.get_related_courses` — **Guest: yes**

Full course details for every course listed in the source course's *Related Courses*
child table, in the order the author arranged them.

Related courses the viewer cannot see (unpublished after being tagged, for example)
are dropped rather than returned as blanks.

**Parameters** — `course` (`str`, required).

**Returns** — array of `get_course_details` objects.

---

## `get_reviews`

`lms.lms.utils.get_reviews` — **Guest: yes**

Reviews for a course, newest first.

**Parameters** — `course` (`str`, required).

**Returns**

```json
[{
  "review": "Clear and well paced.",
  "rating": 4.5,
  "owner": "student@example.com",
  "creation": "2026-03-02 10:11:12.000000",
  "owner_details": { "username": "asha", "full_name": "Asha K", "user_image": "/files/a.png" }
}]
```

`rating` is scaled to the Rating field's configured maximum (5 by default) — the
stored value is a 0–1 fraction.

---

## `get_my_courses`

`lms.lms.api.get_my_courses` — **Guest: no**

Home-screen course rail for the session user, with graceful fallbacks: the user's
most recent enrollments, else featured home courses, else the most popular courses.

**Returns** — array of `get_course_details` objects.

---

## `get_created_courses`

`lms.lms.api.get_created_courses` — **Guest: no**

Up to **3** most recently published courses the session user is a Course Instructor
on. A Moderator with no authored courses gets the site's 3 most recent instead, so
the admin dashboard is never blank.

**Returns** — array of `get_course_details` objects.

---

## `get_certification_details`

`lms.lms.api.get_certification_details` — **Guest: no**

Whether the session user is enrolled, whether the course sells a certificate, and
whether a certificate has already been issued.

**Parameters** — `course` (`str`, required).

**Returns**

```json
{
  "membership": { "name": "enr-001", "purchased_certificate": 1 },
  "paid_certificate": 1,
  "certificate": { "name": "cert-001", "template": "Default" }
}
```

`membership` and `certificate` are `null` when absent.

---

## `delete_course`

`lms.lms.api.delete_course` — **Guest: no** · **Writes** · *Requires `can_modify_course`*

Deletes a course and everything that hangs off it, in one transaction.

**Cascade-deleted:** enrollments, course progress, video watch durations,
certificates, certificate requests, certificate evaluations, course interest,
mentor mappings, batch-course links, reviews, related-course rows, program-course
rows, every chapter and lesson, and every discussion topic and reply attached to
those lessons.

**Preserved and unlinked** (authored assessments and graded work survive):
`LMS Quiz`, `LMS Quiz Submission`, `LMS Assignment`, `LMS Assignment Submission` —
their `course`/`lesson` links are nulled rather than the rows deleted.

**Parameters** — `course` (`str`, required).

**Returns** — `null`. Raises `PermissionError` if the caller is neither an
instructor on the course nor a Moderator.

---

## `delete_category`

`lms.lms.api.delete_category` — **Guest: no** · **Writes** · *Roles: Moderator*

Unlinks a category from every course and batch that references it, then deletes the
`LMS Category`. Both steps run in one transaction, because `category` is a Link
field and Frappe refuses to delete a category still in use.

**Parameters** — `category` (`str`, required).

**Returns** — a count of what was unlinked:

```json
{ "LMS Course": 12, "LMS Batch": 3 }
```

Throws if the category is missing or empty.

---

## `get_course_progress_distribution`

`lms.lms.api.get_course_progress_distribution` — **Guest: no** · *Requires `can_modify_course`*

Aggregate progress across every enrollment in a course, for the instructor
dashboard.

**Parameters** — `course` (`str`, required).

**Returns**

```json
{
  "average_progress": 47.3,
  "progress_distribution": { "0-25": 41, "26-50": 22, "51-75": 15, "76-100": 30 }
}
```

---

## `get_lesson_completion_stats`

`lms.lms.api.get_lesson_completion_stats` — **Guest: no** · *Roles: Course Creator, Moderator*

Per-lesson completion counts for a course, in outline order. One grouped query — not
one per lesson.

**Parameters** — `course` (`str`, required).

**Returns**

```json
[{
  "idx": 1,
  "chapter_idx": 1,
  "lesson": "lesson-0001",
  "lesson_name": "lesson-0001",
  "title": "Variables",
  "completion_count": 214
}]
```

Lessons nobody has completed still appear, with `completion_count: 0`.

---

## `get_course_assessment_progress`

`lms.lms.api.get_course_assessment_progress` — **Guest: no** · *Requires `can_modify_course`*

One student's assessment standing across a whole course.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `course` | `str` | yes | `LMS Course` name. |
| `member` | `str` | yes | User to report on. |

**Returns**

```json
{ "quizzes": [ … ], "assignments": [ … ], "exercises": [ … ] }
```

---

## `export_course_as_zip`

`lms.lms.api.export_course_as_zip` — **Guest: no** · *Requires `can_modify_course`*

Packages a course — chapters, lessons, attached files — into a downloadable zip.
The zip is streamed to the caller by `export_course_zip`; the method itself returns
`null`.

**Parameters** — `course_name` (`str`, required).

---

## `import_course_from_zip`

`lms.lms.api.import_course_from_zip` — **Guest: no** · **Writes** · *Roles: Moderator, Course Creator*

Recreates a course from a zip previously produced by `export_course_as_zip`.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `zip_file_path` | `str` | yes | Server-side path to an already-uploaded zip. Upload with `/api/method/upload_file` first and pass the returned `file_url`. |

**Returns** — the import result from `import_course_zip` (created course name and
a summary of imported records).
