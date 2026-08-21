# Copyright (c) 2026, FOSS United and Contributors
# See license.txt

"""A published certificate is public; the holder's email and code are not.

`LMS Certificate` deliberately lets any signed-in user read published rows --
that is what makes a certificate showable. What it must not do is hand over
`member` (the holder's email address) and `verification_code` with them, which
it did at permlevel 0 while LMS Student held read, export, report, email, print
and share. Five bulk paths, one field guard: permlevel is put on the fields
rather than taken off the grants, because dropping `export` alone would leave
`report` and `email` open.
"""

import frappe

from lms.lms.certificates import get_certificates
from lms.lms.test_helpers import BaseTestUtils

# `snapshot` belongs here and it is not obvious why: a permlevel guards a field,
# not a value. `freeze_certificate` resolves the design at issue time, and
# `course_certificate_values` puts `certificate_id` and `verification_url` into
# the values it renders -- so on any certificate whose design places the
# "Certificate ID" or "Verification link" element, and placing the link is the
# normal case, the code sits in the frozen JSON as plain text. Locking
# `verification_code` while leaving `snapshot` at permlevel 0 left the same bulk
# enumeration reachable one field over. Found by learno-management-system-b8,
# whose fix put the permlevel on the field; the positive control below is what
# stops these assertions from passing on an empty snapshot.
# `evaluator` is on the list because it is an email address in disguise:
# `Course Evaluator` is `autoname: field:evaluator` over a Link to User, so the
# docname stored here IS the evaluator's address. Same leak class as `member`,
# one doctype further out.
#
# `evaluator_name` is here and `member_name` is not, and the asymmetry is the
# point. The holder's name is genuinely public: `get_public_certificate` returns
# it to any guest and the artwork prints it, so guarding it would protect
# something a stranger can already read from the link. Nothing about the
# evaluator reaches that page -- the payload carries participant name, title,
# dates, organisation and the snapshot, and the design catalogue offers
# `instructor_name`, never the evaluator. A student meets their own evaluator's
# name through the booking mail in `lms_certificate_request.py`, which is
# per-relationship disclosure; at permlevel 0 here it was instead a staff roster
# any self-signup account could assemble in one `get_list`.
#
# Caught by learno-management-system-b8, who pointed out that "the name is public
# already" is load-bearing for `member_name` and simply untrue of this one.
GUARDED_FIELDS = ("member", "verification_code", "snapshot", "evaluator", "evaluator_name")

# Fixed rather than randomised, and never torn down. Frappe throttles `User`
# creation site-wide (60/hour in core), so a suite that mints and deletes an
# account per test spends that budget on behalf of every other suite on the
# site. Three stable accounts cost one creation each, once.
HOLDER = "cert-holder@fixtures.test"
SNOOPER = "cert-snooper@fixtures.test"
MODERATOR = "cert-moderator@fixtures.test"


