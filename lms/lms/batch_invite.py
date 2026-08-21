# Copyright (c) 2026, Frappe and Contributors
# For license information, please see license.txt

"""Getting people into a batch, and getting them signed in once they are.

Four doors, all ending at one row (``LMS Batch Enrollment``), because that
controller owns the rules that matter — duplicates, seats, payment and
self-enrollment, under a row lock. Nothing here inserts around it.

  1. a moderator adds an existing user      (``send_invitations``, `existing`)
  2. a moderator invites by email           (``send_invitations``, `new`)
  3. somebody redeems an invite link        (``join_with_link``)
  4. paid self-enrollment                   (unchanged, in lms.lms.utils)

Doors 1 and 2 never write on the first call. ``preview_invitations`` answers
"what will this do?" without doing it, because **"will this create accounts?" is
a question the moderator has to be able to answer before it happens**, not
after — and the answer is what the confirmation dialog renders.
"""

from __future__ import annotations

import hashlib

import frappe
from frappe import _
from frappe.utils import add_days, cint, get_url, now_datetime, validate_email_address

from lms.lms.batch_access import assert_batch_moderator, is_batch_moderator
from lms.lms.utils import create_user

#: Above this many addresses one request would outlive the HTTP timeout, so the
#: work goes to a worker and the dialog reports what was queued.
ENQUEUE_THRESHOLD = 25

#: A hard cap on one submission. Not a performance limit — a paste of ten
#: thousand addresses is a mistake, and silently accepting it mails ten thousand
#: people.
MAX_ADDRESSES = 500

TEMP_PASSWORD_LENGTH = 12

VERDICTS = ("existing", "new", "already_enrolled", "invalid", "no_seats")


# --- helpers ----------------------------------------------------------------


def _clean(emails: list[str] | str) -> list[str]:
	"""Split a pasted blob into addresses, preserving order and dropping repeats."""
	if isinstance(emails, str):
		emails = emails.replace(",", "\n").replace(";", "\n").split("\n")
	seen, out = set(), []
	for raw in emails or []:
		email = (raw or "").strip().lower()
		if not email or email in seen:
			continue
		seen.add(email)
		out.append(email)
	return out


def _is_email(email: str) -> bool:
	try:
		validate_email_address(email, throw=True)
		return True
	except Exception:
		return False


def _seats_left(batch: str) -> int | None:
	"""Remaining seats, or None when the batch is uncapped."""
	seat_count = cint(frappe.db.get_value("LMS Batch", batch, "seat_count"))
	if not seat_count:
		return None
	return max(0, seat_count - frappe.db.count("LMS Batch Enrollment", {"batch": batch}))


def outgoing_mail_configured() -> bool:
	"""Whether this site can actually send an email.

	An invitation is a message; if it cannot be delivered there is no invitation,
	and for a provisioned account the temporary password exists only in that
	message. Checked up front rather than discovered per address: without this,
	an unconfigured site reports fifty individual failures carrying Frappe's
	generic "Please setup default outgoing Email Account", which reads as fifty
	bad addresses rather than one missing setting.
	"""
	if frappe.conf.get("mail_login") or frappe.conf.get("mail_server"):
		return True
	return bool(frappe.db.exists("Email Account", {"default_outgoing": 1, "enable_outgoing": 1}))


def assert_can_send_mail() -> None:
	if outgoing_mail_configured():
		return
	frappe.throw(
		_(
			"This site has no outgoing email account, so invitations cannot be "
			"delivered. Set a default outgoing account up in Email Account first."
		)
	)


def _batch_title(batch: str) -> str:
	return frappe.db.get_value("LMS Batch", batch, "title") or batch


# --- door 1 + 2: preview, then send -----------------------------------------


