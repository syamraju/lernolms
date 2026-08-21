# Copyright (c) 2026, FOSS United and Contributors
# See license.txt

"""Huddle roster, relay and access.

These test the parts a call cannot recover from on its own: a peer that is in
the roster but nobody offers to, a call that never ends because a laptop lid
closed, a signal forwarded to someone who is not in the room. Media itself is
the browsers' business and is not exercised here.
"""

import time
from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from lms.lms import huddle
from lms.lms.conversation import dm_id, parse
from lms.lms.test_helpers import BaseTestUtils


class TestConversationIds(UnitTestCase):
	def test_dm_id_sorts_so_both_ends_derive_the_same_thread(self):
		self.assertEqual(dm_id("b@x.com", "a@x.com"), dm_id("a@x.com", "b@x.com"))

	def test_dm_id_is_case_insensitive(self):
		self.assertEqual(dm_id("A@X.com", "b@x.com"), "dm:a@x.com|b@x.com")

	def test_dm_id_refuses_a_thread_with_yourself(self):
		with self.assertRaises(frappe.ValidationError):
			dm_id("a@x.com", "A@x.com")

	def test_parse_splits_on_the_first_colon_only(self):
		self.assertEqual(parse("batch:has:colon"), ("batch", "has:colon"))

	def test_parse_rejects_an_unknown_kind(self):
		with self.assertRaises(frappe.ValidationError):
			parse("email:someone@x.com")

	def test_parse_rejects_a_kind_with_no_key(self):
		with self.assertRaises(frappe.ValidationError):
			parse("batch:")


class TestEndedBody(UnitTestCase):
	def test_a_short_call_reports_seconds_only(self):
		self.assertEqual(huddle._ended_body(7), "Huddle ended (7s)")

	def test_a_longer_call_reports_minutes_and_seconds(self):
		self.assertEqual(huddle._ended_body(192), "Huddle ended (3m 12s)")

	def test_a_negative_duration_from_a_clock_skew_does_not_render_negative(self):
		self.assertEqual(huddle._ended_body(-5), "Huddle ended (0s)")


class HuddleTestCase(BaseTestUtils):
	"""A batch with two students in it, plus an outsider."""

	def setUp(self):
		super().setUp()
		self.alice = self._create_user("alice.huddle@example.com", "Alice", "H", ["LMS Student"]).name
		self.bob = self._create_user("bob.huddle@example.com", "Bob", "H", ["LMS Student"]).name
		self.mallory = self._create_user("mallory.huddle@example.com", "Mallory", "H", ["LMS Student"]).name

		evaluator = self._create_evaluator(self.alice)
		course = self._create_course(title="Huddle Course", instructor=self.alice)
		batch = self._create_batch(
			course.name, instructor=self.alice, title="Huddle Batch", evaluator=evaluator.name
		)
		self._create_batch_enrollment(self.alice, batch.name)
		self._create_batch_enrollment(self.bob, batch.name)

		self.batch = batch.name
		self.conversation = f"batch:{batch.name}"
		self.dm = dm_id(self.alice, self.bob)

		frappe.cache().delete_value(huddle._key(self.conversation))
		frappe.cache().delete_value(huddle._key(self.dm))
		frappe.set_user(self.alice)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.cache().delete_value(huddle._key(self.conversation))
		frappe.cache().delete_value(huddle._key(self.dm))
		super().tearDown()

	def as_user(self, user):
		frappe.set_user(user)


class TestHuddleAccess(HuddleTestCase):
	def test_a_batch_member_may_join(self):
		result = huddle.join(self.conversation, "peer-alice")
		self.assertEqual(len(result["huddle"]["participants"]), 1)

	def test_someone_outside_the_batch_may_not(self):
		self.as_user(self.mallory)
		with self.assertRaises(frappe.PermissionError):
			huddle.join(self.conversation, "peer-mallory")

	def test_a_dm_admits_only_its_two_named_people(self):
		self.as_user(self.mallory)
		with self.assertRaises(frappe.PermissionError):
			huddle.join(self.dm, "peer-mallory")

	def test_a_guest_is_asked_to_sign_in_rather_than_told_it_is_forbidden(self):
		self.as_user("Guest")
		with self.assertRaises(frappe.AuthenticationError):
			huddle.join(self.conversation, "peer-guest")


