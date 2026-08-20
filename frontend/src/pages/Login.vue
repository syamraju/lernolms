<!--
	Sign-in.

	The Figma has no login frame, so nothing here is copied from one. What it is
	instead: the design's own vocabulary — the coral primary, the cream canvas,
	the pill buttons, the 16px card radius, DM Sans, the brand card from the
	sidebar's header — applied to the sign-in flow the app already had. Carrying
	`.learno` on the root is what switches those tokens on; see
	src/styles/learno.css.

	The behaviour below is unchanged and deliberate: `Continue` only advances the
	form, because Frappe answers a wrong password and an unknown user with the
	same error and validating the two steps separately would leak which addresses
	have accounts.
-->
<template>
	<div class="learno flex min-h-dvh w-full bg-[var(--learno-app)] p-1.5">
		<!-- Brand panel. Decorative, so it is the half that goes when the viewport
		     cannot afford two columns — the form never shrinks below the width it
		     needs. -->
		<section
			class="relative hidden w-1/2 shrink-0 overflow-hidden rounded-[var(--learno-r-lg)] bg-[var(--learno-primary-soft)] lg:flex lg:flex-col"
			aria-hidden="true"
		>
			<div class="pointer-events-none absolute inset-0 login-wash"></div>

			<div class="relative flex h-full flex-col p-10">
				<span class="flex items-end gap-2.5">
					<LearnoMark
						class="h-[34px] w-[35px] text-[var(--learno-primary)]"
						:label="brandName"
					/>
					<span class="flex flex-col leading-none">
						<span class="text-[22px] font-semibold text-[#272727]">
							{{ brandName }}
						</span>
						<span class="mt-0.5 text-[13px] text-[#272727]">{{ __('edu') }}</span>
					</span>
				</span>

				<div class="flex flex-1 items-center">
					<div class="max-w-[32rem]">
						<p class="text-[32px] font-semibold leading-[1.25] text-[#3e2020]">
							{{ __('Everything you are learning, in one place.') }}
						</p>
						<p class="mt-5 text-[16px] leading-[1.7] text-[#7a5b5b]">
							{{
								__(
									'Your courses, sessions, materials and certificates — with your progress carried across all of them.'
								)
							}}
						</p>
					</div>
				</div>

				<p class="text-[12px] text-[#a58585]">
					{{ __('Powered by {0}').format(brandName) }}
				</p>
			</div>
		</section>

		<!-- Form panel -->
		<section
			class="ms-1.5 flex w-full flex-col rounded-[var(--learno-r-lg)] bg-white px-6 lg:w-1/2"
		>
			<div class="flex flex-1 items-center justify-center">
				<div class="w-full max-w-[25rem] py-16">
					<span class="mb-8 flex items-end justify-center gap-2.5 lg:hidden">
						<LearnoMark
							class="h-[34px] w-[35px] text-[var(--learno-primary)]"
							:label="brandName"
						/>
						<span class="text-[22px] font-semibold text-[#272727]">
							{{ brandName }}
						</span>
					</span>

					<h1
						class="text-center text-[27px] font-semibold leading-[1.2] text-[var(--learno-ink-strong)]"
					>
						{{ __('Welcome to {0}').format(brandName) }}
					</h1>
					<p class="mt-2 text-center text-[14px] text-[var(--learno-ink-muted)]">
						{{ subtitle }}
					</p>

					<!-- Sign in -->
					<form
						v-if="mode === 'signin'"
						class="mt-8 space-y-3"
						@submit.prevent="onSubmit"
					>
						<!-- The email input stays mounted across both steps rather than
						     being swapped for a summary row: swapping it out loses the
						     browser's password-manager association between the address
						     and the password field that appears next to it. -->
						<label class="sr-only" for="login-email">{{ __('Email') }}</label>
						<input
							id="login-email"
							ref="emailInput"
							v-model.trim="email"
							type="email"
							name="username"
							autocomplete="username"
							required
							:readonly="step === 'password'"
							:placeholder="__('Email address')"
							class="login-field"
							:class="step === 'password' && 'text-[var(--learno-ink-muted)]'"
						/>

						<template v-if="step === 'password'">
							<label class="sr-only" for="login-password">
								{{ __('Password') }}
							</label>
							<input
								id="login-password"
								ref="passwordInput"
								v-model="password"
								type="password"
								name="password"
								autocomplete="current-password"
								required
								:placeholder="__('Password')"
								class="login-field"
							/>
						</template>

						<p
							v-if="error"
							class="text-[12px] text-[#ea2b2b]"
							role="alert"
							aria-live="polite"
						>
							{{ error }}
						</p>

						<button
							type="submit"
							class="learno-btn learno-btn-primary w-full py-3 text-[14px]"
							:disabled="busy"
						>
							<LoadingIndicator v-if="busy" class="size-4" />
							<span>
								{{ step === 'email' ? __('Continue') : __('Sign in') }}
							</span>
						</button>

						<div v-if="step === 'password'" class="flex justify-between pt-1">
							<button
								type="button"
								class="text-[12px] text-[var(--learno-ink-muted)] hover:text-[var(--learno-ink)]"
								@click="backToEmail"
							>
								{{ __('Use a different email') }}
							</button>
							<button
								type="button"
								class="text-[12px] text-[var(--learno-ink-muted)] hover:text-[var(--learno-ink)]"
								:disabled="busy"
								@click="sendResetLink"
							>
								{{ __('Forgot password?') }}
							</button>
						</div>
					</form>

					<!-- Sign up -->
					<form v-else class="mt-8 space-y-3" @submit.prevent="onSignup">
						<label class="sr-only" for="signup-name">
							{{ __('Full name') }}
						</label>
						<input
							id="signup-name"
							v-model.trim="fullName"
							type="text"
							autocomplete="name"
							required
							:placeholder="__('Full name')"
							class="login-field"
						/>
						<label class="sr-only" for="signup-email">{{ __('Email') }}</label>
						<input
							id="signup-email"
							v-model.trim="email"
							type="email"
							autocomplete="email"
							required
							:placeholder="__('Email address')"
							class="login-field"
						/>

						<p
							v-if="error"
							class="text-[12px] text-[#ea2b2b]"
							role="alert"
							aria-live="polite"
						>
							{{ error }}
						</p>

						<button
							type="submit"
							class="learno-btn learno-btn-primary w-full py-3 text-[14px]"
							:disabled="busy"
						>
							<LoadingIndicator v-if="busy" class="size-4" />
							<span>{{ __('Create account') }}</span>
						</button>
					</form>

					<p
						v-if="message"
						class="mt-3 text-center text-[12px] text-[#166534]"
						role="status"
						aria-live="polite"
					>
						{{ message }}
					</p>

					<div class="my-6 flex items-center gap-4">
						<span class="h-px flex-1 bg-[var(--learno-line)]"></span>
						<span class="text-[12px] text-[var(--learno-ink-subtle)]">
							{{ __('or') }}
						</span>
						<span class="h-px flex-1 bg-[var(--learno-line)]"></span>
					</div>

					<button
						v-if="!showOptions"
						type="button"
						class="learno-btn learno-btn-secondary w-full py-3 text-[14px]"
						@click="showOptions = true"
					>
						{{ __('Show other options') }}
					</button>

					<div v-else class="space-y-3">
						<a
							v-for="provider in providers"
							:key="provider.name"
							:href="safeUrl(provider.auth_url)"
							class="learno-btn learno-btn-secondary w-full py-3 text-[14px]"
						>
							<img
								v-if="provider.icon"
								:src="safeUrl(provider.icon)"
								alt=""
								class="size-4"
							/>
							{{ __('Continue with {0}').format(provider.label) }}
						</a>

						<button
							v-if="mode === 'signin' && allowSignup"
							type="button"
							class="learno-btn learno-btn-secondary w-full py-3 text-[14px]"
							@click="switchMode('signup')"
						>
							{{ __('Create an account') }}
						</button>
						<button
							v-if="mode === 'signup'"
							type="button"
							class="learno-btn learno-btn-secondary w-full py-3 text-[14px]"
							@click="switchMode('signin')"
						>
							{{ __('Sign in instead') }}
						</button>

						<a
							href="/app"
							class="learno-btn learno-btn-secondary w-full py-3 text-[14px]"
						>
							{{ __('Go to the desk') }}
						</a>
					</div>
				</div>
			</div>

			<footer class="pb-8 text-center text-[12px] text-[var(--learno-ink-subtle)]">
				{{ __('By signing in you agree to our') }}
				<a
					class="underline hover:text-[var(--learno-ink)]"
					href="/terms-of-use"
				>
					{{ __('Terms of service') }}
				</a>
				&amp;
				<a
					class="underline hover:text-[var(--learno-ink)]"
					href="/privacy-policy"
				>
					{{ __('Privacy policy') }}
				</a>
			</footer>
		</section>
	</div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { call, createResource, LoadingIndicator, usePageMeta } from 'frappe-ui'