@frappe.whitelist()
def preview_invitations(batch: str, emails: list[str] | str) -> dict:
	"""What ``send_invitations`` would do. Writes nothing.

	Deliberately a separate round trip rather than a dry-run flag on the writer:
	a flag that is easy to forget is a flag that eventually gets forgotten, and
	the failure mode is silently creating accounts for a typo'd paste.
	"""
	assert_batch_moderator(batch)
	# No mail check here on purpose: a dry run describes, it does not refuse. An
	# unconfigured site comes back as `mail_configured: false` so the dialog can
	# say "nothing would be delivered" instead of throwing at the person who
	# clicked Preview.

	addresses = _clean(emails)
	if len(addresses) > MAX_ADDRESSES:
		frappe.throw(
			_("{0} addresses at once is more than this form accepts (limit {1}).").format(
				len(addresses), MAX_ADDRESSES
			)
		)

	seats = _seats_left(batch)
	would_enroll = 0
	rows = []

	for email in addresses:
		if not _is_email(email):
			rows.append({"email": email, "verdict": "invalid"})
			continue

		exists = frappe.db.exists("User", email)
		if exists and frappe.db.exists("LMS Batch Enrollment", {"batch": batch, "member": email}):
			rows.append({"email": email, "verdict": "already_enrolled"})
			continue

		# Seats are counted against the running total, not the starting one: a
		# paste of forty addresses into a batch with three seats must not report
		# forty enrolments.
		if seats is not None and would_enroll >= seats:
			rows.append({"email": email, "verdict": "no_seats"})
			continue

		would_enroll += 1
		rows.append(
			{
				"email": email,
				"verdict": "existing" if exists else "new",
				"full_name": frappe.db.get_value("User", email, "full_name") if exists else None,
			}
		)

	counts = {verdict: 0 for verdict in VERDICTS}
	for row in rows:
		counts[row["verdict"]] += 1

	return {
		"batch": batch,
		"batch_title": _batch_title(batch),
		"mail_configured": outgoing_mail_configured(),
		"rows": rows,
		"counts": counts,
		"seats_left": seats,
		"will_enqueue": len(addresses) > ENQUEUE_THRESHOLD,
	}


@frappe.whitelist()
def send_invitations(batch: str, emails: list[str] | str) -> dict:
	"""Enroll and notify. Returns a per-address result.

	Per-address rather than a single success flag: a blanket toast over a batch
	operation that half-worked is worse than no toast at all, because it reports
	success for the people who were not actually invited.
	"""
	assert_batch_moderator(batch)
	# Refused up front, not per address: see outgoing_mail_configured().
	assert_can_send_mail()

	addresses = _clean(emails)
	if len(addresses) > MAX_ADDRESSES:
		frappe.throw(
			_("{0} addresses at once is more than this form accepts (limit {1}).").format(
				len(addresses), MAX_ADDRESSES
			)
		)

	if len(addresses) > ENQUEUE_THRESHOLD:
		frappe.enqueue(
			"lms.lms.batch_invite.invite_many",
			queue="long",
			batch=batch,
			addresses=addresses,
			actor=frappe.session.user,
		)
		return {"queued": True, "count": len(addresses), "results": []}

	return {"queued": False, "count": len(addresses), "results": invite_many(batch, addresses)}


def invite_many(batch: str, addresses: list[str], actor: str | None = None) -> list[dict]:
	"""The worker body. Each address succeeds or fails on its own.

	One bad address must not roll back the twenty good ones before it — a partial
	invite that reports honestly beats an all-or-nothing that a single typo
	undoes.

	The failure path unwinds to a **savepoint**, not to the start of the
	transaction. A bare ``frappe.db.rollback()`` here discards everything
	uncommitted, including work the caller did before calling this — when the
	enqueued path runs in its own job that is invisible, but called inline it
	silently undoes the caller's changes. One address failing should cost exactly
	that one address.
	"""
	if actor:
		frappe.set_user(actor)

	results = []
	for index, email in enumerate(addresses):
		# Named per address: savepoint names are identifiers, not values, so they
		# cannot be parameterised and must not be built from the address itself.
		point = f"lms_invite_{index}"
		frappe.db.savepoint(point)
		try:
			results.append(invite_one(batch, email))
			frappe.db.commit()
		except Exception as e:
			frappe.db.rollback(save_point=point)
			frappe.log_error(
				title="LMS batch invitation failed",
				message=f"batch={batch} email={email}\n{frappe.get_traceback()}",
			)
			results.append({"email": email, "status": "failed", "error": str(e)})
	return results


def invite_one(batch: str, email: str) -> dict:
	"""Enroll one address, creating the account if there is not one yet."""
	if not _is_email(email):
		return {"email": email, "status": "invalid"}

	if frappe.db.exists("LMS Batch Enrollment", {"batch": batch, "member": email}):
		return {"email": email, "status": "already_enrolled"}

	created = False
	temp_password = None
	if not frappe.db.exists("User", email):
		create_user(email=email, roles=["LMS Student"])
		temp_password = provision_temporary_password(email)
		created = True

	frappe.get_doc(
		{
			"doctype": "LMS Batch Enrollment",
			"batch": batch,
			"member": email,
		}
	).insert(ignore_permissions=True)

	send_invitation_email(batch, email, temp_password)
	return {"email": email, "status": "created" if created else "enrolled"}


# --- provisioning -----------------------------------------------------------