class TestHuddleRoster(HuddleTestCase):
	def test_the_first_joiner_starts_the_call(self):
		result = huddle.join(self.conversation, "peer-alice")
		self.assertEqual(result["huddle"]["started_by"], self.alice)
		self.assertEqual(result["self"]["peer_id"], "peer-alice")

	def test_the_second_joiner_lands_in_the_same_call(self):
		first = huddle.join(self.conversation, "peer-alice")
		self.as_user(self.bob)
		second = huddle.join(self.conversation, "peer-bob")

		self.assertEqual(first["huddle"]["id"], second["huddle"]["id"])
		self.assertEqual(len(second["huddle"]["participants"]), 2)

	def test_rejoining_from_a_new_tab_replaces_the_seat_rather_than_adding_one(self):
		huddle.join(self.conversation, "peer-tab-one")
		result = huddle.join(self.conversation, "peer-tab-two")

		self.assertEqual(len(result["huddle"]["participants"]), 1)
		self.assertEqual(result["huddle"]["participants"][0]["peer_id"], "peer-tab-two")

	def test_a_rejoin_keeps_the_original_join_time(self):
		first = huddle.join(self.conversation, "peer-tab-one")
		time.sleep(0.01)
		second = huddle.join(self.conversation, "peer-tab-two")

		self.assertEqual(
			first["huddle"]["participants"][0]["joined_at"],
			second["huddle"]["participants"][0]["joined_at"],
		)

	def test_a_full_call_refuses_the_next_person(self):
		with patch.object(huddle, "MAX_PARTICIPANTS", 1):
			huddle.join(self.conversation, "peer-alice")
			self.as_user(self.bob)
			with self.assertRaises(frappe.ValidationError):
				huddle.join(self.conversation, "peer-bob")

	def test_a_full_call_still_lets_someone_already_in_it_rejoin(self):
		# Otherwise a reload during a full call locks the person out of the call
		# they are already in.
		with patch.object(huddle, "MAX_PARTICIPANTS", 1):
			huddle.join(self.conversation, "peer-tab-one")
			result = huddle.join(self.conversation, "peer-tab-two")

		self.assertEqual(result["huddle"]["participants"][0]["peer_id"], "peer-tab-two")

	def test_leaving_frees_the_seat(self):
		huddle.join(self.conversation, "peer-alice")
		self.as_user(self.bob)
		huddle.join(self.conversation, "peer-bob")

		result = huddle.leave(self.conversation, "peer-bob")
		self.assertEqual([p["user"] for p in result["huddle"]["participants"]], [self.alice])

	def test_the_last_person_out_ends_the_call(self):
		huddle.join(self.conversation, "peer-alice")
		self.assertIsNone(huddle.leave(self.conversation, "peer-alice")["huddle"])
		self.assertIsNone(huddle._read(self.conversation))

	def test_a_stale_tabs_leave_does_not_evict_the_tab_that_replaced_it(self):
		huddle.join(self.conversation, "peer-tab-one")
		huddle.join(self.conversation, "peer-tab-two")

		result = huddle.leave(self.conversation, "peer-tab-one")
		self.assertEqual(result["huddle"]["participants"][0]["peer_id"], "peer-tab-two")

	def test_leaving_a_call_that_is_already_over_is_not_an_error(self):
		self.assertIsNone(huddle.leave(self.conversation, "peer-alice")["huddle"])


class TestHuddleHeartbeat(HuddleTestCase):
	def test_a_heartbeat_keeps_the_seat(self):
		huddle.join(self.conversation, "peer-alice")
		result = huddle.heartbeat(self.conversation, "peer-alice")
		self.assertEqual(len(result["huddle"]["participants"]), 1)

	def test_a_peer_that_stopped_beating_is_pruned(self):
		# The closed-lid case: no leave is ever sent, so without the prune the
		# thread shows "Join" into a room with a ghost in it, forever.
		huddle.join(self.conversation, "peer-alice")
		self.as_user(self.bob)
		huddle.join(self.conversation, "peer-bob")

		stale = huddle._read(self.conversation)
		stale["participants"][self.alice]["seen_at"] -= huddle.PEER_TTL + 5
		huddle._write(self.conversation, stale)

		result = huddle.heartbeat(self.conversation, "peer-bob")
		self.assertEqual([p["user"] for p in result["huddle"]["participants"]], [self.bob])

	def test_the_last_peer_lapsing_ends_the_call(self):
		huddle.join(self.conversation, "peer-alice")
		stale = huddle._read(self.conversation)
		stale["participants"][self.alice]["seen_at"] -= huddle.PEER_TTL + 5
		huddle._write(self.conversation, stale)

		self.assertIsNone(huddle.heartbeat(self.conversation, "peer-alice")["huddle"])
		self.assertIsNone(huddle._read(self.conversation))

	def test_a_superseded_tab_is_told_it_was_evicted_rather_than_stealing_the_seat_back(self):
		huddle.join(self.conversation, "peer-tab-one")
		huddle.join(self.conversation, "peer-tab-two")

		result = huddle.heartbeat(self.conversation, "peer-tab-one")
		self.assertTrue(result["evicted"])
		self.assertEqual(result["huddle"]["participants"][0]["peer_id"], "peer-tab-two")


