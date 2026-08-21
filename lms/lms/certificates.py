"""Certificate design, completeness and public verification.

A certificate here is not a print format. The moderator uploads a PNG or JPG —
the **canvas** — and places elements on top of it: the mandatory variables, any
optional ones, free text, and extra images such as a signature or a seal. Every
coordinate is stored in the canvas image's own pixel space, so the same design
renders identically in the editor, in the preview and on the public
verification page regardless of how wide the viewport is.

Two rules drive the rest of this module:

* **A course cannot be handed to instructors until its certificate is
  complete.** "Complete" is one computation — `missing_requirements` — and both
  the designer's checklist and the server-side gate read it, so the button and
  the error can never disagree about what is still missing.
* **An issued certificate never changes.** The design is frozen into the
  certificate at issue time (`freeze_certificate`). Editing the template
  afterwards changes what the *next* learner receives, not what an already
  certified one can show an employer.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, flt, formatdate, get_url, getdate, nowdate

REFERENCE_DOCTYPES = ("LMS Course", "LMS Program")

# The uploaded background is the coordinate system. These are only the defaults
# used before an image has been measured client side — an A4 landscape sheet at
# 150dpi, which is what most certificate artwork is exported as.
DEFAULT_CANVAS_WIDTH = 1754
DEFAULT_CANVAS_HEIGHT = 1240

ELEMENT_TYPES = ("Variable", "Text", "Image")

DATE_FORMATS = ("d MMMM yyyy", "MMMM d, yyyy", "dd/MM/yyyy", "dd-MM-yyyy", "yyyy-MM-dd")
DEFAULT_DATE_FORMAT = "d MMMM yyyy"

# The variable catalogue. `mandatory` entries are exactly the fields a
# certificate is not allowed to omit — the course set and the program set differ,
# which is why this is keyed by reference doctype rather than being one list with
# a flag on each row.
COURSE_VARIABLES = (
	{
		"key": "participant_name",
		"label": "Participant name",
		"type": "text",
		"mandatory": True,
		"hint": "Full name of the learner being certified.",
	},
	{
		"key": "course_name",
		"label": "Course name",
		"type": "text",
		"mandatory": True,
		"hint": "Title of the course, as published.",
	},
	{
		"key": "course_start_date",
		"label": "Course start date",
		"type": "date",
		"mandatory": True,
		"hint": "Batch start date, or the day the learner enrolled.",
	},
	{
		"key": "course_end_date",
		"label": "Course end date",
		"type": "date",
		"mandatory": True,
		"hint": "Batch end date, or the day the learner finished.",
	},
	{
		"key": "issue_date",
		"label": "Certificate issue date",
		"type": "date",
		"mandatory": True,
		"hint": "The completion date, or a fixed date you set on this template.",
	},
	{
		"key": "certificate_id",
		"label": "Certificate ID",
		"type": "text",
		"mandatory": False,
		"hint": "The public verification code printed on the certificate.",
	},
	{
		"key": "verification_url",
		"label": "Verification link",
		"type": "text",
		"mandatory": False,
		"hint": "Address of the public page that proves this certificate is real.",
	},
	{
		"key": "organisation_name",
		"label": "Organisation name",
		"type": "text",
		"mandatory": False,
		"hint": "Who authorises the certificate, taken from your site settings.",
	},
	{
		"key": "instructor_name",
		"label": "Instructor name",
		"type": "text",
		"mandatory": False,
		"hint": "The first visible instructor on the course.",
	},
	{
		"key": "batch_name",
		"label": "Batch name",
		"type": "text",
		"mandatory": False,
		"hint": "Blank for a learner who took the course on their own.",
	},
	{
		"key": "expiry_date",
		"label": "Expiry date",
		"type": "date",
		"mandatory": False,
		"hint": "Blank unless the certificate is issued with one.",
	},
)

PROGRAM_VARIABLES = (
	{
		"key": "participant_name",
		"label": "Participant name",
		"type": "text",
		"mandatory": True,
		"hint": "Full name of the learner being certified.",
	},
	{
		"key": "program_name",
		"label": "Program name",
		"type": "text",
		"mandatory": True,
		"hint": "Title of the program, as published.",
	},
	{
		"key": "program_start_date",
		"label": "Program start date",
		"type": "date",
		"mandatory": True,
		"hint": "The day the learner joined the program.",
	},
	{
		"key": "program_end_date",
		"label": "Program end date",
		"type": "date",
		"mandatory": True,
		"hint": "The day the learner finished the last course in it.",
	},
	{
		"key": "issue_date",
		"label": "Certificate issue date",
		"type": "date",
		"mandatory": True,
		"hint": "The completion date, or a fixed date you set on this template.",
	},
	{
		"key": "certificate_id",
		"label": "Certificate ID",
		"type": "text",
		"mandatory": False,
		"hint": "The public verification code printed on the certificate.",
	},
	{
		"key": "verification_url",
		"label": "Verification link",
		"type": "text",
		"mandatory": False,
		"hint": "Address of the public page that proves this certificate is real.",
	},
	{
		"key": "organisation_name",
		"label": "Organisation name",
		"type": "text",
		"mandatory": False,
		"hint": "Who authorises the certificate, taken from your site settings.",
	},
	{
		"key": "course_count",
		"label": "Number of courses",
		"type": "text",
		"mandatory": False,
		"hint": "How many courses the program contains.",
	},
)

VARIABLES = {"LMS Course": COURSE_VARIABLES, "LMS Program": PROGRAM_VARIABLES}


def validate_reference_doctype(reference_doctype: str) -> str:
	if reference_doctype not in REFERENCE_DOCTYPES:
		frappe.throw(_("{0} does not have certificates.").format(reference_doctype))
	return reference_doctype


def variables_for(reference_doctype: str) -> list[dict]:
	return [dict(variable) for variable in VARIABLES[validate_reference_doctype(reference_doctype)]]


def mandatory_keys(reference_doctype: str) -> list[str]:
	return [
		variable["key"]
		for variable in VARIABLES[validate_reference_doctype(reference_doctype)]
		if variable["mandatory"]
	]


def variable_labels(reference_doctype: str) -> dict[str, str]:
	return {
		variable["key"]: variable["label"]
		for variable in VARIABLES[validate_reference_doctype(reference_doctype)]
	}


def missing_requirements(reference_doctype: str, background_image, elements) -> list[dict]:
	"""Everything standing between this design and a usable certificate.

	Pure: it takes the background and a list of element dicts rather than a
	document, so the gate, the designer checklist and the tests all run the same
	code against the same shapes.
	"""
	labels = variable_labels(reference_doctype)
	missing = []

	if not background_image:
		missing.append(
			{
				"code": "background",
				"message": _("Upload a certificate background (PNG or JPG)"),
			}
		)

	placed = {
		(element.get("variable") or "")
		for element in (elements or [])
		if (element.get("element_type") or "") == "Variable"
	}
	for key in mandatory_keys(reference_doctype):
		if key not in placed:
			missing.append(
				{
					"code": key,
					"message": _("Place {0} on the certificate").format(_(labels[key])),
				}
			)

	return missing


def clamp_element(element: dict, canvas_width: int, canvas_height: int) -> dict:
	"""Pull one element back inside the canvas, returning a new dict.

	A box dragged half off the artwork would render clipped on the public page
	and print clipped on paper, and nothing downstream would report why. Rather
	than refuse the save — which would lose the moderator's other edits — the box
	is moved in far enough to be visible and kept.
	"""
	width = max(flt(element.get("width")) or 0, 1)
	height = max(flt(element.get("height")) or 0, 1)
	width = min(width, canvas_width)
	height = min(height, canvas_height)

	x = min(max(flt(element.get("x")) or 0, 0), canvas_width - width)
	y = min(max(flt(element.get("y")) or 0, 0), canvas_height - height)

	return {**element, "x": x, "y": y, "width": width, "height": height}


def format_value(value, variable_type: str, date_format: str | None) -> str:
	"""Render one resolved value as the string that goes on the canvas."""
	if value in (None, ""):
		return ""
	if variable_type != "date":
		return str(value)
	return formatdate(value, date_format or DEFAULT_DATE_FORMAT)


def render_elements(reference_doctype: str, elements, values: dict) -> list[dict]:
	"""Resolve every element to the literal text or image it draws.

	The returned rows are what both the preview and the frozen snapshot carry —
	geometry plus a finished `value`, with no further lookups needed to draw
	them. That is what lets the public verification page render a certificate
	whose course was since renamed and still show what was awarded.
	"""
	types = {variable["key"]: variable["type"] for variable in VARIABLES[reference_doctype]}
	rendered = []
	for element in elements or []:
		element_type = element.get("element_type") or "Text"
		row = {
			"element_type": element_type,
			"variable": element.get("variable"),
			"x": flt(element.get("x")),
			"y": flt(element.get("y")),
			"width": flt(element.get("width")),
			"height": flt(element.get("height")),
			"rotation": flt(element.get("rotation")),
			"font_family": element.get("font_family") or "Inter",
			"font_size": flt(element.get("font_size")) or 32,
			"font_weight": element.get("font_weight") or "400",
			"italic": cint(element.get("italic")),
			"letter_spacing": flt(element.get("letter_spacing")),
			"color": element.get("color") or "#111827",
			"align": element.get("align") or "center",
			"opacity": flt(element.get("opacity")) if element.get("opacity") not in (None, "") else 1,
			"image": element.get("image"),
			"value": "",
		}
		if element_type == "Variable":
			key = element.get("variable") or ""
			row["value"] = format_value(values.get(key), types.get(key, "text"), element.get("date_format"))
		elif element_type == "Text":
			row["value"] = element.get("content") or ""
		rendered.append(row)
	return rendered


def organisation_name() -> str:
	"""Who the certificate is authorised by.

	`app_name` is the name the site already presents itself under everywhere
	else, so a site that has been rebranded says the new name here without
	anyone remembering to set a second field. "Learno" is the fallback, not the
	default.
	"""
	return frappe.db.get_single_value("Website Settings", "app_name") or "Learno"


def verification_url(code: str) -> str:
	"""The public address of one certificate.

	Built from `get_lms_path` rather than a literal "/lms": a site that has
	moved the app with the `lms_path` conf key would otherwise print an address
	on every certificate it issues that does not resolve on its own domain.
	"""
	from lms.hooks import get_lms_path

	return get_url(f"/{get_lms_path()}/verify/{code}")


def template_name_for(reference_doctype: str, reference_name: str) -> str | None:
	return frappe.db.get_value(
		"LMS Certificate Template",
		{"reference_doctype": reference_doctype, "reference_name": reference_name},
		"name",
	)


def get_template_doc(reference_doctype: str, reference_name: str):
	name = template_name_for(reference_doctype, reference_name)
	return frappe.get_doc("LMS Certificate Template", name) if name else None


def template_payload(doc) -> dict:
	"""A template as the designer edits it — plain data, no document wrapper."""
	return {
		"name": doc.name,
		"reference_doctype": doc.reference_doctype,
		"reference_name": doc.reference_name,
		"background_image": doc.background_image,
		"canvas_width": cint(doc.canvas_width) or DEFAULT_CANVAS_WIDTH,
		"canvas_height": cint(doc.canvas_height) or DEFAULT_CANVAS_HEIGHT,
		"issue_date_source": doc.issue_date_source,
		"custom_issue_date": doc.custom_issue_date,
		"is_complete": cint(doc.is_complete),
		"elements": [
			{
				"element_type": element.element_type,
				"variable": element.variable,
				"content": element.content,
				"image": element.image,
				"date_format": element.date_format,
				"x": flt(element.x),
				"y": flt(element.y),
				"width": flt(element.width),
				"height": flt(element.height),
				"rotation": flt(element.rotation),
				"font_family": element.font_family,
				"font_size": flt(element.font_size),
				"font_weight": element.font_weight,
				"italic": cint(element.italic),
				"letter_spacing": flt(element.letter_spacing),
				"color": element.color,
				"align": element.align,
				"opacity": flt(element.opacity),
			}
			for element in doc.elements
		],
	}


def blank_template(reference_doctype: str, reference_name: str) -> dict:
	return {
		"name": None,
		"reference_doctype": reference_doctype,
		"reference_name": reference_name,
		"background_image": None,
		"canvas_width": DEFAULT_CANVAS_WIDTH,
		"canvas_height": DEFAULT_CANVAS_HEIGHT,
		"issue_date_source": "Completion Date",
		"custom_issue_date": None,
		"is_complete": 0,
		"elements": [],
	}


def certificate_readiness(reference_doctype: str, reference_name: str) -> dict:
	"""Whether this course or program has a certificate that could be issued."""
	validate_reference_doctype(reference_doctype)
	doc = get_template_doc(reference_doctype, reference_name)
	template = template_payload(doc) if doc else blank_template(reference_doctype, reference_name)
	missing = missing_requirements(reference_doctype, template["background_image"], template["elements"])
	return {
		"exists": bool(doc),
		"is_complete": not missing,
		"missing": missing,
		"template": template,
	}


def throw_if_incomplete(missing: list[dict]) -> None:
	"""One wording for the handoff gate, wherever it is reached from.

	The gate has two entry points — a design arriving with a brand new course,
	and one already stored on an existing course — and they must refuse for the
	same reasons in the same words, or the moderator learns two different rules.
	"""
	if not missing:
		return
	frappe.throw(
		_("The certificate for this course is not finished yet: {0}.").format(
			"; ".join(item["message"] for item in missing)
		),
		title=_("Certificate incomplete"),
	)


def enforce_certificate_ready(reference_doctype: str, reference_name: str) -> None:
	"""Raise unless the stored certificate design is finished.

	This is the handoff gate. A course whose certificate is half designed cannot
	be pushed to instructors, because the certificate is the moderator's half of
	the contract and nobody chases it once the content work has started.
	"""
	throw_if_incomplete(certificate_readiness(reference_doctype, reference_name)["missing"])


def enforce_certificate_payload(reference_doctype: str, certificate) -> None:
	"""The same gate, for a design that has not been saved yet.

	The create wizard designs the certificate before the course row exists, so
	there is nothing to read back. Checking the payload keeps the refusal ahead
	of the insert — an invitation that is going to be refused must be refused
	before the instructor rows are written, not after.
	"""
	if isinstance(certificate, str):
		certificate = frappe.parse_json(certificate)
	certificate = certificate or {}
	throw_if_incomplete(
		missing_requirements(
			reference_doctype,
			certificate.get("background_image"),
			certificate.get("elements"),
		)
	)


def can_design_certificate(reference_doctype: str, reference_name: str) -> bool:
	"""Whether this user may design the certificate for one course or program.

	Ownership of the course, not of the doctype: the DocPerms grant every Course
	Creator write access to LMS Certificate Template as a whole, which is the
	right shape for a permission row and the wrong shape for the rule. Both the
	whitelisted endpoints and the doctype's `has_permission` hook read this, so
	the REST API cannot be used to walk around the designer.
	"""
	if reference_doctype not in REFERENCE_DOCTYPES:
		return False

	if "Moderator" in frappe.get_roles():
		return True

	if reference_doctype == "LMS Course":
		from lms.lms.utils import can_modify_course

		return bool(can_modify_course(reference_name))

	# A program has no instructor list to check against, so it stays with the
	# people who can create one in the first place.
	return "Course Creator" in frappe.get_roles()


def enforce_design_access(reference_doctype: str, reference_name: str) -> None:
	"""Only the people who own the course or the site may design its certificate."""
	validate_reference_doctype(reference_doctype)
	if not frappe.db.exists(reference_doctype, reference_name):
		frappe.throw(
			_("{0} {1} does not exist.").format(_(reference_doctype), reference_name),
			frappe.DoesNotExistError,
		)

	if not can_design_certificate(reference_doctype, reference_name):
		frappe.throw(_("You are not permitted to design this certificate."), frappe.PermissionError)


def sample_values(reference_doctype: str, reference_name: str) -> dict:
	"""Stand-in values for the designer, so a blank canvas is never laid out blind."""
	title = frappe.db.get_value(reference_doctype, reference_name, "title") or reference_name
	today = nowdate()
	shared = {
		"participant_name": frappe.db.get_value("User", frappe.session.user, "full_name")
		or _("Participant Name"),
		"issue_date": today,
		"certificate_id": "LRN-SAMPLE-0000",
		"verification_url": verification_url("LRN-SAMPLE-0000"),
		"organisation_name": organisation_name(),
	}
	if reference_doctype == "LMS Program":
		return {
			**shared,
			"program_name": title,
			"program_start_date": today,
			"program_end_date": today,
			"course_count": cint(frappe.db.get_value("LMS Program", reference_name, "course_count")),
		}

	instructor = frappe.db.get_value(
		"Course Instructor", {"parent": reference_name, "parenttype": "LMS Course"}, "instructor"
	)
	return {
		**shared,
		"course_name": title,
		"course_start_date": today,
		"course_end_date": today,
		"instructor_name": (instructor and frappe.db.get_value("User", instructor, "full_name")) or "",
		"batch_name": "",
		"expiry_date": None,
	}


@frappe.whitelist()
def get_certificate_variables(reference_doctype: str) -> dict:
	"""The variable catalogue, for a design being laid out before its course exists.

	The create wizard draws the certificate in the same breath as naming the
	course, so there is nothing to hang a template on yet. It still has to offer
	the right variables — and the right *mandatory* ones — which is all this
	returns.
	"""
	frappe.only_for(["Moderator", "Course Creator"])
	validate_reference_doctype(reference_doctype)
	return {
		"variables": variables_for(reference_doctype),
		"date_formats": list(DATE_FORMATS),
		"organisation_name": organisation_name(),
	}


@frappe.whitelist()
def get_certificate_designer(reference_doctype: str, reference_name: str) -> dict:
	"""Everything the designer screen needs in one fetch."""
	enforce_design_access(reference_doctype, reference_name)
	readiness = certificate_readiness(reference_doctype, reference_name)
	return {
		**readiness,
		"title": frappe.db.get_value(reference_doctype, reference_name, "title"),
		"variables": variables_for(reference_doctype),
		"date_formats": list(DATE_FORMATS),
		"sample_values": sample_values(reference_doctype, reference_name),
		"organisation_name": organisation_name(),
	}


@frappe.whitelist()
def save_certificate_template(reference_doctype: str, reference_name: str, template) -> dict:
	"""Create or rewrite the design, and report what is still missing."""
	enforce_design_access(reference_doctype, reference_name)
	write_template(reference_doctype, reference_name, template)
	return get_certificate_designer(reference_doctype, reference_name)


def write_template(reference_doctype: str, reference_name: str, template) -> str:
	"""Persist a design payload. Shared by the designer and the create wizard."""
	validate_reference_doctype(reference_doctype)
	if isinstance(template, str):
		template = frappe.parse_json(template)
	template = template or {}

	name = template_name_for(reference_doctype, reference_name)
	doc = (
		frappe.get_doc("LMS Certificate Template", name)
		if name
		else frappe.new_doc("LMS Certificate Template")
	)
	doc.reference_doctype = reference_doctype
	doc.reference_name = reference_name
	doc.background_image = template.get("background_image") or None
	doc.canvas_width = cint(template.get("canvas_width")) or DEFAULT_CANVAS_WIDTH
	doc.canvas_height = cint(template.get("canvas_height")) or DEFAULT_CANVAS_HEIGHT
	doc.issue_date_source = (
		"Custom Date" if template.get("issue_date_source") == "Custom Date" else "Completion Date"
	)
	doc.custom_issue_date = (
		template.get("custom_issue_date") if doc.issue_date_source == "Custom Date" else None
	)

	doc.elements = []
	for element in template.get("elements") or []:
		if (element.get("element_type") or "") not in ELEMENT_TYPES:
			continue
		doc.append("elements", clamp_element(element, doc.canvas_width, doc.canvas_height))

	doc.save(ignore_permissions=True)
	return doc.name


def resolve_issue_date(template, completion_date):
	"""The date printed as "issued on".

	A moderator either wants the date the learner actually finished, or one
	fixed date for a whole cohort — a convocation, say. Both are legitimate and
	the template says which.
	"""
	if template and template.get("issue_date_source") == "Custom Date" and template.get("custom_issue_date"):
		return getdate(template["custom_issue_date"])
	return getdate(completion_date or nowdate())


def course_certificate_values(certificate) -> dict:
	"""Resolve every course variable for one issued certificate."""
	course = certificate.course
	member = certificate.member

	enrollment = frappe.db.get_value(
		"LMS Enrollment",
		{"course": course, "member": member},
		["name", "creation", "modified", "progress", "enrollment_from_batch"],
		as_dict=True,
	)

	batch = certificate.batch_name or (enrollment and enrollment.enrollment_from_batch)
	batch_row = (
		frappe.db.get_value("LMS Batch", batch, ["title", "start_date", "end_date"], as_dict=True)
		if batch
		else None
	)

	# A cohort has real dates on it. A self-paced learner has none, so the only
	# honest answer is when they started and when they finished — anything else
	# would print a boundary that never existed.
	if batch_row and batch_row.start_date:
		start_date = batch_row.start_date
	else:
		start_date = getdate(enrollment.creation) if enrollment else None

	if batch_row and batch_row.end_date:
		end_date = batch_row.end_date
	else:
		end_date = getdate(enrollment.modified) if enrollment else None

	instructor = frappe.db.get_value(
		"Course Instructor", {"parent": course, "parenttype": "LMS Course"}, "instructor"
	)

	return {
		"participant_name": certificate.member_name or frappe.db.get_value("User", member, "full_name"),
		"course_name": frappe.db.get_value("LMS Course", course, "title"),
		"course_start_date": start_date,
		"course_end_date": end_date,
		"issue_date": certificate.issue_date,
		"expiry_date": certificate.expiry_date,
		"certificate_id": certificate.verification_code,
		"verification_url": verification_url(certificate.verification_code or ""),
		"organisation_name": organisation_name(),
		"instructor_name": (instructor and frappe.db.get_value("User", instructor, "full_name")) or "",
		"batch_name": batch_row.title if batch_row else "",
	}


def freeze_certificate(certificate) -> dict | None:
	"""Snapshot the design and the values onto the certificate, once.

	Everything the public page draws comes out of this snapshot. The template it
	came from can be redesigned the next day and this certificate still shows
	what was awarded, which is the entire point of a verification link.
	"""
	if not certificate.course:
		return None

	template = certificate_readiness("LMS Course", certificate.course)["template"]
	if not template["background_image"]:
		return None

	values = course_certificate_values(certificate)
	values["issue_date"] = resolve_issue_date(template, certificate.issue_date)

	return {
		"reference_doctype": "LMS Course",
		"reference_name": certificate.course,
		"background_image": template["background_image"],
		"canvas_width": template["canvas_width"],
		"canvas_height": template["canvas_height"],
		"issue_date": str(values["issue_date"]),
		"organisation_name": values["organisation_name"],
		"participant_name": values["participant_name"],
		"title": values["course_name"],
		"elements": render_elements("LMS Course", template["elements"], values),
	}


@frappe.whitelist()
def get_certificates(member: str | None = None, course: str | None = None) -> list:
	"""One person's certificates: the profile tab, and the course certificate page.

	Exists because `member` now sits at permlevel 1. Both pages used to reach
	`LMS Certificate` through the generic list API and filter it by `member`,
	and Frappe refuses a filter on a field the caller's roles cannot read -- so
	the field guard that stops a student enumerating every holder's email would
	also have stopped a student finding their own certificate.

	The scoping is deliberately the same rule the list API applied, read from
	the same place the doctype's own guards read it: staff see every row, and
	everyone else sees published ones. Nothing here returns `member` or
	`verification_code`; the caller already knows whose profile they asked for,
	and the code is what the guard exists to protect.
	"""
	from lms.lms.doctype.lms_certificate.lms_certificate import is_staff

	if frappe.session.user == "Guest":
		frappe.throw(_("Please sign in to continue."), frappe.AuthenticationError)

	filters = {"member": member or frappe.session.user}
	if course:
		filters["course"] = course
	if not is_staff():
		filters["published"] = 1

	return frappe.get_all(
		"LMS Certificate",
		filters=filters,
		fields=["name", "course", "course_title", "batch_title", "issue_date", "template"],
		order_by="issue_date desc",
		limit_page_length=0,
	)


# nosemgrep: guest-whitelisted-method
# Reviewed, and guest access is the feature rather than an oversight: a
# certificate whose proof only works for people who already have an account here
# proves nothing to the employer it is shown to. The rule asks for a human
# review, so this records one.
#
# What an anonymous caller can reach: one certificate, by a 12-character
# unguessable code, returning only the frozen snapshot — the participant's name
# and the course title as printed on the artwork, the dates, and the issuing
# organisation. Never the holder's email, never the certificate's document name,
# never anything about the course beyond its title, and no way to enumerate.
# `snapshot`, `member` and `verification_code` are all permlevel 1 so the same
# data cannot be reached in bulk through /api/resource by a signed-in student.
#
# Also listed in lms/tests/guest_endpoints.txt, which freezes the guest surface
# so a NEW allow_guest endpoint cannot arrive unreviewed.
@frappe.whitelist(allow_guest=True)
def get_public_certificate(code: str) -> dict:
	"""The digital copy anyone with the link can check.

	Guest-readable on purpose: a certificate whose link only works for people
	who already have an account on this site proves nothing to an employer. Only
	the frozen snapshot is returned — never the member's email, never the
	certificate's document name, never anything about the course beyond its
	title.
	"""
	code = (code or "").strip().upper()
	if not code:
		frappe.throw(_("No certificate code was given."), frappe.DoesNotExistError)

	row = frappe.db.get_value(
		"LMS Certificate",
		{"verification_code": code},
		["name", "member_name", "course", "issue_date", "expiry_date", "snapshot"],
		as_dict=True,
	)
	if not row:
		frappe.throw(
			_("No certificate has been issued with the code {0}.").format(code),
			frappe.DoesNotExistError,
		)

	snapshot = frappe.parse_json(row.snapshot) if row.snapshot else None
	expired = bool(row.expiry_date and getdate(row.expiry_date) < getdate(nowdate()))

	return {
		"code": code,
		"participant_name": (snapshot or {}).get("participant_name") or row.member_name,
		"title": (snapshot or {}).get("title") or frappe.db.get_value("LMS Course", row.course, "title"),
		"issue_date": (snapshot or {}).get("issue_date") or str(row.issue_date or ""),
		"expiry_date": str(row.expiry_date) if row.expiry_date else None,
		"is_expired": expired,
		"organisation_name": (snapshot or {}).get("organisation_name") or organisation_name(),
		"verification_url": verification_url(code),
		"canvas": snapshot,
	}
