[← API index](./README.md)

# Payments & billing

Checkout for paid courses, paid certificates and paid batches, plus gateway
administration.

Requires the [`payments`](https://github.com/frappe/payments) app to be installed —
check with [`check_payments_app`](./admin.md#check_payments_app) or the
`is_payments_app_installed` flag on [`get_lms_settings`](./admin.md#get_lms_settings).

| Endpoint | Guest | Writes |
| --- | --- | --- |
| [`validate_billing_access`](#validate_billing_access) | no | — |
| [`get_order_summary`](#get_order_summary) | no | — |
| [`get_payment_link`](#get_payment_link) | no | yes |
| [`get_payment_field_meta`](#get_payment_field_meta) | no | — |
| [`get_payment_gateway_details`](#get_payment_gateway_details) | no | — |
| [`get_new_gateway_fields`](#get_new_gateway_fields) | no | — |

---

## Checkout flow

```
validate_billing_access   →  may this user buy this, and what does the form need?
        ↓
get_order_summary         →  price, currency, coupon, GST — for display
        ↓
get_payment_link          →  records the payment, returns a gateway URL
        ↓
(gateway redirect)        →  enrollment completed by the payment webhook
```

---

## `validate_billing_access`

`lms.lms.api.validate_billing_access` — **Guest: no**

Whether the session user may proceed to checkout, together with everything the
billing form needs to render: their saved address and the field metadata for both
the payment and address forms.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `billing_type` | `str` | yes | `"course"`, `"batch"` or `"certificate"`. |
| `name` | `str` | yes | The `LMS Course` or `LMS Batch` docname. |

**Returns**

```json
{
  "access": false,
  "message": "You are already enrolled for this course.",
  "address": { "name": "…", "billing_name": "Asha K", "address_line1": "…", "address_line2": "…",
               "city": "…", "state": "…", "country": "India", "pincode": "…", "phone": "…" },
  "billing_field_meta": { "gstin": { "reqd": 0, "default": null, "description": "…" } }
}
```

`address` is `null` when the user has no saved Address.

**Reasons `access` comes back `false`:**

| `billing_type` | Condition | `message` |
| --- | --- | --- |
| any | Caller is Guest | Please login to continue with payment. |
| any | Unknown billing type | Module is incorrect. |
| any | Document does not exist | Module Name is incorrect or does not exist. |
| `course` | Already enrolled | You are already enrolled for this course. |
| `batch` | Already enrolled | You are already enrolled for this batch. |
| `batch` | Seats full | Batch is sold out. |
| `batch` | Start date passed | Batch has already started. |
| `certificate` | Certificate already purchased | *(certificate-specific message)* |

---

## `get_order_summary`

`lms.lms.utils.get_order_summary` — **Guest: no**

Priced order lines for the checkout screen — currency conversion, coupon discount
and GST applied in that order.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `doctype` | `str` | yes | `"LMS Course"` or `"LMS Batch"`. |
| `docname` | `str` | yes | The document being bought. |
| `coupon` | `str` | no | Coupon code to apply. |
| `country` | `str` | no | Buyer's country, for currency and GST. Falls back to the saved Address country, then the User's country, then IP geolocation. |

**Returns**

```json
{
  "name": "intro-to-python", "title": "Intro to Python",
  "currency": "USD",
  "original_amount": 60, "original_amount_formatted": "$ 60",
  "discount_amount": 6, "discount_amount_formatted": "$ 6", "coupon": "LAUNCH10",
  "gst_applied": 0, "gst_amount_formatted": "₹ 0",
  "amount": 54,
  "total_amount": 54, "total_amount_formatted": "$ 54"
}
```

**Currency conversion.** Governed by LMS Settings: `show_usd_equivalent`,
`exception_country` (countries never converted) and `apply_rounding`. An explicit
`amount_usd` on the course/batch is used verbatim when set; otherwise the live
exchange rate is applied and, with rounding on, the result is rounded up to the
next 100.

**GST** is applied only when the resolved currency is `INR`.

Throws `This course is free.` for a course that is neither `paid_course` nor
`paid_certificate`, and `To join this batch, please contact the Administrator.` for
a non-paid batch.

---

## `get_payment_link`

`lms.lms.payments.get_payment_link` — **Guest: no** · **Writes**

The one call that turns a checkout into money. Records an `LMS Payment`, saves the
billing address, and returns the gateway URL to redirect the browser to.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `doctype` | `str` | yes | `"LMS Course"` or `"LMS Batch"`. |
| `docname` | `str` | yes | The document being bought. |
| `address` | `dict` | yes | Billing address. Must carry `billing_name`; the remaining Address fields are saved as given. |
| `payment_for_certificate` | `int` | yes | `1` when buying a certificate for an already-enrolled course, else `0`. |
| `coupon_code` | `str` | no | |
| `country` | `str` | no | For currency and GST resolution. |

**Returns** — a `str` URL. Either the gateway's hosted payment page, or the
in-app redirect route when no payment is needed.

**Three important behaviours**

1. **Double-purchase guard.** Checkout is reachable from a stale tab or the back
   button. If the caller *already has* the access being bought, the billing details
   they typed are still saved and the in-app redirect URL is returned — no second
   charge, no extra coupon redemption.
2. **Free after discount.** When the total lands at zero or below, the `LMS Payment`
   is marked received, enrollment is completed immediately, and the redirect URL is
   returned. No gateway call.
3. **Gateway resolved before any write.** The controller is fetched up front so a
   misconfigured gateway fails with an actionable message instead of leaving an
   orphan Address / `LMS Payment` row behind. The order is created by the gateway
   controller, not pre-created here.

The redirect target after payment is `/{lms}/courses/{name}/certification` for a
certificate purchase, `/{lms}/courses/{name}` for a course, `/{lms}/batches/{name}`
for a batch.

---

## `get_payment_field_meta`

`lms.lms.api.get_payment_field_meta` — **Guest: no**

Field metadata (`reqd`, `default`, `description`) for the `LMS Payment` fields the
billing form renders: `member`, `billing_name`, `source`, `payment_for_document_type`,
`payment_for_document`, `currency`, `amount`, `amount_with_gst`, `original_amount`,
`discount_amount`, `coupon`, `coupon_code`, `address`, `gstin`, `pan`, `payment_id`,
`order_id`, `member_consent`.

**Returns** — `{ "<fieldname>": {"reqd": 0|1, "default": …, "description": …} }`.

Also returned inline as `billing_field_meta` by `validate_billing_access`, so a
separate call is usually unnecessary.

---

## `get_payment_gateway_details`

`lms.lms.api.get_payment_gateway_details` — **Guest: no** · *Roles: Moderator*

Current configuration and form schema for a configured payment gateway. Resolves
the settings doctype either from the gateway's `gateway_controller` or, when absent,
by convention (`"<Gateway> Settings"`).

**Parameters** — `payment_gateway` (`str`, required — `Payment Gateway` name).

**Returns**

```json
{
  "fields": [ { "fieldname": "api_key", "label": "API Key", "fieldtype": "Data", "reqd": 1 } ],
  "data":   { "api_key": "rzp_live_…", "…": "…" },
  "doctype": "Razorpay Settings",
  "docname": "Razorpay Settings"
}
```

Throws `<Gateway> Settings not found` when the settings document is missing.

---

## `get_new_gateway_fields`

`lms.lms.api.get_new_gateway_fields` — **Guest: no** · *Roles: Moderator*

The blank form schema for configuring a gateway that has no settings document yet.

**Parameters** — `doctype` (`str`, required — the settings doctype, e.g.
`"Stripe Settings"`).

**Returns** — an array of transformed field descriptors, same shape as the `fields`
key of `get_payment_gateway_details`. Throws `<doctype> not found` for an unknown
doctype.
