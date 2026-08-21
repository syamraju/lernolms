# Copyright (c) 2026, FOSS United and Contributors
# See license.txt

"""Every permission function the app defines is actually wired into hooks.py.

A `has_permission` or a `get_permission_query_conditions` that hooks.py does not
name is never called. It sits in the controller looking like protection, reads
correctly in review, and enforces nothing.

That is not hypothetical: lms_chat_channel.py and lms_chat_message.py each
shipped a complete, correct pair of these functions that hooks.py referenced
neither of, so the LMS Student `read` grant on the chat doctypes was unscoped
across every cohort — staff-room channels included — until they were registered
on 2026-08-21.

test_permission_pairs.py catches a *registered* has_permission with no
registered query condition. It cannot catch a function nothing references at
all, because it only ever reads the two hook dicts. This file reads the tree.
"""

import json
from pathlib import Path

import frappe
from frappe.tests.utils import FrappeTestCase

from lms import hooks

APP = Path(__file__).parent.parent

PERM_FUNCTIONS = ("has_permission", "get_permission_query_conditions")

# Perm functions frappe reaches by some route other than these two hook dicts.
# Add a name here only with a written reason: the default assumption is that an
# unregistered perm function is a bug, not a special case.
UNREGISTERED_EXEMPT: set[tuple[str, str]] = set()


def _defined_perm_functions():
	"""(doctype, module, function) for every perm function in the app's tree.

	Walks the doctype directories rather than the hook dicts, which is the whole
	point: a function missing from the dicts is exactly what this looks for.
	"""
	for controller in sorted(APP.glob("*/doctype/*/*.py")):
		if controller.stem != controller.parent.name:
			continue

		definition = controller.parent / f"{controller.parent.name}.json"
		if not definition.exists():
			continue

		doctype = json.loads(definition.read_text())["name"]
		module = "lms." + str(controller.relative_to(APP).with_suffix("")).replace("/", ".")
		source = controller.read_text()

		for function in PERM_FUNCTIONS:
			if f"def {function}(" in source:
				yield doctype, module, function


class TestPermissionHooksRegistered(FrappeTestCase):
	def test_every_perm_function_is_registered(self):
		registered = {
			"has_permission": hooks.has_permission,
			"get_permission_query_conditions": hooks.permission_query_conditions,
		}

		missing = [
			f"{doctype}.{function} ({module}.{function})"
			for doctype, module, function in _defined_perm_functions()
			if (doctype, function) not in UNREGISTERED_EXEMPT and doctype not in registered[function]
		]

		self.assertEqual(
			missing,
			[],
			f"permission functions defined but never registered in hooks.py: {missing}. "
			"Frappe only calls what the hook dicts name, so each of these enforces "
			"nothing while looking like it does. Register it, or add it to "
			"UNREGISTERED_EXEMPT with a reason.",
		)

	def test_every_registered_hook_resolves(self):
		"""A hook path that no longer imports is the same silence by another route."""
		broken = []
		for dotted in (*hooks.has_permission.values(), *hooks.permission_query_conditions.values()):
			try:
				frappe.get_attr(dotted)
			except Exception as e:
				broken.append(f"{dotted} ({type(e).__name__})")

		self.assertEqual(
			broken,
			[],
			f"hooks.py names permission functions that do not import: {broken}. A "
			"renamed or deleted function leaves the hook registered and the rule "
			"unenforced.",
		)
