[← API index](./README.md)

# Users, members & profiles

Signup, session identity, member administration, roles, profiles and gamification.

| Endpoint | Guest | Writes |
| --- | --- | --- |
| [`sign_up`](#sign_up) | yes | yes |
| [`get_user_info`](#get_user_info) | no | — |
| [`get_all_users`](#get_all_users) | no | — |
| [`get_member`](#get_member) | no | — |
| [`get_members`](#get_members) | no | — |
| [`get_application_users`](#get_application_users) | no | — |
| [`search_users_by_role`](#search_users_by_role) | no | — |
| [`get_roles`](#get_roles) | no | — |
| [`save_role`](#save_role) | no | yes |
| [`delete_member`](#delete_member) | no | yes |
| [`get_profile_details`](#get_profile_details) | no | — |
| [`get_heatmap_data`](#get_heatmap_data) | no | — |
| [`get_streak_info`](#get_streak_info) | no | — |
| [`get_badges`](#get_badges) | no | — |
| [`assign_badge`](#assign_badge) | no | yes |
| [`capture_user_persona`](#capture_user_persona) | no | yes |
| [`get_doc_permissions_many`](#get_doc_permissions_many) | no | — |

---

## `sign_up`

`lms.lms.user.sign_up` — **Guest: yes** · **Writes**

Registers a new Website User. Assigns the Portal Settings default role, generates a
random password, and triggers the verification email.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `email` | `str` | yes | Login email. |
| `full_name` | `str` | yes | HTML-escaped before storage. |
| `verify_terms` | `bool` | yes | Terms acceptance flag. |
| `user_category` | `str` | yes | Persona category captured at signup. |

**Returns** — a `[code, message]` pair:

| Code | Meaning |
| --- | --- |
| `0` | Already registered (or registered but disabled). |
| `1` | Signup successful — verification email sent. |
| `2` | Signup successful — an administrator must verify. |

```json
{ "message": [1, "Signup successful. Please check your email for verification."] }
```

**Throttling and races.** Throws `Sign Up is disabled` when signup is off. Once
`max_signups_allowed_per_hour` (System Settings, default 300) is exceeded, responds
with HTTP **429**. Concurrent inserts for the same email are resolved as "already
registered"; deadlocks are retried up to three times with backoff.

---

## `get_user_info`

`lms.lms.api.get_user_info` — **Guest: no**

Everything the client needs about the session user in one call. Returns `null` for
Guest.

**Returns**

| Field | Type | Notes |
| --- | --- | --- |
| `name`, `email`, `username`, `full_name`, `user_image`, `bio`, `headline` | | Profile. |
| `enabled`, `user_type` | | Account state. |
| `roles` | `array` | Every role held. |
| `is_instructor` | `bool` | Holds `Course Creator`. |
| `is_moderator` | `bool` | Holds `Moderator`. |
| `is_evaluator` | `bool` | Holds `Batch Evaluator`. |
| `is_student` | `bool` | None of the three above. |
| `is_system_manager` | `bool` | |
| `is_fc_site` | `bool` | Running on Frappe Cloud. |
| `site_info` | `object` | Frappe Cloud site info — only for System Managers on an FC site. |
| `sitename` | `str` | |
| `developer_mode` | `bool` | |
| `permissions` | `object` | Doctype-level permission map for the caller. |

---

## `get_all_users`

`lms.lms.api.get_all_users` — **Guest: no** · *Roles: Moderator, Course Creator, Batch Evaluator*

Every enabled user, keyed by name — for client-side avatar and mention lookups.

**Returns**

```json
{
  "asha@example.com": { "name": "asha@example.com", "full_name": "Asha K", "user_image": "/files/a.png" }
}
```

---

## `get_member`

`lms.lms.api.get_member` — **Guest: no** · *Roles: Moderator*

One member by exact name, for the member edit form.

Distinct from `get_members`, which is a paginated search that also hides disabled
users — a member past the first page, or a disabled one, comes back empty there and
leaves the form unable to save.

**Parameters** — `member` (`str`, required). `Administrator`, `Guest`, empty and
non-string values are rejected as `ValidationError`.

**Returns**

```json
{
  "name": "asha@example.com", "full_name": "Asha K",
  "user_image": "/files/a.png", "username": "asha",
  "last_active": "2026-08-20 09:14:02.000000",
  "roles": { "moderator": false, "course_creator": true, "batch_evaluator": false, "lms_student": true }
}
```

Raises `DoesNotExistError` for an unknown member.

---

## `get_members`

`lms.lms.api.get_members` — **Guest: no** · *Roles: Moderator*

Paginated, searchable member list. Always excludes `Administrator`, `Guest` and
disabled users.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `start` | `int` | no | Row offset. Default `0`. **Page size is fixed at 13.** |
| `search` | `str` | no | Substring match on full name OR email. |
| `role` | `str` | no | `"All"` (default) or one of `Moderator`, `Course Creator`, `Batch Evaluator`, `LMS Student`. Anything else is a `ValidationError`. |

**Returns** — array of the `get_member` row shape. `[]` when a role filter matches
no users.

---

## `get_application_users`

`lms.lms.api.get_application_users` — **Guest: no**

User details for a set of job applicants, filtered through the caller's read
permission on `LMS Job Application` — names the caller cannot see are dropped
before the User lookup.

**Parameters** — `user_names` (`list` \| `str`, required — array of user names, or a
JSON-encoded array).

**Returns** — array of `{name, user_image, full_name, email}`. `[]` when the input
is empty or nothing is visible.

---

## `search_users_by_role`

`lms.lms.api.search_users_by_role` — **Guest: no** · *Roles: Moderator, Course Creator, Batch Evaluator*

Typeahead over users holding given LMS roles, returned in Frappe's `search_link`
option format.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `roles` | `str` \| `list` | yes | Roles to search within. Must be a subset of `Moderator`, `Course Creator`, `Batch Evaluator`, `LMS Student` — anything else throws. Returns `[]` if omitted. |
| `txt` | `str` | no | Substring matched against full name or user name. Default `""`. |
| `page_length` | `int` | no | Max results. Default `10`. |
| `names` | `str` \| `list` | no | Explicit user names. **Bypasses the `txt` match entirely** and returns exactly those users — used to hydrate already-selected values. |

**Returns**

```json
[{ "value": "asha@example.com", "label": "Asha K", "description": "Asha K", "user_image": "/files/a.png" }]
```

Sorted by full name. `Administrator`, `Guest` and disabled users are always excluded.

---

## `get_roles`

`lms.lms.utils.get_roles` — **Guest: no** · *Roles: Moderator, Batch Evaluator*

Which LMS roles a user holds.

**Parameters** — `name` (`str`, required — the user).

**Returns**

```json
{ "moderator": false, "course_creator": true, "batch_evaluator": false, "lms_student": true }
```

---

## `save_role`

`lms.lms.api.save_role` — **Guest: no** · **Writes** · *Roles: Moderator*

Grants or revokes one LMS role. Clears the target user's cache afterwards, so the
change takes effect on their next request.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `user` | `str` | yes | Target user. |
| `role` | `str` | yes | Must be one of `Moderator`, `Course Creator`, `Batch Evaluator`, `LMS Student`. Any other role raises `PermissionError` — **this endpoint cannot grant `System Manager` or arbitrary framework roles.** |
| `value` | `int` | yes | `1` to grant, `0` to revoke. |

`Batch Evaluator` is delegated to `save_evaluator_role`, which also maintains the
associated `Course Evaluator` record.

**Returns** — `true`.

---

## `delete_member`

`lms.lms.api.delete_member` — **Guest: no** · **Writes** · *Roles: Moderator*

Permanently deletes a user.

**Refuses** to delete `Administrator`, `Guest`, or **the caller themselves** — each
raises `PermissionError`. An unknown user raises `ValidationError`.

**Parameters** — `user` (`str`, required).

**Returns** — `true`.

---

## `get_profile_details`

`lms.lms.api.get_profile_details` — **Guest: no**

Public profile for a username.

**Access rule.** Anyone may read **their own** profile, regardless of roles — users
created in Desk, by Data Import or by another app never pick up `LMS Student` and
must still be able to open their own page. Reading **someone else's** requires an
LMS role, and that refusal is raised *before* the not-found check, so the two
errors cannot be used to enumerate usernames.

**Parameters** — `username` (`str`, required).

**Returns**

```json
{
  "name": "asha@example.com", "username": "asha",
  "first_name": "Asha", "last_name": "K", "full_name": "Asha K",
  "user_image": "/files/a.png", "cover_image": "/files/cover.png",
  "bio": "…", "headline": "Backend engineer", "language": "en",
  "open_to": "Work",
  "linkedin": "…", "github": "…", "twitter": "…",
  "roles": ["LMS Student", "Course Creator"]
}
```

`roles` is the **full** role list only for the profile's owner or a Moderator;
everyone else sees it filtered down to LMS roles.

---

## `get_heatmap_data`

`lms.lms.api.get_heatmap_data` — **Guest: no** · *Roles: Course Creator, Moderator or Batch Evaluator*

GitHub-style activity heatmap for a member, combining lesson completions, quiz
submissions and assignment submissions.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `member` | `str` | yes | User to chart. |
| `base_days` | `int` | no | Window length in days. Default `200`. |

**Returns**

```json
{ "heatmap_data": { "2026-08-19": 3 }, "labels": [ … ], "total_activities": 412, "weeks": 29 }
```

---

## `get_streak_info`

`lms.lms.api.get_streak_info` — **Guest: no**

Learning streak for **the session user** — no parameters, no way to read someone
else's.

**Returns** — `{ "current_streak": 6, "longest_streak": 23 }`.

---

## `get_badges`

`lms.lms.api.get_badges` — **Guest: no** · *Requires any LMS role*

Badges awarded to a member.

**Parameters** — `member` (`str`, required).

**Returns**

```json
[{ "name": "ba-001", "member": "asha@example.com", "badge": "First Course",
   "badge_image": "/files/badge.png", "badge_description": "…", "issued_on": "2026-05-02" }]
```

---

## `assign_badge`

`lms.lms.doctype.lms_badge.lms_badge.assign_badge` — **Guest: no** · **Writes** · *Roles: Moderator, Course Creator, Batch Evaluator*

Runs a **manual-assignment** badge: evaluates the badge's stored condition against
its reference doctype and awards the badge to every matching user.

No-ops (returns `null`) if the badge's event is not `Manual Assignment` — automatic
badges are awarded by their own document hooks.

**Parameters** — `badge_name` (`str`, required). An unknown badge raises
`DoesNotExistError`.

**Returns** — `"success"` if at least one badge was awarded, `"failed"` if none were.

---

## `capture_user_persona`

`lms.lms.api.capture_user_persona` — **Guest: no** · **Writes** · *Roles: System Manager*

Posts onboarding persona responses to `https://school.frappe.io` and, on success,
sets `LMS Settings.persona_captured`. **This endpoint transmits data off-site.**

**Parameters** — `responses` (`str`, required — JSON payload of survey answers).

**Returns** — the remote service's response.

---

## `get_doc_permissions_many`

`lms.lms.api.get_doc_permissions_many` — **Guest: no**

Evaluated permissions for **several documents of one doctype in a single call**.

Batched deliberately: a course outline resolves affordances for every lesson on
screen at once, and one call per document behind a hide-until-known gate means one
UI flicker per document.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `doctype` | `str` | yes | Must be a real doctype, else `ValidationError`. |
| `names` | `str` \| `list[str]` | yes | Document names. JSON-encoded strings accepted. **Maximum 200 per request.** |

**Returns** — a map from name to permission map:

```json
{
  "lesson-0001": { "read": 1, "write": 1, "delete": 0, "…": 0 },
  "lesson-0002": {}
}
```

A document the caller **cannot read** answers exactly like one that **does not
exist**: `{}`. Anything else would let a caller submit guessed names and read the
difference. Hide-until-known treats a missing ptype as a deny, so `{}` and
`read: 0` render identically.
