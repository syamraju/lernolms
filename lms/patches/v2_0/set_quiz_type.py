import frappe


def execute():
	"""Classify quizzes written before the objective/subjective split existed.

	`quiz_type` defaults to Objective, and an objective quiz is not allowed to hold
	open ended questions — so without this, every existing open ended quiz would be
	refused the next time anyone saved it. The old rule was that a quiz containing
	an open ended question contained nothing else, which is exactly what subjective
	now means.
	"""
	# Resolved through LMS Question rather than the child row's own `type`. That
	# column is a fetch_from copy, and a row written before the fetch ran — or by a
	# path that bypassed it — holds NULL while its question is plainly Open Ended.
	# Missing such a quiz here is not cosmetic: it would stay Objective, and an
	# Objective quiz holding an open ended question submits as already-final rather
	# than pending an evaluator. Cross-checked both ways so neither representation
	# alone decides it.
	open_ended_questions = frappe.get_all("LMS Question", filters={"type": "Open Ended"}, pluck="name")

	open_ended = set(
		frappe.get_all(
			"LMS Quiz Question",
			filters={"type": "Open Ended", "parenttype": "LMS Quiz"},
			pluck="parent",
			distinct=True,
		)
	)
	if open_ended_questions:
		open_ended |= set(
			frappe.get_all(
				"LMS Quiz Question",
				filters={"question": ("in", open_ended_questions), "parenttype": "LMS Quiz"},
				pluck="parent",
				distinct=True,
			)
		)

	open_ended.discard(None)
	open_ended = sorted(open_ended)
	if not open_ended:
		return

	frappe.db.set_value(
		"LMS Quiz",
		{"name": ("in", open_ended)},
		{"quiz_type": "Subjective", "show_answers": 0},
		update_modified=False,
	)

	# Their submissions were graded by hand on the instructor's submission page.
	# Anything already carrying marks has been dealt with; the rest is the queue the
	# evaluator inherits.
	submissions = frappe.get_all(
		"LMS Quiz Submission", filters={"quiz": ("in", open_ended)}, fields=["name", "score"]
	)
	for submission in submissions:
		frappe.db.set_value(
			"LMS Quiz Submission",
			submission.name,
			"evaluation_status",
			"Evaluated" if submission.score else "Pending",
			update_modified=False,
		)
