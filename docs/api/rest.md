[← API index](./README.md)

# Generic REST resources

Everything the custom endpoints do not cover is reachable through Frappe's generic
document API. Use it to create, read, update and delete LMS documents directly.

Custom endpoints exist where a plain CRUD call would be wrong — batched permission
lookups, cascade deletes, gated media, ordering rewrites. **Prefer the documented
endpoint whenever one exists.**

---

## Endpoints

| Operation | Route |
| --- | --- |
| List | `GET /api/resource/{doctype}` |
| Read | `GET /api/resource/{doctype}/{name}` |
| Create | `POST /api/resource/{doctype}` |
| Update | `PUT /api/resource/{doctype}/{name}` |
| Delete | `DELETE /api/resource/{doctype}/{name}` |
| File upload | `POST /api/method/upload_file` |

The RPC equivalents — `frappe.client.get_list`, `get`, `get_value`, `get_count`,
`insert`, `set_value`, `delete`, `rename_doc` — stay reachable even when the site
runs with `block_endpoints` on.

## List parameters

| Parameter | Example |
| --- | --- |
| `fields` | `["name","title","published"]` |
| `filters` | `[["published","=",1],["enrollments",">",100]]` |
| `or_filters` | `[["title","like","%python%"]]` |
| `order_by` | `creation desc` |
| `limit_start` | `0` |
| `limit_page_length` | `20` |
| `parent` | required when reading a child table |

```bash
curl -s -G "$SITE/api/resource/LMS Course" \
  -H "Authorization: token $KEY:$SECRET" \
  --data-urlencode 'fields=["name","title","enrollments"]' \
  --data-urlencode 'filters=[["published","=",1]]' \
  --data-urlencode 'order_by=enrollments desc' \
  --data-urlencode 'limit_page_length=10'
```

List responses put rows under `data`, not `message`:

```json
{ "data": [ { "name": "intro-to-python", "title": "Intro to Python", "enrollments": 812 } ] }
```

## Creating and updating

```bash
curl -s -X POST "$SITE/api/resource/LMS Course Review" \
  -H "Authorization: token $KEY:$SECRET" \
  -H 'Content-Type: application/json' \
  -d '{"course": "intro-to-python", "review": "Excellent pacing.", "rating": 0.8}'
```

Rating fields store a **0–1 fraction**, not a 1–5 score.

## Uploading files

```bash
curl -s -X POST "$SITE/api/method/upload_file" \
  -H "Authorization: token $KEY:$SECRET" \
  -F 'file=@lesson-video.mp4' \
  -F 'is_private=1' \
  -F 'doctype=Course Lesson' \
  -F 'docname=lesson-0011'
```

Returns the created `File` document; use its `file_url` where an endpoint asks for
one (SCORM packages, course-import zips, assignment submissions).

Private lesson media is **not** served from `/private/files/` — see
[`serve_resource`](./lessons.md#serve_resource).

---

## Principal doctypes

### Content

| Doctype | Notes |
| --- | --- |
| `LMS Course` | Root course record. Delete via [`delete_course`](./courses.md#delete_course), not `DELETE`. |
| `Course Chapter` | Create/update via [`upsert_chapter`](./lessons.md#upsert_chapter). |
| `Chapter Reference` | Child of `LMS Course` — outline order. Reorder via [`update_chapter_index`](./lessons.md#update_chapter_index). |
| `Course Lesson` | Create via [`create_lesson`](./lessons.md#create_lesson); edit body/content over REST. |
| `Lesson Reference` | Child of `Course Chapter`. Reorder via [`update_lesson_index`](./lessons.md#update_lesson_index). |
| `Course Instructor` | Child of `LMS Course` / `LMS Batch`. |
| `Related Courses`, `LMS Category` | Category deletion goes through [`delete_category`](./courses.md#delete_category). |

### Enrollment & progress

| Doctype | Notes |
| --- | --- |
| `LMS Enrollment` | One per member per course. Carries `progress` and `current_lesson`. |
| `LMS Course Progress` | One per completed lesson. Write via [`save_progress`](./lessons.md#save_progress). |
| `LMS Video Watch Duration` | Write via [`track_video_watch_duration`](./lessons.md#track_video_watch_duration). |
| `LMS Batch Enrollment` | Create via [`enroll_in_batch`](./batches.md#enroll_in_batch). |
| `LMS Program Member` | Create via [`enroll_in_program`](./programs.md#enroll_in_program). |

### Assessment

| Doctype | Notes |
| --- | --- |
| `LMS Quiz`, `LMS Quiz Question`, `LMS Question` | Read via [`get_quiz_with_questions`](./assessments.md#get_quiz_with_questions). |
| `LMS Quiz Submission` | Created by [`submit_quiz`](./assessments.md#submit_quiz) — do not insert directly. |
| `LMS Assignment`, `LMS Assignment Submission` | Submissions are keyed on `member`, not `owner` — see [`get_own_assignment_submission`](./assessments.md#get_own_assignment_submission). |
| `LMS Programming Exercise`, `LMS Programming Exercise Submission` | |
| `LMS Assessment` | Child of `LMS Batch`. |

### Cohorts

| Doctype | Notes |
| --- | --- |
| `LMS Batch`, `Batch Course`, `LMS Batch Timetable`, `LMS Batch Feedback` | |
| `LMS Live Class` | Create via [`create_live_class`](./batches.md#create_live_class) or the Google Meet variant — direct insert skips the provider call. |
| `LMS Program`, `LMS Program Course` | |

### Certification

| Doctype | Notes |
| --- | --- |
| `LMS Certificate` | Issue via [`create_certificate`](./certifications.md#create_certificate) or [`save_certificate_details`](./certifications.md#save_certificate_details). |
| `LMS Certificate Request` | The booking record. |
| `LMS Certificate Evaluation` | Write via [`save_evaluation_details`](./certifications.md#save_evaluation_details). |
| `Course Evaluator`, `Evaluator Schedule` | Manage through the evaluator-slot endpoints — direct writes can grant the Batch Evaluator role as a side effect. |

### Commerce & social

| Doctype | Notes |
| --- | --- |
| `LMS Payment`, `LMS Coupon` | Payments are written by [`get_payment_link`](./payments.md#get_payment_link). |
| `Discussion Topic`, `Discussion Reply` | Insert here; read via the [discussion endpoints](./discussions.md). |
| `LMS Course Review` | |
| `LMS Badge`, `LMS Badge Assignment` | Manual awards via [`assign_badge`](./users.md#assign_badge). |
| `LMS Settings`, `LMS Sidebar Item` | Single doctype: `GET /api/resource/LMS Settings/LMS Settings`. |

---

## Permissions

The generic API enforces Frappe's role permissions and every
`permission_query_conditions` hook the app registers. It does **not** enforce the
extra rules the custom endpoints add — `can_modify_course`, `can_access_lesson`,
`can_access_quiz`, the batch admin checks. Where a documented endpoint exists,
those rules exist for a reason; go through it.

To find out what the caller may do with a set of documents before rendering
affordances, use
[`get_doc_permissions_many`](./users.md#get_doc_permissions_many) — one call for up
to 200 documents.
