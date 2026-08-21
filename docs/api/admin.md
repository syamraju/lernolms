[← API index](./README.md)

# Platform, settings & admin

Site configuration, branding, search, statistics, SEO metadata, bulk deletion and
integrations.

| Endpoint | Guest | Writes |
| --- | --- | --- |
| [`get_lms_settings`](#get_lms_settings) | yes | — |
| [`get_branding`](#get_branding) | yes | — |
| [`get_translations`](#get_translations) | yes | — |
| [`get_sidebar_settings`](#get_sidebar_settings) | yes | — |
| [`update_sidebar_item`](#update_sidebar_item) | no | yes |
| [`delete_sidebar_item`](#delete_sidebar_item) | no | yes |
| [`get_pwa_manifest`](#get_pwa_manifest) | yes | — |
| [`search_sqlite`](#search_sqlite) | no | — |
| [`get_chart_details`](#get_chart_details) | yes | — |
| [`get_chart_data`](#get_chart_data) | yes | — |
| [`get_course_completion_data`](#get_course_completion_data) | yes | — |
| [`get_meta_info`](#get_meta_info) | no | — |
| [`update_meta_info`](#update_meta_info) | no | yes |
| [`get_unsplash_photos`](#get_unsplash_photos) | no | — |
| [`delete_documents`](#delete_documents) | no | yes |
| [`clear_demo_data`](#clear_demo_data) | no | yes |
| [`check_payments_app`](#check_payments_app) | no | yes |
| [`create_email_account`](#create_email_account) | no | yes |
| [`get_raven_setup`](#get_raven_setup) | no | — |

---

## `get_lms_settings`

`lms.lms.api.get_lms_settings` — **Guest: yes**

Client-safe subset of `LMS Settings`. Deliberately an **allow-list** — adding a
field to LMS Settings does not automatically expose it here.

**Returns**

| Field | Type | Meaning |
| --- | --- | --- |
| `allow_guest_access` | `bool` | Whether unauthenticated browsing is on. Gates most guest endpoints. |
| `prevent_skipping_videos` | `bool` | Video scrubbing restriction. |
| `enforce_video_completion` | `bool` | Video must finish before the lesson completes. |
| `enforce_quiz_completion` | `bool` | Quiz must be passed before the lesson completes. |
| `enforce_assignment_completion` | `bool` | Assignment must be submitted before the lesson completes. |
| `lesson_dwell_time` | `int` | Minimum seconds on a lesson before it can be marked done. |
| `contact_us_email`, `contact_us_url` | `str` | Support links. |
| `livecode_url` | `str` | Code-execution service endpoint. |
| `disable_pwa` | `bool` | |
| `demo_data_present` | `bool` | Whether seeded demo content is still installed. |
| `is_payments_app_installed` | `bool` | Computed — whether the `payments` app is installed. |

---

## `get_branding`

`lms.lms.api.get_branding` — **Guest: yes**

Site branding from Website Settings.

**Returns**

```json
{
  "app_name": "Learno",
  "app_logo":     { "file_url": "/files/logo.svg", "file_name": "logo.svg", "…": "…" },
  "banner_image": { "…": "…" },
  "footer_logo":  { "…": "…" },
  "favicon":      { "…": "…" }
}
```

`app_name` is a plain string; the four image fields are resolved to full file-info
objects, or `null` when unset.

---

## `get_translations`

`lms.lms.api.get_translations` — **Guest: yes**

The full translation dictionary for the caller's language — the User's `language`
for a signed-in caller, System Settings' language for a guest.

**Returns** — `{ "<source string>": "<translated string>" }`.

---

## `get_sidebar_settings`

`lms.lms.api.get_sidebar_settings` — **Guest: yes**

Which navigation items to render, plus any custom web pages an administrator has
pinned.

Returns `[]` — an empty **array**, not an object — for a guest when guest access is
off. Handle both shapes.

**Returns**

```json
{
  "courses": 1, "batches": 1, "certifications": 1,
  "statistics": 1, "notifications": 1, "programming_exercises": 0,
  "web_pages": [
    { "name": "si-001", "web_page": "handbook", "route": "/handbook",
      "to": "/handbook", "label": "Handbook", "icon": "book" }
  ]
}
```

`web_pages` is present only when custom items are configured. `to` mirrors `route`
for router convenience.

---

## `update_sidebar_item`

`lms.lms.api.update_sidebar_item` — **Guest: no** · **Writes** · *Roles: Moderator*

Sets the icon for a custom sidebar web-page item, creating the `LMS Sidebar Item`
row if it does not exist yet.

**Parameters** — `webpage` (`str`, required — Web Page name), `icon` (`str`, required).

**Returns** — `null`.

---

## `delete_sidebar_item`

`lms.lms.api.delete_sidebar_item` — **Guest: no** · **Writes** · *Roles: Moderator*

Removes a custom sidebar item.

**Parameters** — `webpage` (`str`, required).

**Returns** — the delete result.

---

## `get_pwa_manifest`

`lms.lms.api.get_pwa_manifest` — **Guest: yes**

**Does not use the JSON envelope.** Returns a raw HTTP response with
`Content-Type: application/manifest+json` — link it directly from a page:

```html
<link rel="manifest" href="/api/method/lms.lms.api.get_pwa_manifest">
```

**Returns** — a Web App Manifest. `name` / `short_name` come from Website Settings'
`app_name` (falling back to `"Learno"`); `id`, `start_url` and `scope` all use the
configured LMS route, so a changed start URL is not treated as a different app.
`display` is `standalone`, orientation `portrait`.

Icons are split by purpose — separate `any` and `maskable` entries at 192 and
512 px — so the `any` slot is never drawn with maskable cropping. The Website
Settings banner image is deliberately not a source: it is a wide banner and would
render as a squashed app icon.

---

## `search_sqlite`

`lms.command_palette.search_sqlite` — **Guest: no**

Command-palette search over the local SQLite full-text index.

**Title-only.** The index also matches descriptions, which meant `"cour"` returned
every course whose blurb contained the word "course" — and since a palette row
renders only its title, the reason for the match was invisible. Matching is
restricted to titles.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `query` | `str` | yes | Search text. |
| `category` | `str` | no | One of `courses`, `batches`, `quizzes`, `assignments`, `programs`. Any other value throws. |

**Returns** — results grouped in fixed order (Courses, Batches, Quizzes,
Assignments, Programs), deduplicated, newest-modified first:

```json
[{
  "title": "Courses",
  "items": [{ "doctype": "LMS Course", "name": "intro-to-python",
              "title": "Intro to Python", "modified": "2026-08-01 10:00:00.000000" }]
}]
```

Only those four fields leave the server — an unprojected index row would carry a
whole course description or assignment question, up to 100 of them per keystroke.

Returns `[]` when the search index has not been built.

**Visibility.** Quizzes and assignments are scoped by hand rather than by
`frappe.get_list`: they grant `read` to `LMS Student` with no query-conditions hook,
so the generic route would hand every student every row on the site. A Moderator
sees all; an instructor sees their own courses'; nobody else sees any.

---

## `get_chart_details`

`lms.lms.api.get_chart_details` — **Guest: yes**

Headline counters for the public statistics page.

**Returns**

```json
{
  "enrollments": 4821,
  "courses": 62,
  "users": 3140,
  "completions": 1102,
  "certifications": 418
}
```

`courses` counts published, non-upcoming courses. `users` excludes `Administrator`
and `Guest` and counts only enabled accounts. `completions` counts enrollments at
100% progress. `certifications` counts published certificates.

---

## `get_chart_data`

`lms.lms.utils.get_chart_data` — **Guest: yes**

Time series for a configured Frappe `Dashboard Chart`.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `chart_name` | `str` | yes | `Dashboard Chart` name. |
| `timegrain` | `str` | no | Bucket size. Default `"Daily"`. |
| `from_date` | `str` | no | `YYYY-MM-DD`. Defaults applied by `get_chart_date_range`. |
| `to_date` | `str` | no | `YYYY-MM-DD`. |

**Returns** — `[{"date": "2026-08-01", "count": 14}, …]`.

---

## `get_course_completion_data`

`lms.lms.utils.get_course_completion_data` — **Guest: yes**

Completed vs in-progress enrollments across the whole site, ready to plot.

**Returns** — `[{"label": "Completed", "value": 1102}, {"label": "In Progress", "value": 3719}]`.

---

## `get_meta_info`

`lms.lms.api.get_meta_info` — **Guest: no**

SEO meta tags stored for a route.

**Parameters** — `type` (`str`, required — e.g. `"courses"` or `"batches"`),
`route` (`str`, required). They are joined as `"<type>/<route>"` to form the
`Website Route Meta` parent.

**Returns** — `[{"name": "wmt-01", "key": "og:title", "value": "Intro to Python"}]`,
or `[]`.

---

## `update_meta_info`

`lms.lms.api.update_meta_info` — **Guest: no** · **Writes** · *Roles: Course Creator, Batch Evaluator, Moderator*

Upserts SEO meta tags for a route, creating the parent `Website Route Meta` if
needed.

**Per-type permission** is checked on top of the role gate: `meta_type = "courses"`
requires Course Creator or Moderator; `"batches"` requires Batch Evaluator or
Moderator.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `meta_type` | `str` | yes | `"courses"` or `"batches"`. |
| `route` | `str` | yes | Route segment. |
| `meta_tags` | `list` | yes | `[{"key": "og:title", "value": "…"}, …]`. |

**Sending an empty `value` deletes that tag.** All values are HTML-stripped before
storage.

**Returns** — `null`.

---

## `get_unsplash_photos`

`lms.lms.api.get_unsplash_photos` — **Guest: no**

Cover-image picker backed by Unsplash. With a `keyword`, performs a live search;
without one, returns the cached default list.

Only a **non-empty** result is cached — otherwise a site that had not yet configured
an Unsplash access key would cache the empty list and keep serving nothing after the
key was added, until someone cleared the cache by hand.

**Parameters** — `keyword` (`str`, optional). A non-string raises `ValidationError`.

**Returns** — array of Unsplash photo objects. `[]` when no access key is configured.

---

## `delete_documents`

`lms.lms.api.delete_documents` — **Guest: no** · **Writes** · *Roles: Moderator*

Bulk-deletes documents of one doctype.

**Scope limit.** The doctype must belong to the **LMS module**, with exactly two
exceptions: `Payment Gateway` and `Email Template`. Anything else throws
`Deletion not allowed for <doctype>` — so this cannot be turned on core framework
doctypes.

Each name is validated as a non-empty string; documents are deleted one at a time
through `frappe.delete_doc`, so link validation and `on_trash` hooks still run.

**Parameters** — `doctype` (`str`, required), `documents` (`list`, required).

**Returns** — `null`.

---

## `clear_demo_data`

`lms.lms.api.clear_demo_data` — **Guest: no** · **Writes** · *Roles: Moderator*

Removes seeded demo content: the demo quizzes (both the current and pre-rebrand
titles), every demo course — deleted through the full
[`delete_course`](./courses.md#delete_course) cascade — and the demo users
`ash@ipp.com`, `john.doe@example.com`, `jane.smith@example.com`,
`jannat@example.com`. Finally clears `LMS Settings.demo_data_present`.

**Returns** — `null`. **Irreversible.**

---

## `check_payments_app`

`lms.lms.doctype.lms_settings.lms_settings.check_payments_app` — **Guest: no** · **Writes**

Reports whether the `payments` app is installed and, if so, wires
`LMS Settings.payment_gateway` up as a Link field to `Payment Gateway` by creating
the two Property Setters — which is why a read-shaped endpoint writes.

Idempotent: once the Property Setters exist it returns `true` without writing.

**Returns** — `false` if the `payments` app is absent, `true` otherwise.

---

## `create_email_account`

`lms.lms.email_account.create_email_account` — **Guest: no** · **Writes** · *Requires `create` on Email Account*

Creates an `Email Account` with correct host/port presets for the chosen service —
Frappe does not auto-apply these to API-created accounts.

**Supported `service` values:** `Frappe Mail`, `GMail`, `Outlook.com`, `Sendgrid`,
`SparkPost`, `Yahoo Mail`, `Yandex.Mail`. Anything else throws
`Email service <x> is not supported`.

**Parameters** — a single `data` object:

| Key | Type | Notes |
| --- | --- | --- |
| `service` | `str` | Required. See above. |
| `email_id` | `str` | The address. |
| `email_account_name` | `str` | Display name. |
| `enable_incoming`, `enable_outgoing` | `bool` | |
| `default_incoming`, `default_outgoing` | `bool` | |
| `password` | `str` | For every service **except** Frappe Mail. |
| `api_key`, `api_secret`, `frappe_mail_site` | `str` | Frappe Mail only. |

Fixed defaults applied to every account: `email_sync_option: "ALL"`,
`initial_sync_count: 100`, `track_email_status: 1`. For non-Frappe-Mail services
with incoming enabled, an `INBOX` → `Communication` folder mapping is added.

**Credentials are verified by Frappe on save** — bad credentials surface as a
`ValidationError` carrying the underlying message, and no account is created.

**Returns** — the new `Email Account` docname.

---

## `get_raven_setup`

`lms.raven_provider.get_raven_setup` — **Guest: no** · *Roles: System Manager (plus any role in the `raven_integration_manager_roles` hook)*

Setup state for the Raven chat integration: are both apps installed, and is the
integration enabled?

The settings panel cannot ask `raven_integration` directly — Frappe answers a method
of an uninstalled app with `AppNotInstalledError`, and frappe-ui prints the server
traceback and rethrows it before any `onError` handler runs. That is an unquietable
error on the very screen whose job is to say "install the app". So LMS answers the
install half itself and delegates only when it can be served.

**Returns**

```json
{ "raven": true, "raven_integration": true, "enabled": false }
```

`enabled` is `false` unless both apps are installed, in which case
`raven_integration.api.is_setup` supplies it.
