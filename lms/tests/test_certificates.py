# Copyright (c) 2026, FOSS United and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from lms.lms.certificates import (
	DEFAULT_DATE_FORMAT,
	can_design_certificate,
	clamp_element,
	format_value,
	mandatory_keys,
	missing_requirements,
	render_elements,
	resolve_issue_date,
	variables_for,
)


def variable(key, **kw):
	return {"element_type": "Variable", "variable": key, **kw}


def complete_course_design():
	return [variable(key) for key in mandatory_keys("LMS Course")]


class TestMandatoryVariables(FrappeTestCase):
	# The four fields the brief names, plus the issue date. If this list ever
	# shrinks by accident, certificates start going out without a course name on
	# them and nothing else in the system notices.
	def test_a_course_certificate_requires_the_five_named_fields(self):
		self.assertEqual(
			mandatory_keys("LMS Course"),
			[
				"participant_name",
				"course_name",
				"course_start_date",
				"course_end_date",
				"issue_date",
			],
		)

	def test_a_program_certificate_names_the_program_not_the_course(self):
		keys = mandatory_keys("LMS Program")
		self.assertIn("program_name", keys)
		self.assertIn("program_start_date", keys)
		self.assertNotIn("course_name", keys)
		self.assertNotIn("course_start_date", keys)

	def test_every_variable_offered_declares_a_type(self):
		for reference_doctype in ("LMS Course", "LMS Program"):
			for entry in variables_for(reference_doctype):
				self.assertIn(entry["type"], ("text", "date"), entry["key"])


class TestMissingRequirements(FrappeTestCase):
	def test_a_finished_design_is_missing_nothing(self):
		self.assertEqual(
			missing_requirements("LMS Course", "/files/bg.png", complete_course_design()),
			[],
		)

	def test_a_design_with_no_background_is_not_finished(self):
		missing = missing_requirements("LMS Course", None, complete_course_design())
		self.assertEqual([item["code"] for item in missing], ["background"])

	def test_every_unplaced_mandatory_field_is_reported_at_once(self):
		missing = missing_requirements("LMS Course", "/files/bg.png", [variable("participant_name")])
		self.assertEqual(
			[item["code"] for item in missing],
			["course_name", "course_start_date", "course_end_date", "issue_date"],
		)

	# A moderator who typed the learner's name as free text has not placed the
	# variable: the certificate would carry one name for everybody.
	def test_free_text_does_not_satisfy_a_mandatory_variable(self):
		elements = [
			{"element_type": "Text", "content": "Participant Name"},
			*[variable(key) for key in mandatory_keys("LMS Course")[1:]],
		]
		missing = missing_requirements("LMS Course", "/files/bg.png", elements)
		self.assertEqual([item["code"] for item in missing], ["participant_name"])

	def test_an_empty_design_reports_the_background_and_all_five_fields(self):
		missing = missing_requirements("LMS Course", None, [])
		self.assertEqual(len(missing), 6)

	def test_a_program_design_is_judged_against_the_program_fields(self):
		elements = [variable(key) for key in mandatory_keys("LMS Program")]
		self.assertEqual(missing_requirements("LMS Program", "/files/bg.png", elements), [])


class TestClampElement(FrappeTestCase):
	def test_an_element_inside_the_canvas_is_left_alone(self):
		clamped = clamp_element({"x": 100, "y": 50, "width": 200, "height": 60}, 1000, 500)
		self.assertEqual((clamped["x"], clamped["y"]), (100, 50))

	def test_an_element_dragged_past_the_right_edge_is_pulled_back_in(self):
		clamped = clamp_element({"x": 950, "y": 10, "width": 200, "height": 60}, 1000, 500)
		self.assertEqual(clamped["x"], 800)

	def test_a_negative_position_is_pulled_to_the_edge(self):
		clamped = clamp_element({"x": -40, "y": -10, "width": 200, "height": 60}, 1000, 500)
		self.assertEqual((clamped["x"], clamped["y"]), (0, 0))

	def test_an_element_wider_than_the_canvas_is_capped_at_the_canvas(self):
		clamped = clamp_element({"x": 0, "y": 0, "width": 4000, "height": 60}, 1000, 500)
		self.assertEqual(clamped["width"], 1000)
		self.assertEqual(clamped["x"], 0)

	# A zero-height box is invisible and unselectable once saved, which reads to
	# the moderator as "my field disappeared".
	def test_a_sizeless_element_is_given_a_size(self):
		clamped = clamp_element({"x": 0, "y": 0, "width": 0, "height": 0}, 1000, 500)
		self.assertEqual((clamped["width"], clamped["height"]), (1, 1))

	def test_the_other_keys_survive_and_the_input_is_not_mutated(self):
		element = {"x": -5, "y": 0, "width": 10, "height": 10, "color": "#fff"}
		clamped = clamp_element(element, 1000, 500)
		self.assertEqual(clamped["color"], "#fff")
		self.assertEqual(element["x"], -5)


