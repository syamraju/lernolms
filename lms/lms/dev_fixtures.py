"""Named test accounts for local development, one per LMS role.

Why this file exists: a set of `*@learno.test` accounts appeared on the dev site
with no committed script explaining them and no recorded password. Frappe stores
passwords hashed, so once that happens the accounts are unusable and nobody can
say where they came from. This makes the fixture explicit, documented, and
reproducible instead.

Run it with:

    bench --site lms.localhost execute lms.lms.dev_fixtures.create_dev_users

Every account gets the SAME throwaway password, printed on completion:

    learno-dev

Override it for one run with the LMS_DEV_PASSWORD environment variable. It is
deliberately not read from site config — a password that lives in a config file
is one that gets copied to a real site by accident.

SAFETY: this refuses to run unless the site has developer_mode on. That is the
only thing standing between a convenience fixture and five known-password
accounts on a production LMS, so the guard raises rather than warns, and there
is intentionally no force flag.
"""

import os

import frappe

from lms.lms.utils import create_user

# The password is a constant rather than generated: the whole point is that it
# can be written down in this docstring. Generating one would recreate exactly
# the problem this file solves.
DEFAULT_DEV_PASSWORD = "learno-dev"

# One account per role an LMS actually distinguishes, because the interesting
# bugs live in the differences — a learner with no authoring rights lands in the
# student shell, a Course Creator lands in the admin app, and the two paths are
# easy to break independently. `roles` is exact, not cumulative: sysadmin is the
# only one carrying System Manager, so "does this leak to non-admins?" has a
# real account to answer it.
DEV_USERS = [
	{
		"email": "student@learno.test",
		"first_name": "Sara",
		"last_name": "Student",
		"roles": ["LMS Student"],
	},
	{
		"email": "instructor@learno.test",
		"first_name": "Ivan",
		"last_name": "Instructor",
		"roles": ["LMS Student", "Course Creator"],
	},
	{
		"email": "evaluator@learno.test",
		"first_name": "Eva",
		"last_name": "Evaluator",
		"roles": ["LMS Student", "Batch Evaluator"],
	},
	{
		"email": "moderator@learno.test",
		"first_name": "Mona",
		"last_name": "Moderator",
		"roles": ["LMS Student", "Course Creator", "Batch Evaluator", "Moderator"],
	},
	{
		"email": "sysadmin@learno.test",
		"first_name": "Sam",
		"last_name": "Sysadmin",
		"roles": [
			"LMS Student",
			"Course Creator",
			"Batch Evaluator",
			"Moderator",
			"System Manager",
		],
	},
]


def _assert_developer_mode():
	"""Refuse to seed known-password accounts on a site that is not a dev site."""
	if not frappe.conf.get("developer_mode"):
		frappe.throw(
			"lms.lms.dev_fixtures refuses to run without developer_mode. "
			"These accounts share one published password and must never exist on a real site. "
			"Enable it with: bench --site <site> set-config developer_mode 1"
		)


def create_dev_users(password: str = None) -> list[str]:
	"""Create (or repair) the dev accounts and return the emails touched.

	Idempotent by design — running it twice is how you recover an account whose
	password someone changed, so it re-applies roles and the password to users
	that already exist rather than skipping them. `create_user` returns the
	existing doc instead of raising, which is what makes that cheap.
	"""
	_assert_developer_mode()

	password = password or os.environ.get("LMS_DEV_PASSWORD") or DEFAULT_DEV_PASSWORD
	touched = []

	for spec in DEV_USERS:
		user = create_user(
			email=spec["email"],
			first_name=spec["first_name"],
			last_name=spec["last_name"],
			full_name=f"{spec['first_name']} {spec['last_name']}",
			roles=spec["roles"],
		)
		_apply_roles(user, spec["roles"])
		_set_password(user.name, password)
		touched.append(user.name)

	frappe.db.commit()

	print(f"\nSeeded {len(touched)} dev accounts, all with password: {password}")
	for email in touched:
		print(f"  {email}")
	print()

	return touched


def _apply_roles(user, roles: list[str]):
	"""Add any missing roles to an account that already existed.

	`create_user` only assigns roles at insert time, so an account created by
	something else — which is exactly how these first appeared — would otherwise
	keep whatever roles it was born with and quietly not match this fixture.
	"""
	existing = {row.role for row in user.roles}
	missing = [role for role in roles if role not in existing]
	if not missing and user.enabled:
		return

	for role in missing:
		user.append("roles", {"role": role})
	user.enabled = 1
	user.save(ignore_permissions=True)


def _set_password(email: str, password: str):
	"""Write the password straight to the auth table.

	Deliberately not `doc.new_password`: that path runs the site's password
	strength policy, so a site with a policy configured would reject the shared
	fixture password and leave the accounts unusable — the exact failure this
	file exists to prevent.
	"""
	from frappe.utils.password import update_password

	update_password(email, password)