class TestHuddleSignal(HuddleTestCase):
	def setUp(self):
		super().setUp()
		huddle.join(self.conversation, "peer-alice")
		self.as_user(self.bob)
		huddle.join(self.conversation, "peer-bob")
		self.as_user(self.alice)

	def test_an_offer_reaches_the_named_peer(self):
		with patch("frappe.publish_realtime") as publish:
			result = huddle.signal(self.conversation, self.bob, "peer-bob", "offer", {"sdp": "v=0"})

		self.assertTrue(result["delivered"])
		published = publish.call_args
		self.assertEqual(published.args[0], huddle.EVENT_SIGNAL)
		self.assertEqual(published.kwargs["user"], self.bob)

	def test_the_payload_is_forwarded_verbatim(self):
		# An SDP the server rewrites is an SDP that breaks a codec the server
		# has never heard of.
		payload = {"sdp": "v=0\r\na=weird-future-attribute:1\r\n"}
		with patch("frappe.publish_realtime") as publish:
			huddle.signal(self.conversation, self.bob, "peer-bob", "offer", payload)

		self.assertEqual(publish.call_args.args[1]["payload"], payload)

	def test_a_json_encoded_payload_from_the_http_layer_is_decoded(self):
		with patch("frappe.publish_realtime") as publish:
			huddle.signal(self.conversation, self.bob, "peer-bob", "ice", '{"candidate": "x"}')

		self.assertEqual(publish.call_args.args[1]["payload"], {"candidate": "x"})

	def test_an_unknown_signal_kind_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			huddle.signal(self.conversation, self.bob, "peer-bob", "chat", {})

	def test_a_frame_for_a_peer_that_has_reloaded_is_dropped_not_misdelivered(self):
		self.as_user(self.bob)
		huddle.join(self.conversation, "peer-bob-reloaded")
		self.as_user(self.alice)

		with patch("frappe.publish_realtime") as publish:
			result = huddle.signal(self.conversation, self.bob, "peer-bob", "offer", {"sdp": "v=0"})

		self.assertFalse(result["delivered"])
		publish.assert_not_called()

	def test_someone_not_in_the_call_cannot_use_it_as_a_relay(self):
		huddle.leave(self.conversation, "peer-alice")
		with self.assertRaises(frappe.PermissionError):
			huddle.signal(self.conversation, self.bob, "peer-bob", "offer", {"sdp": "v=0"})


class TestHuddleFlags(HuddleTestCase):
	def test_a_mute_is_recorded_so_late_joiners_render_it(self):
		huddle.join(self.conversation, "peer-alice")
		result = huddle.set_flags(self.conversation, "peer-alice", muted=1)
		self.assertTrue(result["huddle"]["participants"][0]["muted"])

	def test_flags_left_unset_are_not_disturbed(self):
		huddle.join(self.conversation, "peer-alice", video=1)
		huddle.set_flags(self.conversation, "peer-alice", muted=1)
		result = huddle.set_flags(self.conversation, "peer-alice", screensharing=1)

		participant = result["huddle"]["participants"][0]
		self.assertTrue(participant["muted"])
		self.assertTrue(participant["video"])
		self.assertTrue(participant["screensharing"])

	def test_a_stale_tab_cannot_toggle_the_live_tabs_microphone(self):
		huddle.join(self.conversation, "peer-tab-one")
		huddle.join(self.conversation, "peer-tab-two")

		result = huddle.set_flags(self.conversation, "peer-tab-one", muted=1)
		self.assertFalse(result["huddle"]["participants"][0]["muted"])


class TestHuddleBadges(HuddleTestCase):
	def test_get_active_reports_a_live_call(self):
		huddle.join(self.conversation, "peer-alice")
		active = huddle.get_active([self.conversation])
		self.assertEqual(active[self.conversation]["participant_count"], 1)

	def test_get_active_omits_a_thread_with_no_call(self):
		self.assertEqual(huddle.get_active([self.conversation]), {})

	def test_get_active_skips_threads_the_caller_cannot_see_instead_of_failing(self):
		# One unreadable id in a sidebar of twenty must not blank the other
		# nineteen badges.
		huddle.join(self.conversation, "peer-alice")
		self.as_user(self.bob)
		active = huddle.get_active([self.conversation, "dm:someone@else.com|third@party.com"])

		self.assertIn(self.conversation, active)
		self.assertEqual(len(active), 1)

	def test_get_active_accepts_the_json_string_the_http_layer_sends(self):
		huddle.join(self.conversation, "peer-alice")
		active = huddle.get_active(frappe.as_json([self.conversation]))
		self.assertIn(self.conversation, active)


class TestHuddleRing(HuddleTestCase):
	def test_ringing_reaches_the_other_person_and_not_the_caller(self):
		huddle.join(self.dm, "peer-alice")
		with patch("frappe.publish_realtime") as publish:
			result = huddle.ring(self.dm)

		self.assertEqual(result["rang"], [self.bob])
		self.assertEqual(publish.call_args.kwargs["user"], self.bob)

	def test_ringing_cannot_page_someone_outside_the_conversation(self):
		huddle.join(self.dm, "peer-alice")
		result = huddle.ring(self.dm, [self.mallory])
		self.assertEqual(result["rang"], [])
