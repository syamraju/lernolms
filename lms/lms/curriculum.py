"""Server side of the curriculum builder.

A course's curriculum is sections (Course Chapter) holding ordered items
(Course Lesson). An item is one of four kinds, and `Course Lesson.item_type`
says which:

    Lecture          the body content lives on the lesson itself
    Quiz             delegates to an LMS Quiz
    Assignment       delegates to an LMS Assignment
    Coding Exercise  delegates to an LMS Programming Exercise

Keeping every kind on one row — rather than four parallel tables — is what lets
the existing outline, progress tracking and lesson player keep working
unchanged: to everything downstream a curriculum item is still a lesson.

Sections and items each carry their own `is_published`. Authors build in the
open and reveal work when it is ready, so "in the curriculum" and "visible to a
learner" are deliberately different questions. `visible_to_learner` below is the
single place that answers the second one.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

from lms.lms.course_creation import enforce_course_access

ITEM_TYPES = ("Lecture", "Quiz", "Assignment", "Coding Exercise")

# Which document backs each delegating item type, and the field on the lesson
# that points at it. A Lecture has no backing document — its content is the
# lesson body — so it is absent here rather than mapped to None.
BACKING_DOCTYPE = {
	"Quiz": ("LMS Quiz", "quiz"),
	"Assignment": ("LMS Assignment", "assignment"),
	"Coding Exercise": ("LMS Programming Exercise", "exercise"),
}


def validate_item_type(item_type: str) -> str:
	if item_type not in ITEM_TYPES:
		frappe.throw(_("{0} is not a curriculum item type.").format(item_type))
	return item_type


# An objective quiz is marked the moment it is submitted, against answers the author
# supplied. A subjective one holds work an evaluator has to read — code, an argument —
# and waits in their queue until they do.
QUIZ_TYPES = ("Objective", "Subjective")


def validate_quiz_type(quiz_type: str | None) -> str:
	if quiz_type and quiz_type not in QUIZ_TYPES:
		frappe.throw(_("{0} is not a quiz type.").format(quiz_type))
	return quiz_type or "Objective"


def course_of_chapter(chapter: str) -> str:
	course = frappe.db.get_value("Course Chapter", chapter, "course")
	if not course:
		frappe.throw(_("Section {0} does not exist.").format(chapter), frappe.DoesNotExistError)
	return course


def course_of_lesson(lesson: str) -> str:
	course = frappe.db.get_value("Course Lesson", lesson, "course")
	if not course:
		frappe.throw(_("Curriculum item {0} does not exist.").format(lesson), frappe.DoesNotExistError)
	return course


# --------------------------------------------------------------------------
# Reading the curriculum
# --------------------------------------------------------------------------


def can_author(course: str) -> bool:
	"""Whether the session user may see unpublished work on this course."""
	from lms.lms.utils import can_modify_course

	return bool(can_modify_course(course))


@frappe.whitelist()
def get_curriculum(course: str, for_author: bool = True) -> list[dict]:
	"""The full curriculum tree.

	`for_author` asks for the editing view — every section and item, published
	or not. It is honoured only for someone who may actually edit the course;
	anyone else gets the learner view regardless of what they ask for, so the
	flag can never be used to read unpublished content.
	"""
	authoring = bool(for_author) and can_author(course)
	if not authoring:
		from lms.lms.utils import get_membership, guest_access_allowed

		if not guest_access_allowed():
			return []
		published = frappe.db.get_value("LMS Course", course, "published")
		if not published and not get_membership(course):
			return []

	chapter_rows = frappe.get_all(
		"Chapter Reference",
		filters={"parent": course, "parenttype": "LMS Course"},
		fields=["chapter", "idx"],
		order_by="idx asc",
	)

	sections = []
	for row in chapter_rows:
		chapter = frappe.db.get_value(
			"Course Chapter",
			row.chapter,
			["name", "title", "learning_objective", "is_published", "is_scorm_package"],
			as_dict=True,
		)
		if not chapter:
			continue
		if not authoring and not cint(chapter.is_published):
			continue
		chapter["idx"] = row.idx
		chapter["items"] = get_section_items(chapter.name, authoring)
		sections.append(chapter)
	return sections


def get_section_items(chapter: str, authoring: bool) -> list[dict]:
	rows = frappe.get_all(
		"Lesson Reference", filters={"parent": chapter}, fields=["lesson", "idx"], order_by="idx asc"
	)
	items = []
	for row in rows:
		lesson = frappe.db.get_value(
			"Course Lesson",
			row.lesson,
			[
				"name",
				"title",
				"item_type",
				"is_published",
				"duration_minutes",
				"video_duration",
				"description",
				"include_in_preview",
				"is_shared_activity",
				"quiz",
				"assignment",
				"exercise",
			],
			as_dict=True,
		)
		if not lesson:
			continue
		# Rows created before item_type existed are lectures; defaulting here
		# rather than backfilling keeps old courses working without a patch.
		lesson.item_type = lesson.item_type or "Lecture"
		if not authoring and not cint(lesson.is_published):
			continue
		lesson.idx = row.idx
		lesson.resources = get_lesson_resources(lesson.name)
		lesson.has_video = bool(lesson.video_duration) or has_video_content(lesson.name)
		if lesson.quiz:
			lesson.quiz_summary = get_quiz_summary(lesson.quiz)
		items.append(lesson)
	return items


def get_quiz_summary(quiz: str) -> dict | None:
	"""Enough of a quiz to describe it in a curriculum row without opening it.

	The row has to show a reused quiz's shape — how many questions, what mark
	passes — because a shared quiz is not edited from the curriculum builder and
	the author would otherwise be looking at a name and nothing else.
	"""
	details = frappe.db.get_value(
		"LMS Quiz",
		quiz,
		["name", "title", "passing_percentage", "max_attempts", "quiz_type"],
		as_dict=True,
	)
	if not details:
		return None
	details["question_count"] = frappe.db.count("LMS Quiz Question", {"parent": quiz})
	return details


def has_video_content(lesson: str) -> bool:
	from lms.lms.course_creation import is_video_block
	from lms.lms.utils import get_editorjs_blocks

	content = frappe.db.get_value("Course Lesson", lesson, "content")
	return any(is_video_block(block) for block in get_editorjs_blocks(content))


def get_lesson_resources(lesson: str) -> list[dict]:
	return frappe.get_all(
		"Lesson Resource",
		filters={"parent": lesson, "parenttype": "Course Lesson"},
		fields=["name", "resource_type", "title", "file", "url"],
		order_by="idx asc",
	)


# --------------------------------------------------------------------------
# Sections
# --------------------------------------------------------------------------


@frappe.whitelist()
def upsert_section(
	course: str,
	title: str,
	learning_objective: str | None = None,
	name: str | None = None,
) -> dict:
	"""Create or rename a section, keeping its outline row in step."""
	enforce_course_access(course)
	title = (title or "").strip()
	if not title:
		frappe.throw(_("A section title is required."))

	if name:
		chapter = frappe.get_doc("Course Chapter", name)
		if chapter.course != course:
			frappe.throw(_("That section belongs to another course."))
		chapter.title = title
		chapter.learning_objective = learning_objective
		chapter.save()
	else:
		chapter = frappe.new_doc("Course Chapter")
		chapter.update(
			{
				"title": title,
				"course": course,
				"learning_objective": learning_objective,
				# New sections start hidden. An author adds the section first
				# and fills it afterwards; publishing it empty would show
				# learners a blank heading.
				"is_published": 0,
			}
		)
		chapter.insert()
		# Linking the outline row here — rather than from the client — keeps
		# the Chapter Reference atomic with the chapter it points at.
		course_doc = frappe.get_doc("LMS Course", course)
		course_doc.append("chapters", {"chapter": chapter.name})
		course_doc.save()

	return get_curriculum(course)


@frappe.whitelist()
def set_section_published(chapter: str, published: bool) -> list[dict]:
	"""Show or hide a whole section.

	Publishing a section with nothing published inside it would put an empty
	heading in front of learners, so that case is refused with the reason
	rather than quietly allowed.
	"""
	course = course_of_chapter(chapter)
	enforce_course_access(course)
	published = 1 if cint(published) else 0

	if published:
		lessons = frappe.get_all("Lesson Reference", filters={"parent": chapter}, pluck="lesson")
		visible = [
			lesson for lesson in lessons if cint(frappe.db.get_value("Course Lesson", lesson, "is_published"))
		]
		if not visible:
			frappe.throw(_("Publish at least one item in this section before publishing the section."))

	frappe.db.set_value("Course Chapter", chapter, "is_published", published)
	return get_curriculum(course)


@frappe.whitelist()
def delete_section(chapter: str) -> list[dict]:
	"""Delete a section and everything in it."""
	course = course_of_chapter(chapter)
	enforce_course_access(course)
	from lms.lms.api import delete_chapter

	delete_chapter(chapter)
	return get_curriculum(course)


@frappe.whitelist()
def reorder_sections(course: str, order: list | str) -> list[dict]:
	"""Rewrite the section order from a full list of chapter names.

	Takes the whole order rather than a single move so the client can apply an
	optimistic reorder and have the server agree in one round trip, instead of
	n calls each rewriting every sibling's idx.
	"""
	enforce_course_access(course)
	if isinstance(order, str):
		order = frappe.parse_json(order)

	existing = frappe.get_all(
		"Chapter Reference",
		filters={"parent": course, "parenttype": "LMS Course"},
		fields=["name", "chapter"],
	)
	by_chapter = {row.chapter: row.name for row in existing}
	if set(order) != set(by_chapter):
		frappe.throw(_("The section order does not match this course's sections."))

	for index, chapter in enumerate(order, start=1):
		frappe.db.set_value("Chapter Reference", by_chapter[chapter], "idx", index)
	return get_curriculum(course)


# --------------------------------------------------------------------------
# Items
# --------------------------------------------------------------------------


def create_backing_document(
	item_type: str, title: str, course: str, description: str | None, quiz_type: str = "Objective"
):
	"""Create the document a non-Lecture item delegates to, and return its name."""
	doctype, _field = BACKING_DOCTYPE[item_type]

	if item_type == "Quiz":
		doc = frappe.new_doc("LMS Quiz")
		doc.update(
			{
				"title": title,
				"course": course,
				# Asked for up front rather than switched later: the two types take
				# different questions, so an author who picks the wrong one has
				# written the wrong quiz, not a quiz with the wrong setting.
				"quiz_type": validate_quiz_type(quiz_type),
				# The quiz starts with no questions, so a marks-based pass
				# threshold is meaningless until the author adds some. These are
				# the doctype's own required fields; seeding them keeps the
				# insert valid without asking the author for numbers up front.
				"passing_percentage": 60,
				"total_marks": 0,
			}
		)
	elif item_type == "Assignment":
		doc = frappe.new_doc("LMS Assignment")
		doc.update({"title": title, "course": course, "type": "Text", "description": description})
	else:
		doc = frappe.new_doc("LMS Programming Exercise")
		doc.update({"title": title, "course": course, "language": "Python"})

	doc.insert()
	return doc.name


@frappe.whitelist()
def add_curriculum_item(
	chapter: str,
	item_type: str = "Lecture",
	title: str | None = None,
	description: str | None = None,
	quiz: str | None = None,
	quiz_type: str = "Objective",
) -> dict:
	"""Append a new item of the given type to a section.

	The lesson row and its backing document are created together so a failed
	insert leaves neither behind — a lesson pointing at a quiz that does not
	exist would break the outline for everyone.

	Passing `quiz` places a quiz that already exists — one written in the Quizzes
	section, or used by another course — instead of creating an empty one. That
	item does not own the quiz: see `is_shared_activity`.
	"""
	course = course_of_chapter(chapter)
	enforce_course_access(course)
	validate_item_type(item_type)

	if quiz and item_type != "Quiz":
		frappe.throw(_("Only a quiz item can be linked to a quiz."))

	title = (title or "").strip()
	backing = None
	shared = 0
	if quiz:
		backing = enforce_quiz_access(quiz)
		shared = 1
		# An unnamed placement takes the quiz's own name — the author picked it
		# from a list showing that name, so anything else reads as the wrong
		# quiz. The reverse never happens: the library quiz keeps its title, so
		# two courses reusing one quiz cannot rename it for each other.
		title = title or frappe.db.get_value("LMS Quiz", quiz, "title")

	title = title or _("Untitled {0}").format(_(item_type))

	if not quiz and item_type in BACKING_DOCTYPE:
		backing = create_backing_document(item_type, title, course, description, quiz_type)

	lesson = frappe.new_doc("Course Lesson")
	lesson.update(
		{
			"title": title,
			"chapter": chapter,
			"course": course,
			"item_type": item_type,
			"description": description,
			"is_shared_activity": shared,
			# New items start hidden, matching sections: an author adds the row
			# first and writes the content afterwards.
			"is_published": 0,
		}
	)
	if backing:
		lesson.set(BACKING_DOCTYPE[item_type][1], backing)
	lesson.insert()

	idx = frappe.db.count("Lesson Reference", {"parent": chapter}) + 1
	chapter_doc = frappe.get_doc("Course Chapter", chapter)
	chapter_doc.append("lessons", {"lesson": lesson.name, "idx": idx})
	chapter_doc.save()

	return {"lesson": lesson.name, "curriculum": get_curriculum(course)}


ITEM_FIELDS = ("title", "description", "duration_minutes")


@frappe.whitelist()
def update_curriculum_item(lesson: str, **values) -> list[dict]:
	"""Patch the editable fields of a curriculum item."""
	course = course_of_lesson(lesson)
	enforce_course_access(course)

	updates = {field: values[field] for field in ITEM_FIELDS if field in values}
	if not updates:
		return get_curriculum(course)
	if "title" in updates:
		updates["title"] = (updates["title"] or "").strip()
		if not updates["title"]:
			frappe.throw(_("A title is required."))

	doc = frappe.get_doc("Course Lesson", lesson)
	doc.update(updates)
	doc.save()

	# The delegating document carries its own copy of the title, which is what
	# the assignment list and quiz player show. Keep the two in step rather
	# than letting a rename in the curriculum leave the old name behind.
	#
	# Except when the activity is shared: renaming a placement of a library quiz
	# would rename it inside every other course using it, which is not a change
	# this author is making or can see.
	if "title" in updates and doc.item_type in BACKING_DOCTYPE and not cint(doc.is_shared_activity):
		doctype, field = BACKING_DOCTYPE[doc.item_type]
		if doc.get(field):
			frappe.db.set_value(doctype, doc.get(field), "title", updates["title"])

	return get_curriculum(course)


@frappe.whitelist()
def set_item_published(lesson: str, published: bool) -> list[dict]:
	"""Show or hide one curriculum item.

	Unpublishing the last visible item in a published section would leave an
	empty heading on the learner's outline, so the section is pulled back with
	it. The mirror of the guard in `set_section_published`.
	"""
	course = course_of_lesson(lesson)
	enforce_course_access(course)
	published = 1 if cint(published) else 0

	doc = frappe.get_doc("Course Lesson", lesson)
	frappe.db.set_value("Course Lesson", lesson, "is_published", published)
	# A shared activity's own visibility belongs to the library, not to one
	# course's outline: hiding the item here must not withdraw it elsewhere.
	if (
		doc.item_type in BACKING_DOCTYPE
		and doc.get(BACKING_DOCTYPE[doc.item_type][1])
		and not cint(doc.is_shared_activity)
	):
		doctype, field = BACKING_DOCTYPE[doc.item_type]
		if frappe.get_meta(doctype).has_field("is_published"):
			frappe.db.set_value(doctype, doc.get(field), "is_published", published)

	chapter = doc.chapter
	if not published and cint(frappe.db.get_value("Course Chapter", chapter, "is_published")):
		siblings = frappe.get_all("Lesson Reference", filters={"parent": chapter}, pluck="lesson")
		any_visible = any(
			cint(frappe.db.get_value("Course Lesson", sibling, "is_published")) for sibling in siblings
		)
		if not any_visible:
			frappe.db.set_value("Course Chapter", chapter, "is_published", 0)

	return get_curriculum(course)


@frappe.whitelist()
def delete_curriculum_item(lesson: str) -> list[dict]:
	"""Delete an item, and the document it delegates to."""
	course = course_of_lesson(lesson)
	enforce_course_access(course)

	doc = frappe.get_doc("Course Lesson", lesson)
	backing = None
	# Only an activity this item created is deleted with it. One reused from the
	# library outlives the placement — other courses may be using it, and even
	# if none are, it is still the author's quiz sitting in their quiz list.
	if doc.item_type in BACKING_DOCTYPE and not cint(doc.is_shared_activity):
		doctype, field = BACKING_DOCTYPE[doc.item_type]
		if doc.get(field):
			backing = (doctype, doc.get(field))

	from lms.lms.api import delete_lesson

	delete_lesson(lesson, doc.chapter)

	if backing:
		# After the lesson, so the link is already gone: deleting the quiz
		# first would trip Frappe's LinkExistsError.
		frappe.delete_doc(backing[0], backing[1], force=1, ignore_permissions=True)

	return get_curriculum(course)


@frappe.whitelist()
def move_curriculum_item(lesson: str, target_chapter: str, idx: int) -> list[dict]:
	"""Move an item within or between sections."""
	course = course_of_lesson(lesson)
	enforce_course_access(course)
	if course_of_chapter(target_chapter) != course:
		frappe.throw(_("That section belongs to another course."))

	source_chapter = frappe.db.get_value("Course Lesson", lesson, "chapter")
	from lms.lms.api import update_lesson_index

	update_lesson_index(lesson, source_chapter, target_chapter, cint(idx))
	return get_curriculum(course)


# --------------------------------------------------------------------------
# Resources
# --------------------------------------------------------------------------


@frappe.whitelist()
def add_lesson_resource(
	lesson: str,
	resource_type: str,
	title: str,
	file: str | None = None,
	url: str | None = None,
) -> list[dict]:
	"""Attach a downloadable file, source bundle or external link to an item."""
	course = course_of_lesson(lesson)
	enforce_course_access(course)

	if resource_type not in ("Downloadable File", "External Resource", "Source Code"):
		frappe.throw(_("{0} is not a resource type.").format(resource_type))
	title = (title or "").strip()
	if not title:
		frappe.throw(_("A resource title is required."))
	if resource_type == "External Resource":
		if not url:
			frappe.throw(_("An external resource needs a URL."))
		file = None
	elif not file:
		frappe.throw(_("Upload a file for this resource."))
	else:
		url = None

	doc = frappe.get_doc("Course Lesson", lesson)
	doc.append("resources", {"resource_type": resource_type, "title": title, "file": file, "url": url})
	doc.save()
	return get_lesson_resources(lesson)


@frappe.whitelist()
def delete_lesson_resource(lesson: str, row: str) -> list[dict]:
	course = course_of_lesson(lesson)
	enforce_course_access(course)
	doc = frappe.get_doc("Course Lesson", lesson)
	remaining = [resource for resource in doc.resources if resource.name != row]
	if len(remaining) == len(doc.resources):
		frappe.throw(_("That resource is not on this item."))
	doc.resources = remaining
	doc.save()
	return get_lesson_resources(lesson)


# --------------------------------------------------------------------------
# Quiz questions
# --------------------------------------------------------------------------

# LMS Question stores its choices as ten flat option_N / is_correct_N /
# explanation_N triples rather than a child table. These helpers are the only
# place that shape is dealt with, so the API and the client can both speak in
# terms of a plain list of answers.
MAX_OPTIONS = 10


def question_to_dict(name: str) -> dict:
	doc = frappe.get_doc("LMS Question", name)
	answers = []
	for index in range(1, MAX_OPTIONS + 1):
		option = doc.get(f"option_{index}")
		if not option:
			continue
		answers.append(
			{
				"index": index,
				"option": option,
				"is_correct": cint(doc.get(f"is_correct_{index}")),
				"explanation": doc.get(f"explanation_{index}"),
			}
		)
	return {
		"name": doc.name,
		"question": doc.question,
		"type": doc.type,
		"multiple": cint(doc.multiple),
		"answers": answers,
	}


def apply_answers(doc, answers: list[dict]) -> None:
	"""Write a list of answers back into the flat option_N fields.

	Every slot is cleared first: without that, shortening a five-answer
	question to three would leave options 4 and 5 in place and the learner
	would still see them.
	"""
	for index in range(1, MAX_OPTIONS + 1):
		doc.set(f"option_{index}", None)
		doc.set(f"is_correct_{index}", 0)
		doc.set(f"explanation_{index}", None)

	for slot, answer in enumerate(answers[:MAX_OPTIONS], start=1):
		doc.set(f"option_{slot}", (answer.get("option") or "").strip() or None)
		doc.set(f"is_correct_{slot}", 1 if answer.get("is_correct") else 0)
		doc.set(f"explanation_{slot}", answer.get("explanation") or None)


# Roles that may reach any quiz in the library. A quiz written outside a course
# has no course to check access against, so authorship stands in for it.
QUIZ_LIBRARY_ROLES = {"Moderator", "Course Creator"}


def can_manage_quiz(quiz_row) -> bool:
	"""Whether the session user may edit this quiz or place it in a course."""
	if quiz_row.get("course"):
		from lms.lms.utils import can_modify_course

		return bool(can_modify_course(quiz_row.get("course")))
	if QUIZ_LIBRARY_ROLES & set(frappe.get_roles()):
		return True
	return quiz_row.get("owner") == frappe.session.user


def enforce_quiz_access(quiz: str) -> str:
	"""Raise unless the session user may use this quiz. Returns its name.

	Quizzes written in the Quizzes section carry no course, so the course check
	the curriculum endpoints used to rely on simply did not run for them — every
	standalone quiz was editable by anyone who could reach the endpoint. Placing
	a quiz from the library goes through here for the same reason: otherwise a
	course author could pull any quiz on the site into their own course.
	"""
	row = frappe.db.get_value("LMS Quiz", quiz, ["name", "course", "owner"], as_dict=True)
	if not row:
		frappe.throw(_("Quiz {0} does not exist.").format(quiz), frappe.DoesNotExistError)
	if not can_manage_quiz(row):
		frappe.throw(_("You are not permitted to use this quiz."), frappe.PermissionError)
	return row.name


# Fetched-to-filtered ratio for the library listing. Access is decided per row in
# Python, so the query has to over-fetch to still fill a page after filtering.
LIBRARY_OVERFETCH = 4
LIBRARY_MAX_LIMIT = 50


@frappe.whitelist()
def list_quiz_library(course: str | None = None, search: str | None = None, limit: int = 20) -> list[dict]:
	"""Quizzes the session user may place in a course.

	Backs the "use an existing quiz" picker. Standalone quizzes — the ones
	written in the Quizzes section, which is where a teacher builds a question
	bank — come first, because they are what the picker exists to reach; a quiz
	already embedded in another course is offered after them.
	"""
	if course:
		enforce_course_access(course)

	limit = max(1, min(cint(limit) or 20, LIBRARY_MAX_LIMIT))
	filters = {}
	if search and search.strip():
		filters["title"] = ("like", f"%{search.strip()}%")

	candidates = frappe.get_all(
		"LMS Quiz",
		filters=filters,
		fields=["name", "title", "course", "owner", "passing_percentage", "max_attempts", "modified"],
		order_by="modified desc",
		limit=limit * LIBRARY_OVERFETCH,
	)

	allowed = [row for row in candidates if can_manage_quiz(row)]
	# The query already ordered by last edit; sorting on "belongs to a course" is
	# stable, so that order survives inside each group.
	allowed.sort(key=lambda row: 1 if row.course else 0)

	results = []
	for row in allowed[:limit]:
		row = dict(row)
		row["question_count"] = frappe.db.count("LMS Quiz Question", {"parent": row["name"]})
		row["course_title"] = (
			frappe.db.get_value("LMS Course", row["course"], "title") if row["course"] else None
		)
		results.append(row)
	return results


def release_quiz(lesson_doc) -> None:
	"""Detach the quiz a Quiz item currently points at, before it gets another.

	An empty quiz this item created is deleted: it exists only because the item
	did, and leaving it behind would fill the author's quiz list with blanks
	every time they changed their mind. A quiz with questions, with submissions,
	or reused from the library is kept and simply unlinked — a swap in one course
	is not permission to destroy work.
	"""
	quiz = lesson_doc.get("quiz")
	if not quiz:
		return

	lesson_doc.quiz = None
	# Cleared on the row as well as in memory so the delete below is not refused
	# for a link that only the caller's unsaved copy has dropped. Leaving
	# `modified` alone keeps the caller's own save() from tripping the timestamp
	# check on a document it is holding.
	frappe.db.set_value("Course Lesson", lesson_doc.name, "quiz", None, update_modified=False)

	if cint(lesson_doc.is_shared_activity):
		return

	has_questions = frappe.db.count("LMS Quiz Question", {"parent": quiz})
	has_submissions = frappe.db.exists("LMS Quiz Submission", {"quiz": quiz})
	if has_questions or has_submissions:
		frappe.db.set_value("LMS Quiz", quiz, "lesson", None)
		return

	frappe.delete_doc("LMS Quiz", quiz, force=1, ignore_permissions=True)


@frappe.whitelist()
def set_item_quiz(lesson: str, quiz: str | None = None) -> list[dict]:
	"""Point a Quiz item at a different quiz.

	With `quiz`, the item reuses that one from the library. Without it, the item
	goes back to owning a fresh empty quiz of its own, which is how an author
	undoes a reuse without deleting and re-adding the row.
	"""
	course = course_of_lesson(lesson)
	enforce_course_access(course)

	doc = frappe.get_doc("Course Lesson", lesson)
	if (doc.item_type or "Lecture") != "Quiz":
		frappe.throw(_("Only a quiz item can be linked to a quiz."))

	if quiz:
		target = enforce_quiz_access(quiz)
		if target == doc.quiz:
			return get_curriculum(course)
		release_quiz(doc)
		doc.quiz = target
		doc.is_shared_activity = 1
	else:
		if doc.quiz and not cint(doc.is_shared_activity):
			return get_curriculum(course)
		release_quiz(doc)
		doc.quiz = create_backing_document("Quiz", doc.title, course, doc.description)
		doc.is_shared_activity = 0

	doc.save()
	return get_curriculum(course)


# The quiz settings an author sets from the curriculum builder. Anything else on
# LMS Quiz stays with the desk form; these are the ones that change what a
# learner has to do, which is the decision the builder is for.
QUIZ_SETTING_FIELDS = (
	"passing_percentage",
	"max_attempts",
	"show_answers",
	"shuffle_questions",
	"block_progress_until_evaluated",
)


@frappe.whitelist()
def update_quiz_settings(quiz: str, **values) -> dict:
	"""Set the pass mark and attempt rules on a quiz.

	The pass mark is what makes a section-ending quiz a gate rather than a
	formality: `get_pending_quizzes` refuses to let the lesson close until the
	learner's best attempt reaches it.
	"""
	enforce_quiz_access(quiz)

	updates = {field: values[field] for field in QUIZ_SETTING_FIELDS if field in values}
	if not updates:
		return get_quiz(quiz)

	if "passing_percentage" in updates:
		percentage = cint(updates["passing_percentage"])
		if percentage < 0 or percentage > 100:
			frappe.throw(_("The pass mark has to be between 0 and 100."))
		updates["passing_percentage"] = percentage

	if "max_attempts" in updates:
		attempts = cint(updates["max_attempts"])
		if attempts < 0:
			frappe.throw(_("Attempts cannot be negative. Use 0 for unlimited."))
		updates["max_attempts"] = attempts

	for flag in ("show_answers", "shuffle_questions", "block_progress_until_evaluated"):
		if flag in updates:
			updates[flag] = 1 if cint(updates[flag]) else 0

	doc = frappe.get_doc("LMS Quiz", quiz)

	if "quiz_type" in values:
		requested = validate_quiz_type(values["quiz_type"])
		if requested != doc.quiz_type and doc.questions:
			# The two types take different questions — one has answers, the other has
			# nothing to compare against. Switching would silently invalidate every
			# question already written, so an author has to clear them first.
			frappe.throw(_("Remove the questions before changing the quiz type. They do not carry across."))
		updates["quiz_type"] = requested

	doc.update(updates)
	doc.save()
	return get_quiz(quiz)


@frappe.whitelist()
def get_quiz(quiz: str) -> dict:
	"""A quiz with its questions expanded into plain answer lists."""
	enforce_quiz_access(quiz)
	doc = frappe.get_doc("LMS Quiz", quiz)
	return {
		"name": doc.name,
		"title": doc.title,
		"quiz_type": doc.quiz_type or "Objective",
		"block_progress_until_evaluated": cint(doc.block_progress_until_evaluated),
		"passing_percentage": doc.passing_percentage,
		"total_marks": doc.total_marks,
		"max_attempts": doc.max_attempts,
		"show_answers": cint(doc.show_answers),
		"shuffle_questions": cint(doc.shuffle_questions),
		# `question` is the Link to LMS Question; `question_detail` on the same
		# child row is a fetched copy of the question text, not an id.
		# Marks live on the child row rather than the question, so a question reused
		# by two quizzes can be worth a different amount in each.
		"questions": [
			question_to_dict(row.question) | {"marks": cint(row.marks)}
			for row in doc.questions
			if row.question
		],
	}


MAX_QUESTION_MARKS = 100


@frappe.whitelist()
def save_quiz_question(
	quiz: str,
	question: str,
	answers: list | str | None = None,
	name: str | None = None,
	multiple: bool = False,
	marks: int = 1,
) -> dict:
	"""Create or update one question on a quiz.

	What a question needs depends on the quiz. An objective one needs answers and a
	correct one among them. A subjective one needs only the prompt and what it is
	worth — there is no answer to store, because the answer is whatever the learner
	writes and the evaluator judges.
	"""
	enforce_quiz_access(quiz)
	quiz_doc = frappe.get_doc("LMS Quiz", quiz)
	subjective = quiz_doc.quiz_type == "Subjective"

	if not (question or "").strip():
		frappe.throw(_("A question is required."))

	marks = cint(marks) or 1
	if marks < 1 or marks > MAX_QUESTION_MARKS:
		frappe.throw(_("Marks have to be between 1 and {0}.").format(MAX_QUESTION_MARKS))

	if isinstance(answers, str):
		answers = frappe.parse_json(answers)
	answers = [answer for answer in (answers or []) if (answer.get("option") or "").strip()]

	if not subjective:
		if len(answers) < 2:
			frappe.throw(_("A question needs at least two answers."))
		if not any(answer.get("is_correct") for answer in answers):
			frappe.throw(_("Mark at least one answer as correct."))

	doc = frappe.get_doc("LMS Question", name) if name else frappe.new_doc("LMS Question")

	doc.question = question
	doc.type = "Open Ended" if subjective else "Choices"
	doc.multiple = 0 if subjective else (1 if multiple else 0)
	# Cleared rather than left alone: a question that used to be objective must not
	# keep a stale answer key an evaluator's view would have no place to show.
	apply_answers(doc, [] if subjective else answers)
	doc.save()

	# The row's own `type` and `question_detail` are fetch_from copies of the question
	# and refresh themselves on save; only the marks are the row's to hold.
	row = next((row for row in quiz_doc.questions if row.question == doc.name), None)
	if row:
		row.marks = marks
	else:
		quiz_doc.append("questions", {"question": doc.name, "marks": marks})

	# calculate_total_marks() on the quiz recomputes the total from these rows.
	quiz_doc.save()

	return get_quiz(quiz)


@frappe.whitelist()
def delete_quiz_question(quiz: str, name: str) -> dict:
	"""Remove a question from a quiz and delete it."""
	enforce_quiz_access(quiz)
	quiz_doc = frappe.get_doc("LMS Quiz", quiz)

	remaining = [row for row in quiz_doc.questions if row.question != name]
	if len(remaining) == len(quiz_doc.questions):
		frappe.throw(_("That question is not on this quiz."))
	quiz_doc.questions = remaining
	# The total is recomputed from the rows by calculate_total_marks() on save.
	quiz_doc.save()
	frappe.delete_doc("LMS Question", name, force=1, ignore_permissions=True)
	return get_quiz(quiz)


# --------------------------------------------------------------------------
# Bulk upload
# --------------------------------------------------------------------------


@frappe.whitelist()
def create_lecture_from_upload(
	chapter: str,
	title: str,
	file_url: str,
	file_type: str,
	duration: float = 0,
	publish: bool = False,
) -> dict:
	"""Turn one uploaded video into a lecture, in a single call.

	The bulk uploader could do this with add_curriculum_item followed by
	set_lecture_video, but a failure between the two would leave an empty
	lecture in the curriculum that the author then has to find and delete. One
	endpoint means one unit of work: either the lecture exists with its video
	attached, or nothing was added.
	"""
	from lms.lms.course_creation import VIDEO_EXTENSIONS, set_lecture_video

	course = course_of_chapter(chapter)
	enforce_course_access(course)

	if (file_type or "").lower() not in VIDEO_EXTENSIONS:
		frappe.throw(_("{0} is not a supported video format.").format(file_type))

	title = (title or "").strip() or _("Untitled Lecture")

	lesson = frappe.new_doc("Course Lesson")
	lesson.update(
		{
			"title": title,
			"chapter": chapter,
			"course": course,
			"item_type": "Lecture",
			# Bulk-uploaded lectures follow the same draft-first rule as
			# hand-added ones unless the author opts in: a batch of raw footage
			# is rarely ready to show the moment it finishes uploading.
			"is_published": 1 if cint(publish) else 0,
		}
	)
	lesson.insert()

	set_lecture_video(lesson.name, file_url, file_type, duration)

	idx = frappe.db.count("Lesson Reference", {"parent": chapter}) + 1
	chapter_doc = frappe.get_doc("Course Chapter", chapter)
	chapter_doc.append("lessons", {"lesson": lesson.name, "idx": idx})
	chapter_doc.save()

	return {"lesson": lesson.name, "title": title}
