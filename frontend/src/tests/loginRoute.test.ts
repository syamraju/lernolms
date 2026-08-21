import { describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import { defineComponent, h } from 'vue'

vi.stubGlobal('__', (text: string) => text)

// vue-router resolves a matched record's async `component()` during navigation,
// so the page SFC is stubbed (it imports frappe-ui, which does not resolve under
// plain Node module resolution). The route TABLE is the genuine one.
vi.mock('@/pages/Login.vue', () => ({
	default: defineComponent({ render: () => h('div') }),
}))
vi.mock('@/pages/Home/Home.vue', () => ({
	default: defineComponent({ render: () => h('div') }),
}))
vi.mock('@/pages/Courses/Courses.vue', () => ({
	default: defineComponent({ render: () => h('div') }),
}))
vi.mock('@/pages/CertificateVerification.vue', () => ({
	default: defineComponent({ render: () => h('div') }),
}))

import { routes } from '@/routes'

function makeRouter() {
	return createRouter({ history: createMemoryHistory(), routes })
}

// The guard under test lives in router.js, which cannot be imported here: it
// constructs the real router against a browser history and pulls in pinia and
// frappe-ui at module scope. What this file locks down is the contract that
// guard depends on — which routes are marked public, and why each one is —
// plus a faithful re-statement of the redirect rule wired onto the real table.
//
// "Faithful" is load-bearing and this stub had already drifted once: it kept
// sending every signed-in visitor away from any public route after router.js
// had learned to exempt `allowLoggedIn`. A stub that is a copy rather than the
// original only earns its keep if a change to the original that it fails to
// mirror is caught here — so the two must be diffed by eye when either moves.
function installAuthGuard(router: ReturnType<typeof makeRouter>, isLoggedIn: boolean) {
	router.beforeEach((to) => {
		if (!isLoggedIn && !to.meta.isPublic) {
			return {
				name: 'Login',
				query: to.fullPath === '/' ? {} : { redirect: to.fullPath },
			}
		}
		if (isLoggedIn && to.meta.isPublic && !to.meta.allowLoggedIn) {
			return { name: 'Home' }
		}
		return true
	})
}

// Every route reachable without an account, and the reason it is one. Kept as an
// exact set rather than a count or a "some exist" check: the point is that a
// third public door cannot arrive unreviewed. Adding one means adding it here,
// with its reason, which is the review.
//
//   Login                   — the way in. Nobody can sign in from behind a
//                             sign-in wall.
//   CertificateVerification — the whole purpose is that a stranger with no
//                             account can check a certificate somebody showed
//                             them. `allowLoggedIn` because the learner who
//                             earned it must be able to open it too; without it
//                             they are the one person the guard bounces Home.
const PUBLIC_ROUTES: Record<string, { path: string; allowLoggedIn: boolean }> = {
	Login: { path: '/login', allowLoggedIn: false },
	CertificateVerification: { path: '/verify/:code', allowLoggedIn: true },
}

describe('login route', () => {
	it('is public, and so is exactly one other route', () => {
		const publicRoutes = routes.filter((route: any) => route.meta?.isPublic)
		const byName = Object.fromEntries(
			publicRoutes.map((route: any) => [
				route.name,
				{ path: route.path, allowLoggedIn: Boolean(route.meta.allowLoggedIn) },
			])
		)

		expect(byName).toEqual(PUBLIC_ROUTES)
	})

	it('renders without the app chrome', () => {
		const login = routes.find((route: any) => route.name === 'Login') as any
		expect(login.meta.noLayout).toBe(true)
	})

	it('sends a signed-out visitor to login instead of the catalogue', async () => {
		const router = makeRouter()
		installAuthGuard(router, false)

		await router.push('/courses')

		expect(router.currentRoute.value.name).toBe('Login')
		expect(router.currentRoute.value.query.redirect).toBe('/courses')
	})

	it('does not carry a redirect back to the root', async () => {
		const router = makeRouter()
		installAuthGuard(router, false)

		await router.push('/')

		expect(router.currentRoute.value.name).toBe('Login')
		expect(router.currentRoute.value.query.redirect).toBeUndefined()
	})

	it('lets a signed-in learner open the certificate they earned', async () => {
		// The regression b3bcecb fixed: the guard sent every signed-in visitor
		// away from anything marked `isPublic`, so a learner following their own
		// "view certificate" link landed on Home.
		const router = makeRouter()
		installAuthGuard(router, true)

		await router.push('/verify/abc123')

		expect(router.currentRoute.value.name).toBe('CertificateVerification')
	})

	it('keeps a signed-in user off the login page', async () => {
		const router = makeRouter()
		installAuthGuard(router, true)

		await router.push('/login')

		expect(router.currentRoute.value.name).toBe('Home')
	})
})
