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
		items.append(lesson)
	return items


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
			lesson
			for lesson in lessons
			if cint(frappe.db.get_value("Course Lesson", lesson, "is_published"))
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


def create_backing_document(item_type: str, title: str, course: str, description: str | None):
	"""Create the document a non-Lecture item delegates to, and return its name."""
	doctype, _field = BACKING_DOCTYPE[item_type]

	if item_type == "Quiz":
		doc = frappe.new_doc("LMS Quiz")
		doc.update(
			{
				"title": title,
				"course": course,
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
) -> dict:
	"""Append a new item of the given type to a section.

	The lesson row and its backing document are created together so a failed
	insert leaves neither behind — a lesson pointing at a quiz that does not
	exist would break the outline for everyone.
	"""
	course = course_of_chapter(chapter)
	enforce_course_access(course)
	validate_item_type(item_type)

	title = (title or "").strip() or _("Untitled {0}").format(_(item_type))
	backing = None
	if item_type in BACKING_DOCTYPE:
		backing = create_backing_document(item_type, title, course, description)

	lesson = frappe.new_doc("Course Lesson")
	lesson.update(
		{
			"title": title,
			"chapter": chapter,
			"course": course,
			"item_type": item_type,
			"description": description,
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
	if "title" in updates and doc.item_type in BACKING_DOCTYPE:
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
	if doc.item_type in BACKING_DOCTYPE and doc.get(BACKING_DOCTYPE[doc.item_type][1]):
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
	if doc.item_type in BACKING_DOCTYPE:
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
	doc.append(
		"resources", {"resource_type": resource_type, "title": title, "file": file, "url": url}
	)
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


@frappe.whitelist()
def get_quiz(quiz: str) -> dict:
	"""A quiz with its questions expanded into plain answer lists."""
	doc = frappe.get_doc("LMS Quiz", quiz)
	if doc.course:
		enforce_course_access(doc.course)
	return {
		"name": doc.name,
		"title": doc.title,
		"passing_percentage": doc.passing_percentage,
		"total_marks": doc.total_marks,
		"max_attempts": doc.max_attempts,
		"show_answers": cint(doc.show_answers),
		"shuffle_questions": cint(doc.shuffle_questions),
		# `question` is the Link to LMS Question; `question_detail` on the same
		# child row is a fetched copy of the question text, not an id.
		"questions": [question_to_dict(row.question) for row in doc.questions if row.question],
	}

@frappe.whitelist()
def save_quiz_question(
	quiz: str, question: str, answers: list | str, name: str | None = None, multiple: bool = False
) -> dict:
	"""Create or update one question on a quiz."""
	quiz_doc = frappe.get_doc("LMS Quiz", quiz)
	if quiz_doc.course:
		enforce_course_access(quiz_doc.course)

	if isinstance(answers, str):
		answers = frappe.parse_json(answers)
	answers = [answer for answer in (answers or []) if (answer.get("option") or "").strip()]

	if len(answers) < 2:
		frappe.throw(_("A question needs at least two answers."))
	if not any(answer.get("is_correct") for answer in answers):
		frappe.throw(_("Mark at least one answer as correct."))
	if not (question or "").strip():
		frappe.throw(_("A question is required."))

	doc = frappe.get_doc("LMS Question", name) if name else frappe.new_doc("LMS Question")

	doc.question = question
	doc.type = "Choices"
	doc.multiple = 1 if multiple else 0
	apply_answers(doc, answers)
	doc.save()

	if not name:
		quiz_doc.append("questions", {"question": doc.name, "marks": 1})
		# One mark per question. The quiz doctype requires a total, and any
		# other weighting is a decision the author has not been asked to make.
		quiz_doc.total_marks = len(quiz_doc.questions)
		quiz_doc.save()

	return get_quiz(quiz)


@frappe.whitelist()
def delete_quiz_question(quiz: str, name: str) -> dict:
	"""Remove a question from a quiz and delete it."""
	quiz_doc = frappe.get_doc("LMS Quiz", quiz)
	if quiz_doc.course:
		enforce_course_access(quiz_doc.course)

	remaining = [row for row in quiz_doc.questions if row.question != name]
	if len(remaining) == len(quiz_doc.questions):
		frappe.throw(_("That question is not on this quiz."))
	quiz_doc.questions = remaining
	quiz_doc.total_marks = len(remaining)
	quiz_doc.save()
	frappe.delete_doc("LMS Question", name, force=1, ignore_permissions=True)
	return get_quiz(quiz)
