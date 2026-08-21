import frappe

from lms.lms.api import MAX_PERMISSION_BATCH, get_doc_permissions_many
from lms.lms.test_helpers import BaseTestUtils


class TestDocPermissionsMany(BaseTestUtils):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		hash = frappe.generate_hash(length=6)
		self.instructor = self._create_user(
			f"permmany-instr-{hash}@example.com", "Perm", "Many", ["Course Creator", "Moderator"]
		)
		self.course = self._create_course(title=f"Perm Many Course {hash}", instructor=self.instructor.email)

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def test_returns_a_map_keyed_by_name(self):
		result = get_doc_permissions_many("LMS Course", [self.course.name])
		self.assertEqual(sorted(result), [self.course.name])
		self.assertEqual(result[self.course.name]["read"], 1)

	def test_accepts_the_json_string_the_http_layer_delivers(self):
		"""Every argument arrives as a string over HTTP, so a list that only works
		when called in-process is a test that passes and an endpoint that 500s."""
		result = get_doc_permissions_many("LMS Course", frappe.as_json([self.course.name]))
		self.assertEqual(result[self.course.name]["read"], 1)

	def test_rejects_a_non_string_doctype(self):
		# require_type_annotated_api_methods is on, so the framework rejects this
		# on the annotation before the body runs. FrappeTypeError is a TypeError,
		# not a ValidationError.
		with self.assertRaises(frappe.exceptions.FrappeTypeError):
			get_doc_permissions_many({"evil": 1}, ["x"])

	def test_rejects_an_unknown_doctype(self):
		with self.assertRaises(frappe.ValidationError):
			get_doc_permissions_many("No Such Doctype", ["x"])

	def test_caps_the_batch_size(self):
		names = [f"c{i}" for i in range(MAX_PERMISSION_BATCH + 1)]
		with self.assertRaises(frappe.ValidationError):
			get_doc_permissions_many("LMS Course", names)

	def test_a_missing_document_reports_empty_not_an_error(self):
		result = get_doc_permissions_many("LMS Course", [self.course.name, "does-not-exist-xyz"])
		self.assertEqual(result["does-not-exist-xyz"], {})
		self.assertEqual(result[self.course.name]["read"], 1)

	def test_an_unreadable_document_is_indistinguishable_from_a_missing_one(self):
		"""Otherwise the endpoint enumerates inaccessible records: submit guessed
		names, and a permission map back means the row is real while {} means it
		is not. LMS Program.has_permission hides an unpublished program from a
		student who is not enrolled, so it is a real row this caller must not be
		able to confirm."""
		program = frappe.get_doc(
			{
				"doctype": "LMS Program",
				"title": f"Perm Many Program {frappe.generate_hash(length=6)}",
				"published": 0,
			}
		).insert(ignore_permissions=True)

		student = self._create_user(
			f"permmany-outsider-{frappe.generate_hash(length=6)}@example.com",
			"Perm",
			"Outsider",
			["LMS Student"],
		)
		frappe.set_user(student.name)

		result = get_doc_permissions_many("LMS Program", [program.name, "does-not-exist-xyz"])
		self.assertEqual(result[program.name], {})
		self.assertEqual(result[program.name], result["does-not-exist-xyz"])

	def test_unreadable_document_reports_zero_not_an_error(self):
		student = self._create_user(
			f"permmany-{frappe.generate_hash(length=6)}@example.com",
			"Perm",
			"Student",
			["LMS Student"],
		)
		frappe.set_user(student.name)
		result = get_doc_permissions_many("LMS Course", [self.course.name])
		self.assertEqual(result[self.course.name].get("write", 0), 0)
