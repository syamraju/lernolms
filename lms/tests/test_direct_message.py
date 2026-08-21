# Copyright (c) 2026, FOSS United and Contributors
# See license.txt

"""Direct messages and the traces a call leaves in them.

Not to be confused with `lms/lms/test_chat.py`, which covers the batch channel
tree in `lms.lms.chat`. Different store, different access rule, different test.
"""

from unittest.mock import patch

import frappe

from lms.lms import direct_message, huddle
from lms.lms.conversation import dm_id, like_literal
from lms.lms.doctype.lms_direct_message.lms_direct_message import (
	get_permission_query_conditions,
)
from lms.lms.doctype.lms_direct_message.lms_direct_message import (
	has_permission as message_has_permission,
)
from lms.lms.test_helpers import BaseTestUtils


class ChatTestCase(BaseTestUtils):
	def setUp(self):
		super().setUp()
		self.alice = self._create_user("alice.chat@example.com", "Alice", "C", ["LMS Student"]).name
		self.bob = self._create_user("bob.chat@example.com", "Bob", "C", ["LMS Student"]).name
		self.mallory = self._create_user("mallory.chat@example.com", "Mallory", "C", ["LMS Student"]).name

		evaluator = self._create_evaluator(self.alice)
		course = self._create_course(title="Chat Course", instructor=self.alice)
		batch = self._create_batch(
			course.name, instructor=self.alice, title="Chat Batch", evaluator=evaluator.name
		)
		self._create_batch_enrollment(self.alice, batch.name)
		self._create_batch_enrollment(self.bob, batch.name)

		self.batch = batch.name
		self.dm = dm_id(self.alice, self.bob)
		frappe.set_user(self.alice)

	def tearDown(self):
		frappe.set_user("Administrator")
		for name in frappe.get_all("LMS Direct Message", pluck="name"):
			frappe.delete_doc("LMS Direct Message", name, force=True)
		for name in frappe.get_all("LMS Direct Message Read State", pluck="name"):
			frappe.delete_doc("LMS Direct Message Read State", name, force=True)
		frappe.cache().delete_value(huddle._key(self.dm))
		super().tearDown()


class TestSendMessage(ChatTestCase):
	def test_a_message_lands_in_the_thread(self):
		direct_message.send_message(self.dm, "hello")
		rows = direct_message.get_messages(self.dm)
		self.assertEqual([r.content for r in rows], ["hello"])

	def test_an_empty_message_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			direct_message.send_message(self.dm, "   ")

	def test_an_overlong_message_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			direct_message.send_message(self.dm, "x" * (direct_message.MAX_MESSAGE_LENGTH + 1))

	def test_someone_outside_the_thread_cannot_post_into_it(self):
		frappe.set_user(self.mallory)
		with self.assertRaises(frappe.PermissionError):
			direct_message.send_message(self.dm, "let me in")

	def test_a_message_is_pushed_to_both_people(self):
		with patch("frappe.publish_realtime") as publish:
			direct_message.send_message(self.dm, "hello")

		notified = {c.kwargs["user"] for c in publish.call_args_list if c.args[0] == direct_message.EVENT_MESSAGE}
		self.assertEqual(notified, {self.alice, self.bob})

	def test_content_is_stored_verbatim_rather_than_escaped(self):
		# The client renders bodies as text nodes, so escaping here would show
		# people their own angle brackets as entities.
		direct_message.send_message(self.dm, "a < b && c > d")
		self.assertEqual(direct_message.get_messages(self.dm)[0].content, "a < b && c > d")


