import time

import frappe
from frappe import _
from frappe.model.naming import append_number_if_name_exists
from frappe.utils import cint, escape_html, random_string
from frappe.website.utils import cleanup_page_name, is_signup_disabled

from lms.lms.utils import get_country_code, get_lms_route


#: `while` needs a floor. Each pass appends a number to a candidate that already
#: exists, so a handful of rounds settles any real collision; more than this means
#: the candidate is not converging and the loop would never end.
MAX_USERNAME_ATTEMPTS = 10


def validate_username_duplicates(doc, method):
	"""Give the user a unique username, deriving one from their name if needed.

	The loop is bounded. An empty `full_name` makes `cleanup_page_name` return "",
	`append_number_if_name_exists` hands "" straight back, and `not doc.username`
	stays true forever — a hung worker, holding its row locks, on a request that
	looks like an ordinary signup. `process_user_names` now guarantees a name so
	the bad candidate should never arrive, but a spin that only shows up under a
	name nobody supplied is exactly the kind that gets reintroduced.
	"""
	for _attempt in range(MAX_USERNAME_ATTEMPTS):
		if doc.username and not doc.username_exists():
			break
		doc.username = append_number_if_name_exists(
			doc.doctype, cleanup_page_name(doc.full_name), fieldname="username"
		)
	else:
		# Fall through to the email-derived form below rather than throwing: a
		# username is cosmetic, and refusing the insert would fail the signup.
		doc.username = ""

	if " " in doc.username:
		doc.username = doc.username.replace(" ", "")

	if len(doc.username) < 4:
		doc.username = doc.email.replace("@", "").replace(".", "")


def add_lms_student_role(doc, method):
	doc.append_roles("LMS Student")


@frappe.whitelist(allow_guest=True)  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
def sign_up(email: str, full_name: str, verify_terms: bool, user_category: str):
	if is_signup_disabled():
		frappe.throw(_("Sign Up is disabled"), _("Not Allowed"))

	user = frappe.db.get("User", {"email": email})
	if user:
		if user.enabled:
			return 0, _("Already Registered")
		else:
			return 0, _("Registered but disabled")
	else:
		max_signups_allowed_per_hour = cint(frappe.get_system_settings("max_signups_allowed_per_hour") or 300)
		users_created_past_hour = frappe.db.get_creation_count("User", 60)
		if users_created_past_hour >= max_signups_allowed_per_hour:
			frappe.respond_as_web_page(
				_("Temporarily Disabled"),
				_(
					"Too many users signed up recently, so the registration is disabled. Please try back in an hour"
				),
				http_status_code=429,
			)

	default_role = frappe.db.get_single_value("Portal Settings", "default_role")

	# Concurrent signups deadlock on User insert (Frappe doesn't retry 1213); retry, and append roles pre-insert to keep it to one transaction.
	for attempt in range(3):
		try:
			user = frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": escape_html(full_name),
					"verify_terms": verify_terms,
					"user_category": user_category,
					"country": "",
					"enabled": 1,
					"new_password": random_string(10),
					"user_type": "Website User",
				}
			)
			user.flags.ignore_permissions = True
			user.flags.ignore_password_policy = True
			if default_role:
				user.append_roles(default_role)
			user.insert()
			break
		except frappe.DuplicateEntryError:
			# A concurrent signup for the same email won the race; treat as already registered.
			frappe.db.rollback()
			return 0, _("Already Registered")
		except frappe.QueryDeadlockError:
			frappe.db.rollback()
			if attempt == 2:
				raise
			time.sleep(0.1 * (attempt + 1))

	set_country_from_ip(None, user.name)

	if user.flags.email_sent:
		return 1, _("Signup successful. Please check your email for verification.")
	else:
		return 2, _("Signup successful. Please ask your administrator to verify your sign-up.")


def set_country_from_ip(login_manager: object = None, user: str = None):
	if not user and login_manager:
		user = login_manager.user
	user_country = frappe.db.get_value("User", user, "country")
	if user_country:
		return
	frappe.db.set_value("User", user, "country", get_country_code())
	return


#: Where an account provisioned with a temporary password lands, and stays,
#: until it has chosen a real one.
SET_PASSWORD_ROUTE = "/set-password"


def on_login(login_manager):
	user = getattr(login_manager, "user", None) or frappe.session.user

	# A provisioned account has a working password that somebody else generated
	# and mailed. Sending it anywhere but the set-password screen would leave that
	# credential valid for as long as the user ignored the prompt.
	if user not in ("Guest", "Administrator") and frappe.db.get_value(
		"User", user, "must_reset_password"
	):
		frappe.local.response["home_page"] = SET_PASSWORD_ROUTE
		return

	default_app = frappe.db.get_single_value("System Settings", "default_app")
	if default_app == "lms":
		frappe.local.response["home_page"] = get_lms_route()


@frappe.whitelist()
def must_reset_password() -> bool:
	"""Whether the signed-in user is still holding a provisioned password.

	Read by the router on every load, not only at login: `on_login` fires once,
	and a session that was already open when the flag was set — a re-issue while
	the student is signed in on another tab — would otherwise never see it.
	"""
	if frappe.session.user == "Guest":
		return False
	return bool(frappe.db.get_value("User", frappe.session.user, "must_reset_password"))


@frappe.whitelist()
def set_own_password(new_password: str) -> None:
	"""Replace a temporary password with one the user chose, and clear the flag.

	Only ever acts on the caller, and the old password is not required: the whole
	situation is that the current one arrived by email and is not a secret the
	user picked. What makes that safe is that they are already authenticated —
	this is not a recovery path.

	Unlike `provision_temporary_password`, this runs the site's password policy.
	A generated string has to bypass it; a human-chosen one is exactly what it
	exists to check.
	"""
	if frappe.session.user == "Guest":
		frappe.throw(_("You are not signed in."), frappe.PermissionError)

	if not new_password or not isinstance(new_password, str):
		frappe.throw(_("Please choose a password."))

	from frappe.core.doctype.user.user import (
		MAX_PASSWORD_SIZE,
		handle_password_test_fail,
		test_password_strength,
	)
	from frappe.utils.password import update_password

	if len(new_password) > MAX_PASSWORD_SIZE:
		frappe.throw(_("Password size exceeded the maximum allowed size."))

	feedback = (test_password_strength(new_password) or {}).get("feedback")
	if feedback and not feedback.get("password_policy_validation_passed", False):
		handle_password_test_fail(feedback)

	# Other sessions are dropped: the temporary password was mailed, so anything
	# already signed in with it is not necessarily this user.
	update_password(frappe.session.user, new_password, logout_all_sessions=True)
	frappe.db.set_value("User", frappe.session.user, "must_reset_password", 0)
