# Copyright (c) 2026, FOSS United and Contributors
# See license.txt

"""An unreleased course is not part of the public catalogue.

`lms.lms.utils.get_courses` is `allow_guest=True` and applied whatever publish
state the caller asked for -- including none at all, which returned everything.
An anonymous request to the bare endpoint listed every draft on the site by
title and slug:

    GET /api/method/lms.lms.utils.get_courses
      -> 23 courses, published flags [0, 1]

No parameter, no session, no crafted input. The endpoint sat in
`lms/tests/guest_endpoints.txt` as reviewed and accepted, and is not among the
entries that file's header flags as questionable -- so a human signed it off
while it was doing this.

The admin list is what wanted the publish filter honoured, and it is staff-only,
so the fix honours it for staff rather than removing it. These tests pin both
halves: that a caller without authoring rights cannot ask past the gate, and
that staff can still reach the Unpublished tab.
"""

import frappe

from lms.lms.test_helpers import BaseTestUtils
from lms.lms.utils import may_see_unpublished, scope_to_published

DRAFT_TITLE = "Publish Exposure Draft"


class TestCoursePublishExposure(BaseTestUtils):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		self.author = self._create_user(
			"publish-exposure-author@fixtures.test", "Pub", "Author", ["Course Creator"]
		)
		self.student = self._create_user_with_exact_roles(
			"publish-exposure-student@fixtures.test", "Pub", "Student", ["LMS Student"]
		)
		course = self._create_course(title=DRAFT_TITLE, instructor=self.author.name)
		frappe.db.set_value("LMS Course", course.name, "published", 0)
		self.draft = course.name
		self.cleanup_items.append(("LMS Course", course.name))

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	# The control every other assertion in this file rests on. "No drafts came
	# back" is true of a site with no drafts, which is exactly what the dev site
	# looked like while this endpoint was leaking -- a bare probe came back clean
	# and proved nothing.
	def test_there_really_is_an_unpublished_course_to_leak(self):
		self.assertEqual(frappe.db.get_value("LMS Course", self.draft, "published"), 0)

	def test_a_guest_cannot_ask_for_unpublished_courses(self):
		frappe.set_user("Guest")
		self.assertFalse(may_see_unpublished())
		self.assertEqual(scope_to_published({"published": 0}), {"published": 1})

	def test_a_student_cannot_ask_for_unpublished_courses(self):
		frappe.set_user(self.student.name)
		self.assertFalse(may_see_unpublished())
		self.assertEqual(scope_to_published({"published": 0}), {"published": 1})

	def test_an_author_can_still_reach_the_unpublished_tab(self):
		# The admin list has explicit Published / Unpublished tabs and calls this
		# endpoint. Narrowing the leak must not take those away.
		frappe.set_user(self.author.name)
		self.assertTrue(may_see_unpublished())
		self.assertEqual(scope_to_published({"published": 0}), {"published": 0})

	def test_the_catalogue_is_published_only_even_for_staff(self):
		# Asking for nothing is the learner-facing "Explore courses" view. It
		# should never surface a draft, whoever is looking.
		for user in ("Guest", self.student.name, self.author.name, "Administrator"):
			with self.subTest(user=user):
				frappe.set_user(user)
				self.assertEqual(scope_to_published({}), {"published": 1})

	def test_a_relationship_filter_is_left_alone(self):
		# `enrolled` and `created` already restrict to rows the caller has a
		# relationship with. Forcing a publish state on top would drop a
		# learner's own in-progress course the moment its author unpublished it.
		frappe.set_user(self.student.name)
		self.assertEqual(scope_to_published({"enrolled": 1}), {"enrolled": 1})
		self.assertEqual(scope_to_published({"created": 1}), {"created": 1})

	def test_the_caller_s_own_filters_are_not_mutated(self):
		# The caller's dict is reused by `get_courses` for the featured query, so
		# scoping has to hand back a copy rather than edit it in place.
		frappe.set_user("Guest")
		asked = {"published": 0}
		scope_to_published(asked)
		self.assertEqual(asked, {"published": 0})
