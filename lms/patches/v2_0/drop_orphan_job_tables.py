# Copyright (c) 2026, FOSS United and contributors
# For license information, please see license.txt

"""Drop the job board's tables, which `drop_job_doctypes` left behind.

That patch removed the postings, the applications, the two DocType records and
the Job Module Def, and all of it worked. What it did not do is drop
`tabJob Opportunity` and `tabLMS Job Application`, because it assumed deleting a
DocType takes its table with it. It does not, and never has — see
`lms.patches.utils.drop_orphan_tables` for why, and for frappe's own precedent.

A separate patch rather than a fix to that one: `drop_job_doctypes` is already
recorded in the Patch Log on every site that has migrated since, so editing it
would change nothing anywhere it has run.

Empty tables on the sites we can see, so this is tidiness rather than recovery.
It is still worth doing: schema nothing will ever reach again is the kind of
thing that outlives everyone who knows what it was for.
"""

import frappe

from lms.patches.utils import drop_orphan_tables

# Applications first, mirroring drop_job_doctypes: the order does not matter for
# DDL, but keeping the two lists in the same shape is what makes them readable
# against each other.
JOB_DOCTYPES = ("LMS Job Application", "Job Opportunity")


def execute():
	dropped = drop_orphan_tables(JOB_DOCTYPES)
	if dropped:
		# Says what happened on this site specifically. A site that never ran the
		# job board, and one that was cleaned up by hand, both reach here with
		# nothing to do, and neither is a problem worth a log line.
		frappe.logger("lms").info(f"dropped orphaned job tables: {', '.join(dropped)}")
