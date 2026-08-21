# Copyright (c) 2026, FOSS United and Contributors
# See license.txt

import json
from pathlib import Path

import frappe
from frappe.tests.utils import FrappeTestCase

BASELINE = Path(__file__).parent / "docperms.json"

# Roles a self-signup user can hold, or an authoring user can be given without
# an administrator's involvement. A grant to any of these is the interesting case.
WATCHED_ROLES = ("LMS Student", "Course Creator", "Batch Evaluator", "Moderator", "All", "Guest")

# The permission types this guard watches. `print`, `email` and `import` were
# all outside it until 2026-08-21, so a grant of any of them to a watched role
# passed the baseline in silence while looking covered.
#
# `print` and `email` are enumeration paths: the query-report builder, the email
# dialog and a print view read the same rows the REST list does. LMS Certificate
# and LMS Appointment grant both to LMS Student today.
#
# `import` is the heaviest thing here and the odd one out — it is a bulk WRITE,
# not a read. Twenty-two grants of it are live, to Course Creator, Batch
# Evaluator and Moderator across LMS Course, LMS Batch Enrollment, LMS Coupon
# and others; LMS Student holds it nowhere, which is the only reason this was
# not urgent. Recording them is not blessing them: it means the next change to
# any of them has to be argued for in a diff.
#
# Still outside the set, with the reasoning checked rather than assumed: `amend`
# (no doctype in the app is submittable, so no role can hold it), `select` (a
# link-field lookup; all eleven grants sit beside a `read` on the same row, so
# it reaches nothing new) and `mask`.
#
# New ptypes are APPENDED, never slotted in: each entry then grows at the end
# and the regeneration diff stays additive within every key, which is what makes
# it reviewable in a file several sessions hold hunks in.
PTYPES = (
	"read",
	"write",
	"create",
	"delete",
	"submit",
	"cancel",
	"share",
	"report",
	"export",
	"print",
	"email",
	"import",
)

# The modules lms/modules.txt is expected to list. Kept here rather than derived
# so that adding a module is a deliberate edit to this file: a module nobody
# adds to the snapshot is invisible to the baseline test, not absent from the
# REST API.
APP_MODULES = {"LMS"}


def _app_modules() -> list[str]:
	"""The app's modules, as listed in lms/modules.txt."""
	return frappe.get_module_list("lms")


def _snapshot():
	# The app's own modules, read from lms/modules.txt rather than matched with a
	# LIKE pattern, so a module added later is covered without editing this file.
	modules = _app_modules()
	out = {}
	for name in frappe.get_all("DocType", filters={"module": ("in", modules)}, pluck="name"):
		meta = frappe.get_meta(name)
		roles = {}
		for perm in meta.permissions:
			if perm.role not in WATCHED_ROLES:
				continue
			granted = [p for p in PTYPES if perm.get(p)]
			if granted:
				key = f"{perm.role}#{perm.permlevel}" + ("#if_owner" if perm.if_owner else "")
				roles[key] = granted
		if roles:
			out[name] = roles
	return out


class TestDocPermSnapshot(FrappeTestCase):
	def test_snapshot_covers_every_app_module(self):
		modules = set(_app_modules())
		self.assertEqual(
			modules,
			APP_MODULES,
			"lms/modules.txt changed. Regenerate lms/tests/docperms.json so the new "
			"module's doctypes are covered — a module missing from the snapshot is "
			"invisible to the test below, not absent from the REST API.",
		)

	def test_docperms_match_baseline(self):
		expected = json.loads(BASELINE.read_text())
		actual = _snapshot()
		self.assertEqual(
			actual,
			expected,
			"low-privilege DocPerms changed. Every diff here widens or narrows what a "
			"self-signup user can reach through the generic REST API, which is a "
			"separate door from the app's whitelisted endpoints. Update "
			"lms/tests/docperms.json in the same commit if the change is intended.",
		)
