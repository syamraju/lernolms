# Copyright (c) 2026, Frappe and Contributors
# For license information, please see license.txt

"""The four doors into a batch, and what happens to a provisioned account.

Named by situation rather than by function: these are use cases from
``docs/design/batches.md`` §5–§7, and a refactor that keeps the functions but
breaks the situations has broken the feature.
"""

import frappe
from frappe.tests.utils import FrappeTestCase

from lms.lms import batch_invite
from lms.lms.batch_invite import (
	create_invite_link,
	join_with_link,
	preview_invitations,
	reissue_password,
	revoke_invite_link,
	send_invitations,
)
from lms.lms.test_batch_access import _batch, _user


class InviteTestCase(FrappeTestCase):
	"""Shared fixture: one moderator with one batch, and no mail going out."""

	def setUp(self):
		self.moderator = _user(self.mod_email, ["Moderator"])
		self.batch = _batch(self.batch_title, self.moderator)
		frappe.set_user(self.moderator)
		# frappe.sendmail would need an outgoing account; the assertions are about
		# enrollment and credentials, and the templates are exercised separately.
		self._sent = []
		self._real_sendmail = frappe.sendmail
		frappe.sendmail = lambda **kwargs: self._sent.append(kwargs)

		# The writers refuse up front on a site with no outgoing account, which a
		# test site does not have. Stubbed here so the enrollment assertions still
		# run; the guard itself is covered by TestMailIsAPrecondition.
		self._real_mail_check = batch_invite.outgoing_mail_configured
		batch_invite.outgoing_mail_configured = lambda: True

	def tearDown(self):
		frappe.sendmail = self._real_sendmail
		batch_invite.outgoing_mail_configured = self._real_mail_check
		frappe.set_user("Administrator")

	def _cleanup_user(self, email):
		if frappe.db.exists("User", email):
			frappe.delete_doc("User", email, force=True, ignore_permissions=True)


class TestPreviewIsADryRun(InviteTestCase):
	mod_email = "invite-preview-mod@example.com"
	batch_title = "Preview Cohort"

	def test_preview_creates_no_account(self):
		"""The whole reason preview is a separate call: a typo'd paste must not
		create accounts before anyone has seen what it would do."""
		fresh = "invite-preview-fresh@example.com"
		self._cleanup_user(fresh)

		result = preview_invitations(self.batch, [fresh])

		self.assertEqual(result["counts"]["new"], 1)
		self.assertFalse(frappe.db.exists("User", fresh))
		self.assertFalse(frappe.db.exists("LMS Batch Enrollment", {"batch": self.batch}))

	def test_preview_classifies_every_address(self):
		existing = _user("invite-preview-existing@example.com", ["LMS Student"])
		fresh = "invite-preview-new@example.com"
		self._cleanup_user(fresh)
		frappe.set_user(self.moderator)

		result = preview_invitations(self.batch, [existing, fresh, "not-an-email"])
		verdicts = {row["email"]: row["verdict"] for row in result["rows"]}

		self.assertEqual(verdicts[existing], "existing")
		self.assertEqual(verdicts[fresh], "new")
		self.assertEqual(verdicts["not-an-email"], "invalid")

	def test_already_enrolled_is_reported_not_repeated(self):
		student = _user("invite-preview-enrolled@example.com", ["LMS Student"])
		frappe.set_user(self.moderator)
		frappe.get_doc({"doctype": "LMS Batch Enrollment", "batch": self.batch, "member": student}).insert(
			ignore_permissions=True
		)

		result = preview_invitations(self.batch, [student])
		self.assertEqual(result["counts"]["already_enrolled"], 1)

	def test_seats_are_counted_against_the_running_total(self):
		"""A paste of three addresses into a one-seat batch reports one
		enrolment and two refusals, not three enrolments."""
		frappe.db.set_value("LMS Batch", self.batch, "seat_count", 1)
		result = preview_invitations(
			self.batch,
			["seat-a@example.com", "seat-b@example.com", "seat-c@example.com"],
		)
		self.assertEqual(result["counts"]["new"], 1)
		self.assertEqual(result["counts"]["no_seats"], 2)
		frappe.db.set_value("LMS Batch", self.batch, "seat_count", 0)

	def test_a_moderator_of_another_batch_is_refused(self):
		outsider = _user("invite-preview-outsider@example.com", ["Moderator"])
		frappe.set_user(outsider)
		with self.assertRaises(frappe.PermissionError):
			preview_invitations(self.batch, ["whoever@example.com"])


