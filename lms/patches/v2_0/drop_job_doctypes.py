import frappe

# The job board is gone from the app: the Job module, its two doctypes, the web
# form and the alert have all left the source tree. A site keeps its own copies
# of those records and their tables, and migrate has no reason to guess that a
# doctype missing from the app should be dropped, so it is spelled out here.
#
# Destructive by design: every posting and every application goes, along with
# the resumes attached to them. Take a backup before migrating a site that ran
# the board for real.

# Applications first. They Link to Job Opportunity, and frappe refuses to drop a
# doctype another live doctype still links to.
DOCTYPES = ("LMS Job Application", "Job Opportunity")

# Residue frappe does not clear when a whole doctype is dropped, and the column
# each table keys it on. Custom fields, property setters, custom docperms and
# reports are handled by DocType.on_trash itself.
RESIDUE = {
	"DocShare": "share_doctype",
	"Version": "ref_doctype",
	"Comment": "reference_doctype",
	"Notification Log": "document_type",
}


def execute():
	frappe.delete_doc("Notification", "New job alert", ignore_missing=True, force=True)
	frappe.delete_doc("Web Form", "job-opportunity", ignore_missing=True, force=True)

	for doctype in DOCTYPES:
		if not frappe.db.exists("DocType", doctype):
			continue
		delete_attachments(doctype)
		for table, column in RESIDUE.items():
			frappe.db.delete(table, {column: doctype})
		frappe.delete_doc("DocType", doctype, ignore_missing=True, force=True)

	# Only reachable once both doctypes are gone: a Module Def with doctypes
	# still filed under it cannot be deleted.
	frappe.delete_doc("Module Def", "Job", ignore_missing=True, force=True)

	# `jobs` (sidebar) and `allow_job_posting` are no longer fields on LMS
	# Settings, but the values they held are rows in tabSingles and outlive the
	# fields. Same shape as v0_0.user_singles_issue.
	frappe.db.delete(
		"Singles",
		{"doctype": "LMS Settings", "field": ["in", ["jobs", "allow_job_posting"]]},
	)

	# Navbar links, in every spelling they have had: v1_0.change_jobs_url moved
	# them from /jobs to /job-openings and v1_0.change_navbar_urls then put them
	# under /lms. Deleted through the db layer rather than delete_doc because
	# Top Bar Item is a child table and get_all refuses to query one parentless.
	frappe.db.delete("Top Bar Item", {"url": ["in", ["/jobs", "/job-openings", "/lms/job-openings"]]})


def delete_attachments(doctype):
	"""Resumes and company logos are File records of their own.

	Dropping the doctype takes the rows that referenced them, not the files, so
	an applicant's private resume would stay readable at its URL forever.
	"""
	for name in frappe.get_all("File", filters={"attached_to_doctype": doctype}, pluck="name"):
		frappe.delete_doc("File", name, ignore_permissions=True, force=True, delete_permanently=True)
