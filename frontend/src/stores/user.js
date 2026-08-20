import { defineStore } from 'pinia'
import { createResource } from 'frappe-ui'
import { getLmsRoute } from '@/utils/basePath'

export const usersStore = defineStore('lms-users', () => {
	let userResource = createResource({
		url: 'lms.lms.api.get_user_info',
		onError(error) {
			if (error && error.exc_type === 'AuthenticationError') {
				// The app's own login page, not Frappe's desk one — a session that
				// expires mid-visit must land where a cold visit lands.
				window.location.href = getLmsRoute('/login')
			}
		},
	})

	const allUsers = createResource({
		url: 'lms.lms.api.get_all_users',
		cache: ['allUsers'],
	})

	return {
		userResource,
		allUsers,
	}
})