class TestInvitingProvisionsAccounts(InviteTestCase):
	mod_email = "invite-send-mod@example.com"
	batch_title = "Send Cohort"

	def test_a_new_address_gets_an_account_a_password_and_a_seat(self):
		fresh = "invite-send-fresh@example.com"
		self._cleanup_user(fresh)
		frappe.set_user(self.moderator)

		result = send_invitations(self.batch, [fresh])

		self.assertEqual(result["results"][0]["status"], "created")
		self.assertTrue(frappe.db.exists("User", fresh))
		self.assertTrue(frappe.db.exists("LMS Batch Enrollment", {"batch": self.batch, "member": fresh}))
		self.assertTrue(frappe.db.get_value("User", fresh, "must_reset_password"))

	def test_the_temporary_password_goes_only_to_the_student(self):
		"""It is mailed and nowhere else — not in the return value, which is what
		the moderator's browser receives."""
		fresh = "invite-send-secret@example.com"
		self._cleanup_user(fresh)
		frappe.set_user(self.moderator)

		result = send_invitations(self.batch, [fresh])

		self.assertNotIn("temp_password", str(result))
		mail = [m for m in self._sent if m.get("recipients") == fresh][0]
		self.assertEqual(mail["template"], "batch_invitation_new_account")
		self.assertTrue(mail["args"]["temp_password"])

	def test_an_existing_user_is_enrolled_without_a_new_password(self):
		existing = _user("invite-send-existing@example.com", ["LMS Student"])
		frappe.set_user(self.moderator)

		result = send_invitations(self.batch, [existing])

		self.assertEqual(result["results"][0]["status"], "enrolled")
		self.assertFalse(frappe.db.get_value("User", existing, "must_reset_password"))
		mail = [m for m in self._sent if m.get("recipients") == existing][0]
		self.assertEqual(mail["template"], "batch_invitation")

	def test_one_bad_address_does_not_sink_the_good_ones(self):
		good = "invite-send-good@example.com"
		self._cleanup_user(good)
		frappe.set_user(self.moderator)

		result = send_invitations(self.batch, ["not-an-email", good])
		statuses = {row["email"]: row["status"] for row in result["results"]}

		self.assertEqual(statuses["not-an-email"], "invalid")
		self.assertEqual(statuses[good], "created")


class TestPasswordReissue(InviteTestCase):
	mod_email = "reissue-mod@example.com"
	batch_title = "Reissue Cohort"

	def _enrolled(self, email, roles):
		user = _user(email, roles)
		frappe.set_user(self.moderator)
		frappe.get_doc({"doctype": "LMS Batch Enrollment", "batch": self.batch, "member": user}).insert(
			ignore_permissions=True
		)
		return user

	def test_a_student_can_be_reset_and_is_forced_to_choose(self):
		student = self._enrolled("reissue-student@example.com", ["LMS Student"])
		reissue_password(self.batch, student)
		self.assertTrue(frappe.db.get_value("User", student, "must_reset_password"))

	def test_the_moderator_never_receives_the_password(self):
		student = self._enrolled("reissue-quiet@example.com", ["LMS Student"])
		returned = reissue_password(self.batch, student)
		self.assertIsNone(returned)
		mail = [m for m in self._sent if m.get("recipients") == student][0]
		self.assertTrue(mail["args"]["temp_password"])

	def test_a_target_holding_staff_roles_is_refused(self):
		"""The load-bearing check. Without it this endpoint is a path from
		moderator to System Manager."""
		staff = self._enrolled("reissue-staff@example.com", ["LMS Student", "Course Creator"])
		with self.assertRaises(frappe.PermissionError):
			reissue_password(self.batch, staff)
		self.assertFalse(frappe.db.get_value("User", staff, "must_reset_password"))

	def test_a_moderator_target_is_refused(self):
		other_mod = self._enrolled("reissue-mod-target@example.com", ["LMS Student", "Moderator"])
		with self.assertRaises(frappe.PermissionError):
			reissue_password(self.batch, other_mod)

	def test_a_student_of_another_batch_is_refused(self):
		stranger = _user("reissue-stranger@example.com", ["LMS Student"])
		frappe.set_user(self.moderator)
		with self.assertRaises(frappe.PermissionError):
			reissue_password(self.batch, stranger)

	def test_the_reset_is_audited(self):
		student = self._enrolled("reissue-audited@example.com", ["LMS Student"])
		reissue_password(self.batch, student)
		self.assertTrue(
			frappe.db.exists(
				"Comment",
				{"reference_doctype": "User", "reference_name": student, "comment_type": "Info"},
			)
		)


