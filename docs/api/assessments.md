[← API index](./README.md)

# Assessments

Quizzes, assignments and programming exercises.

A quiz is one of two kinds, set by `LMS Quiz.quiz_type` and fixed once it has
questions:

- **Objective** — carries its own answer key and is scored the moment it is
  submitted.
- **Subjective** — every question is open ended. There is no key, so submissions
  queue for a person to read. Who that person is comes from the assignment a
  Moderator makes on the `Course Evaluator` record.

A quiz is never both: mixed types would land half-scored and half-pending, with no
single percentage for the lesson gate to read.

| Endpoint | Guest | Writes |
| --- | --- | --- |
| [`get_assessments`](#get_assessments) | no | — |
| [`get_quiz_with_questions`](#get_quiz_with_questions) | no | — |
| [`submit_quiz`](#submit_quiz) | no | yes |
| [`check_answer`](#check_answer) | no | — |
| [`get_own_assignment_submission`](#get_own_assignment_submission) | yes | — |
| [`create_programming_exercise_submission`](#create_programming_exercise_submission) | no | yes |
| [`delete_programming_exercise`](#delete_programming_exercise) | no | yes |
| [`list_evaluation_queue`](#list_evaluation_queue) | no | — |
| [`get_evaluation`](#get_evaluation) | no | — |
| [`save_evaluation`](#save_evaluation) | no | yes |
| [`list_evaluators`](#list_evaluators) | no | — |
| [`set_evaluator_assignments`](#set_evaluator_assignments) | no | yes |
| [`get_course_evaluators`](#get_course_evaluators) | no | — |

---

## `get_assessments`

`lms.lms.utils.get_assessments` — **Guest: no** · *Enrolled students, or `can_modify_batch`*

Every assessment attached to a batch, in author order, each enriched with the
caller's own standing on it.

**Parameters** — `batch` (`str`, required).

**Returns** — array of assessments. Each row carries `name`, `assessment_type` and
`assessment_name`, plus type-specific detail merged in:

| `assessment_type` | Added by | Typical extra fields |
| --- | --- | --- |
| `LMS Assignment` | `get_assignment_details` | submission status, grade, submitted file |
| `LMS Quiz` | `get_quiz_details` | attempts, score, pass/fail |
| `LMS Programming Exercise` | `get_exercise_details` | latest submission, test-case results |

Throws if the caller is neither enrolled in the batch nor a batch admin.

---

## `get_quiz_with_questions`

`lms.lms.utils.get_quiz_with_questions` — **Guest: no** · *Requires `can_access_quiz`*

The quiz document **plus every question's full detail in a single round trip** —
options, explanations, type and multi-answer flag. Replaces N+1 per-question fetches.

Access is gated by `can_access_quiz`; a denial is logged to the `lms.security`
logger before the `PermissionError` is raised.

**Parameters** — `quiz` (`str`, required).

**Returns**

```json
{
  "quiz": { "name": "quiz-basics", "title": "Basics", "total_marks": 10,
            "passing_percentage": 60, "show_answers": 0, "questions": [ … ] },
  "questions_by_name": {
    "question-001": {
      "name": "question-001", "question": "What is 2+2?",
      "type": "Choices", "multiple": 0,
      "option_1": "3", "option_2": "4", "…": "…",
      "explanation_1": "…", "…": "…"
    }
  }
}
```

`quiz.questions` is the ordered child table of question references; look each one up
in `questions_by_name`. Correctness flags are not included in the option fields
returned here — grading happens server-side.

---

## `submit_quiz`

`lms.lms.doctype.lms_quiz.lms_quiz.submit_quiz` — **Guest: no** · **Writes** · *Requires `can_access_quiz`*

Grades a full quiz attempt, creates an `LMS Quiz Submission`, and advances lesson
progress if the attempt passes.

Score and percentage are read back **from the saved submission**, not recomputed
here, so the API result and the stored record cannot drift.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `quiz` | `str` | yes | `LMS Quiz` name. |
| `results` | `str` | no | JSON array of per-question answers. Omitted or empty is treated as an empty attempt. |

Each entry in `results` names a question and the submitted answer(s); the array is
validated before grading and a malformed entry raises `ValidationError`.

**Returns**

```json
{
  "score": 7,
  "score_out_of": 10,
  "submission": "quiz-sub-0912",
  "pass": true,
  "percentage": 70.0,
  "is_open_ended": false,
  "pending_evaluation": false,
  "blocks_progress": false
}
```

`is_open_ended` is `true` when the quiz contains questions requiring manual grading —
in that case `score` reflects only the auto-gradable portion.

For a **subjective** quiz the submission settles nothing on its own:

- `pending_evaluation` is `true` and the submission's `evaluation_status` is
  `Pending`. An objective submission is `Not Required`.
- `pass` is `null`, not `false` — reporting a failure the learner has not earned
  would be a lie. `score` is `0` until an evaluator awards marks.
- `blocks_progress` reports whether the lesson waits. When the quiz has
  `block_progress_until_evaluated` off, handing the work in completes the lesson
  immediately and the mark that arrives later never takes it back. When it is on,
  the lesson stays open until [`save_evaluation`](#save_evaluation) releases a
  passing result.

---

## `check_answer`

`lms.lms.doctype.lms_quiz.lms_quiz.check_answer` — **Guest: no**

Checks a single answer live, mid-quiz — the "show me if I got that right" affordance.

**Only available when the quiz has `show_answers` enabled**, unless the caller holds
System Manager, Moderator, Course Creator or Batch Evaluator. Otherwise it raises
`PermissionError`, so the endpoint cannot be used to farm answers from a quiz that
hides them.

The question must actually belong to the named quiz — cross-quiz probing raises
`PermissionError`.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `quiz` | `str` | yes | `LMS Quiz` name. |
| `question` | `str` | yes | `LMS Question` name. Must be a member of this quiz. |
| `question_type` | `str` | yes | `"Choices"` for option questions; anything else is treated as a free-text input. |
| `answers` | `str` | yes | JSON array. For `Choices`, the selected option values. For input questions, only the first element is used. |

An empty array — or the `[null]` an untouched input field emits — scores as
incorrect rather than erroring.

**Returns** — the correctness verdict for that question, with per-option detail for
`Choices` questions.

---

## `get_own_assignment_submission`

`lms.lms.api.get_own_assignment_submission` — **Guest: yes**

The name of the session user's submission for an assignment, or `null`.

Exists because the permission-filtered generic lookup (`frappe.client.get_value`)
keys on `owner` for students, while the uniqueness rule on
`LMS Assignment Submission` keys on `member`. A submission created *on a student's
behalf* therefore reads back as absent through the generic route, and the client
would try to insert a duplicate. This endpoint keys on `member`, matching the
constraint.

Guest-callable because read-only assignment views render on public lessons; a guest
owns no submission, so this returns `null` and the client routes to a new one.

**Parameters** — `assignment` (`str`, required).

**Returns** — `str` (submission docname) or `null`.

---

## `create_programming_exercise_submission`

`lms.lms.api.create_programming_exercise_submission` — **Guest: no** · **Writes** · *Roles: Moderator, Course Creator, Batch Evaluator*

Creates or updates a programming exercise submission with the submitted code and
its test-case results.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `exercise` | `str` | yes | `LMS Programming Exercise` name. |
| `submission` | `str` | yes | Existing submission docname to update, **or the literal string `"new"`** to create one. |
| `code` | `str` | yes | The submitted source. |
| `test_cases` | `list` | yes | Test-case results to record. |

**Returns** — the new submission's name when `submission` is `"new"`; `null` on
update.

---

## `delete_programming_exercise`

`lms.lms.api.delete_programming_exercise` — **Guest: no** · **Writes** · *Roles: Moderator, Course Creator, Batch Evaluator*

Deletes a programming exercise and every submission against it.

**Parameters** — `exercise` (`str`, required).

**Returns** — `null`.

---

## `list_evaluation_queue`

`lms.lms.evaluation.list_evaluation_queue` — **Guest: no** · *Scoped to the caller's assignments*

Subjective submissions waiting on the caller. Pending work is returned oldest
first — the queue exists to be emptied, so the longest wait surfaces first;
already-marked work is returned newest first.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `status` | `str` | no | `Pending` (default) or `Evaluated`. Anything else raises `ValidationError`. |
| `course` | `str` | no | Narrow to one course. Raises `PermissionError` if it is not assigned to the caller. |
| `search` | `str` | no | Matches learner name or quiz title. |
| `limit` | `int` | no | Page size, clamped to 1–100. Defaults to 20. |
| `start` | `int` | no | Offset. |

**Scope** — a Moderator sees every submission, including those from quizzes with no
course (a quiz used only through a batch), which no assignment could otherwise
reach. Everyone else sees the union of the courses assigned to them on their
`Course Evaluator` record, the courses inside the programs assigned to them, and
the courses they instruct. An unassigned caller gets an empty queue rather than an
error.

**Returns** — `{ submissions, total, courses, pending_count }`. `courses` lists only
courses that actually have work in them, for the filter control; `pending_count`
is the unmarked total under the same scope, so a badge does not need a second call.

---

## `get_evaluation`

`lms.lms.evaluation.get_evaluation` — **Guest: no** · *Scoped to the caller's assignments*

One submission expanded for review: the learner, the quiz, and every answer with
the marks awarded so far and what it is out of.

**Parameters** — `submission` (`str`, required).

Each entry in `answers` carries a `row` — the child row's name, which is what
[`save_evaluation`](#save_evaluation) addresses marks to. `blocks_progress` says
whether the learner's lesson is being held open by this submission.

Raises `PermissionError` if the submission's course is not in the caller's scope.

---

## `save_evaluation`

`lms.lms.evaluation.save_evaluation` — **Guest: no** · **Writes** · *Scoped to the caller's assignments*

Records an evaluator's marks against a submission.

**Parameters**

| Name | Type | Required | Description |
| --- | --- | --- | --- |
| `submission` | `str` | yes | `LMS Quiz Submission` name. |
| `marks` | `list` | no | `[{ row, marks, evaluator_feedback }]`. `row` comes from `get_evaluation`. |
| `comment` | `str` | no | An overall note to the learner. |
| `finalize` | `bool` | no | Defaults to `true`. |

`finalize: false` saves the marks without releasing them, so an evaluator part-way
through a long answer keeps their work without the learner being told the result is
final. `true` moves the submission to `Evaluated`, stamps the evaluator and time,
notifies the learner, and — if the quiz was holding the lesson open and the result
now passes — writes the learner's course progress.

Score and percentage are **never** accepted from the caller: the submission's own
`validate()` recomputes both from the marks, so the two cannot drift. A mark above
what the question is worth, or below zero, raises `ValidationError`.

Returns the same shape as `get_evaluation`.

---

## `list_evaluators`

`lms.lms.evaluation.list_evaluators` — **Guest: no** · *Moderator only*

Every evaluator with the courses and programs they have been given.

---

## `set_evaluator_assignments`

`lms.lms.evaluation.set_evaluator_assignments` — **Guest: no** · **Writes** · *Moderator only*

Replaces an evaluator's assignments wholesale — the lists sent are the lists they
end up with, so removing an assignment means sending it omitted.

**Parameters** — `evaluator` (`str`, required), `courses` (`list`), `programs` (`list`).

A program assignment is shorthand for its courses, expanded at read time rather
than stored. Adding a course to a program therefore reaches every evaluator on
that program without anyone re-assigning anything.

Returns the updated `list_evaluators` payload. Non-moderators raise
`PermissionError`; an unknown course or program raises `DoesNotExistError`.

---

## `get_course_evaluators`

`lms.lms.evaluation.get_course_evaluators` — **Guest: no** · *Requires `can_modify_course`*

Who can mark this course's subjective work, for the course's own settings page.
Each row carries `via`: `"course"` for a direct assignment, `"program"` for one
inherited through a program.

**Parameters** — `course` (`str`, required).
