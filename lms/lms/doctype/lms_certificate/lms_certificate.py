# Copyright (c) 2021, FOSS United and contributors
# For license information, please see license.txt

import json

import frappe
from frappe import _
from frappe.email.doctype.email_template.email_template import get_email_template
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import nowdate
from frappe.utils.telemetry import capture

from lms.lms.certificates import (
	certificate_readiness,
	freeze_certificate,
	template_name_for,
	verification_url,
)

# Long enough that codes cannot be guessed by walking the space, short enough to
# read off a printed certificate and type into the verification page by hand.
VERIFICATION_CODE_LENGTH = 12
VERIFICATION_CODE_PREFIX = "LRN"


def make_verification_code() -> str:
	"""A public, unguessable handle for one certificate.

	The document name is a hash already, but it is also the key the whole desk
	uses; printing it on a certificate would publish an internal identifier. This
	is a separate value that exists only to be shown.
	"""
	raw = frappe.generate_hash(length=VERIFICATION_CODE_LENGTH).upper()
	return f"{VERIFICATION_CODE_PREFIX}-{raw[:4]}-{raw[4:8]}-{raw[8:12]}"


class LMSCertificate(Document):
	def validate(self):
		self.validate_criteria()
		self.validate_duplicate_certificate()

	def autoname(self):
		self.name = make_autoname("hash", self.doctype)

	def before_save(self):
		"""Mint the code and freeze the design, once, on the way in.

		Both run only for a new certificate. Re-running them on an edit would
		change the code an employer already has a link to, and would redraw an
		awarded certificate from whatever the template says today.
		"""
		if not self.is_new():
			return
		if not self.verification_code:
			self.verification_code = make_verification_code()
		self.freeze_design()

	def freeze_design(self):
		if self.snapshot or not self.course:
			return
		snapshot = freeze_certificate(self)
		if not snapshot:
			return
		self.certificate_template = template_name_for("LMS Course", self.course)
		self.snapshot = json.dumps(snapshot, default=str)

	def after_insert(self):
		capture("certificate_issued", "lms")
		self.send_certification_email()

	def send_certification_email(self):
		outgoing_email_account = frappe.get_cached_value(
			"Email Account", {"default_outgoing": 1, "enable_outgoing": 1}, "name"
		)
		if outgoing_email_account or frappe.conf.get("mail_login"):
			self.send_mail()

	def send_mail(self):
		subject = _("Congratulations on getting certified!")
		template = "certification"
		custom_template = frappe.db.get_single_value("LMS Settings", "certification_template")

		args = {
			"member_name": self.member_name,
			"course_name": self.course,
			"course_title": frappe.db.get_value("LMS Course", self.course, "title"),
			"name": self.name,
			"template": self.template,
			# The public page, when there is one. It needs no sign-in and it is
			# the thing worth forwarding, so it is the link the mail leads with.
			"verification_url": verification_url(self.verification_code)
			if self.verification_code
			else None,
		}

		if custom_template:
			email_template = get_email_template(custom_template, args)
			subject = email_template.get("subject")
			content = email_template.get("message")
		frappe.sendmail(
			recipients=self.member,
			subject=subject,
			template=template if not custom_template else None,
			content=content if custom_template else None,
			args=args,
			header=[subject, "green"],
		)

	def validate_criteria(self):
		self.validate_role_of_owner()
		if self.batch_name:
			self.validate_batch_enrollment()
		elif self.course:
			self.validate_course_enrollment()

	def validate_role_of_owner(self):
		roles = frappe.get_roles()
		is_admin = any(role in roles for role in ["Moderator", "Course Creator", "Batch Evaluator"])
		if not self.course and not self.batch_name and not is_admin:
			frappe.throw(_("Course or Batch is required to issue a certificate."))

	def validate_batch_enrollment(self):
		if self.batch_name:
			is_enrolled = frappe.db.exists(
				"LMS Batch Enrollment", {"batch": self.batch_name, "member": self.member}
			)
			if not is_enrolled:
				frappe.throw(_("Certification cannot be issued as the member is not enrolled in this batch."))

	def validate_course_enrollment(self):
		if self.course:
			is_enrolled = frappe.db.exists("LMS Enrollment", {"course": self.course, "member": self.member})
			if not is_enrolled:
				frappe.throw(
					_("Certification cannot be issued as the member is not enrolled in this course.")
				)

			completion_certificate = frappe.db.get_value("LMS Course", self.course, "enable_certification")
			if completion_certificate:
				progress = frappe.db.get_value(
					"LMS Enrollment", {"course": self.course, "member": self.member}, "progress"
				)
				if progress < 100:
					frappe.throw(
						_("Certification cannot be issued as the member has not completed the course.")
					)

	def validate_duplicate_certificate(self):
		self.validate_course_duplicates()
		self.validate_batch_duplicates()

	def validate_course_duplicates(self):
		if self.course:
			course_duplicates = frappe.get_all(
				"LMS Certificate",
				filters={
					"member": self.member,
					"name": ["!=", self.name],
					"course": self.course,
				},
				fields=["name", "course", "course_title"],
			)
			if len(course_duplicates):
				full_name = frappe.db.get_value("User", self.member, "full_name")
				frappe.throw(
					_("{0} is already certified for the course {1}").format(
						full_name, course_duplicates[0].course_title
					)
				)

	def validate_batch_duplicates(self):
		if self.batch_name:
			batch_duplicates = frappe.get_all(
				"LMS Certificate",
				filters={
					"member": self.member,
					"name": ["!=", self.name],
					"batch_name": self.batch_name,
				},
				fields=["name", "batch_name", "batch_title"],
			)
			if len(batch_duplicates):
				full_name = frappe.db.get_value("User", self.member, "full_name")
				frappe.throw(
					_("{0} is already certified for the batch {1}").format(
						full_name, batch_duplicates[0].batch_title
					)
				)

	def on_update(self):
		frappe.share.add_docshare(
			self.doctype,
			self.name,
			self.member,
			write=1,
			share=1,
			flags={"ignore_share_permission": True},
		)


