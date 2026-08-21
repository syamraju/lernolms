# Copyright (c) 2026, Frappe and Contributors
# For license information, please see license.txt

"""Batch chat: who can see which channel, and who can post in it.

The access rules are derived from the batch roster on every request, so these
tests are mostly about *changing the roster* and checking that the channel tree
follows without anything being synced.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from lms.lms.chat import (
	can_access_channel,
	can_post,
	general_channel,
	get_channel_tree,
	get_messages,
	get_my_channels,
	post_message,
	seed_default_channels,
)
from lms.lms.test_batch_access import _batch, _user


def _channel(batch: str, title: str):
	return frappe.db.get_value(
		"LMS Chat Channel",
		{"batch": batch, "title": title},
		["name", "batch", "audience", "post_permission", "is_archived"],
		as_dict=True,
	)


class ChatTestCase(FrappeTestCase):
	def setUp(self):
		self.moderator = _user(self.mod_email, ["Moderator"])
		self.batch = _batch(self.batch_title, self.moderator)
		seed_default_channels(self.batch)
		frappe.set_user(self.moderator)

	def tearDown(self):
		frappe.set_user("Administrator")

	def _enrol(self, email):
		user = _user(email, ["LMS Student"])
		frappe.set_user(self.moderator)
		frappe.get_doc({"doctype": "LMS Batch Enrollment", "batch": self.batch, "member": user}).insert(
			ignore_permissions=True
		)
		return user


class TestSeeding(ChatTestCase):
	mod_email = "chat-seed-mod@example.com"
	batch_title = "Chat Seed Cohort"

	def test_a_new_batch_gets_three_channels(self):
		titles = frappe.get_all("LMS Chat Channel", filters={"batch": self.batch}, pluck="title")
		self.assertIn("announcements", titles)
		self.assertIn("general", titles)
		self.assertIn("staff-room", titles)

	def test_seeding_twice_does_not_duplicate(self):
		seed_default_channels(self.batch)
		count = frappe.db.count("LMS Chat Channel", {"batch": self.batch, "title": "general"})
		self.assertEqual(count, 1)

	def test_depth_is_capped_at_two(self):
		"""Channels and sub-channels — not a tree."""
		parent = general_channel(self.batch)
		child = frappe.get_doc(
			{"doctype": "LMS Chat Channel", "batch": self.batch, "title": "topic", "parent_channel": parent}
		).insert(ignore_permissions=True)

		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "LMS Chat Channel",
					"batch": self.batch,
					"title": "sub-topic",
					"parent_channel": child.name,
				}
			).insert(ignore_permissions=True)

	def test_a_sub_channel_cannot_cross_batches(self):
		other = _batch("Chat Other Cohort", self.moderator)
		seed_default_channels(other)
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "LMS Chat Channel",
					"batch": self.batch,
					"title": "smuggled",
					"parent_channel": general_channel(other),
				}
			).insert(ignore_permissions=True)


class TestChannelAccess(ChatTestCase):
	mod_email = "chat-access-mod@example.com"
	batch_title = "Chat Access Cohort"

	def test_a_student_reads_general_but_not_the_staff_room(self):
		student = self._enrol("chat-access-student@example.com")
		self.assertTrue(can_access_channel(_channel(self.batch, "general"), student))
		self.assertFalse(can_access_channel(_channel(self.batch, "staff-room"), student))

	def test_an_outsider_reads_nothing(self):
		outsider = _user("chat-access-outsider@example.com", ["LMS Student"])
		self.assertFalse(can_access_channel(_channel(self.batch, "general"), outsider))
		self.assertFalse(can_access_channel(_channel(self.batch, "announcements"), outsider))

	def test_a_moderator_of_another_batch_reads_nothing(self):
		"""Holding Moderator is not a key to every cohort's conversation."""
		other_mod = _user("chat-access-othermod@example.com", ["Moderator"])
		self.assertFalse(can_access_channel(_channel(self.batch, "general"), other_mod))

	def test_removing_a_student_removes_their_access_with_no_sync(self):
		"""Access is the roster query. Nothing is written when membership changes,
		which is exactly why a deleted enrollment takes effect immediately."""
		student = self._enrol("chat-access-removed@example.com")
		channel = _channel(self.batch, "general")
		self.assertTrue(can_access_channel(channel, student))

		enrollment = frappe.db.get_value(
			"LMS Batch Enrollment", {"batch": self.batch, "member": student}, "name"
		)
		frappe.delete_doc("LMS Batch Enrollment", enrollment, ignore_permissions=True)

		self.assertFalse(can_access_channel(channel, student))

	def test_the_tree_hides_what_the_caller_cannot_read(self):
		student = self._enrol("chat-access-tree@example.com")
		frappe.set_user(student)
		titles = [node["title"] for node in get_channel_tree(self.batch)]
		self.assertTrue(titles, "the student's channel tree came back empty")
		self.assertIn("general", titles)
		self.assertNotIn("staff-room", titles)