import { sessionStore } from '@/stores/session'
import { getLmsRoute } from '@/utils/basePath'
import LearnoMark from '@/components/Learno/LearnoMark.vue'
import { safeUrl } from '@/utils/safeUrl'

const route = useRoute()
const { brand } = sessionStore()

const mode = ref<'signin' | 'signup'>('signin')
const step = ref<'email' | 'password'>('email')
const email = ref('')
const password = ref('')
const fullName = ref('')
const error = ref('')
const message = ref('')
const busy = ref(false)
const showOptions = ref(false)
const emailInput = ref<HTMLInputElement | null>(null)
const passwordInput = ref<HTMLInputElement | null>(null)

const brandName = computed(() => brand.name || 'Learno')

const loginOptions = createResource({
	url: 'lms.lms.api.get_login_options',
	auto: true,
})

const providers = computed(() => loginOptions.data?.providers ?? [])
const allowSignup = computed(() => Boolean(loginOptions.data?.allow_signup))

const subtitle = computed(() =>
	mode.value === 'signup'
		? __('Create an account to get started')
		: __('Sign in to continue')
)

usePageMeta(() => ({ title: __('Sign in') }))

onMounted(() => emailInput.value?.focus())

function switchMode(next: 'signin' | 'signup') {
	mode.value = next
	step.value = 'email'
	password.value = ''
	error.value = ''
	message.value = ''
}