class TestConversations(ChatTestCase):
	def test_a_thread_appears_once_it_has_a_message(self):
		self.assertEqual(direct_message.get_conversations(), [])
		direct_message.send_message(self.dm, "hello")
		self.assertEqual([c["conversation"] for c in direct_message.get_conversations()], [self.dm])

	def test_the_other_person_is_named_from_the_readers_side(self):
		direct_message.send_message(self.dm, "hello")

		mine = direct_message.get_conversations()[0]
		self.assertEqual(mine["peer"]["user"], self.bob)

		frappe.set_user(self.bob)
		theirs = direct_message.get_conversations()[0]
		self.assertEqual(theirs["peer"]["user"], self.alice)

	def test_an_unread_message_is_counted_for_the_recipient(self):
		direct_message.send_message(self.dm, "hello")
		frappe.set_user(self.bob)
		self.assertEqual(direct_message.get_conversations()[0]["unread"], 1)

	def test_your_own_message_is_not_unread_to_you(self):
		direct_message.send_message(self.dm, "hello")
		self.assertEqual(direct_message.get_conversations()[0]["unread"], 0)

	def test_marking_read_clears_the_count(self):
		direct_message.send_message(self.dm, "hello")
		frappe.set_user(self.bob)
		direct_message.mark_read(self.dm)
		self.assertEqual(direct_message.get_conversations()[0]["unread"], 0)

	def test_a_thread_you_are_not_in_is_not_listed(self):
		direct_message.send_message(self.dm, "hello")
		frappe.set_user(self.mallory)
		self.assertEqual(direct_message.get_conversations(), [])


class TestStartDm(ChatTestCase):
	def test_opening_a_thread_writes_nothing(self):
		# A DM you opened and closed without typing is not a conversation, and
		# listing it as one is noise in everybody's sidebar.
		direct_message.start_dm(self.bob)
		self.assertEqual(direct_message.get_conversations(), [])

	def test_both_ends_resolve_the_same_thread_id(self):
		mine = direct_message.start_dm(self.bob)["conversation"]
		frappe.set_user(self.bob)
		theirs = direct_message.start_dm(self.alice)["conversation"]
		self.assertEqual(mine, theirs)


class TestPeople(ChatTestCase):
	def test_batchmates_are_offered(self):
		self.assertIn(self.bob, [p.user for p in direct_message.get_people()])

	def test_you_are_not_offered_yourself(self):
		self.assertNotIn(self.alice, [p.user for p in direct_message.get_people()])

	def test_someone_you_share_no_batch_with_is_not_offered(self):
		self.assertNotIn(self.mallory, [p.user for p in direct_message.get_people()])

	def test_search_narrows_the_list(self):
		self.assertEqual([p.user for p in direct_message.get_people(search="Bob")], [self.bob])


class TestThreadLookup(ChatTestCase):
	def test_a_dm_resolves_to_the_other_persons_name(self):
		thread = direct_message.get_thread(self.dm)
		self.assertEqual(thread["kind"], "dm")
		self.assertEqual(thread["peer"]["user"], self.bob)

	def test_a_batch_resolves_to_its_title(self):
		thread = direct_message.get_thread(f"batch:{self.batch}")
		self.assertEqual(thread["title"], "Chat Batch")

	def test_a_thread_you_cannot_see_is_refused(self):
		frappe.set_user(self.mallory)
		with self.assertRaises(frappe.PermissionError):
			direct_message.get_thread(self.dm)


class TestHuddleAnnouncements(ChatTestCase):
	def test_starting_a_call_in_a_dm_says_so_in_the_thread(self):
		huddle.join(self.dm, "peer-alice")
		rows = direct_message.get_messages(self.dm)
		self.assertEqual([r.message_type for r in rows], ["System"])
		self.assertIn("Huddle started", rows[0].content)

	def test_ending_it_reports_how_long_it_ran(self):
		huddle.join(self.dm, "peer-alice")
		huddle.leave(self.dm, "peer-alice")

		rows = direct_message.get_messages(self.dm)
		self.assertEqual(len(rows), 2)
		self.assertIn("Huddle ended", rows[1].content)

	def test_a_second_joiner_does_not_re_announce(self):
		huddle.join(self.dm, "peer-alice")
		frappe.set_user(self.bob)
		huddle.join(self.dm, "peer-bob")

		self.assertEqual(len(direct_message.get_messages(self.dm)), 1)

	def test_a_batch_call_leaves_no_message(self):
		# Batch threads render from LMS Discussion, so a system message here
		# would be written to a table nobody reads.
		conversation = f"batch:{self.batch}"
		huddle.join(conversation, "peer-alice")
		try:
			self.assertEqual(direct_message.get_messages(conversation), [])
		finally:
			frappe.cache().delete_value(huddle._key(conversation))


