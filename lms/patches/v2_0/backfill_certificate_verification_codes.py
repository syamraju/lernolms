# Copyright (c) 2026, FOSS United and contributors
# For license information, please see license.txt

"""Give every certificate issued before verification links existed a code.

Without this, an old certificate's public page 404s while a new one resolves,
and the difference is invisible to the learner holding it. The snapshot stays
empty on purpose: these certificates were never drawn from a designed template,
so there is no frozen design to invent for them, and the verification page falls
back to the plain record it does have.
"""

import frappe

from lms.lms.doctype.lms_certificate.lms_certificate import make_verification_code


def execute():
	frappe.reload_doc("lms", "doctype", "lms_certificate_element")
	frappe.reload_doc("lms", "doctype", "lms_certificate_template")
	frappe.reload_doc("lms", "doctype", "lms_certificate")

	names = frappe.get_all(
		"LMS Certificate",
		filters={"verification_code": ("in", ("", None))},
		pluck="name",
	)
	for name in names:
		frappe.db.set_value(
			"LMS Certificate",
			name,
			"verification_code",
			make_verification_code(),
			update_modified=False,
		)