class TestCertificateFieldExposure(BaseTestUtils):
	def setUp(self):
		super().setUp()
		# `_create_user_with_exact_roles`, not `_create_user`: a reused account
		# keeps whatever roles it was born with, and "a student cannot read this
		# field" must not pass or fail on the history of the site.
		self.holder = self._create_user_with_exact_roles(HOLDER, "Hana", "Holder", ["LMS Student"]).name
		self.snooper = self._create_user_with_exact_roles(SNOOPER, "Sam", "Snooper", ["LMS Student"]).name
		self.moderator = self._create_user_with_exact_roles(
			MODERATOR, "Mia", "Moderator", ["Moderator"]
		).name
		# Accounts outlive the test; only the certificate under test is
		# registered for cleanup, which is what `published` mutations rely on.
		self.cleanup_items = [i for i in self.cleanup_items if i[0] != "User"]

		# `Course Evaluator` is named by its user, so this is the moderator's email.
		self.evaluator = self._create_evaluator(self.moderator).name

		self.course = self._create_course(title="Cert Field Guard Course", instructor=self.moderator)
		# The doctype refuses to certify someone who was never enrolled.
		self._create_enrollment(self.holder, self.course.name)
		self._create_enrollment(self.snooper, self.course.name)
		self.certificate = self._create_certificate(self.course.name, self.holder)

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	# -- the fields themselves -------------------------------------------------

	def test_the_guarded_fields_sit_above_permlevel_zero(self):
		meta = frappe.get_meta("LMS Certificate")
		for fieldname in GUARDED_FIELDS:
			self.assertEqual(meta.get_field(fieldname).permlevel, 1, fieldname)

	def test_a_student_asking_for_the_guarded_fields_is_not_given_them(self):
		# Frappe drops a selected field the caller's roles cannot read rather
		# than refusing the query, so the row still arrives -- just without the
		# email and the code on it. Asserted as absence rather than as an
		# exception because absence is the property that matters and the one
		# that would actually regress.
		frappe.set_user(self.snooper)
		rows = frappe.get_list(
			"LMS Certificate", fields=["name", *GUARDED_FIELDS], limit_page_length=0
		)
		self.assertTrue(rows, "the published row should still be readable")
		for row in rows:
			for fieldname in GUARDED_FIELDS:
				self.assertNotIn(fieldname, row)

	def test_a_student_cannot_filter_or_sort_by_the_guarded_fields(self):
		# The other half of enumeration. Dropping the field from the result is
		# not enough on its own: filtering confirms an address one guess at a
		# time, and ordering by it leaks the order. Both are refused outright.
		frappe.set_user(self.snooper)
		for fieldname in GUARDED_FIELDS:
			with self.assertRaises(frappe.PermissionError, msg=fieldname):
				frappe.get_list("LMS Certificate", filters={fieldname: "x"}, fields=["name"])
			with self.assertRaises(frappe.PermissionError, msg=fieldname):
				frappe.get_list("LMS Certificate", fields=["name"], order_by=f"{fieldname} asc")

	def test_a_student_selecting_everything_gets_none_of_them(self):
		frappe.set_user(self.snooper)
		rows = frappe.get_list("LMS Certificate", fields=["*"], limit_page_length=0)
		self.assertTrue(rows, "the published row should still be readable")
		for row in rows:
			for fieldname in GUARDED_FIELDS:
				self.assertNotIn(fieldname, row)

	def test_the_holder_is_no_more_privileged_than_any_other_student(self):
		# Frappe resolves permlevel by role alone, so owning the row does not
		# reopen the field. Recorded so the next reader does not assume it does,
		# and so `get_certificates` keeps being the way a learner finds their
		# own certificate.
		frappe.set_user(self.holder)
		rows = frappe.get_list(
			"LMS Certificate",
			fields=["name", "member"],
			limit_page_length=0,
		)
		self.assertTrue(rows)
		self.assertNotIn("member", rows[0])

	def test_a_moderator_still_reads_the_guarded_fields(self):
		frappe.set_user(self.moderator)
		rows = frappe.get_list(
			"LMS Certificate",
			filters={"name": self.certificate.name},
			fields=["name", *GUARDED_FIELDS],
		)
		self.assertEqual(rows[0].member, self.holder)
		self.assertTrue(rows[0].verification_code)

	def test_a_moderator_can_still_set_the_member_on_a_new_certificate(self):
		# Bulk certificate generation inserts through the permission-checked
		# client API, so permlevel-1 *write* has to survive too or every
		# generated certificate would come out with an empty holder.
		frappe.set_user(self.moderator)
		doc = frappe.get_doc(
			{
				"doctype": "LMS Certificate",
				"member": self.snooper,
				"evaluator": self.evaluator,
				"course": self.course.name,
				"issue_date": frappe.utils.nowdate(),
				"published": 1,
			}
		).insert()
		self.cleanup_items.append(("LMS Certificate", doc.name))
		stored = frappe.db.get_value(
			"LMS Certificate", doc.name, ["member", "evaluator", "evaluator_name"], as_dict=True
		)
		self.assertEqual(stored.member, self.snooper)
		self.assertEqual(stored.evaluator, self.evaluator)
		# Control for the guard below: `evaluator_name` is `fetch_from` and a
		# permlevel must not stop it populating, or "a student cannot read the
		# evaluator's name" would hold because nobody can write it either.
		self.assertTrue(stored.evaluator_name, "fetch_from should still populate")

	# -- the positive control -------------------------------------------------

	def _certificate_carrying_its_own_code(self):
		"""A certificate whose frozen design actually contains the code.

		Every `snapshot` assertion above is worthless without this. A certificate
		issued against a course with no finished design freezes nothing, so its
		snapshot is the empty string and "the code is not in the snapshot" holds
		for the wrong reason -- which is exactly what the pre-existing rows on
		the dev site looked like while the leak was live.
		"""
		from lms.lms.certificates import mandatory_keys

		course = self._create_course(title="Cert Snapshot Probe Course", instructor=self.moderator)
		frappe.db.set_value("LMS Course", course.name, "enable_certification", 1)

		elements = [
			{"element_type": "Variable", "variable": key, "left": 10, "top": 10 * i, "width": 200, "height": 30}
			for i, key in enumerate(mandatory_keys("LMS Course"))
		]
		# The element that carries the leak. Placing it is the ordinary thing to
		# do -- it is why the variable is offered at all.
		elements.append(
			{"element_type": "Variable", "variable": "verification_url", "left": 10, "top": 400, "width": 400, "height": 30}
		)

		template = frappe.new_doc("LMS Certificate Template")
		template.update(
			{
				"reference_doctype": "LMS Course",
				"reference_name": course.name,
				"title": "Snapshot Probe Template",
				"background_image": "/files/probe-bg.png",
				"canvas_width": 1754,
				"canvas_height": 1240,
				"elements": elements,
			}
		)
		template.insert()
		self.cleanup_items.append(("LMS Certificate Template", template.name))

		enrollment = self._create_enrollment(self.holder, course.name)
		frappe.db.set_value("LMS Enrollment", enrollment.name, "progress", 100)

		certificate = self._create_certificate(course.name, self.holder)
		return certificate

	def test_the_frozen_snapshot_really_does_carry_the_code(self):
		# The control itself. If this ever fails, the two tests below stopped
		# proving anything and started passing on an empty string.
		certificate = self._certificate_carrying_its_own_code()
		self.assertTrue(certificate.snapshot, "the design should have frozen")
		self.assertIn(certificate.verification_code, certificate.snapshot)

	def test_a_student_cannot_read_the_code_out_of_the_snapshot(self):
		certificate = self._certificate_carrying_its_own_code()
		code = certificate.verification_code

		frappe.set_user(self.snooper)
		rows = frappe.get_list("LMS Certificate", fields=["*"], limit_page_length=0)
		self.assertTrue(rows, "published rows should still be readable")
		self.assertNotIn("snapshot", rows[0])
		for row in rows:
			self.assertNotIn(code, str(row))

	def test_the_public_page_still_draws_the_frozen_design(self):
		# `snapshot` is what the verification page renders. It reaches it through
		# `frappe.db.get_value`, which bypasses permlevel -- so guarding the field
		# must not blank the page it exists to draw.
		from lms.lms.certificates import get_public_certificate

		certificate = self._certificate_carrying_its_own_code()
		frappe.set_user("Guest")
		payload = get_public_certificate(certificate.verification_code)
		self.assertTrue(payload["canvas"], "the public page lost its design")
		self.assertTrue(payload["canvas"]["elements"])

	def _certificate_naming_its_evaluator(self):
		"""A certificate that actually has an evaluator on it.

		Same trap as the snapshot: `evaluator` is null on most rows, so
		"a student cannot read the evaluator" holds for the wrong reason unless
		one is set. Every certificate on the dev site had it null, which is why
		the first probe came back clean while the field was wide open.
		"""
		frappe.db.set_value("LMS Certificate", self.certificate.name, "evaluator", self.evaluator)
		return frappe.db.get_value("LMS Certificate", self.certificate.name, "evaluator")

	def test_the_certificate_really_does_name_an_evaluator(self):
		# The control. If this fails, the test below stopped proving anything.
		self.assertEqual(self._certificate_naming_its_evaluator(), self.evaluator)
		self.assertIn("@", self.evaluator, "the evaluator docname should be an address")

	def test_a_student_cannot_read_the_evaluator_email(self):
		email = self._certificate_naming_its_evaluator()

		frappe.set_user(self.snooper)
		rows = frappe.get_list("LMS Certificate", fields=["*"], limit_page_length=0)
		self.assertTrue(rows, "published rows should still be readable")
		self.assertNotIn("evaluator", rows[0])
		for row in rows:
			self.assertNotIn(email, str(row))

	def test_the_holders_name_stays_public(self):
		# `member_name` is deliberately NOT guarded: the public verification page
		# returns it to any guest, so hiding it from a signed-in student would
		# protect nothing while breaking the certificate lists that render it.
		frappe.set_user(self.snooper)
		rows = frappe.get_list("LMS Certificate", fields=["name", "member_name"], limit_page_length=0)
		self.assertIn("member_name", rows[0])

	def test_a_moderator_still_reads_the_evaluator(self):
		email = self._certificate_naming_its_evaluator()
		frappe.set_user(self.moderator)
		rows = frappe.get_list(
			"LMS Certificate", filters={"name": self.certificate.name}, fields=["name", "evaluator"]
		)
		self.assertEqual(rows[0].evaluator, email)

	# -- the replacement endpoint ---------------------------------------------

	def test_the_endpoint_returns_a_persons_certificates_without_their_email(self):
		frappe.set_user(self.snooper)
		rows = get_certificates(member=self.holder)
		self.assertEqual([r.name for r in rows], [self.certificate.name])
		for fieldname in GUARDED_FIELDS:
			self.assertNotIn(fieldname, rows[0])

	def test_the_endpoint_defaults_to_the_caller(self):
		frappe.set_user(self.holder)
		self.assertEqual([r.name for r in get_certificates()], [self.certificate.name])

	def test_the_endpoint_narrows_to_one_course(self):
		frappe.set_user(self.holder)
		self.assertEqual(get_certificates(course="no-such-course"), [])

	def test_the_endpoint_hides_an_unpublished_certificate_from_a_student(self):
		frappe.db.set_value("LMS Certificate", self.certificate.name, "published", 0)
		frappe.set_user(self.snooper)
		self.assertEqual(get_certificates(member=self.holder), [])

	def test_the_endpoint_shows_an_unpublished_certificate_to_staff(self):
		frappe.db.set_value("LMS Certificate", self.certificate.name, "published", 0)
		frappe.set_user(self.moderator)
		self.assertEqual([r.name for r in get_certificates(member=self.holder)], [self.certificate.name])

	def test_the_endpoint_refuses_a_guest(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.AuthenticationError):
			get_certificates(member=self.holder)

	def test_the_public_verification_page_still_works(self):
		# The code is unreadable through the list API and still resolvable by
		# anyone holding it -- which is the whole point of a verification code.
		from lms.lms.certificates import get_public_certificate

		code = frappe.db.get_value("LMS Certificate", self.certificate.name, "verification_code")
		frappe.set_user("Guest")
		self.assertEqual(get_public_certificate(code)["code"], code)