class TestDmReachability(ChatTestCase):
	"""Being named in a conversation id is not permission to use it."""

	def test_you_cannot_open_a_thread_with_someone_you_share_nothing_with(self):
		# Anyone can compose dm:<anyone>|<me>. Without a relationship test, that
		# is a licence to message, ring and CALL every address on the site.
		with self.assertRaises(frappe.PermissionError):
			direct_message.start_dm(self.mallory)

	def test_a_batchmate_is_reachable(self):
		self.assertEqual(direct_message.start_dm(self.bob)["peer"]["user"], self.bob)

	def test_an_existing_thread_survives_the_cohort_ending(self):
		# Otherwise two people lose a conversation they are in the middle of the
		# moment their batch is unenrolled.
		direct_message.send_message(self.dm, "hello")
		frappe.set_user("Administrator")
		for name in frappe.get_all(
			"LMS Batch Enrollment", filters={"batch": self.batch}, pluck="name"
		):
			frappe.delete_doc("LMS Batch Enrollment", name, force=True)
		frappe.set_user(self.alice)

		self.assertEqual(direct_message.get_messages(self.dm)[0].content, "hello")

	def test_a_moderator_cannot_read_two_students_private_thread(self):
		# Staff drop-in is deliberate for shared conversations and deliberately
		# absent for DMs. If this ever passes, the DocPerm drop and the guard
		# have drifted apart.
		direct_message.send_message(self.dm, "private")
		# Creating a User is an administrator's job; the suite is running as a
		# student here.
		frappe.set_user("Administrator")
		mod = self._create_user("mod.dm@example.com", "Mod", "DM", ["Moderator"]).name
		frappe.set_user(mod)

		with self.assertRaises(frappe.PermissionError):
			direct_message.get_messages(self.dm)


class TestRestDoor(ChatTestCase):
	"""/api/resource is a second door onto these rows and the app's own access
	checks do not run on it. These guard the hooks that close it."""

	def test_the_query_condition_is_wired_up_in_hooks(self):
		# The chat doctypes shipped with both functions written and neither
		# registered, so the grant was unscoped and nothing said so.
		import lms.hooks as hooks

		self.assertIn("LMS Direct Message", hooks.permission_query_conditions)
		self.assertIn("LMS Direct Message", hooks.has_permission)
		self.assertIn("LMS Direct Message Read State", hooks.permission_query_conditions)
		self.assertIn("LMS Direct Message Read State", hooks.has_permission)

	def test_the_condition_carries_an_escape_clause(self):
		# Without ESCAPE the escaping below is inert. Asserting only the clause,
		# not the escaped text: frappe.db.escape doubles `%` for its own
		# substitution layer, so a string assertion about the address matches the
		# wrong layer and breaks whenever escape() changes. The behaviour is
		# pinned by the SQL tests instead.
		self.assertIn("ESCAPE", get_permission_query_conditions("a_b@example.com"))

	def test_the_escaper_neutralises_percent(self):
		# The pure form, free of frappe's escaping layer.
		self.assertEqual(like_literal("a%b@example.com"), "a!%b@example.com")

	def test_a_percent_lookalike_is_excluded_in_sql(self):
		# `%` matches ANY run of characters, so an unescaped `a%b` pattern would
		# match every address starting a... and ending ...b -- a far wider net
		# than the underscore case.
		victim = "dm:a-anything-b@example.com|someone@example.com"
		pattern = f"dm:{like_literal('a%b@example.com')}|%"
		matched = frappe.db.sql("SELECT %s LIKE %s ESCAPE '!'", (victim, pattern))[0][0]
		self.assertEqual(matched, 0)

	def test_the_escape_character_itself_is_escaped(self):
		self.assertEqual(like_literal("a!b"), "a!!b")

	def test_the_lookalike_address_really_is_excluded_in_sql(self):
		# The unit test above checks the pattern; this checks the database
		# agrees, which is the part that actually protects anyone.
		victim = "dm:axb@example.com|someone@example.com"
		pattern = f"dm:{like_literal('a_b@example.com')}|%"
		matched = frappe.db.sql(
			"SELECT %s LIKE %s ESCAPE '!'", (victim, pattern)
		)[0][0]
		self.assertEqual(matched, 0)

	def test_the_real_address_still_matches(self):
		mine = "dm:a_b@example.com|someone@example.com"
		pattern = f"dm:{like_literal('a_b@example.com')}|%"
		matched = frappe.db.sql(
			"SELECT %s LIKE %s ESCAPE '!'", (mine, pattern)
		)[0][0]
		self.assertEqual(matched, 1)

	def test_a_guest_query_matches_nothing_rather_than_everything(self):
		self.assertEqual(get_permission_query_conditions("Guest"), "1 = 0")

	def test_the_read_state_hook_refuses_a_guest_the_same_way(self):
		# The two hooks compared Guest differently -- one lowercased, one did
		# not. Both happened to work, which is exactly how that kind of drift
		# survives until the day it does not.
		from lms.lms.doctype.lms_direct_message_read_state.lms_direct_message_read_state import (
			get_permission_query_conditions as read_state_conditions,
		)

		self.assertEqual(read_state_conditions("Guest"), "1 = 0")

	def test_both_hooks_agree_that_a_system_manager_is_unrestricted(self):
		# One shared definition of super-user across the permission layer, not
		# a local copy per doctype.
		from lms.lms.doctype.lms_direct_message_read_state.lms_direct_message_read_state import (
			get_permission_query_conditions as read_state_conditions,
		)

		self.assertEqual(get_permission_query_conditions("Administrator"), "")
		self.assertEqual(read_state_conditions("Administrator"), "")

	def test_has_permission_refuses_a_thread_you_are_not_in(self):
		frappe.set_user(self.mallory)
		doc = frappe._dict({"conversation": self.dm})
		self.assertFalse(message_has_permission(doc, "read", self.mallory))

	def test_has_permission_allows_a_participant(self):
		doc = frappe._dict({"conversation": self.dm})
		self.assertTrue(message_has_permission(doc, "read", self.alice))


