# Copyright (c) 2026, FOSS United and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from lms.patches.utils import drop_orphan_tables


class TestDropOrphanTables(FrappeTestCase):
	"""The guard matters more than the drop.

	This helper runs on every site that upgrades, including ones still running
	the feature being removed. A bug here does not strand a table — it deletes
	somebody's data, silently, during a migrate they had no reason to distrust.
	"""

	def test_a_doctype_that_still_exists_is_never_dropped(self):
		# The whole safety property, stated against a doctype this app cannot
		# live without. If this ever fails, a migrate is destroying live data.
		self.assertTrue(frappe.db.exists("DocType", "LMS Course"))

		self.assertEqual(drop_orphan_tables(["LMS Course"]), [])

		self.assertTrue(
			frappe.db.table_exists("LMS Course", cached=False),
			"drop_orphan_tables dropped the table of a doctype that still exists",
		)

	def test_a_name_that_was_never_a_doctype_is_a_no_op(self):
		# No DocType and no table: nothing to drop, and nothing to raise about.
		self.assertEqual(drop_orphan_tables(["LMS Nonexistent Thing"]), [])

	def test_a_backtick_in_a_name_is_refused_rather_than_interpolated(self):
		# The one character that would break out of the DDL quoting. Refused
		# rather than escaped, because a doctype name has no business containing
		# one and the safe answer to an impossible name is to do nothing.
		self.assertEqual(drop_orphan_tables(["Evil`Name"]), [])

	def test_an_orphaned_table_is_actually_dropped(self):
		"""The drop path itself, proven against a table nothing owns.

		Built here rather than aimed at the real job tables: this runs on
		developer machines and in CI, and a test that deletes whatever orphan it
		happens to find would be indistinguishable from the bug it is guarding
		against.
		"""
		orphan = "LMS Patch Utils Fixture"
		self.assertFalse(frappe.db.exists("DocType", orphan))
		frappe.db.sql_ddl(f"CREATE TABLE IF NOT EXISTS `tab{orphan}` (name varchar(140) PRIMARY KEY)")
		self.addCleanup(lambda: frappe.db.sql_ddl(f"DROP TABLE IF EXISTS `tab{orphan}`"))
		self.assertTrue(frappe.db.table_exists(orphan, cached=False))

		self.assertEqual(drop_orphan_tables([orphan]), [orphan])

		self.assertFalse(
			frappe.db.table_exists(orphan, cached=False),
			"drop_orphan_tables reported a drop it did not perform",
		)

	def test_the_live_doctype_survives_a_mixed_batch(self):
		# The realistic shape of a module removal: some names orphaned, some
		# still installed, handed over together. One bad name must not take a
		# good one with it, in either direction.
		dropped = drop_orphan_tables(["LMS Nonexistent Thing", "LMS Course"])

		self.assertNotIn("LMS Course", dropped)
		self.assertTrue(frappe.db.table_exists("LMS Course", cached=False))
