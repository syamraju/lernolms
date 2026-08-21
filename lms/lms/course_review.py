"""The course approval workflow: who builds a course, and who lets it out.

A course passes through three hands:

    Moderator    starts the draft and names the instructors who will build it
    Instructor   fills in the curriculum, then submits it for review
    Reviewer     approves it — which publishes it — or sends it back with a reason

`LMS Course.status` is the state: ``In Progress`` → ``Under Review`` →
``Approved``. Sending a course back returns it to ``In Progress`` with the
reason on `review_feedback`, so the instructor reads what to fix rather than
finding the course silently back in their queue.

Publishing is deliberately tied to approval rather than left as a separate
switch. A course that could be published without passing review would make the
review optional, and an optional gate is not a gate.

Reviewers are moderators and holders of the evaluator role. Moderators could
already approve courses; extending it to evaluators is what puts the queue in
front of the people who actually read the material.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.desk.doctype.notification_log.notification_log import make_notification_logs
from frappe.utils import cint, now

from lms.lms.utils import get_lms_route, has_evaluator_role, has_moderator_role

REVIEW_ACTIONS = ("approve", "reject")


def can_review_courses(user: str | None = None) -> bool:
	"""Whether this user may approve a course or send it back."""
	user = user or frappe.session.user
	if user == "Guest":
		return False
	return bool(has_moderator_role(user) or has_evaluator_role(user))


def enforce_reviewer() -> None:
	if not can_review_courses():
		frappe.throw(
			_("Only a moderator or an evaluator can review courses."), frappe.PermissionError
		)


def course_instructors(course: str) -> list[str]:
	return frappe.get_all(
		"Course Instructor",
		filters={"parent": course, "parenttype": "LMS Course"},
		pluck="instructor",
		order_by="idx asc",
	)


def reviewers() -> list[str]:
	"""Everyone who should see a course arrive in the review queue.

	Deduped across the two roles: someone holding both would otherwise be sent
	the same notification twice for one submission.
	"""
	rows = frappe.get_all(
		"Has Role",
		filters={"role": ("in", ["Moderator", "Batch Evaluator"]), "parenttype": "User"},
		pluck="parent",
	)
	enabled = frappe.get_all(
		"User", filters={"name": ("in", rows or [""]), "enabled": 1}, pluck="name"
	)
	# Administrator and Guest are not people with a review queue to read.
	return [user for user in dict.fromkeys(enabled) if user not in ("Administrator", "Guest")]


def notify(users: list[str], subject: str, body: str, course: str) -> None:
	"""Send one in-app notification, skipping the person who caused it.

	Nobody needs telling about their own action, and a self-notification in the
	bell reads as something to act on.
	"""
	recipients = [user for user in dict.fromkeys(users) if user and user != frappe.session.user]
	if not recipients:
		return

	notification = frappe._dict(
		{
			"subject": subject,
			"email_content": body,
			"document_type": "LMS Course",
			"document_name": course,
			"from_user": frappe.session.user,
			"type": "Alert",
			"link": get_lms_route(f"courses/{course}"),
		}
	)
	make_notification_logs(notification, recipients)


def notify_instructor_added(course: str, email: str) -> None:
	"""Tell a newly named instructor that a course is waiting for them.

	This is the handoff the whole flow turns on: a moderator names the course,
	and the instructor has no way of knowing it exists until they are told.
	"""
	title = frappe.db.get_value("LMS Course", course, "title") or course
	notify(
		[email],
		_("You have been added as an instructor on {0}").format(frappe.bold(title)),
		_(
			"You can now build out {0} — add its sections, lectures, quizzes and assignments, "
			"then submit it for review when it is ready."
		).format(title),
		course,
	)


def notify_submitted_for_review(course: str) -> None:
	title = frappe.db.get_value("LMS Course", course, "title") or course
	notify(
		reviewers(),
		_("{0} has been submitted for review").format(frappe.bold(title)),
		_("An instructor has finished building {0} and is waiting on a review.").format(title),
		course,
	)


def notify_reviewed(course: str, action: str, feedback: str | None) -> None:
	title = frappe.db.get_value("LMS Course", course, "title") or course
	if action == "approve":
		subject = _("{0} has been approved and published").format(frappe.bold(title))
		body = _("Your course {0} passed review and is now live.").format(title)
	else:
		subject = _("{0} needs changes before it can be published").format(frappe.bold(title))
		body = feedback or _("A reviewer sent {0} back for changes.").format(title)
	notify(course_instructors(course), subject, body, course)


@frappe.whitelist()
def get_review_queue(limit: int = 50) -> list[dict]:
	"""Courses waiting on a review, oldest submission first.

	Oldest first because the queue is a backlog, not a feed: the course that has
	been waiting longest is the one holding an instructor up.
	"""
	enforce_reviewer()

	courses = frappe.get_all(
		"LMS Course",
		filters={"status": "Under Review"},
		fields=["name", "title", "image", "submitted_on", "category", "course_type"],
		order_by="submitted_on asc",
		limit_page_length=cint(limit) or 50,
	)
	for course in courses:
		instructors = course_instructors(course.name)
		course["instructors"] = frappe.get_all(
			"User",
			filters={"name": ("in", instructors or [""])},
			fields=["name", "full_name", "user_image"],
		)
		course["lessons"] = frappe.db.count("Course Lesson", {"course": course.name})
	return courses


@frappe.whitelist()
def review_course(course: str, action: str, feedback: str | None = None) -> dict:
	"""Approve a course under review, or send it back with a reason.

	A rejection without a reason is refused. "Sent back" with nothing attached
	leaves the instructor to guess what the reviewer objected to, which is the
	failure mode this whole step exists to avoid.
	"""
	enforce_reviewer()
	if action not in REVIEW_ACTIONS:
		frappe.throw(_("Unknown review action {0}.").format(action))

	status = frappe.db.get_value("LMS Course", course, "status")
	if not status:
		frappe.throw(_("Course {0} does not exist.").format(course), frappe.DoesNotExistError)
	if status != "Under Review":
		frappe.throw(_("This course is not awaiting review."))

	feedback = (feedback or "").strip()
	if action == "reject" and not feedback:
		frappe.throw(_("Say what needs to change before sending this course back."))

	stamp = {"reviewed_by": frappe.session.user, "reviewed_on": now()}
	if action == "approve":
		# Approval is what publishes. Keeping the two in one write means a course
		# can never sit approved-but-invisible waiting for a second click.
		frappe.db.set_value(
			"LMS Course",
			course,
			{"status": "Approved", "published": 1, "review_feedback": feedback or None, **stamp},
		)
	else:
		frappe.db.set_value(
			"LMS Course",
			course,
			{"status": "In Progress", "submitted_on": None, "review_feedback": feedback, **stamp},
		)

	notify_reviewed(course, action, feedback)
	return get_review_state(course)


@frappe.whitelist()
def get_review_state(course: str) -> dict:
	"""Where a course stands in the workflow.

	Deliberately not `get_course_creation_status`: that one is the author's
	checklist and enforces edit access, so a reviewer who is neither moderator
	nor instructor on the course would be refused the answer to the question
	they just decided.
	"""
	if not (can_review_courses() or _can_edit(course)):
		raise frappe.PermissionError

	state = frappe.db.get_value(
		"LMS Course",
		course,
		["name", "title", "status", "published", "submitted_on", "review_feedback", "reviewed_by", "reviewed_on"],
		as_dict=True,
	)
	if not state:
		frappe.throw(_("Course {0} does not exist.").format(course), frappe.DoesNotExistError)
	state["published"] = cint(state["published"])
	state["can_review"] = can_review_courses()
	return state


def _can_edit(course: str) -> bool:
	from lms.lms.utils import can_modify_course

	return bool(can_modify_course(course))
