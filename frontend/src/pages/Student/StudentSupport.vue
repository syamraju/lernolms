<!--
	Support. The Figma has the sidebar row but no frame; this keeps to the
	design's card vocabulary and routes to the help channels the app already has
	rather than inventing a ticketing flow that has no backend.
-->
<template>
	<div class="flex h-full min-h-0 flex-col">
		<header
			class="shrink-0 border-b border-[var(--learno-line-soft)] bg-white px-6 py-[22px] lg:px-10"
		>
			<h1
				class="text-[27px] font-semibold leading-[1.2] text-black max-lg:ps-12"
			>
				{{ __('Support') }}
			</h1>
			<p class="mt-1 text-[13px] text-[var(--learno-ink-muted)]">
				{{ __('Get help with your courses, your account, or the platform.') }}
			</p>
		</header>

		<div
			class="learno-scroll min-h-0 flex-1 overflow-y-auto bg-[var(--learno-canvas)] px-6 py-7 lg:px-10"
		>
			<div class="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
				<a
					v-for="channel in channels"
					:key="channel.label"
					:href="safeUrl(channel.href)"
					class="learno-card flex flex-col gap-3 p-6 transition hover:shadow-[var(--learno-shadow)]"
					:target="channel.external ? '_blank' : undefined"
					:rel="channel.external ? 'noopener noreferrer' : undefined"
				>
					<span
						class="grid size-11 place-items-center rounded-full bg-[var(--learno-primary-soft)] text-[var(--learno-primary)]"
					>
						<span :class="[channel.icon, 'size-5']" aria-hidden="true" />
					</span>
					<span
						class="text-[15px] font-semibold text-[var(--learno-ink-strong)]"
					>
						{{ channel.label }}
					</span>
					<span
						class="text-[12px] leading-[1.6] text-[var(--learno-ink-muted)]"
					>
						{{ channel.description }}
					</span>
				</a>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { usePageMeta } from 'frappe-ui'
import { sessionStore } from '@/stores/session'
import { safeUrl } from '@/utils/safeUrl'

usePageMeta(() => ({ title: __('Support') }))

const { brand } = sessionStore()

const channels = computed(() => [
	{
		label: __('Email the team'),
		description: __(
			'Questions about a course, your enrolment, or a certificate.'
		),
		icon: 'lucide-mail',
		href: `mailto:?subject=${encodeURIComponent(
			__('Help with {0}').format(brand.name || 'Learno')
		)}`,
		external: false,
	},
	{
		label: __('Documentation'),
		description: __('How the platform works, end to end.'),
		icon: 'lucide-book-open',
		href: 'https://docs.frappe.io/learning',
		external: true,
	},
	{
		label: __('Report a problem'),
		description: __('Something on a session page is broken or missing.'),
		icon: 'lucide-triangle-alert',
		href: `mailto:?subject=${encodeURIComponent(__('Issue report'))}`,
		external: false,
	},
])
</script>
