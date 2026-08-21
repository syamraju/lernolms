# Copyright (c) 2026, Frappe and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class LessonResource(Document):
	"""One downloadable file, source-code bundle or external link on a lecture.

	Resources sit beside the lecture body rather than inside it: they are
	listed as their own section under the player and stay reachable when the
	lecture is a quiz, an assignment or a coding exercise instead of a video.
	"""

	pass
