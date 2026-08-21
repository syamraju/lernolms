import { createRouter, createWebHistory } from 'vue-router'
import { call } from 'frappe-ui'
import { usersStore } from './stores/user'
import { sessionStore } from './stores/session'
import { getLmsBasePath } from './utils/basePath'
import { routes } from './routes'

// Run the fresh-site-admin persona check at most once per app load.
let personaChecked = false

// Same, for the provisioned-password gate. Once per load is enough because
// `provision_temporary_password` drops the user's existing sessions: a re-issue
// ends the session it would otherwise have had to interrupt, so the next thing
// that user does is sign in, and `on_login` lands them on the screen anyway.
let passwordChecked = false

async function shouldCapturePersona() {
	const captured = await call('frappe.client.get_single_value', {
		doctype: 'LMS Settings',
		field: 'persona_captured',
	})
	if (captured) return false
	const courseCount = await call('frappe.client.get_count', {
		doctype: 'LMS Course',
		filters: {
			// Sites seeded before the Learno rebrand still carry the old demo
			// title, so neither spelling counts as a course the user made.
			title: [
				'not in',
				['A guide to Learno', 'A guide to Frappe Learning'],
			],
		},
	})
	return !courseCount
}

// `is_student` is set for everyone, so it cannot tell the two apps apart.
// Authoring rights are what decide whether there is an admin app to land on.
function isLearnerOnly(user) {
	if (!user) return false
	return !(
		user.is_moderator ||
		user.is_instructor ||
		user.is_system_manager ||
		user.is_evaluator
	)
}

let router = createRouter({
	history: createWebHistory(`/${getLmsBasePath()}`),
	routes,
})

router.beforeEach(async (to, from, next) => {
	const { userResource } = usersStore()
	let { isLoggedIn } = sessionStore()

	try {
		if (isLoggedIn) {
			await userResource.promise
		}
	} catch (error) {
		isLoggedIn = false
	}

	// Sign-in comes before anything else in the app: a signed-out visitor gets
	// the login page, not a browsable catalogue. This deliberately ignores the
	// `allow_guest_access` LMS setting for in-app routes — the public surface is
	// now the website pages Frappe serves outside the SPA, not this bundle.
	if (!isLoggedIn && !to.meta.isPublic) {
		return next({
			name: 'Login',
			query: to.fullPath === '/' ? {} : { redirect: to.fullPath },
		})
	}

	// An account still holding a provisioned password goes nowhere else. The
	// temporary one was mailed, so it stays a working credential in an inbox
	// until it is replaced — letting the user dismiss the prompt and carry on
	// would leave it valid indefinitely. `on_login` sets the landing page; this
	// is what makes it stick across navigation, and it also catches a re-issue
	// that happened while the user was already signed in on another tab.
	if (isLoggedIn && !passwordChecked && to.name !== 'SetPassword') {
		passwordChecked = true
		try {
			if (await call('lms.lms.user.must_reset_password')) {
				return next({ name: 'SetPassword' })
			}
		} catch (_) {
			// Fail open: a transient API error must not lock the app.
		}
	}

	if (isLoggedIn && to.meta.isPublic) {
		return next({ name: 'Home' })
	}

	// A learner with no authoring rights has nothing to do in the admin app, so
	// the root hands them the student shell instead. Anyone who can author or
	// moderate still lands on the admin home and reaches /learn from the sidebar
	// — the switch has to work both ways for the people who need both.
	if (isLoggedIn && to.name === 'Home' && isLearnerOnly(userResource.data)) {
		return next({ name: 'StudentDashboard' })
	}

	if (
		isLoggedIn &&
		!personaChecked &&
		to.name !== 'PersonaForm' &&
		userResource.data?.is_system_manager &&
		!userResource.data?.developer_mode
	) {
		personaChecked = true
		try {
			if (await shouldCapturePersona()) {
				return next({ name: 'PersonaForm' })
			}
		} catch (_) {
			// Fail open: a transient API error must not block navigation.
		}
	}

	return next()
})

export default router
