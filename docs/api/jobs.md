[← API index](./README.md)

# Jobs

The job board: `Job Opportunity` listings and `LMS Job Application`.

Job posting must be enabled in LMS Settings (`allow_job_posting`) — read it from
[`get_lms_settings`](./admin.md#get_lms_settings).

| Endpoint | Guest | Writes |
| --- | --- | --- |
| [`get_job_opportunities`](#get_job_opportunities) | yes | — |
| [`get_job_opportunities_count`](#get_job_opportunities_count) | yes | — |
| [`get_job_details`](#get_job_details) | yes | — |
| [`get_application_users`](#get_application_users) | no | — |
| [`report`](#report) | no | yes |

---

## `get_job_opportunities`

`lms.lms.api.get_job_opportunities` — **Guest: yes**

Paginated job listings, newest first. Descriptions are returned with HTML stripped,
suitable for a card blurb, and each row carries a live applicant count.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `filters` | `dict` | no | **Allow-listed:** `status`, `type`, `work_mode`, `country`. Any other key is silently dropped. |
| `or_filters` | `dict` | no | **Allow-listed:** `job_title`, `company_name`, `location`. Any other key is silently dropped. |
| `start` | `int` | no | Offset. Default `0`. Alias: `limit_start`. |
| `page_length` | `int` | no | Page size. Default `40`. Alias: `limit_page_length`. |

When both `start` and `limit_start` are sent, `limit_start` wins; likewise
`limit_page_length` over `page_length`.

**Closed jobs are scoped.** Filtering `status = "Closed"` as a non-Moderator
silently adds `owner = <session user>` — you see only your own closed postings.

**Returns**

```json
[{
  "name": "job-0042", "job_title": "Backend Engineer",
  "company_name": "Acme", "company_logo": "/files/acme.png",
  "location": "Bengaluru", "country": "India",
  "type": "Full Time", "work_mode": "Hybrid",
  "description": "We are looking for…",
  "creation": "2026-08-01 10:00:00.000000",
  "applicants": 17
}]
```

---

## `get_job_opportunities_count`

`lms.lms.api.get_job_opportunities_count` — **Guest: yes**

Count matching the same allow-listed `filters` / `or_filters`, including the
closed-jobs owner scoping.

**Parameters** — `filters` (`dict`), `or_filters` (`dict`), both optional.

**Returns** — `int`.

---

## `get_job_details`

`lms.lms.api.get_job_details` — **Guest: yes**

One job listing in full — the description is **not** stripped here, so the detail
page renders the author's formatting.

**Parameters** — `job` (`str`, required). A non-string raises `ValidationError`.

**Returns**

```json
{
  "name": "job-0042", "job_title": "Backend Engineer",
  "company_name": "Acme", "company_logo": "/files/acme.png", "company_website": "https://acme.example",
  "location": "Bengaluru", "country": "India",
  "type": "Full Time", "work_mode": "Hybrid",
  "description": "<p>We are looking for…</p>",
  "creation": "2026-08-01 10:00:00.000000",
  "owner": "recruiter@acme.example",
  "applicants": 17
}
```

Returns `null` for an unknown job.

---

## `get_application_users`

`lms.lms.api.get_application_users` — **Guest: no**

Profile details for a set of applicants, **filtered through the caller's read
permission on `LMS Job Application`** — names the caller may not see are dropped
before the User lookup, so this cannot be used to resolve arbitrary user records.

**Parameters** — `user_names` (`list` \| `str`, required — array of user names, or a
JSON-encoded array).

**Returns** — array of `{name, user_image, full_name, email}`. `[]` when the input
is empty or nothing is visible.

---

## `report`

`lms.job.doctype.job_opportunity.job_opportunity.report` — **Guest: no** · **Writes**

Reports a job posting to the site's System Managers. Sends an email immediately
(`now=True`) using the `job_report` template, including the reporter's name, the
reason and a desk link to the posting.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `job` | `str` | yes | `Job Opportunity` name. |
| `reason` | `str` | yes | Why it is being reported. |

**Returns** — `null`.