function backToEmail() {
	step.value = 'email'
	password.value = ''
	error.value = ''
	nextTick(() => emailInput.value?.focus())
}

// Frappe answers a wrong password and an unknown user with the same
// AuthenticationError, so the two steps cannot be validated separately without
// leaking which addresses have accounts. `Continue` therefore only advances the
// form; the credentials are checked once, together.
async function onSubmit() {
	if (step.value === 'email') {
		error.value = ''
		step.value = 'password'
		await nextTick()
		passwordInput.value?.focus()
		return
	}
	await signIn()
}

async function signIn() {
	busy.value = true
	error.value = ''
	message.value = ''
	try {
		await call('login', { usr: email.value, pwd: password.value })
		// A full document load, not router.push: the session cookie and the CSRF
		// token baked into boot both changed, and every resource already created
		// in this app instance still carries the guest ones.
		window.location.href = destination()
	} catch (e: any) {
		error.value = messageFrom(e, __('Invalid email or password'))
		password.value = ''
		await nextTick()
		passwordInput.value?.focus()
	} finally {
		busy.value = false
	}
}

async function onSignup() {
	busy.value = true
	error.value = ''
	message.value = ''
	try {
		await call('frappe.core.doctype.user.user.sign_up', {
			email: email.value,
			full_name: fullName.value,
			redirect_to: destination(),
		})
		message.value = __('Check your inbox to finish setting up your account.')
	} catch (e: any) {
		error.value = messageFrom(e, __('Could not create the account'))
	} finally {
		busy.value = false
	}
}

async function sendResetLink() {
	if (!email.value) {
		error.value = __('Enter your email first')
		return
	}
	busy.value = true
	error.value = ''
	message.value = ''
	try {
		await call('frappe.core.doctype.user.user.reset_password', {
			user: email.value,
		})
		message.value = __('If that account exists, a reset link is on its way.')
	} catch (e: any) {
		// Deliberately not surfaced as a failure: the error distinguishes a real
		// account from a made-up one, which is the thing the generic message above
		// exists to hide.
		message.value = __('If that account exists, a reset link is on its way.')
	} finally {
		busy.value = false
	}
}

// The redirect target is an in-app path from our own guard, never a URL. It is
// re-anchored under the LMS base and stripped of any scheme/host so a crafted
// `?redirect=//evil.example` cannot turn the login into an open redirect.
// A bare '/' is left to the router's guard, which sends a learner to the student
// shell and anyone with authoring rights to the admin home.
function destination() {
	const requested = route.query.redirect
	const path = typeof requested === 'string' ? requested : ''
	if (!path.startsWith('/') || path.startsWith('//')) {
		return getLmsRoute('/')
	}
	return getLmsRoute(path)
}

function messageFrom(e: any, fallback: string) {
	const messages = e?.messages || e?._server_messages
	if (Array.isArray(messages) && messages.length) return String(messages[0])
	return e?.message || fallback
}
</script>

<style scoped>
.login-field {
	@apply w-full rounded-[var(--learno-r-md)] border border-[var(--learno-line)] bg-white px-4 py-3 text-[14px] text-[var(--learno-ink)] transition;
}

.login-field::placeholder {
	color: #b8bcc8;
}

.login-field:focus {
	@apply border-[var(--learno-primary)] outline-none ring-0;
}

/* Two soft coral pools over the brand panel. Low-contrast blends of this size
   band on 8-bit panels, so a few percent of noise dithers it — the same
   technique the previous brand panel used, retuned to the coral palette. */
.login-wash {
	background:
		radial-gradient(
			70% 55% at 78% 78%,
			rgba(255, 96, 96, 0.22) 0%,
			rgba(255, 96, 96, 0.04) 55%,
			transparent 100%
		),
		radial-gradient(
			55% 45% at 22% 18%,
			rgba(255, 255, 255, 0.65) 0%,
			transparent 100%
		);
}
</style>