class TestRestDoorLive(ChatTestCase):
	"""The permission condition as the database applies it.

	`frappe.get_list` runs the query condition and the DocPerms; the app's own
	`get_all(ignore_permissions=True)` reads do not. This is the only place the
	REST door is exercised the way a real client exercises it.
	"""

	def test_a_participant_sees_their_own_message(self):
		# THE POSITIVE CONTROL, and the most important test here. Without it,
		# a condition of "1 = 0" scores identically to a correct one: every
		# negative case returns zero rows either way.
		direct_message.send_message(self.dm, "mine")

		rows = frappe.get_list(
			"LMS Direct Message", fields=["content"], limit_page_length=0
		)
		self.assertEqual([r.content for r in rows], ["mine"])

	def test_an_uninvolved_student_sees_nothing(self):
		direct_message.send_message(self.dm, "private")
		frappe.set_user(self.mallory)

		self.assertEqual(
			frappe.get_list("LMS Direct Message", fields=["content"], limit_page_length=0), []
		)

	def test_a_course_creator_sees_nothing(self):
		# The original hole: Course Creator is an authoring role a user can hold
		# without an administrator's involvement, and it had unscoped read and
		# export over every private thread on the site.
		direct_message.send_message(self.dm, "private")
		frappe.set_user("Administrator")
		author = self._create_user("author.dm@example.com", "Author", "DM", ["Course Creator"]).name
		frappe.set_user(author)

		self.assertEqual(
			frappe.get_list("LMS Direct Message", fields=["content"], limit_page_length=0), []
		)

	def test_a_read_cursor_is_not_visible_to_anyone_else(self):
		# Less sensitive than a message, but it still says who has been talking
		# to whom and when they last looked.
		direct_message.send_message(self.dm, "private")
		frappe.set_user(self.mallory)

		self.assertEqual(
			frappe.get_list(
				"LMS Direct Message Read State", fields=["conversation"], limit_page_length=0
			),
			[],
		)