def provision_temporary_password(email: str) -> str:
	"""Give ``email`` a temporary password and require them to replace it.

	``update_password`` rather than ``doc.new_password``: the latter runs the
	site's password policy, which will reject a generated string on a strict site
	— the same trap lms/lms/dev_fixtures.py already documents.

	The returned value goes into exactly one place, the invitation email. It is
	never returned by a whitelisted method, never logged, and never shown to the
	moderator who triggered it.
	"""
	from frappe.utils.password import update_password

	temp_password = frappe.generate_hash(length=TEMP_PASSWORD_LENGTH)
	# Existing sessions are dropped. On a re-issue the point is that the old
	# password is gone; leaving a live session behind would let whoever is holding
	# it carry on, and would also mean the "choose a new password" gate is only
	# reached whenever they next happen to sign in.
	update_password(email, temp_password, logout_all_sessions=True)
	frappe.db.set_value("User", email, "must_reset_password", 1)
	return temp_password


def send_invitation_email(batch: str, email: str, temp_password: str | None) -> None:
	batch_row = frappe.db.get_value(
		"LMS Batch", batch, ["title", "start_date", "start_time", "medium"], as_dict=True
	)
	args = {
		"title": batch_row.title,
		"start_date": batch_row.start_date,
		"start_time": batch_row.start_time,
		"medium": batch_row.medium,
		"batch_url": get_url(f"/lms/batches/{batch}"),
		"login_url": get_url("/login"),
		"email": email,
		"temp_password": temp_password,
	}

	frappe.sendmail(
		recipients=email,
		subject=_("You have been added to {0}").format(batch_row.title),
		template="batch_invitation_new_account" if temp_password else "batch_invitation",
		args=args,
		header=[_("Batch Invitation"), "green"],
		retry=3,
	)


@frappe.whitelist()
def reissue_password(batch: str, user: str) -> None:
	"""Re-issue a temporary password for a stuck student. Returns nothing.

	The moderator triggers this and never learns a credential — the password goes
	to the student's mailbox and nowhere else.

	The role check is the load-bearing part. Without "the target holds no role but
	LMS Student", this endpoint is a path from moderator to System Manager, and
	the fact that the moderator does not see the password does not help: they
	control what happens next in that mailbox only until the account they reset
	happens to be an admin's.
	"""
	# Permission first: an outsider should be refused for who they are, not told
	# about this site's mail configuration.
	assert_batch_moderator(batch)
	assert_can_send_mail()

	if not frappe.db.exists("User", user):
		frappe.throw(_("User {0} does not exist.").format(user), frappe.DoesNotExistError)

	if not frappe.db.exists("LMS Batch Enrollment", {"batch": batch, "member": user}):
		frappe.throw(_("{0} is not a student in this batch.").format(user), frappe.PermissionError)

	roles = set(frappe.get_roles(user)) - {"All", "Guest", "Desk User"}
	if roles - {"LMS Student"}:
		frappe.throw(
			_(
				"{0} holds roles beyond Student, so their password cannot be reset from a batch. Ask a System Manager."
			).format(user),
			frappe.PermissionError,
		)

	temp_password = provision_temporary_password(user)
	send_reissue_email(user, temp_password)

	# Audited because a credential change that leaves no trace is not reviewable.
	# Version does not capture this — passwords are not tracked fields.
	frappe.get_doc(
		{
			"doctype": "Comment",
			"comment_type": "Info",
			"reference_doctype": "User",
			"reference_name": user,
			"content": _("Temporary password re-issued by {0} from batch {1}.").format(
				frappe.session.user, batch
			),
		}
	).insert(ignore_permissions=True)
	frappe.logger("lms.credentials").info(
		{"event": "reissue_password", "target": user, "actor": frappe.session.user, "batch": batch}
	)


def send_reissue_email(email: str, temp_password: str) -> None:
	frappe.sendmail(
		recipients=email,
		subject=_("A temporary password for your account"),
		template="temporary_password",
		args={
			"email": email,
			"temp_password": temp_password,
			"login_url": get_url("/login"),
		},
		header=[_("Temporary Password"), "orange"],
		retry=3,
	)


# --- door 3: invite links ---------------------------------------------------


def _hash_token(token: str) -> str:
	return hashlib.sha256(token.encode("utf-8")).hexdigest()


