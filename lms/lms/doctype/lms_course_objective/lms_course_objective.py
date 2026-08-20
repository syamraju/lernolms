# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class LMSCourseObjective(Document):
	"""A single free-text line in one of the course's planning tables.

	The same child doctype backs three tables on LMS Course — learning
	objectives, requirements and intended learners — because all three are the
	same shape (an ordered list of short sentences) and Frappe keeps them apart
	by `parentfield`. One doctype instead of three keeps the reorder/delete
	handling in the UI generic.
	"""

	pass