class TestPosting(ChatTestCase):
	mod_email = "chat-post-mod@example.com"
	batch_title = "Chat Post Cohort"

	def test_a_student_cannot_post_in_announcements(self):
		student = self._enrol("chat-post-student@example.com")
		announcements = _channel(self.batch, "announcements")
		self.assertTrue(can_access_channel(announcements, student))
		self.assertFalse(can_post(announcements, student))

	def test_a_student_can_post_in_general(self):
		student = self._enrol("chat-post-general@example.com")
		frappe.set_user(student)
		result = post_message(general_channel(self.batch), "hello")
		self.assertTrue(result["name"])

	def test_posting_where_you_cannot_read_is_refused(self):
		outsider = _user("chat-post-outsider@example.com", ["LMS Student"])
		frappe.set_user(outsider)
		with self.assertRaises(frappe.PermissionError):
			post_message(general_channel(self.batch), "let me in")

	def test_an_archived_channel_is_read_only_for_students(self):
		student = self._enrol("chat-post-archived@example.com")
		channel = general_channel(self.batch)
		frappe.db.set_value("LMS Chat Channel", channel, "is_archived", 1)

		self.assertFalse(can_post(channel, student))
		# The moderator can still close a thread out.
		self.assertTrue(can_post(channel, self.moderator))

	def test_the_sender_cannot_be_forged(self):
		student = self._enrol("chat-post-forger@example.com")
		frappe.set_user(student)
		doc = frappe.get_doc(
			{
				"doctype": "LMS Chat Message",
				"channel": general_channel(self.batch),
				"sender": self.moderator,
				"content": "not mine",
			}
		).insert(ignore_permissions=True)
		self.assertEqual(doc.sender, student)

	def test_a_deleted_message_keeps_its_row_but_loses_its_body(self):
		"""Soft delete: replies hanging under it still need a parent."""
		from lms.lms.chat import delete_message

		frappe.set_user(self.moderator)
		channel = general_channel(self.batch)
		posted = post_message(channel, "regrettable")
		delete_message(posted["name"])

		rows = get_messages(channel)
		row = [r for r in rows if r["name"] == posted["name"]][0]
		self.assertTrue(row["is_deleted"])
		self.assertIsNone(row["content"])


class TestCourseChannels(ChatTestCase):
	mod_email = "chat-course-mod@example.com"
	batch_title = "Chat Course Cohort"

	def _course(self, title):
		"""`instructors` is mandatory on LMS Course, so a course cannot exist
		without one — the batch moderator stands in."""
		doc = frappe.get_doc(
			{
				"doctype": "LMS Course",
				"title": title,
				"short_introduction": "x",
				"description": "x",
				"instructors": [{"instructor": self.moderator}],
			}
		).insert(ignore_permissions=True)
		return doc.name

	def test_adding_a_course_creates_a_sub_channel(self):
		course = self._course("Chat Channel Course")
		doc = frappe.get_doc("LMS Batch", self.batch)
		doc.append("courses", {"course": course})
		doc.save(ignore_permissions=True)

		channel = frappe.db.get_value(
			"LMS Chat Channel",
			{"batch": self.batch, "course": course},
			["name", "parent_channel", "channel_type"],
			as_dict=True,
		)
		self.assertTrue(channel)
		self.assertEqual(channel.channel_type, "Course")
		self.assertEqual(channel.parent_channel, general_channel(self.batch))

	def test_deleting_the_course_itself_takes_the_channel_with_it(self):
		"""Dropping a course from a batch archives its channel; deleting the
		course removes it. Without this the delete is refused outright — the
		channel holds a Link to the course, so a moderator deleting a course that
		had ever been in a batch got a raw LinkExistsError naming a channel id.
		"""
		from lms.lms.api import delete_course

		course = self._course("Chat Delete Course")
		doc = frappe.get_doc("LMS Batch", self.batch)
		doc.append("courses", {"course": course})
		doc.save(ignore_permissions=True)

		channel = frappe.db.get_value("LMS Chat Channel", {"batch": self.batch, "course": course}, "name")
		self.assertTrue(channel)
		posted = frappe.get_doc(
			{"doctype": "LMS Chat Message", "channel": channel, "content": "hello"}
		).insert(ignore_permissions=True)

		frappe.set_user("Administrator")
		delete_course(course)

		self.assertFalse(frappe.db.exists("LMS Chat Channel", channel))
		# The channel's on_trash is what clears these; a bare row delete on the
		# channel would leave both orphaned.
		self.assertFalse(frappe.db.exists("LMS Chat Message", posted.name))
		self.assertFalse(frappe.db.exists("LMS Chat Read State", {"channel": channel}))

	def test_deleting_the_batch_takes_its_channels_with_it(self):
		"""Seeding a channel per batch made every batch undeletable: the channel
		Links to the batch, so frappe refused the delete outright."""
		batch = _batch("Chat Deletable Cohort", self.moderator)
		seed_default_channels(batch)
		channels = frappe.get_all("LMS Chat Channel", {"batch": batch}, pluck="name")
		self.assertTrue(channels)

		frappe.set_user("Administrator")
		frappe.delete_doc("LMS Batch", batch, ignore_permissions=True, force=True)

		for channel in channels:
			self.assertFalse(frappe.db.exists("LMS Chat Channel", channel))

	def test_removing_a_course_archives_rather_than_deletes(self):
		"""Dropping a course must not destroy the discussion that happened in it."""
		course = self._course("Chat Archive Course")
		doc = frappe.get_doc("LMS Batch", self.batch)
		doc.append("courses", {"course": course})
		doc.save(ignore_permissions=True)

		channel = frappe.db.get_value("LMS Chat Channel", {"batch": self.batch, "course": course}, "name")

		doc = frappe.get_doc("LMS Batch", self.batch)
		doc.courses = []
		doc.save(ignore_permissions=True)

		self.assertTrue(frappe.db.exists("LMS Chat Channel", channel))
		self.assertTrue(frappe.db.get_value("LMS Chat Channel", channel, "is_archived"))


