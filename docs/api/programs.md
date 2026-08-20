[← API index](./README.md)

# Programs

`LMS Program` — an ordered sequence of courses with optional gating, so a learner
unlocks each course by completing the one before it.

| Endpoint | Guest | Writes |
| --- | --- | --- |
| [`get_programs`](#get_programs) | no | — |
| [`get_program_details`](#get_program_details) | no | — |
| [`enroll_in_program`](#enroll_in_program) | no | yes |

---

## `get_programs`

`lms.lms.utils.get_programs` — **Guest: no**

The program directory, split into what the session user is already in and what they
could join. Programs the user is enrolled in are removed from `published`, so the
two lists never overlap.

Throws `Please login to view programs.` when guest access is off and the caller is a
guest.

**Returns**

```json
{
  "enrolled": [
    { "name": "fullstack-2026", "progress": 34.5, "course_count": 6, "member_count": 120 }
  ],
  "published": [
    { "name": "data-track", "course_count": 4, "member_count": 88 }
  ]
}
```

---

## `get_program_details`

`lms.lms.utils.get_program_details` — **Guest: no**

One program with its full ordered course list, each course annotated with whether
the learner may start it yet.

**Access.** An unpublished program is visible only to its members; anyone else gets
`You are not authorized to view the details of this program.`

**Parameters** — `program_name` (`str`, required).

**Returns**

```json
{
  "name": "fullstack-2026",
  "member_count": 120,
  "course_count": 6,
  "published": 1,
  "enforce_course_order": 1,
  "progress": 34.5,
  "courses": [
    { "name": "html-basics", "title": "HTML Basics", "eligible": true,  "membership": {"progress": 100}, "…": "…" },
    { "name": "css-basics",  "title": "CSS Basics",  "eligible": true,  "membership": {"progress": 20},  "…": "…" },
    { "name": "js-basics",   "title": "JS Basics",   "eligible": false, "membership": false, "…": "…" }
  ]
}
```

**The `eligible` flag.** The first course is always eligible. Every later course is
eligible only if the learner's progress on the **immediately preceding** course is
exactly `100`. Each `courses` entry is a full
[`get_course_details`](./courses.md#get_course_details) object with `eligible` added.

`progress` is present only for authenticated callers.

---

## `enroll_in_program`

`lms.lms.utils.enroll_in_program` — **Guest: no** · **Writes**

Enrolls the session user in a program by creating an `LMS Program Member` row.

Idempotent — enrolling twice is a no-op rather than an error. Eligibility rules are
enforced by `validate_program_enrollment` and surface as a `ValidationError`.

**Parameters** — `program` (`str`, required).

**Returns** — `null`.
