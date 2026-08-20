<!--
	The student navigation panel. Figma: node 68:11759 ("Frame 6").

	Two things the design does not say, decided here:

	1. The rows are real router-links, so the active state comes from the route
	   rather than a prop. The Figma shows "Courses" selected with a white card
	   + soft blue hairline + the file's one elevation; that is `is-active`.
	2. The footer identity card links to the profile the app already has, and —
	   for anyone who can author or moderate — carries the way back into the
	   admin app. A student never sees that entry.
-->
<template>
	<aside
		class="flex h-full w-[314px] shrink-0 flex-col justify-between overflow-y-auto learno-scroll rounded-[var(--learno-r-sm)] bg-white px-3 py-[22px]"
	>
		<div class="flex flex-col gap-[25px]">
			<!-- Brand -->
			<router-link
				:to="{ name: 'StudentDashboard' }"
				class="flex items-center justify-between rounded-[var(--learno-r-lg)] bg-[var(--learno-primary-soft)] p-[15px] transition hover:brightness-[0.98]"
			>
				<span class="flex items-end gap-2.5">
					<LearnoMark
						class="h-[34px] w-[35px] shrink-0 text-[var(--learno-primary)]"
						:label="brandName"
					/>
					<span class="flex flex-col leading-none">
						<span class="text-[22px] font-semibold text-[#272727]">
							{{ brandName }}
						</span>
						<span class="mt-0.5 text-[13px] text-[#272727]">
							{{ __('edu') }}
						</span>
					</span>
				</span>
				<span
					class="lucide-arrow-up-right size-6 text-[var(--learno-primary)]"
					aria-hidden="true"
				/>
			</router-link>

			<!-- Primary navigation -->
			<nav class="flex flex-col gap-1.5" :aria-label="__('Main')">
				<SidebarRow
					v-for="item in primary"
					:key="item.label"
					v-bind="item"
				/>
			</nav>
		</div>

		<div class="flex flex-col gap-[18px]">
			<nav class="flex flex-col gap-[11px]" :aria-label="__('Support')">
				<SidebarRow v-for="item in secondary" :key="item.label" v-bind="item" />
			</nav>

			<!-- Identity card -->
			<component
				:is="user?.username ? 'router-link' : 'div'"
				:to="
					user?.username
						? { name: 'Profile', params: { username: user.username } }
						: undefined
				"
				class="flex items-center justify-between rounded-[var(--learno-r-lg)] border border-[var(--learno-line)] bg-white px-3.5 py-4 transition"
				:class="user?.username && 'hover:border-[#d8dae3]'"
			>
				<span class="flex min-w-0 items-center gap-4">
					<img
						v-if="user?.user_image"
						:src="safeUrl(user.user_image)"
						alt=""
						class="size-10 shrink-0 rounded-full object-cover"
					/>
					<span
						v-else
						class="grid size-10 shrink-0 place-items-center rounded-full bg-[var(--learno-primary-soft)] text-[15px] font-semibold text-[var(--learno-primary)]"
					>
						{{ initials }}
					</span>
					<span class="flex min-w-0 flex-col gap-[3px]">
						<span class="truncate text-[16px] text-[var(--learno-ink)]">
							{{ user?.full_name || __('Guest') }}
						</span>
						<span
							class="truncate text-[14px] leading-[18px] text-[var(--learno-ink-subtle)]"
						>
							{{ user?.name || __('Not signed in') }}
						</span>
					</span>
				</span>
				<span
					class="lucide-chevron-right size-4 shrink-0 text-[var(--learno-ink-subtle)] rtl:rotate-180"
					aria-hidden="true"
				/>
			</component>

			<!-- The way back into the authoring/admin app. Only shown to accounts
			     that actually have somewhere to go, so a student's sidebar matches
			     the Figma exactly. -->
			<div v-if="canAdminister" class="flex flex-col gap-1.5">
				<a
					:href="safeUrl(adminHref)"
					class="learno-btn learno-btn-secondary w-full"
					data-testid="learno-admin-link"
				>
					<span class="lucide-layout-dashboard size-4" aria-hidden="true" />
					{{ __('Switch to admin') }}
				</a>
				<a
					v-if="user?.is_system_manager"
					href="/app"
					class="learno-btn learno-btn-secondary w-full"
				>
					<span class="lucide-terminal size-4" aria-hidden="true" />
					{{ __('Open desk') }}
				</a>
			</div>

			<button
				type="button"
				class="learno-btn learno-btn-secondary w-full"
				@click="signOut"
			>
				<span class="lucide-log-out size-4" aria-hidden="true" />
				{{ __('Sign out') }}
			</button>
		</div>
	</aside>
</template>

<script setup lang="ts">
import { computed, inject } from 'vue'
import { sessionStore } from '@/stores/session'
import { getLmsRoute } from '@/utils/basePath'
import { unreadCount } from '@/stores/notifications'
import LearnoMark from '@/components/Learno/LearnoMark.vue'
import SidebarRow from '@/components/Learno/SidebarRow.vue'
import { safeUrl } from '@/utils/safeUrl'

const userResource = inject<any>('$user')
const { brand, logout } = sessionStore()

const user = computed(() => userResource?.data)
const brandName = computed(() => brand.name || 'Learno')

const initials = computed(() => {
	const name = user.value?.full_name || user.value?.name || '?'
	return name
		.split(/\s+/)
		.slice(0, 2)
		.map((part: string) => part.charAt(0).toUpperCase())
		.join('')
})

// `is_student` is true for everyone, so it cannot distinguish the two apps.
// Authoring rights are what decide whether there is an admin side to switch to.
const canAdminister = computed(
	() =>
		Boolean(user.value?.is_moderator) ||
		Boolean(user.value?.is_instructor) ||
		Boolean(user.value?.is_system_manager)
)

// The admin app is the same SPA under the same base, so this is a plain
// document link to its root rather than a router push — the two shells do not
// share a layout and a full load is the honest transition.
const adminHref = computed(() => getLmsRoute('/'))

const primary = computed(() => [
	{
		label: __('Dashboard'),
		icon: 'lucide-layout-grid',
		to: { name: 'StudentDashboard' },
	},
	{
		label: __('Courses'),
		icon: 'lucide-video',
		to: { name: 'StudentCourses' },
		// The course pages live under the courses branch; keep the row lit there.
		match: ['StudentCourses', 'StudentCourseDetail', 'StudentSession'],
	},
	{
		label: __('Chats'),
		icon: 'lucide-message-square',
		to: { name: 'StudentChats' },
		count: unreadCount.value || 0,
	},
	{
		label: __('Calendar'),
		icon: 'lucide-calendar',
		to: { name: 'StudentCalendar' },
	},
	{
		label: __('Materials'),
		icon: 'lucide-folder',
		to: { name: 'StudentMaterials' },
	},
])

const secondary = computed(() => [
	{
		label: __('Support'),
		icon: 'lucide-headphones',
		to: { name: 'StudentSupport' },
	},
	{
		label: __('Settings'),
		icon: 'lucide-settings',
		to: { name: 'StudentSettings' },
	},
	{
		label: __('Terms and Conditions'),
		icon: 'lucide-file-text',
		href: '/terms-of-use',
	},
])

function signOut() {
	logout.submit()
}
</script>
