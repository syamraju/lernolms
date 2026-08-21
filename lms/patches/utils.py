# Copyright (c) 2026, FOSS United and contributors
# For license information, please see license.txt

"""Helpers shared by patches."""

import frappe


def drop_orphan_tables(doctypes) -> list[str]:
	"""Drop the backing table of every doctype in `doctypes` that no longer exists.

	Removing a module from the app does not remove its tables from a site that
	ran it. `frappe.delete_doc("DocType", ...)` deletes the DocType record and
	leaves `tab<Doctype>` in place — by design, not by accident: there is no
	`on_trash` on DocType and no `DROP TABLE` anywhere in that path, and frappe
	states the intent on `remove_orphan_doctypes` ("Deleting the entry doesn't
	delete any data. So this is supposed to be non-destrictive operation").
	Frappe's own removals drop tables by hand for the same reason — see
	`frappe/patches/v13_0/replace_old_data_import.py` — which is what this does.

	Guarded on the orphan condition rather than on a name. A patch runs on every
	site that upgrades, including ones still running the feature being removed
	elsewhere, and dropping `tabX` because this version of the app no longer
	ships X would take their data with it. A table is dropped only where the
	DocType it belonged to is already gone, which is the state a completed
	removal leaves behind and the only state where the table is unreachable.

	Returns the doctypes whose tables were actually dropped, so the caller can
	report what it did rather than assume.
	"""
	dropped = []

	for doctype in doctypes:
		# The name is interpolated into DDL, which cannot be parameterised.
		# Callers pass literals today, but this is meant to be reused, and a
		# backtick is the one character that would break out of the quoting.
		if "`" in doctype:
			frappe.log_error(
				title="drop_orphan_tables: refusing unsafe doctype name",
				message=doctype,
			)
			continue

		# Uncached: the doctype was almost certainly deleted earlier in this
		# same migrate, and a cached answer would still say it is there.
		if frappe.db.exists("DocType", doctype):
			continue

		if not frappe.db.table_exists(doctype, cached=False):
			continue

		frappe.db.sql_ddl(f"DROP TABLE IF EXISTS `tab{doctype}`")
		dropped.append(doctype)

	return dropped
