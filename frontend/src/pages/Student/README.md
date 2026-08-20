# The Learno student experience

The student-facing app, built from the **Learno** Figma file
([`XrsWXVoEcXTHrnbbzdOn0b`][figma], page *1st Draft*).

[figma]: https://www.figma.com/design/XrsWXVoEcXTHrnbbzdOn0b/Learno

## Why it is a separate tree and not a re-skin

The repo already carries a token layer that re-points frappe-ui's semantic
variables app-wide. Learno cannot be a second one, because the two designs
disagree about what the *same* token should be — `--surface-base` is white in
one and a warm cream in the other, the primary is blue in one and coral
(`#ff6060`) in the other. Re-pointing the shared variables would drag the
author/moderator app along, and this Figma does not describe that app.

So the student app opts in: `StudentLayout.vue` puts `.learno` on its root, and
everything in `src/styles/learno.css` is scoped under it. Nothing outside
`/learn` changes.

## Where things are

| Path | What |
|---|---|
| `src/styles/learno.css` | tokens + primitives (`.learno-btn`, `.learno-pill`, `.learno-tag`, `.learno-card`, `.learno-prose`) |
| `src/components/Layouts/StudentLayout.vue` | the shell: grey gutter, sidebar panel, page panel |
| `src/components/Learno/` | sidebar, nav row, brand mark, course card |
| `src/pages/Student/` | the routed pages |
| `src/pages/Student/components/` | the four course-detail panels and the shared pieces |
| `lms/lms/student_api.py` | the whitelisted endpoints this app needs |

Routes are `/learn/*` and are selected by `meta.layout: 'student'`, which
`App.vue` keys the shell off.

## Typeface

The design is DM Sans; the admin app stays on its own face. `@fontsource-variable/dm-sans`
is imported in `src/index.css` and applied by the `.learno` scope only.

## Design → data mapping

The Figma asks for a few things `LMS Course` does not store. Rather than invent
them, each slot shows the nearest real field:

| Figma | Source |
|---|---|
| "Subject Name" | `course.category` |
| "New Course" | published within 30 days |
| "Beginner Level" | first entry of the comma-separated `tags` field |
| "Organisation badge" | first instructor (there is no organisation doctype) |
| "Skills You Earn: …" | `course.short_introduction` |
| **"16 hrs"** | **not stored** — the slot shows the chapter count instead |
| "21 Sessions" | `course.lessons` |
| "99+ Enrolments" | `course.enrollments` |
| "Skills you Unlock" | `tags` after the first entry |

## Deliberate departures from the design

* **The three header counts are the scope control.** The design draws them as
  cards and the pill row below as tabs. Wiring the counts as static text would
  have left them decorative, so they select the scope (pending / enrolled /
  completed) and the pills select the content type.
* **Assessments / Projects / Assignments pills are omitted.** Quizzes,
  assignments and programming exercises are lesson content in this LMS, reached
  from inside a session; their doctype lists are author tools. There is no
  student-facing list for them to open, so they are not rendered as dead chrome.
  **Bundles** is kept — it maps to `LMS Program`.
* **The calendar is read-only.** "+ Add New" and "Book Appointments" in the
  design are evaluator/moderator actions.
* **The certificate panel shows real state**, not the mock artwork: the issued
  certificate, the progress toward it, or a plain statement that the course does
  not certify.
* **Chapters expand in the Sessions tab.** The design draws a flat list with a
  chevron per row; the real outline is chapter → lessons, and a chapter is not
  itself openable, so the chevron discloses its lessons.

## Backend

`lms/lms/student_api.py`. Every function answers a question about *the
signed-in student* and none of them accepts a `member` argument, so none can be
pointed at somebody else's record.

| Method | Notes |
|---|---|
| `get_student_courses` | `lms.lms.utils.get_courses` + `chapters_count` + `progress` |
| `get_enrollment_summary` | the pending / enrolled / completed counts |
| `enroll` | always for the caller; eligibility is `LMSEnrollment.before_insert` |
| `get_course_materials` | `upload` blocks across a course's lessons, grouped by chapter; access mirrors `get_course_details` |
| `get_my_materials` | the same across every enrolled course |
| `get_my_batches` | strictly the caller's enrolments — unlike `lms.lms.api.get_my_batches`, which substitutes upcoming published batches when there are none |
| `get_calendar_events` | live classes + evaluations + batch starts, flattened |

## Crossing between the two apps

* The router sends a signed-in user with **no** authoring rights to
  `StudentDashboard` when they hit `/`.
* Anyone who can author or moderate lands on the admin home and gets a **Switch
  to admin** button (and **Open desk** for a System Manager) in the student
  sidebar.
* Both are full document loads, not router pushes: the shells do not share a
  layout, so the transition should read as one.

## Local development

The repo is bind-mounted into the Docker bench at `apps/lms`
(`docker/docker-compose.local.yml`), so **nothing needs copying**:

* **Python** — edit and the next request picks it up (`developer_mode` is on, so
  the werkzeug reloader is running).
* **Frontend** — `yarn --cwd frontend build` on the host writes into
  `lms/public/frontend/`, which the container serves directly. No container
  command, no restart.

Two things that mount setup has to get right, and does:

* `frontend/node_modules` is a **named volume**, not the host directory. The
  host's are darwin-arm64 binaries (esbuild, rollup, lightningcss) and the
  container is linux-arm64, so each side keeps its own tree. Building in the
  container still works: `docker exec learno-lms-frappe-1 bash -lc 'cd
  ~/frappe-bench/apps/lms/frontend && yarn build'`.
* `bench get-app` clones into `apps/lms` and cannot, once the mount occupies it.
  `docker/init-local.sh` detects a populated `apps/lms` and registers the app in
  place (editable pip install + `sites/apps.txt`) instead, so a from-scratch
  `docker compose up` still bootstraps.

The host build needs a bench-layout stub at `~/sites/common_site_config.json`
(`{ "socketio_port": 9000 }`) because `src/socket.js` imports
`../../../../sites/common_site_config.json`. Inside the container that path is
real.

**Don't run a host build and a container build at once** — both write into
`lms/public/frontend/assets/`, and you end up with two complete-but-different
`index-*.js` bundles side by side. Clear the directory if that happens.
