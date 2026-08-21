<!--
	/batches/join/:token — redeeming an invite link.

	The door for enrollment through a URL pasted into a group chat. The token is
	validated server-side on every step: `describe_invite_link` says whether it is
	still live (and answers `valid: false` rather than throwing, so an expired
	link can say so instead of rendering an error), and `join_with_link` performs
	the enrollment under the batch row lock.

	The route is not public — the router's own guard sends a signed-out visitor to
	login with this path as `redirect`, so the token survives the round trip and
	they land back here. The signed-out branch in `join()` below is therefore
	belt-and-braces rather than the normal path.
-->
<template>
	<div
		class="learno flex min-h-dvh w-full items-center justify-center bg-[var(--learno-app)] p-4"
	>
		<div
			class="w-full max-w-[28rem] rounded-[var(--learno-r-lg)] bg-white p-8 shadow-sm"
		>
			<div v-if="loading" class="text-[14px] text-[var(--learno-ink-muted)]">
				{{ __('Checking this invitation…') }}
			</div>

			<template v-else-if="!link?.valid">
				<h1 class="text-[22px] font-semibold text-black">
					{{ __('This invitation is no longer valid') }}
				</h1>
				<p class="mt-2 text-[13px] leading-5 text-[var(--learno-ink-muted)]">
					{{
						__(
							'It may have expired, been used up, or been revoked. Ask whoever shared it for a new one.'
						)
					}}
				</p>
				<Button class="mt-6 w-full" @click="goHome">{{
					__('Go to Learno')
				}}</Button>
			</template>

			<template v-else-if="joined">
				<h1 class="text-[22px] font-semibold text-black">
					{{ __('You are in') }}
				</h1>
				<p class="mt-2 text-[13px] leading-5 text-[var(--learno-ink-muted)]">
					{{ __('You have been added to {0}.').format(link.batch.title) }}
				</p>
				<Button variant="solid" class="mt-6 w-full" @click="openBatch">
					{{ __('Open the batch') }}
				</Button>
			</template>

			<template v-else>
				<h1 class="text-[22px] font-semibold text-black">
					{{ link.batch.title }}
				</h1>
				<p
					v-if="link.batch.start_date"
					class="mt-2 text-[13px] leading-5 text-[var(--learno-ink-muted)]"
				>
					{{ __('Starts {0}').format(formatDate(link.batch.start_date)) }}
					<template v-if="link.batch.medium">
						· {{ link.batch.medium }}</template
					>
				</p>

				<ErrorMessage class="mt-4" :message="error" />

				<Button
					variant="solid"
					class="mt-6 w-full"
					:loading="joining"
					@click="join"
				>
					{{ __('Join this batch') }}
				</Button>
			</template>
		</div>
	</div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Button, ErrorMessage, call, usePageMeta } from 'frappe-ui'
import { sessionStore } from '@/stores/session'

usePageMeta(() => ({ title: __('Join a batch') }))

const route = useRoute()
const router = useRouter()
const { isLoggedIn } = sessionStore()

const loading = ref(true)
const joining = ref(false)
const joined = ref(false)
const link = ref(null)
const error = ref('')

const formatDate = (value) => new Date(value).toLocaleDateString()

onMounted(async () => {
	try {
		link.value = await call('lms.lms.batch_invite.describe_invite_link', {
			token: route.params.token,
		})
	} catch (err) {
		link.value = { valid: false }
	}
	loading.value = false
})

const join = async () => {
	if (!isLoggedIn) {
		// Preserve the token across sign-in rather than losing it: this is often
		// somebody's first visit to the site.
		return router.push({
			name: 'Login',
			query: { redirect: route.fullPath },
		})
	}

	joining.value = true
	error.value = ''
	try {
		await call('lms.lms.batch_invite.join_with_link', {
			token: route.params.token,
		})
		joined.value = true
	} catch (err) {
		error.value = err.messages?.[0] || err.message || String(err)
	}
	joining.value = false
}

const openBatch = () => {
	router.push({
		name: 'BatchDetail',
		params: { batchName: link.value.batch.name },
	})
}

const goHome = () => {
	router.push({ name: 'Home' })
}
</script>