def has_website_permission(doc, ptype, user, verbose=False):
	if ptype in ["read", "print"] and doc.published:
		return True
	if doc.member == user and ptype == "create":
		return True
	return False


def is_certified(course):
	certificate = frappe.get_all("LMS Certificate", {"member": frappe.session.user, "course": course})
	if len(certificate):
		return certificate[0].name
	return


@frappe.whitelist()
def create_certificate(course: str):
	certificate = is_certified(course)
	if certificate:
		return frappe.db.get_value(
			"LMS Certificate",
			certificate,
			["name", "course", "template", "verification_code"],
			as_dict=True,
		)

	validate_certification_eligibility(course)

	# A course with a finished design is drawn from it, and the print format is
	# left blank: the two are alternative ways of putting the same certificate on
	# paper, and carrying both would leave it ambiguous which one was awarded.
	designed = certificate_readiness("LMS Course", course)["is_complete"]

	certificate = frappe.get_doc(
		{
			"doctype": "LMS Certificate",
			"member": frappe.session.user,
			"course": course,
			"issue_date": nowdate(),
			"template": None if designed else get_default_certificate_template(),
		}
	)
	certificate.save(ignore_permissions=True)
	return certificate


def get_default_certificate_template():
	default_certificate_template = frappe.db.get_value(
		"Property Setter",
		{
			"doc_type": "LMS Certificate",
			"property": "default_print_format",
		},
		"value",
	)
	if not default_certificate_template:
		default_certificate_template = frappe.db.get_value(
			"Print Format",
			{
				"doc_type": "LMS Certificate",
			},
		)

	return default_certificate_template


def validate_certification_eligibility(course):
	if not frappe.db.exists("LMS Enrollment", {"course": course, "member": frappe.session.user}):
		frappe.throw(_("You are not enrolled in this course."))

	if not frappe.db.get_value("LMS Course", course, "enable_certification"):
		frappe.throw(_("Certification is not enabled for this course."))

	progress = frappe.db.get_value(
		"LMS Enrollment", {"course": course, "member": frappe.session.user}, "progress"
	)
	if progress < 100:
		frappe.throw(_("You have not completed the course yet."))


# The roles that administer certificates rather than hold them. Named once so
# the row guard, the list guard and `lms.lms.certificates.get_certificates`
# cannot drift apart: three copies of a role list is how one of them ends up
# one role short and becomes either a leak or a locked door.
STAFF_ROLES = ("Moderator", "Course Creator", "Batch Evaluator")


def is_staff(user=None) -> bool:
	return bool(set(frappe.get_roles(user or frappe.session.user)) & set(STAFF_ROLES))


def has_permission(doc, ptype="read", user=None):
	user = user or frappe.session.user
	if is_staff(user):
		return True
	if doc.owner == user:
		return True
	if ptype not in ("read", "select", "print"):
		return False
	return doc.published


def get_permission_query_conditions(user):
	user = user or frappe.session.user
	if is_staff(user):
		return None
	return """(`tabLMS Certificate`.published = 1)"""