class TestRenderElements(FrappeTestCase):
	def test_a_variable_renders_its_resolved_value(self):
		rendered = render_elements(
			"LMS Course", [variable("participant_name")], {"participant_name": "Asha Rao"}
		)
		self.assertEqual(rendered[0]["value"], "Asha Rao")

	def test_a_date_variable_is_formatted_by_its_own_format(self):
		rendered = render_elements(
			"LMS Course",
			[variable("issue_date", date_format="dd/MM/yyyy")],
			{"issue_date": "2026-08-21"},
		)
		self.assertEqual(rendered[0]["value"], "21/08/2026")

	def test_text_renders_its_own_content_and_ignores_the_values(self):
		rendered = render_elements(
			"LMS Course",
			[{"element_type": "Text", "content": "Certificate of Completion"}],
			{"participant_name": "Asha Rao"},
		)
		self.assertEqual(rendered[0]["value"], "Certificate of Completion")

	def test_an_image_carries_its_file_and_draws_no_text(self):
		rendered = render_elements("LMS Course", [{"element_type": "Image", "image": "/files/sign.png"}], {})
		self.assertEqual(rendered[0]["image"], "/files/sign.png")
		self.assertEqual(rendered[0]["value"], "")

	# A learner with no batch has no batch name. Printing the word "None" on a
	# certificate is worse than printing nothing.
	def test_a_variable_with_no_value_renders_empty(self):
		rendered = render_elements("LMS Course", [variable("batch_name")], {"batch_name": None})
		self.assertEqual(rendered[0]["value"], "")

	def test_style_defaults_are_filled_in_so_the_renderer_never_guesses(self):
		rendered = render_elements("LMS Course", [variable("participant_name")], {})
		self.assertEqual(rendered[0]["align"], "center")
		self.assertEqual(rendered[0]["opacity"], 1)
		self.assertTrue(rendered[0]["font_size"])


class TestFormatValue(FrappeTestCase):
	def test_text_is_passed_through(self):
		self.assertEqual(format_value("Asha Rao", "text", None), "Asha Rao")

	def test_a_date_without_a_chosen_format_uses_the_default(self):
		self.assertEqual(
			format_value("2026-08-21", "date", None),
			format_value("2026-08-21", "date", DEFAULT_DATE_FORMAT),
		)

	def test_nothing_renders_as_nothing(self):
		self.assertEqual(format_value(None, "text", None), "")
		self.assertEqual(format_value("", "date", None), "")


class TestResolveIssueDate(FrappeTestCase):
	def test_completion_date_wins_by_default(self):
		template = {"issue_date_source": "Completion Date", "custom_issue_date": "2026-01-01"}
		self.assertEqual(str(resolve_issue_date(template, "2026-08-21")), "2026-08-21")

	def test_a_custom_date_overrides_the_completion_date(self):
		template = {"issue_date_source": "Custom Date", "custom_issue_date": "2026-12-01"}
		self.assertEqual(str(resolve_issue_date(template, "2026-08-21")), "2026-12-01")

	# Choosing "custom" and then not entering one must not print a blank date.
	def test_a_custom_source_with_no_date_falls_back_to_completion(self):
		template = {"issue_date_source": "Custom Date", "custom_issue_date": None}
		self.assertEqual(str(resolve_issue_date(template, "2026-08-21")), "2026-08-21")

	def test_no_template_at_all_still_yields_a_date(self):
		self.assertEqual(str(resolve_issue_date(None, "2026-08-21")), "2026-08-21")


class TestDesignAccess(FrappeTestCase):
	"""The rule the REST API is gated on, not just the designer's endpoints."""

	def test_a_doctype_without_certificates_is_never_designable(self):
		self.assertFalse(can_design_certificate("LMS Batch", "any"))

	def test_a_moderator_may_design_any_certificate(self):
		self.assertTrue(can_design_certificate("LMS Program", "any-program"))

	def test_the_doctype_gates_writes_on_the_same_rule(self):
		# Registering the hook is the whole protection: the DocPerms behind
		# /api/resource grant Course Creator write on the doctype, not on one
		# course's row, so an unregistered handler is an open door.
		self.assertEqual(
			frappe.get_hooks("has_permission").get("LMS Certificate Template"),
			["lms.lms.doctype.lms_certificate_template.lms_certificate_template.has_permission"],
		)
