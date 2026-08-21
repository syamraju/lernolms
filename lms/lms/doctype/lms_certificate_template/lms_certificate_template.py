# Copyright (c) 2026, FOSS United and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

from lms.lms.certificates import (
	ELEMENT_TYPES,
	REFERENCE_DOCTYPES,
	clamp_element,
	mandatory_keys,
	missing_requirements,
	variables_for,
)


class LMSCertificateTemplate(Document):
	def validate(self):
		self.validate_reference()
		self.validate_one_template_per_reference()
		self.validate_canvas()
		self.validate_elements()
		self.set_title()
		self.set_completion()

	def validate_reference(self):
		if self.reference_doctype not in REFERENCE_DOCTYPES:
			frappe.throw(_("{0} does not have certificates.").format(self.reference_doctype))
		if not frappe.db.exists(self.reference_doctype, self.reference_name):
			frappe.throw(_("{0} {1} does not exist.").format(_(self.reference_doctype), self.reference_name))

	def validate_one_template_per_reference(self):
		"""A course or program owns exactly one certificate design.

		Frappe cannot express a composite unique key across two fields, so the
		rule lives here. Without it a second template can be inserted through
		the REST API and the readiness gate would then read whichever row the
		database happened to return first.
		"""
		duplicate = frappe.db.exists(
			"LMS Certificate Template",
			{
				"reference_doctype": self.reference_doctype,
				"reference_name": self.reference_name,
				"name": ("!=", self.name),
			},
		)
		if duplicate:
			frappe.throw(
				_("{0} already has a certificate design.").format(self.reference_name),
				frappe.DuplicateEntryError,
			)

	def validate_canvas(self):
		"""A canvas with no area would divide by zero everywhere it is drawn."""
		if cint(self.canvas_width) < 1 or cint(self.canvas_height) < 1:
			frappe.throw(_("The certificate background must have a width and a height."))

	def validate_elements(self):
		known = {entry["key"] for entry in variables_for(self.reference_doctype)}
		placed = set()
		for element in self.elements:
			if element.element_type not in ELEMENT_TYPES:
				frappe.throw(_("{0} is not a kind of certificate element.").format(element.element_type))

			if element.element_type == "Variable":
				if not element.variable:
					frappe.throw(_("Every variable placed on the certificate must name a variable."))
				# A key that is not in the catalogue would store cleanly and then
				# render as an empty space on every certificate issued from it.
				if element.variable not in known:
					frappe.throw(
						_("{0} is not a variable a {1} certificate can carry.").format(
							element.variable, _(self.reference_doctype)
						)
					)
				# Two boxes printing the same name is a duplicated field, not a
				# design choice, and the checklist would still read as complete.
				if element.variable in placed:
					frappe.throw(
						_("{0} is placed on the certificate more than once.").format(element.variable)
					)
				placed.add(element.variable)

			clamped = clamp_element(element.as_dict(), cint(self.canvas_width), cint(self.canvas_height))
			element.x = clamped["x"]
			element.y = clamped["y"]
			element.width = clamped["width"]
			element.height = clamped["height"]

	def set_title(self):
		self.title = frappe.db.get_value(self.reference_doctype, self.reference_name, "title")

	def set_completion(self):
		"""`is_complete` is derived, never typed.

		The designer's checklist and the instructor-handoff gate both call
		`missing_requirements`; this field only caches its answer so a list view
		can be filtered on it. Recomputing on every save is what keeps the cache
		from going stale when a mandatory variable is dragged off the canvas.
		"""
		missing = missing_requirements(
			self.reference_doctype,
			self.background_image,
			[element.as_dict() for element in self.elements],
		)
		self.is_complete = 0 if missing else 1

	def mandatory_variables(self) -> list[str]:
		return mandatory_keys(self.reference_doctype)


def has_permission(doc, ptype, user):
	"""Gate the generic REST API on the same rule the designer uses.

	The whitelisted endpoints call `enforce_design_access` before they touch a
	template, but `/api/resource/LMS Certificate Template` is a separate door
	into the same rows — and the DocPerms behind it grant every Course Creator
	write access to the doctype, not to a particular course's row. Without this,
	one course creator could redesign another course's certificate.

	Reads are left open: a template is the artwork on a certificate anyone can
	already see on its public verification page.
	"""
	if ptype in ("read", "report", "export", "select"):
		return True

	if not doc or not doc.reference_doctype or not doc.reference_name:
		return True

	from lms.lms.certificates import can_design_certificate

	return can_design_certificate(doc.reference_doctype, doc.reference_name)
