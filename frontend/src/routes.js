// The route table lives in its own module, separate from router.js, so it can
// be imported without pulling in frappe-ui or the pinia stores that router.js
// wires up around it (the beforeEach guard, the persona check). That keeps
// tests able to assert against the REAL route table via `createRouter` with a
// memory history, rather than a copy that could drift from what router.js
// actually registers.
export const routes = [
	// The only route a signed-out visitor may reach. `meta.isPublic` is what the
	// guard in router.js keys off, so adding another public page is a one-line
	// change here rather than a name check inside the guard.
	{
		path: '/login',
		name: 'Login',
		component: () => import('@/pages/Login.vue'),
		meta: { isPublic: true, noLayout: true },
	},
	{
		path: '/',
		name: 'Home',
		component: () => import('@/pages/Home/Home.vue'),
	},
	{
		path: '/courses',
		name: 'Courses',
		component: () => import('@/pages/Courses/Courses.vue'),
		// Both children are static segments, so vue-router scores them above
		// the sibling '/courses/:courseName' and they win. The trade: a course
		// whose docname is literally `new` or `import` becomes unreachable.
		// Accepted and documented in the design — it is the same trade the app
		// already makes for '/batches/details/:batchName'. Deliberately not
		// guarded.
		children: [
			{
				path: 'new',
				name: 'NewCourse',
				component: () => import('@/pages/Forms/NewCourseForm.vue'),
			},
			{
				path: 'import',
				name: 'CourseImport',
				component: () => import('@/pages/Forms/CourseImportForm.vue'),
			},
		],
	},
	// The guided creation wizard and the editing shell it hands off to both own
	// their whole chrome (a dark command bar and a step rail), so they opt out
	// of the app layout rather than nesting inside it. Registered ahead of
	// '/courses/:courseName' — '/courses/create' would otherwise be read as a
	// course named "create", the same trade already documented for
	// '/courses/new'.
	{
		path: '/courses/create',
		name: 'CourseCreate',
		component: () =>
			import('@/pages/Courses/Create/CourseCreateWizard.vue'),
		meta: { noLayout: true },
	},
	// Registered before the '/courses/:courseName/manage/:step?' redirect so
	// 'assignment' and 'exercise' are read as their own editors rather than as
	// a legacy step named "assignment". Both are full-page editors with their
	// own chrome.
	{
		path: '/courses/:courseName/manage/assignment/:assignmentName',
		name: 'CourseAssignmentEditor',
		component: () => import('@/pages/Courses/Manage/AssignmentEditor.vue'),
		props: true,
		meta: { noLayout: true },
	},
	{
		path: '/courses/:courseName/manage/exercise/:exerciseName',
		name: 'CourseExerciseEditor',
		component: () => import('@/pages/Courses/Manage/ExerciseEditor.vue'),
		props: true,
		meta: { noLayout: true },
	},
	{
		// The standalone setup wizard that used to live here was folded into the
		// course tabs — it had grown duplicate curriculum, landing-page, pricing
		// and messages editors. Old links and bookmarks land on the course, with
		// the checklist's own entry point in its header.
		path: '/courses/:courseName/manage/:step?',
		redirect: (to) => ({
			name: 'CourseDetail',
			params: { courseName: to.params.courseName },
			hash: to.params.step === 'curriculum' ? '#editor' : '#settings',
			query: to.params.step === 'curriculum' ? { view: 'curriculum' } : {},
		}),
	},
	{
		path: '/courses/:courseName',
		name: 'CourseDetail',
		component: () => import('@/pages/Courses/CourseDetail.vue'),
		props: true,
		children: [
			{
				path: 'chapter/:chapterName',
				name: 'ChapterForm',
				component: () => import('@/pages/Forms/ChapterForm.vue'),
				props: true,
			},
			{
				path: 'enrollment/new',
				name: 'NewCourseEnrollment',
				component: () =>
					import('@/pages/Forms/CourseEnrollmentForm.vue'),
				props: true,
			},
		],
	},
	{
		path: '/courses/:courseName/learn/:chapterNumber-:lessonNumber',
		name: 'Lesson',
		component: () => import('@/pages/Lesson.vue'),
		props: true,
	},
	{
		path: '/courses/:courseName/certification',
		name: 'CourseCertification',
		component: () => import('@/pages/Courses/CourseCertification.vue'),
		props: true,
	},
	{
		path: '/courses/:courseName/learn/:chapterName',
		name: 'SCORMChapter',
		component: () => import('@/pages/SCORMChapter.vue'),
		props: true,
	},
	{
		path: '/batches',
		name: 'Batches',
		component: () => import('@/pages/Batches/Batches.vue'),
		children: [
			{
				path: 'new',
				name: 'NewBatch',
				component: () => import('@/pages/Forms/NewBatchForm.vue'),
			},
		],
	},
	{
		path: '/batches/details/:batchName',
		redirect: (to) => `/batches/${to.params.batchName}`,
	},
	{
		path: '/batches/:batchName',
		name: 'BatchDetail',
		component: () => import('@/pages/Batches/BatchDetail.vue'),
		props: true,
		children: [
			{
				path: 'certificates',
				name: 'BulkCertificates',
				component: () =>
					import('@/pages/Forms/BulkCertificatesForm.vue'),
				props: true,
			},
			// `new` is hard-coded rather than a :param (design doc Q3): neither
			// form has an edit mode, so `new` is the only value the param could
			// ever take.
			{
				path: 'live-class/new',
				name: 'NewLiveClass',
				component: () => import('@/pages/Forms/LiveClassForm.vue'),
				props: true,
			},
			{
				path: 'announcement/new',
				name: 'NewAnnouncement',
				component: () => import('@/pages/Forms/AnnouncementForm.vue'),
				props: true,
			},
			{
				path: 'course/new',
				name: 'NewBatchCourse',
				component: () => import('@/pages/Forms/BatchCourseForm.vue'),
				props: true,
			},
			{
				path: 'assessment/new',
				name: 'NewAssessment',
				component: () => import('@/pages/Forms/AssessmentForm.vue'),
				props: true,
			},
			{
				path: 'student/new',
				name: 'NewBatchStudent',
				component: () => import('@/pages/Forms/BatchStudentForm.vue'),
				props: true,
			},
			{
				path: 'email-template/new',
				name: 'NewBatchEmailTemplate',
				component: () => import('@/pages/Forms/EmailTemplateForm.vue'),
				props: true,
			},
		],
	},
	{
		path: '/billing/:type/:name',
		name: 'Billing',
		component: () => import('@/pages/Billing.vue'),
		props: true,
	},
	{
		path: '/statistics',
		name: 'Statistics',
		component: () => import('@/pages/Statistics.vue'),
	},
	{
		path: '/user/:username',
		name: 'Profile',
		component: () => import('@/pages/Profile.vue'),
		props: true,
		redirect: { name: 'ProfileAbout' },
		children: [
			{
				name: 'ProfileAbout',
				path: '',
				component: () => import('@/pages/ProfileAbout.vue'),
			},
			{
				name: 'ProfileCertificates',
				path: 'certificates',
				component: () => import('@/pages/ProfileCertificates.vue'),
			},
			{
				name: 'ProfileRoles',
				path: 'roles',
				component: () => import('@/pages/ProfileRoles.vue'),
			},
			{
				name: 'ProfileEvaluator',
				path: 'slots',
				component: () => import('@/pages/ProfileEvaluator.vue'),
			},
			{
				name: 'ProfileEvaluationSchedule',
				path: 'schedule',
				component: () =>
					import('@/pages/ProfileEvaluationSchedule.vue'),
			},
			{
				name: 'ProfileEditForm',
				path: 'edit',
				component: () => import('@/pages/Forms/ProfileEditForm.vue'),
				props: true,
			},
		],
	},
	{
		path: '/certified-participants',
		name: 'CertifiedParticipants',
		component: () => import('@/pages/CertifiedParticipants.vue'),
	},
	{
		path: '/quizzes',
		name: 'Quizzes',
		component: () => import('@/pages/Quizzes.vue'),
	},
	{
		path: '/quizzes/:quizID',
		name: 'QuizForm',
		component: () => import('@/pages/Forms/QuizForm.vue'),
		props: true,
		children: [
			{
				// :questionName is the LMS Quiz Question ROW name, or 'new'. It is
				// NOT the LMS Question docname — marks lives on the row. See design R2.
				path: 'question/:questionName',
				name: 'QuizQuestion',
				component: () => import('@/pages/Forms/QuizQuestionForm.vue'),
				props: true,
			},
		],
	},
	{
		path: '/quiz/:quizID',
		name: 'QuizPage',
		component: () => import('@/pages/QuizPage.vue'),
		props: true,
	},
	{
		path: '/quiz-submissions/:quizID',
		name: 'QuizSubmissionList',
		component: () => import('@/pages/QuizSubmissionList.vue'),
		props: true,
	},
	{
		path: '/quiz-submission/:submission',
		name: 'QuizSubmission',
		component: () => import('@/pages/QuizSubmission.vue'),
		props: true,
	},
	{
		path: '/programs',
		name: 'Programs',
		component: () => import('@/pages/Programs/Programs.vue'),
		children: [
			{
				// `/edit` is mandatory, not stylistic. A bare `:programName` child
				// would produce a path byte-identical to the sibling ProgramDetail
				// route below with the same match score; vue-router keeps both and
				// serves whichever was registered first — this one — which would
				// silently break every student-facing program link.
				path: ':programName/edit',
				name: 'ProgramForm',
				component: () => import('@/pages/Forms/ProgramForm.vue'),
				props: true,
			},
			{
				// Nested for the same reason `/edit` is, plus one of its own: the
				// student list keeps its selected tab in a local ref, and staying a
				// child is what keeps that list mounted so cancelling lands back on
				// the tab the student opened this from.
				path: ':programName/enroll',
				name: 'ProgramEnrollment',
				component: () =>
					import('@/pages/Programs/ProgramEnrollment.vue'),
				props: true,
			},
		],
	},
	{
		path: '/programs/:programName',
		name: 'ProgramDetail',
		component: () => import('@/pages/Programs/ProgramDetail.vue'),
		props: true,
	},
	{
		path: '/assignments',
		name: 'Assignments',
		component: () => import('@/pages/Assignments.vue'),
		children: [
			{
				path: ':assignmentID',
				name: 'AssignmentForm',
				component: () => import('@/pages/Forms/AssignmentForm.vue'),
				props: true,
			},
		],
	},
	{
		path: '/assignment-submission/:assignmentID/:submissionName',
		name: 'AssignmentSubmission',
		component: () => import('@/pages/AssignmentSubmission.vue'),
		props: true,
	},
	{
		path: '/assignment-submissions',
		name: 'AssignmentSubmissionList',
		component: () => import('@/pages/AssignmentSubmissionList.vue'),
	},
	{
		path: '/persona',
		name: 'PersonaForm',
		component: () => import('@/pages/Forms/PersonaForm.vue'),
	},
	{
		path: '/programming-exercises',
		name: 'ProgrammingExercises',
		component: () =>
			import('@/pages/ProgrammingExercises/ProgrammingExercises.vue'),
		children: [
			{
				// The `edit/` prefix is mandatory, not stylistic: a bare
				// `:exerciseID` child would also match the sibling static
				// `/programming-exercises/submissions` below, and vue-router
				// scores the child higher than a later-registered static route
				// only by accident of ordering. `edit/` keeps the two apart.
				path: 'edit/:exerciseID',
				name: 'ProgrammingExerciseForm',
				component: () =>
					import('@/pages/Forms/ProgrammingExerciseForm.vue'),
				props: true,
			},
		],
	},
	{
		path: '/programming-exercises/submissions',
		name: 'ProgrammingExerciseSubmissions',
		component: () =>
			import('@/pages/ProgrammingExercises/ProgrammingExerciseSubmissions.vue'),
		props: true,
	},
	{
		path: '/programming-exercises/:exerciseID/submission/:submissionID',
		name: 'ProgrammingExerciseSubmission',
		component: () =>
			import('@/pages/ProgrammingExercises/ProgrammingExerciseSubmission.vue'),
		props: true,
	},
	{
		path: '/data-import',
		name: 'DataImportList',
		component: () => import('@/pages/DataImport.vue'),
	},
	{
		path: '/data-import/doctype/:doctype',
		name: 'NewDataImport',
		component: () => import('@/pages/DataImport.vue'),
		props: true,
	},
	{
		path: '/data-import/:importName',
		name: 'DataImport',
		component: () => import('@/pages/DataImport.vue'),
		props: true,
	},
	// The You tab. Only the phone layout offers it — the desk sidebar already
	// shows everything on it — but it is an ordinary route, so it answers a cold
	// deep link with no bar mounted the same way it answers a tap.
	{
		path: '/you',
		name: 'MobileYou',
		component: () => import('@/pages/MobileYou.vue'),
	},
	// The only thing under '/settings' with an address. Settings itself is the
	// desktop dialog, which floats over whatever page the URL points at and has
	// no route of its own — an LMS is not configured with a thumb, so there are
	// no phone settings pages for this to sit beside any more.
	//
	// The path is kept because it reads correctly and Members.vue opens the form
	// by NAME, not by path, so nothing depends on the prefix resolving;
	// '/settings' and '/settings/:item' now fall through to NotFound.
	{
		path: '/settings/users/:memberID',
		name: 'MemberForm',
		component: () => import('@/pages/Forms/MemberForm.vue'),
		props: true,
	},
	// ------------------------------------------------------------------ /learn
	// The student experience built from the Learno Figma. It is a sibling tree
	// rather than a re-skin of the pages above: the two designs disagree about
	// what the same semantic token means (see src/styles/learno.css), and the
	// pages above are shared with the author/moderator app, which this design
	// does not describe.
	//
	// `meta.layout: 'student'` is what App.vue keys the shell off, the same way
	// `meta.noLayout` already selects NoSidebarLayout.
	{
		path: '/learn',
		name: 'StudentDashboard',
		component: () => import('@/pages/Student/StudentDashboard.vue'),
		meta: { layout: 'student' },
	},
	{
		path: '/learn/courses',
		name: 'StudentCourses',
		component: () => import('@/pages/Student/StudentCourses.vue'),
		meta: { layout: 'student' },
	},
	{
		path: '/learn/courses/:courseName',
		name: 'StudentCourseDetail',
		component: () => import('@/pages/Student/StudentCourseDetail.vue'),
		meta: { layout: 'student' },
	},
	{
		path: '/learn/courses/:courseName/session/:chapterNumber-:lessonNumber',
		name: 'StudentSession',
		component: () => import('@/pages/Student/StudentSession.vue'),
		meta: { layout: 'student' },
	},
	{
		path: '/learn/calendar',
		name: 'StudentCalendar',
		component: () => import('@/pages/Student/StudentCalendar.vue'),
		meta: { layout: 'student' },
	},
	{
		path: '/learn/materials',
		name: 'StudentMaterials',
		component: () => import('@/pages/Student/StudentMaterials.vue'),
		meta: { layout: 'student' },
	},
	{
		path: '/learn/chats',
		name: 'StudentChats',
		component: () => import('@/pages/Student/StudentChats.vue'),
		meta: { layout: 'student' },
	},
	{
		path: '/learn/support',
		name: 'StudentSupport',
		component: () => import('@/pages/Student/StudentSupport.vue'),
		meta: { layout: 'student' },
	},
	{
		path: '/learn/settings',
		name: 'StudentSettings',
		component: () => import('@/pages/Student/StudentSettings.vue'),
		meta: { layout: 'student' },
	},
	{
		path: '/:pathMatch(.*)*',
		name: 'NotFound',
		component: () => import('@/pages/NotFound.vue'),
	},
]
