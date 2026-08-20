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

import { routes } from '@/routes'

function makeRouter() {
	return createRouter({ history: createMemoryHistory(), routes })
}

// The guard under test lives in router.js, which cannot be imported here: it
// constructs the real router against a browser history and pulls in pinia and
// frappe-ui at module scope. What this file locks down is the contract that
// guard depends on — the route table marking exactly one route public, and that
// route being reachable by name — plus a faithful re-statement of the redirect
// rule wired onto the real table.
function installAuthGuard(router: ReturnType<typeof makeRouter>, isLoggedIn: boolean) {
	router.beforeEach((to) => {
		if (!isLoggedIn && !to.meta.isPublic) {
			return {
				name: 'Login',
				query: to.fullPath === '/' ? {} : { redirect: to.fullPath },
			}
		}
		if (isLoggedIn && to.meta.isPublic) {
			return { name: 'Home' }
		}
		return true
	})
}

describe('login route', () => {
	it('is registered and is the only public route', () => {
		const publicRoutes = routes.filter((route: any) => route.meta?.isPublic)
		expect(publicRoutes.map((route: any) => route.name)).toEqual(['Login'])
		expect(publicRoutes[0].path).toBe('/login')
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

	it('keeps a signed-in user off the login page', async () => {
		const router = makeRouter()
		installAuthGuard(router, true)

		await router.push('/login')

		expect(router.currentRoute.value.name).toBe('Home')
	})
})
