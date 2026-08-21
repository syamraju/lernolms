<!--
	Choose a password, for an account that arrived with a generated one.

	Reached when `User.must_reset_password` is set — a batch invitation created
	the account, or a moderator re-issued the password. `lms.lms.user.on_login`
	sends the session here, and the router keeps it here: the temporary password
	was mailed, so it stays a working credential in an inbox until it is replaced.

	No "current password" field. The whole situation is that the current one
	arrived by email and is not a secret the user chose; what makes skipping it
	safe is that they are already authenticated. This is not a recovery flow.
-->
<template>
	<div
		class="learno flex min-h-dvh w-full items-center justify-center bg-[var(--learno-app)] p-4"
	>
		<div
			class="w-full max-w-[26rem] rounded-[var(--learno-r-lg)] bg-white p-8 shadow-sm"
		>
			<h1 class="text-[22px] font-semibold text-black">
				{{ __('Choose a password') }}
			</h1>
			<p class="mt-2 text-[13px] leading-5 text-[var(--learno-ink-muted)]">
				{{
					__(
						'Your account was set up with a temporary password. Pick one of your own to finish signing in — the temporary one stops working straight away.'
					)
				}}
			</p>

			<form class="mt-6 space-y-4" @submit.prevent="submit">
				<FormControl
					v-model="password"
					type="password"
					:label="__('New password')"
					autocomplete="new-password"
					required
				/>
				<FormControl
					v-model="confirmation"
					type="password"
					:label="__('Confirm password')"
					autocomplete="new-password"
					required
				/>

				<ErrorMessage :message="error" />

				<Button
					variant="solid"
					class="w-full"
					:loading="saving"
					:disabled="!password || !confirmation"
					@click="submit"
				>
					{{ __('Save and continue') }}
				</Button>
			</form>
		</div>
	</div>
</template>

<script setup>
import { ref } from 'vue'
import { Button, ErrorMessage, FormControl, call, usePageMeta } from 'frappe-ui'

usePageMeta(() => ({ title: __('Choose a password') }))

const password = ref('')
const confirmation = ref('')
const error = ref('')
const saving = ref(false)

const submit = async () => {
	error.value = ''
	if (password.value !== confirmation.value) {
		error.value = __('The two passwords do not match.')
		return
	}

	saving.value = true
	try {
		await call('lms.lms.user.set_own_password', {
			new_password: password.value,
		})
		// A full load, not a router push: `update_password` drops the other
		// sessions and the app's boot state was fetched under the old one.
		window.location.href = '/lms'
	} catch (err) {
		error.value = err.messages?.[0] || err.message || String(err)
		saving.value = false
	}
}
</script>
