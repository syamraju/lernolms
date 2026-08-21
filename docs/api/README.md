# Learno LMS — Developer API

Version: **2.45.2** · App: `frappe_lms` (module `lms`) · Built on the [Frappe Framework](https://frappeframework.com)

This is the complete reference for every server endpoint the Learno LMS exposes to
API clients. It documents the **123 whitelisted RPC methods** shipped by this app,
plus the generic Frappe REST layer they sit alongside.

## Contents

| Guide | What's in it |
| --- | --- |
| [Getting started](#getting-started) | Base URL, auth, request/response shape |
| [Conventions](#conventions) | Type coercion, pagination, filters, errors |
| [Courses](./courses.md) | Discovery, details, outline, categories, authoring, deletion, import/export |
| [Lessons & content](./lessons.md) | Lesson read/write, chapters, progress, video tracking, private media |
| [Batches](./batches.md) | Batch discovery, details, timetable, live classes, enrollment, analytics |
| [Assessments](./assessments.md) | Quizzes, assignments, programming exercises |
| [Users & profiles](./users.md) | Signup, session user, members, roles, profiles, streaks, badges |
| [Certifications & evaluations](./certifications.md) | Certificates, evaluators, slots, scheduling, requests |
| [Payments & billing](./payments.md) | Order summary, billing access, payment links, gateways |
| [Programs](./programs.md) | Program listing, details, enrollment |
| [Discussions & notifications](./discussions.md) | Topics, replies, announcements, notification log |
| [Platform & admin](./admin.md) | Settings, sidebar, branding, PWA, search, SEO meta, integrations |
| [Generic REST resources](./rest.md) | `/api/resource/*` CRUD over LMS doctypes |

---

## Getting started

### Base URL

```
https://<your-site>/api/method/<dotted.python.path>
```

Every endpoint in this reference is a Frappe *whitelisted method*. The dotted path
in each endpoint heading is the full path — for example:

```bash
curl -s 'https://learn.example.com/api/method/lms.lms.utils.get_courses'
```

Frappe also exposes a v2 alias (`/api/v2/method/<path>`) on recent versions. The
`/api/method/` form documented here works on all versions and is what the bundled
frontend uses.

### HTTP verbs

| Verb | When |
| --- | --- |
| `GET` | Read-only endpoints. Arguments go in the query string. |
| `POST` | Anything that writes. Arguments go in a JSON body (`Content-Type: application/json`) or as form fields. |

Frappe does not enforce the verb per method — a read endpoint answers a `POST` too —
but write endpoints called over `GET` are rejected when the site runs with CSRF
protection on. Use `POST` for every endpoint marked **Writes** in this reference.

### Authentication

Three mechanisms, in order of usefulness for API clients:

**1. API key / secret (recommended for server-to-server)**

Generate a key pair on the User document (Desk → User → Settings → API Access), then:

```bash
curl -s 'https://learn.example.com/api/method/lms.lms.api.get_user_info' \
  -H 'Authorization: token <api_key>:<api_secret>'
```

**2. Session cookie (browsers, the bundled Vue frontend)**

```bash
curl -s -c cookies.txt -X POST 'https://learn.example.com/api/method/login' \
  -H 'Content-Type: application/json' \
  -d '{"usr": "student@example.com", "pwd": "••••••"}'

curl -s -b cookies.txt 'https://learn.example.com/api/method/lms.lms.api.get_user_info'
```

Cookie-authenticated `POST` requests must also send the CSRF token that the page
bootstrap exposes as `window.csrf_token`, in an `X-Frappe-CSRF-Token` header.

**3. OAuth 2 / OpenID Connect**

Standard Frappe OAuth endpoints (`frappe.integrations.oauth2.*`) are enabled. Bearer
tokens are accepted as `Authorization: Bearer <token>`.

### Guest access

Endpoints marked **Guest: yes** are decorated `@frappe.whitelist(allow_guest=True)`
and answer unauthenticated requests. Most of them still return `[]` / `{}` unless
**LMS Settings → Allow Guest Access** is enabled — the `guest_access_allowed()` gate.
So a guest-callable endpoint returning an empty result is normal, not an error.

### Endpoint blocking

If the site config sets `block_endpoints`, `lms.auth.authenticate` restricts non
System Users to a fixed allow-list of core Frappe endpoints (`login`, `logout`,
`frappe.client.*`, `upload_file`, …) plus **everything under `lms.*`**. All endpoints
in this reference stay reachable; arbitrary framework internals do not. Extra paths
can be permitted with the `allowed_custom_endpoints` site-config list.

---

## Conventions

### Response envelope

A successful call returns HTTP `200` with the return value under `message`:

```json
{ "message": { "name": "abc123", "title": "Intro to Python" } }
```

Endpoints that return nothing answer `{"message": null}`. Two endpoints break the
envelope deliberately and return a raw HTTP response: `get_pwa_manifest`
(`application/manifest+json`) and `serve_resource` (the file bytes).

### Argument typing is enforced

This app sets `require_type_annotated_api_methods = True`. Frappe reads each
method's Python type annotations and **coerces and validates arguments before the
method body runs**. Practically:

- A parameter annotated `str` rejects a JSON object or array with a `400`.
- A parameter annotated `int` accepts `"3"` and passes `3`.
- A parameter annotated `dict` or `list` accepts either a real JSON value or a
  JSON-encoded string.
- A parameter annotated `bool` accepts `1`/`0`/`true`/`false`.

Type errors surface as `frappe.exceptions.ValidationError` before any permission
check, so a malformed argument never reaches the database.

### Pagination

List endpoints follow one of two shapes.

**Course/batch style** — `start` + `limit_page_length`:

```
?start=0&limit_page_length=24
```

Page size defaults to **24** and is clamped to **1–120** (`resolve_page_length`).
Each list endpoint has a matching `*_count` endpoint that applies the *same*
filters, so the footer count and the rows agree:

| List | Count |
| --- | --- |
| `get_courses` | `get_course_count` |
| `get_batches` | `get_batch_count` |
| `get_certified_participants` | `get_count_of_certified_members` |

**Certification style** — `start` + `page_length`, with `limit_start` /
`limit_page_length` accepted as aliases (they win when both are sent). Default page
size **40**.

`get_members` is fixed at **13** rows per page and takes only `start`.

### Filters

`filters` and `or_filters` accept a Frappe filter dict, either as a JSON object or a
JSON-encoded string:

```json
{"filters": {"published": 1, "category": "Programming"}}
{"filters": {"enrollments": [">", 100]}}
```

Several endpoints add **pseudo-filters** that are not real fields and get rewritten
server-side (`enrolled`, `created`, `live`, `certification`, `title`) — see
[Courses](./courses.md#get_courses) and [Batches](./batches.md#get_batches).

### Errors

Failures come back as a non-2xx status with a JSON body carrying the message and,
in developer mode, a traceback.

| Status | Frappe exception | Typical cause |
| --- | --- | --- |
| `400` | `ValidationError` | Bad argument type, unknown value, failed business rule |
| `401` | `AuthenticationError` | Missing or invalid credentials |
| `403` | `PermissionError` | Authenticated but not allowed |
| `404` | `DoesNotExistError` | Referenced document is gone |
| `409` | `DuplicateEntryError` | Unique constraint |
| `417` | `ValidationError` (legacy) | Older Frappe versions return 417 for `frappe.throw` |
| `429` | — | Rate limit / signup throttle |
| `500` | — | Unhandled server error |

```json
{
  "exception": "frappe.exceptions.PermissionError: You do not have permission to delete this course.",
  "exc_type": "PermissionError",
  "_server_messages": "[\"{\\\"message\\\": \\\"You do not have permission to delete this course.\\\"}\"]"
}
```

Read `exc_type` for branching; read `_server_messages` (a JSON-encoded array of
JSON-encoded objects) for the user-facing text.

### Roles

Permission notes throughout this reference refer to these roles:

| Role | Meaning |
| --- | --- |
| `Moderator` | Full LMS administrator |
| `Course Creator` | Authors courses and lessons |
| `Batch Evaluator` | Runs batches, evaluations and certifications |
| `LMS Student` | Default role for signups |
| `System Manager` | Frappe site administrator |

`LMS_ROLES` — the set `save_role` and `search_users_by_role` will act on — is exactly
`["Moderator", "Course Creator", "Batch Evaluator", "LMS Student"]`.

Two ownership predicates recur:

- **`can_modify_course(course)`** — a listed Course Instructor on that course, or a Moderator.
- **`can_modify_batch(batch)`** — a listed instructor on that batch, or a Moderator.

### Reading this reference

Each endpoint is documented as:

> ### `method_name`
> `dotted.path.to.method` — **Guest: no** · **Writes** · *Roles: Moderator*
>
> What it does.
>
> **Parameters** — table of name, type, required, description.
> **Returns** — the shape of `message`.

---

## Quick example

Fetch the first page of published courses, then one course's outline:

```bash
SITE=https://learn.example.com
AUTH='Authorization: token abc123:def456'

curl -s -H "$AUTH" -G "$SITE/api/method/lms.lms.utils.get_courses" \
  --data-urlencode 'filters={"published":1}' \
  --data-urlencode 'start=0' \
  --data-urlencode 'limit_page_length=12'

curl -s -H "$AUTH" -G "$SITE/api/method/lms.lms.utils.get_course_outline" \
  --data-urlencode 'course=intro-to-python' \
  --data-urlencode 'progress=1'
```

Mark a lesson complete:

```bash
curl -s -H "$AUTH" -H 'Content-Type: application/json' \
  -X POST "$SITE/api/method/lms.lms.doctype.course_lesson.course_lesson.save_progress" \
  -d '{"lesson": "lesson-0042", "course": "intro-to-python"}'
```