class TestCrossBatchSidebar(ChatTestCase):
	mod_email = "chat-sidebar-mod@example.com"
	batch_title = "Chat Sidebar Cohort"

	def test_a_moderator_of_many_batches_gets_one_list(self):
		second = _batch("Chat Sidebar Second", self.moderator)
		seed_default_channels(second)
		frappe.set_user(self.moderator)

		listing = {row["batch"] for row in get_my_channels()}
		self.assertIn(self.batch, listing)
		self.assertIn(second, listing)

	def test_a_student_sees_only_their_own_batches(self):
		student = self._enrol("chat-sidebar-student@example.com")
		other = _batch("Chat Sidebar Other", self.moderator)
		seed_default_channels(other)

		frappe.set_user(student)
		listing = {row["batch"] for row in get_my_channels()}
		self.assertIn(self.batch, listing)
		self.assertNotIn(other, listing)


class TestRestDoor(ChatTestCase):
	"""The generic REST API is a second door onto the same rows.

	`lms.lms.chat` checks access on every call, but a DocPerm granting LMS Student
	`read` on the chat doctypes is honoured by /api/resource too, where none of
	those calls run. What keeps that door shut is the permission hooks in
	hooks.py, and this is the test that notices if they are ever unregistered.
	"""

	mod_email = "chat-restdoor-mod@example.com"
	batch_title = "Chat REST Door Cohort"

	def _other_batch_message(self):
		"""A message in a cohort the student has nothing to do with."""
		other = _batch("Chat REST Door Other", self.moderator)
		seed_default_channels(other)
		frappe.set_user(self.moderator)
		channel = general_channel(other)
		return channel, post_message(channel, "for the other cohort")["name"]

	def test_a_student_cannot_list_another_cohorts_channels(self):
		channel, _ = self._other_batch_message()
		student = self._enrol("chat-restdoor-student@example.com")

		frappe.set_user(student)
		self.assertNotIn(channel, frappe.get_list("LMS Chat Channel", pluck="name", limit_page_length=0))
		self.assertFalse(frappe.has_permission("LMS Chat Channel", "read", doc=channel))

	def test_a_student_cannot_list_another_cohorts_messages(self):
		_, message = self._other_batch_message()
		student = self._enrol("chat-restdoor-reader@example.com")

		frappe.set_user(student)
		self.assertNotIn(message, frappe.get_list("LMS Chat Message", pluck="name", limit_page_length=0))
		self.assertFalse(frappe.has_permission("LMS Chat Message", "read", doc=message))

	def test_a_student_cannot_edit_someone_elses_message(self):
		student = self._enrol("chat-restdoor-editor@example.com")
		other = self._enrol("chat-restdoor-author@example.com")

		frappe.set_user(other)
		channel = general_channel(self.batch)
		message = post_message(channel, "mine, not yours")["name"]

		frappe.set_user(student)
		self.assertTrue(frappe.has_permission("LMS Chat Message", "read", doc=message))
		self.assertFalse(frappe.has_permission("LMS Chat Message", "write", doc=message))
