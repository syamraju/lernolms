import frappe

from lms.lms.api import MEMBERS_PAGE_LENGTH, get_member, get_members
from lms.lms.test_helpers import BaseTestUtils


class TestGetMembers(BaseTestUtils):
	"""Settings > Users pages at MEMBERS_PAGE_LENGTH and searches the whole table.

	The frontend steps `start` by that same number, so a mismatch here silently
	skips or repeats a row on every Load More. Search has to reach past the
	first page, since the panel does not fetch the rest before searching.
	"""

	def setUp(self):
		super().setUp()
		# System Manager, not Moderator. `get_members` is the site-wide user list
		# and was narrowed to System Manager when batch scoping landed: a
		# moderator locked out of a batch could otherwise still enumerate its
		# students here. These cases are about paging and search, so they need an
		# actor the endpoint accepts; that the endpoint now refuses a moderator is
		# covered in lms.lms.test_batch_people.
		# `_create_user_with_exact_roles`, not `_create_user`: the latter returns an
		# existing account untouched, so a leftover from an earlier run keeps
		# whatever roles it was born with. This actor exists to hold System Manager,
		# and without it the suite failed six PermissionErrors on the history of the
		# site rather than on anything the tests were asserting.
		self.operator = self._create_user_with_exact_roles(
			"members-operator@example.com", "Ops", "Erator", ["System Manager"]
		)
		self.members = [
			self._create_user(f"member{index}@example.com", "Member", str(index), ["LMS Student"])
			for index in range(MEMBERS_PAGE_LENGTH + 3)
		]
		frappe.set_user(self.operator.name)

	def _users_in_one_query(self, limit):
		"""What get_members would return if it never paged, read straight from
		the table with the same filters and ordering.

		Deriving this by paging through get_members would make the paging test
		circular: it would agree with itself however wrongly it paged.
		"""
		return [
			user.name
			for user in frappe.get_all(
				"User",
				filters=[
					["enabled", "=", 1],
					["name", "not in", ["Administrator", "Guest"]],
				],
				fields=["name"],
				limit_page_length=limit,
				start=0,
			)
		]

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def test_first_page_stops_at_the_page_length(self):
		self.assertEqual(len(get_members()), MEMBERS_PAGE_LENGTH)

	def test_second_page_continues_the_first_without_gap_or_repeat(self):
		"""Disjointness alone is not enough: it stays true when page two comes
		back empty or skips rows, which are the regressions this claims to pin."""
		first = [member.name for member in get_members()]
		second = [member.name for member in get_members(start=MEMBERS_PAGE_LENGTH)]
		both = first + second

		self.assertEqual(len(first), MEMBERS_PAGE_LENGTH)
		self.assertEqual(len(second), MEMBERS_PAGE_LENGTH, "page two came back short")
		self.assertEqual(len(set(both)), len(both), "a row was served on both pages")
		self.assertEqual(
			both,
			self._users_in_one_query(2 * MEMBERS_PAGE_LENGTH),
			"the two pages do not reconstruct the unpaged list",
		)

	def test_search_reaches_a_member_past_the_first_page(self):
		target = self.members[-1]

		found = get_members(search=target.first_name + " " + target.last_name)

		self.assertIn(target.name, [member.name for member in found])

	def test_search_matches_the_email_too(self):
		target = self.members[-1]

		found = get_members(search=target.name)

		self.assertIn(target.name, [member.name for member in found])

	def test_search_rejects_a_non_string(self):
		# @whitelist's pydantic argument check rejects the list with FrappeTypeError
		# before the body's own isinstance guard can throw ValidationError. Either
		# refusal satisfies the contract; the two classes are unrelated.
		with self.assertRaises((frappe.ValidationError, frappe.FrappeTypeError)):
			get_members(search=["ada"])


class TestGetMember(BaseTestUtils):
	"""The member edit form seeds itself from one exact row.

	It used to ask get_members for it, which pages and hides disabled users, so
	the two cases below came back empty and left Save disabled with nothing on
	screen explaining why.
	"""

	def setUp(self):
		super().setUp()
		# Moderator, deliberately different from TestGetMembers above. The two
		# endpoints were split on purpose: `get_members` is the site-wide paginated
		# search and was narrowed to System Manager when batch scoping landed,
		# because a moderator locked out of a batch could otherwise enumerate its
		# students. `get_member` answers "give me this one row" for the edit form
		# and stayed at Moderator, which is who that form is for.
		#
		# A separate email from the class above, because these two want the same
		# actor to hold different roles and `_create_user_with_exact_roles` would
		# otherwise have them fighting over one account between suites.
		self.operator = self._create_user_with_exact_roles(
			"member-moderator@example.com", "Mod", "Erator", ["Moderator"]
		)
		# Two of these cases prove `get_member` reaches a row `get_members` cannot,
		# so they have to call both — and the two endpoints no longer accept the
		# same actor. This one exists solely to read the paginated list; see
		# `_paged_names`.
		self.reader = self._create_user_with_exact_roles(
			"member-reader@example.com", "Read", "Er", ["System Manager"]
		)
		self.members = [
			self._create_user(f"member{index}@example.com", "Member", str(index), ["LMS Student"])
			for index in range(MEMBERS_PAGE_LENGTH + 3)
		]
		frappe.set_user(self.operator.name)

	def tearDown(self):
		frappe.set_user("Administrator")
		super().tearDown()

	def _paged_names(self, **kwargs):
		"""What the paginated list returns, read by an actor it accepts.

		The contrast is the point of this class: `get_member` reaches a row that
		`get_members` cannot. Both halves have to actually run, and since batch
		scoping the two require different roles — so the plural call switches to
		the System Manager and hands the session straight back.
		"""
		frappe.set_user(self.reader.name)
		try:
			return [member.name for member in get_members(**kwargs)]
		finally:
			frappe.set_user(self.operator.name)

	def test_returns_the_roles_of_the_member_asked_for(self):
		target = self.members[0]

		row = get_member(target.name)

		self.assertEqual(row.name, target.name)
		self.assertIn("LMS Student", row.roles)

	def test_reaches_a_member_past_the_first_page(self):
		# setUp creates three members more than a page holds, but which three fall
		# off it is get_members' ordering (newest first) rather than part of the
		# contract, so take the target from what the first page actually left out.
		first_page = self._paged_names()
		off_page = [member for member in self.members if member.name not in first_page]

		self.assertTrue(off_page, "the fixture no longer exceeds one page")
		self.assertEqual(get_member(off_page[0].name).name, off_page[0].name)

	def test_reaches_a_disabled_member(self):
		target = self.members[0]
		frappe.db.set_value("User", target.name, "enabled", 0)

		self.assertNotIn(target.name, self._paged_names(search=target.name))
		self.assertEqual(get_member(target.name).name, target.name)

	def test_rejects_a_member_that_does_not_exist(self):
		with self.assertRaises(frappe.DoesNotExistError):
			get_member("nobody@example.com")

	def test_rejects_the_built_in_accounts(self):
		for name in ["Administrator", "Guest"]:
			with self.assertRaises(frappe.ValidationError):
				get_member(name)

	def test_rejects_a_blank_member(self):
		with self.assertRaises(frappe.ValidationError):
			get_member("   ")

	def test_rejects_a_non_string(self):
		# Same two-class refusal as get_members' search guard.
		with self.assertRaises((frappe.ValidationError, frappe.FrappeTypeError)):
			get_member(["ada"])
