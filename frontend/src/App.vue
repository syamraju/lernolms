<template>
	<FrappeUIProvider>
		<Layout class="isolate text-p-base">
			<router-view />
		</Layout>
		<!-- Signed-out chrome is nothing but the page itself. Both of these read
		     session-scoped data, and the PWA prompt in particular has no business
		     interrupting someone who has not signed in yet. -->
		<NotificationPanel v-if="!isPublicRoute" />
		<InstallPrompt
			v-if="!isPublicRoute && isMobile && !settings.data?.disable_pwa"
		/>
		<Dialogs />
	</FrappeUIProvider>
</template>
<script setup>
import { FrappeUIProvider } from 'frappe-ui'
import { Dialogs } from '@/utils/dialogs'
import { computed } from 'vue'
import { useScreenSize } from './utils/composables'
import { useSettings } from '@/stores/settings'
import { useRoute } from 'vue-router'
import DesktopLayout from './components/Layouts/DesktopLayout.vue'
import MobileLayout from './components/Layouts/MobileLayout.vue'
import NoSidebarLayout from './components/Layouts/NoSidebarLayout.vue'
import StudentLayout from './components/Layouts/StudentLayout.vue'
import InstallPrompt from './components/InstallPrompt.vue'
import NotificationPanel from '@/components/Notifications/NotificationPanel.vue'

const { isMobile } = useScreenSize()
const route = useRoute()
const { settings } = useSettings()

// Derive the layout from the current route, not a navigation guard. Flipping it
// in beforeEach swaps the layout the instant a navigation starts (before a lazy
// route component resolves), which re-mounts <router-view> while the old page is
// still showing, flashing it back into view. A route-driven computed changes in
// the same tick as the route, so the swap and the page change happen together.
const isPublicRoute = computed(() => Boolean(route.meta.isPublic))

const noSidebar = computed(
	() =>
		Boolean(route.query.fromLesson) ||
		route.path === '/persona' ||
		Boolean(route.meta.noLayout)
)

const Layout = computed(() => {
	// The student shell before the mobile check: it carries its own responsive
	// behaviour (the sidebar becomes a drawer), so routing it through
	// MobileLayout would nest two chromes.
	if (route.meta.layout === 'student') {
		return StudentLayout
	}
	if (noSidebar.value) {
		return NoSidebarLayout
	}
	if (isMobile.value) {
		return MobileLayout
	}
	return DesktopLayout
})
</script>