@frappe.whitelist()
def create_invite_link(
	batch: str,
	expires_in_days: int = 30,
	max_uses: int = 100,
) -> dict:
	"""Mint a join link. The raw token is returned once and never stored.

	Only the SHA-256 lands in the database, so a leaked table yields no working
	links. The caller has one chance to copy it — same contract as an API key.

	Expiry and a use cap are not optional. This link is meant to be pasted into a
	group chat, where it will be forwarded past the audience it was written for
	and outlive the cohort it belongs to.
	"""
	assert_batch_moderator(batch)

	expires_in_days = cint(expires_in_days) or 30
	max_uses = cint(max_uses) or 100

	token = frappe.generate_hash(length=32)
	doc = frappe.get_doc(
		{
			"doctype": "LMS Batch Invite Link",
			"batch": batch,
			"key_hash": _hash_token(token),
			"expires_on": add_days(now_datetime(), expires_in_days),
			"max_uses": max_uses,
			"uses": 0,
			"is_active": 1,
		}
	).insert(ignore_permissions=True)

	return {
		"name": doc.name,
		"url": get_url(f"/lms/batches/join/{token}"),
		"expires_on": doc.expires_on,
		"max_uses": doc.max_uses,
	}


@frappe.whitelist()
def get_invite_links(batch: str) -> list[dict]:
	assert_batch_moderator(batch)
	return frappe.get_all(
		"LMS Batch Invite Link",
		filters={"batch": batch},
		fields=["name", "expires_on", "max_uses", "uses", "is_active", "owner", "creation"],
		order_by="creation desc",
	)


@frappe.whitelist()
def revoke_invite_link(name: str) -> None:
	batch = frappe.db.get_value("LMS Batch Invite Link", name, "batch")
	if not batch:
		frappe.throw(_("That invite link does not exist."), frappe.DoesNotExistError)
	assert_batch_moderator(batch)
	frappe.db.set_value("LMS Batch Invite Link", name, "is_active", 0)


@frappe.whitelist()
def describe_invite_link(token: str) -> dict:
	"""What a token points at, for the landing page. No enrollment, no login required.

	Returns only what a poster of the link has already disclosed to whoever they
	sent it to — the batch's title and dates. An invalid token returns
	``valid: false`` rather than throwing, so the page can say "this link has
	expired" instead of rendering an error.
	"""
	link = _resolve_token(token)
	if not link:
		return {"valid": False}

	batch = frappe.db.get_value(
		"LMS Batch", link.batch, ["name", "title", "start_date", "end_date", "medium"], as_dict=True
	)
	return {"valid": True, "batch": batch}


def _resolve_token(token: str):
	"""The row a token names, if it is still usable. None otherwise."""
	if not token or not isinstance(token, str):
		return None

	link = frappe.db.get_value(
		"LMS Batch Invite Link",
		{"key_hash": _hash_token(token)},
		["name", "batch", "expires_on", "max_uses", "uses", "is_active"],
		as_dict=True,
	)
	if not link or not link.is_active:
		return None
	if link.expires_on and link.expires_on < now_datetime():
		return None
	if link.max_uses and link.uses >= link.max_uses:
		return None
	return link


@frappe.whitelist()
def join_with_link(token: str) -> dict:
	"""Redeem a token for the signed-in user.

	The use counter and the enrollment are taken in one transaction under the
	batch row lock (``LMSBatchEnrollment.validate_duplicate_members`` takes it),
	or a link with thirty uses posted in a busy group over-enrolls: every
	concurrent request reads the same ``uses`` and every one of them passes.

	The grant is set on the document rather than the session, and names the batch
	the token resolved to, so it cannot open a different batch.
	"""
	if frappe.session.user == "Guest":
		frappe.throw(_("Please sign in to join this batch."), frappe.PermissionError)

	link = _resolve_token(token)
	if not link:
		frappe.throw(_("This invite link is no longer valid."))

	# Lock the link row before re-reading `uses`, for the same reason the
	# enrollment controller locks the batch: the check below is worthless if two
	# requests can both read the pre-increment value.
	frappe.db.get_value("LMS Batch Invite Link", link.name, "name", for_update=True)
	current = frappe.db.get_value("LMS Batch Invite Link", link.name, ["uses", "max_uses"], as_dict=True)
	if current.max_uses and current.uses >= current.max_uses:
		frappe.throw(_("This invite link has reached its limit."))

	if frappe.db.exists("LMS Batch Enrollment", {"batch": link.batch, "member": frappe.session.user}):
		return {"batch": link.batch, "already_enrolled": True}

	enrollment = frappe.get_doc(
		{
			"doctype": "LMS Batch Enrollment",
			"batch": link.batch,
			"member": frappe.session.user,
		}
	)
	enrollment.flags.invite_link_granted_for = link.batch
	enrollment.insert(ignore_permissions=True)

	frappe.db.set_value("LMS Batch Invite Link", link.name, "uses", current.uses + 1)

	return {"batch": link.batch, "already_enrolled": False}
