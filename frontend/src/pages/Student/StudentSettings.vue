<!--
	Settings. The Figma has the sidebar row but no frame. A student's settings in
	this LMS are their profile and their session, both of which already have real
	screens — so this is a short index onto them rather than a duplicate form
	that would drift from the profile editor.
-->
<template>
	<div class="flex h-full min-h-0 flex-col">
		<header
			class="shrink-0 border-b border-[var(--learno-line-soft)] bg-white px-6 py-[22px] lg:px-10"
		>
			<h1 class="text-[27px] font-semibold leading-[1.2] text-black max-lg:ps-12">
				{{ __('Settings') }}
			</h1>
		</header>

		<div
			class="learno-scroll min-h-0 flex-1 overflow-y-auto bg-[var(--learno-canvas)] px-6 py-7 lg:px-10"
		>
			<section class="mb-8 max-w-2xl rounded-[var(--learno-r-lg)] bg-white p-6">
				<h2 class="mb-4 text-[16px] font-semibold text-[var(--learno-ink-strong)]">
					{{ __('Account') }}
				</h2>

				<dl class="flex flex-col gap-3 text-[13px]">
					<div class="flex justify-between gap-4">
						<dt class="text-[var(--learno-ink-muted)]">{{ __('Name') }}</dt>
						<dd class="font-medium">{{ user?.full_name || '—' }}</dd>
					</div>
					<div class="flex justify-between gap-4">
						<dt class="text-[var(--learno-ink-muted)]">{{ __('Email') }}</dt>
						<dd class="font-medium">{{ user?.name || '—' }}</dd>
					</div>
					<div class="flex justify-between gap-4">
						<dt class="text-[var(--learno-ink-muted)]">{{ __('Username') }}</dt>
						<dd class="font-medium">{{ user?.username || '—' }}</dd>
					</div>
				</dl>

				<div class="mt-6 flex flex-wrap gap-2">
					<router-link
						v-if="user?.username"
						:to="{
							name: 'ProfileEditForm',
							params: { username: user.username },
						}"
						class="learno-btn learno-btn-primary px-5 py-2.5 text-[13px]"
					>
						{{ __('Edit profile') }}
					</router-link>
					<a
						href="/update-password"
						class="learno-btn learno-btn-secondary px-5 py-2.5 text-[13px]"
					>
						{{ __('Change password') }}
					</a>
				</div>
			</section>

			<section class="max-w-2xl rounded-[var(--learno-r-lg)] bg-white p-6">
				<h2 class="mb-4 text-[16px] font-semibold text-[var(--learno-ink-strong)]">
					{{ __('Session') }}
				</h2>
				<button
					type="button"
					class="learno-btn learno-btn-secondary px-5 py-2.5 text-[13px]"
					@click="logout.submit()"
				>
					<span class="lucide-log-out size-4" aria-hidden="true" />
					{{ __('Sign out') }}
				</button>
			</section>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, inject } from 'vue'
import { usePageMeta } from 'frappe-ui'
import { sessionStore } from '@/stores/session'

usePageMeta(() => ({ title: __('Settings') }))

const userResource = inject<any>('$user')
const { logout } = sessionStore()

const user = computed(() => userResource?.data)
</script>