class TestInviteLinks(InviteTestCase):
	mod_email = "link-mod@example.com"
	batch_title = "Link Cohort"

	def test_the_raw_token_is_never_stored(self):
		"""A leaked table must yield no working links."""
		link = create_invite_link(self.batch)
		token = link["url"].rsplit("/", 1)[-1]
		self.assertFalse(frappe.db.exists("LMS Batch Invite Link", {"key_hash": token}))
		self.assertTrue(
			frappe.db.exists("LMS Batch Invite Link", {"key_hash": batch_invite._hash_token(token)})
		)

	def test_a_link_enrolls_a_closed_batch_without_opening_it(self):
		"""The batch does not have to stand open to self-enrollment for its links
		to work — `allow_self_enrollment` opens it to the entire internet."""
		self.assertFalse(frappe.db.get_value("LMS Batch", self.batch, "allow_self_enrollment"))
		link = create_invite_link(self.batch)
		token = link["url"].rsplit("/", 1)[-1]

		joiner = _user("link-joiner@example.com", ["LMS Student"])
		frappe.set_user(joiner)
		result = join_with_link(token)

		self.assertEqual(result["batch"], self.batch)
		self.assertTrue(frappe.db.exists("LMS Batch Enrollment", {"batch": self.batch, "member": joiner}))

	def test_without_a_link_a_closed_batch_refuses(self):
		joiner = _user("link-refused@example.com", ["LMS Student"])
		frappe.set_user(joiner)
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc({"doctype": "LMS Batch Enrollment", "batch": self.batch, "member": joiner}).insert(
				ignore_permissions=True
			)

	def test_a_revoked_link_stops_working(self):
		link = create_invite_link(self.batch)
		token = link["url"].rsplit("/", 1)[-1]
		revoke_invite_link(link["name"])

		joiner = _user("link-revoked@example.com", ["LMS Student"])
		frappe.set_user(joiner)
		with self.assertRaises(frappe.ValidationError):
			join_with_link(token)

	def test_a_spent_link_stops_working(self):
		"""The use cap is what keeps a link posted in a community group from
		being a seat leak."""
		link = create_invite_link(self.batch, max_uses=1)
		token = link["url"].rsplit("/", 1)[-1]

		first = _user("link-first@example.com", ["LMS Student"])
		frappe.set_user(first)
		join_with_link(token)

		second = _user("link-second@example.com", ["LMS Student"])
		frappe.set_user(second)
		with self.assertRaises(frappe.ValidationError):
			join_with_link(token)

	def test_an_expired_link_stops_working(self):
		link = create_invite_link(self.batch)
		token = link["url"].rsplit("/", 1)[-1]
		frappe.db.set_value("LMS Batch Invite Link", link["name"], "expires_on", "2020-01-01 00:00:00")

		joiner = _user("link-expired@example.com", ["LMS Student"])
		frappe.set_user(joiner)
		with self.assertRaises(frappe.ValidationError):
			join_with_link(token)

	def test_a_garbage_token_enrolls_nobody(self):
		joiner = _user("link-garbage@example.com", ["LMS Student"])
		frappe.set_user(joiner)
		with self.assertRaises(frappe.ValidationError):
			join_with_link("not-a-real-token")

	def test_only_a_moderator_of_the_batch_can_mint_one(self):
		outsider = _user("link-outsider@example.com", ["Moderator"])
		frappe.set_user(outsider)
		with self.assertRaises(frappe.PermissionError):
			create_invite_link(self.batch)


