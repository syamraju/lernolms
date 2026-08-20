[← API index](./README.md)

# Assessments

Quizzes, assignments and programming exercises.

| Endpoint | Guest | Writes |
| --- | --- | --- |
| [`get_assessments`](#get_assessments) | no | — |
| [`get_quiz_with_questions`](#get_quiz_with_questions) | no | — |
| [`submit_quiz`](#submit_quiz) | no | yes |
| [`check_answer`](#check_answer) | no | — |
| [`get_own_assignment_submission`](#get_own_assignment_submission) | yes | — |
| [`create_programming_exercise_submission`](#create_programming_exercise_submission) | no | yes |
| [`delete_programming_exercise`](#delete_programming_exercise) | no | yes |

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
  "is_open_ended": false
}
```

`is_open_ended` is `true` when the quiz contains questions requiring manual grading —
in that case `score` reflects only the auto-gradable portion.

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
