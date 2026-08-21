# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class LMSAvailabilitySlot(Document):
	"""One weekly recurring window an instructor is open for appointments.

	The window is not the bookable unit — `LMS Instructor Availability.slot_duration`
	divides it into the slots a student actually picks from.
	"""

	pass