class TestMailIsAPrecondition(InviteTestCase):
	"""An invitation is a message. If the site cannot send one, there is no
	invitation — and for a provisioned account the temporary password exists
	only in that message."""

	mod_email = "invite-mail-mod@example.com"
	batch_title = "Mail Cohort"

	def _unconfigured(self):
		batch_invite.outgoing_mail_configured = lambda: False

	def test_inviting_is_refused_once_not_per_address(self):
		"""Fifty addresses against an unconfigured site is one missing setting,
		not fifty bad addresses."""
		self._unconfigured()
		with self.assertRaises(frappe.ValidationError):
			send_invitations(self.batch, ["a@example.com", "b@example.com"])

	def test_nothing_is_written_when_mail_is_unconfigured(self):
		self._unconfigured()
		fresh = "invite-mail-fresh@example.com"
		self._cleanup_user(fresh)
		frappe.set_user(self.moderator)

		with self.assertRaises(frappe.ValidationError):
			send_invitations(self.batch, [fresh])
		self.assertFalse(frappe.db.exists("User", fresh))

	def test_reissuing_a_password_is_refused_too(self):
		student = _user("invite-mail-student@example.com", ["LMS Student"])
		frappe.set_user(self.moderator)
		frappe.get_doc({"doctype": "LMS Batch Enrollment", "batch": self.batch, "member": student}).insert(
			ignore_permissions=True
		)

		self._unconfigured()
		with self.assertRaises(frappe.ValidationError):
			reissue_password(self.batch, student)
		self.assertFalse(frappe.db.get_value("User", student, "must_reset_password"))

	def test_preview_describes_rather_than_refuses(self):
		"""A dry run must still answer. Throwing at the person who clicked
		Preview tells them nothing about the addresses they pasted."""
		self._unconfigured()
		result = preview_invitations(self.batch, ["a@example.com"])

		self.assertFalse(result["mail_configured"])
		self.assertEqual(result["counts"]["new"], 1)

	def test_an_outsider_is_refused_for_who_they_are(self):
		"""Permission before configuration: a stranger should not learn this
		site's mail settings from the error they get."""
		self._unconfigured()
		outsider = _user("invite-mail-outsider@example.com", ["Moderator"])
		frappe.set_user(outsider)

		with self.assertRaises(frappe.PermissionError):
			send_invitations(self.batch, ["a@example.com"])


class TestOneBadAddressCostsOneAddress(InviteTestCase):
	mod_email = "invite-savepoint-mod@example.com"
	batch_title = "Savepoint Cohort"

	def test_a_failure_does_not_unwind_the_caller(self):
		"""The failure path unwinds to a savepoint, not to the start of the
		transaction. A bare rollback here discarded everything uncommitted —
		including the batch the caller had just created."""
		marker = frappe.get_doc(
			{"doctype": "LMS Batch Enrollment", "batch": self.batch, "member": self.moderator}
		).insert(ignore_permissions=True)

		def explode(*args, **kwargs):
			raise RuntimeError("delivery exploded")

		frappe.sendmail = explode
		fresh = "invite-savepoint-fresh@example.com"
		self._cleanup_user(fresh)
		frappe.set_user(self.moderator)

		result = send_invitations(self.batch, [fresh])

		self.assertEqual(result["results"][0]["status"], "failed")
		# The failed address left nothing behind...
		self.assertFalse(frappe.db.exists("User", fresh))
		# ...and the caller's own uncommitted work survived.
		self.assertTrue(frappe.db.exists("LMS Batch Enrollment", marker.name))
