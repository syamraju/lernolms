<template>
	<div class="flex h-dvh flex-col bg-surface-base">
		<header
			class="flex shrink-0 items-center justify-between gap-4 border-b ps-5 pe-5"
		>
			<div class="flex items-center gap-5">
				<span class="text-p-lg-semibold text-ink-gray-9">
					{{ brand.name || __('Learno') }}
				</span>
				<div
					class="border-s py-4 ps-5 text-p-base text-ink-gray-7"
					aria-live="polite"
				>
					{{ __('Step {0} of {1}').format(stepIndex + 1, STEPS.length) }}
				</div>
			</div>
			<Button variant="ghost" :label="__('Exit')" @click="exit" />
		</header>
		<div
			class="h-1 shrink-0 bg-surface-gray-2"
			role="progressbar"
			:aria-valuenow="stepIndex + 1"
			aria-valuemin="1"
			:aria-valuemax="STEPS.length"
			:aria-label="__('Course setup progress')"
		>
			<div
				class="h-full bg-surface-gray-7 transition-[width] duration-300 ease-out"
				:style="{ width: `${((stepIndex + 1) / STEPS.length) * 100}%` }"
			/>
		</div>

		<main
			class="flex-1 overflow-y-auto px-5 py-12"
			id="wizardContent"
			tabindex="-1"
		>
			<div
				class="mx-auto"
				:class="current.key === 'certificate' ? 'max-w-6xl' : 'max-w-3xl'"
			>
				<h1
					class="text-center text-2xl font-semibold leading-tight text-ink-gray-9 md:text-3xl"
				>
					{{ current.heading }}
				</h1>
				<p
					v-if="current.subheading"
					class="mt-3 text-center text-p-base text-ink-gray-6"
				>
					{{ current.subheading }}
				</p>

				<!-- Step 1 — what kind of course -->
				<div
					v-if="current.key === 'type'"
					class="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2"
					role="radiogroup"
					:aria-label="__('Course type')"
				>
					<button
						v-for="option in COURSE_TYPES"
						:key="option.value"
						type="button"
						role="radio"
						:aria-checked="draft.course_type === option.value"
						class="rounded-md border-2 p-6 text-center transition-colors hover:border-outline-gray-4"
						:class="
							draft.course_type === option.value
								? 'border-outline-gray-5 bg-surface-gray-1'
								: 'border-outline-gray-2'
						"
						@click="draft.course_type = option.value"
					>
						<span
							class="mx-auto mb-3 block size-6 text-ink-gray-8"
							:class="option.icon"
						/>
						<span class="block text-p-base-semibold text-ink-gray-9">
							{{ option.label }}
						</span>
						<span class="mt-2 block text-p-sm text-ink-gray-6">
							{{ option.description }}
						</span>
					</button>
				</div>

				<!-- Step 2 — working title -->
				<div v-else-if="current.key === 'title'" class="mx-auto mt-10 max-w-xl">
					<FormControl
						ref="titleInput"
						v-model="draft.title"
						variant="outline"
						:label="__('Course title')"
						:placeholder="__('e.g. Learn Journaling for Beginners')"
						:maxlength="TITLE_LIMIT"
						autocomplete="off"
						@keyup.enter="next()"
					/>
					<div class="mt-1.5 text-end text-p-sm tabular-nums text-ink-gray-5">
						{{ TITLE_LIMIT - draft.title.length }}
					</div>
				</div>

				<!-- Step 3 — category -->
				<div
					v-else-if="current.key === 'category'"
					class="mx-auto mt-10 max-w-xl"
				>
					<Link
						v-model="draft.category"
						doctype="LMS Category"
						:label="__('Category')"
						:placeholder="__('Choose a category')"
						:inlineCreate="true"
						inlineCreatePlaceholder="Category name"
						:onCreate="onCreateCategory"
						variant="outline"
					/>
				</div>

				<!-- Step 4 — how much time -->
				<div
					v-else-if="current.key === 'time'"
					class="mx-auto mt-10 max-w-xl space-y-3"
					role="radiogroup"
					:aria-label="__('Time commitment')"
				>
					<button
						v-for="option in TIME_COMMITMENTS"
						:key="option"
						type="button"
						role="radio"
						:aria-checked="draft.time_commitment === option"
						class="flex w-full items-center gap-3 rounded-md border p-4 text-start transition-colors hover:border-outline-gray-4"
						:class="
							draft.time_commitment === option
								? 'border-outline-gray-5 bg-surface-gray-1'
								: 'border-outline-gray-2'
						"
						@click="draft.time_commitment = option"
					>
						<span
							class="grid size-5 shrink-0 place-items-center rounded-full border-2"
							:class="
								draft.time_commitment === option
									? 'border-outline-gray-5'
									: 'border-outline-gray-3'
							"
						>
							<span
								v-if="draft.time_commitment === option"
								class="size-2.5 rounded-full bg-surface-gray-7"
							/>
						</span>
						<span class="text-p-base-medium text-ink-gray-9">
							{{ __(option) }}
						</span>
					</button>
				</div>

				<!--
					Step 5 — the certificate.

					Designed here, by the moderator, while the course is still an
					idea. It is the one thing that cannot be left for later: once
					the course is handed to instructors nobody who remains owns
					the decision, so the next step refuses to invite anyone until
					this one is finished.
				-->
				<div v-else-if="current.key === 'certificate'" class="mt-10">
					<CertificateDesigner
						v-if="certificateMeta.data"
						v-model="draft.certificate"
						v-model:selectedIndex="certificateSelection"
						:variables="certificateMeta.data.variables"
						:sampleValues="sampleValues"
						:dateFormats="certificateMeta.data.date_formats"
					/>
					<SkeletonLoader v-else />
				</div>

				<!--
					Step 6 — who builds it.

					A moderator usually starts a course they will not write. Naming
					the instructors here is what hands it over: each one is notified
					and the course shows up in their own created list, rather than
					sitting in a draft nobody has been told about.
				-->
				<div
					v-else-if="current.key === 'instructors'"
					class="mx-auto mt-10 max-w-xl space-y-4"
				>
					<!--
						Shown instead of an error on the next click. The server
						refuses this invitation either way; saying so here, with
						the way back, is the difference between a rule and a
						dead end.
					-->
					<div
						v-if="certificateMissing.length"
						class="rounded-md border border-outline-amber-2 bg-surface-amber-1 px-4 py-3 text-p-sm text-ink-gray-8"
					>
						<p>
							{{
								__(
									'Instructors cannot be invited until the certificate is finished.'
								)
							}}
						</p>
						<ul class="mt-2 list-disc ps-5">
							<li
								v-for="requirement in certificateMissing"
								:key="requirement.code"
							>
								{{ requirement.message }}
							</li>
						</ul>
						<Button
							class="mt-3"
							variant="subtle"
							size="sm"
							:label="__('Back to the certificate')"
							@click="goToStep('certificate')"
						/>
					</div>

					<MultiLink
						v-if="!certificateMissing.length"
						v-model="draft.instructors"
						doctype="User"
						url="lms.lms.api.search_users_by_role"
						:searchParams="{ roles: JSON.stringify(INSTRUCTOR_ROLES) }"
						:transform="transformUsers"
						:label="__('Instructors')"
						:placeholder="__('Search by name or email')"
					>
						<template #item-prefix="{ item }">
							<Avatar :image="item.image" :label="item.label" size="sm" />
						</template>
					</MultiLink>
					<p v-if="!certificateMissing.length" class="text-p-sm text-ink-gray-6">
						{{
							draft.instructors.length
								? __(
										'Each of them is notified straight away and can start adding lectures, quizzes and assignments. You stay on the course too.'
								  )
								: __(
										'Leave this empty to build the course yourself. You can invite instructors later from the course settings.'
								  )
						}}
					</p>
				</div>
			</div>
		</main>

		<footer
			class="flex shrink-0 items-center justify-between gap-3 border-t px-5 py-4"
		>
			<Button
				v-if="stepIndex > 0"
				variant="outline"
				:label="__('Previous')"
				@click="previous"
			/>
			<span v-else />
			<Button
				variant="solid"
				:disabled="!canContinue"
				:loading="creating"
				:label="isLastStep ? __('Create course') : __('Continue')"
				@click="next"
			/>
		</footer>
	</div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
	Avatar,
	Button,
	FormControl,
	call,
	createResource,
	toast,
	usePageMeta,
} from 'frappe-ui'
import Link from '@/components/Controls/Link.vue'
import MultiLink from '@/components/Controls/MultiLink.vue'
import CertificateDesigner from '@/components/Certificates/CertificateDesigner.vue'
import SkeletonLoader from '@/components/SkeletonLoader.vue'
import { blankTemplate, missingRequirements } from '@/utils/certificate'
import type { CertificateVariable } from '@/utils/certificate'
import { canCreateCourse, createLMSCategory } from '@/utils'
import { getLmsRoute } from '@/utils/basePath'
import { errorMessage } from '@/utils/courseCreation'
import { createHandler } from '@/utils/createHandler'
import { sessionStore } from '@/stores/session'

const TITLE_LIMIT = 60

// Only people who could own a course are worth offering: inviting a student as
// an instructor would create a row that grants edit rights their role does not.
const INSTRUCTOR_ROLES = ['Course Creator', 'Moderator']

interface RawUserHit {
	label?: string
	value?: string
	name?: string
	user_image?: string
}

function transformUsers(rows: Record<string, unknown>[]) {
	return (rows as RawUserHit[]).map((user) => ({
		label: user.label || user.name || user.value || '',
		value: user.value || user.name || '',
		image: user.user_image || '',
	}))
}

const COURSE_TYPES = [
	{
		value: 'Course' as const,
		label: __('Course'),
		icon: 'lucide-monitor-play',
		description: __(
			'Create rich learning experiences with video lessons, quizzes and exercises.'
		),
	},
	{
		value: 'Practice Test' as const,
		label: __('Practice Test'),
		icon: 'lucide-list-checks',
		description: __(
			'Help learners prepare for certification exams with practice questions.'
		),
	},
]

const TIME_COMMITMENTS = [
	'0-2 hours per week',
	'2-4 hours per week',
	'5+ hours per week',
	'Not decided yet',
] as const

interface WizardStep {
	key: 'type' | 'title' | 'category' | 'time' | 'certificate' | 'instructors'
	heading: string
	subheading?: string
}

const STEPS: WizardStep[] = [
	{
		key: 'type',
		heading: __("First, let's find out what type of course you're making."),
	},
	{
		key: 'title',
		heading: __('How about a working title?'),
		subheading: __(
			"It's ok if you can't think of a good title now. You can change it later."
		),
	},
	{
		key: 'category',
		heading: __("What category best fits the knowledge you'll share?"),
		subheading: __(
			"If you're not sure about the right category, you can change it later."
		),
	},
	{
		key: 'time',
		heading: __('How much time can you spend creating your course per week?'),
		subheading: __(
			"There's no wrong answer. We can help you reach your goal even if you don't have much time."
		),
	},
	{
		key: 'certificate',
		heading: __('Design the certificate learners will earn.'),
		subheading: __(
			'Upload your certificate artwork and place the fields on it. This has to be finished before the course can be handed to instructors.'
		),
	},
	{
		key: 'instructors',
		heading: __('Who will build this course?'),
		subheading: __(
			'Add the instructors who will write the lectures, quizzes and assignments. They are notified as soon as the course is created.'
		),
	},
]

const router = useRouter()
const { brand } = sessionStore() as {
	brand: { name?: string; favicon?: string }
}

const draft = reactive({
	course_type: 'Course' as 'Course' | 'Practice Test',
	title: '',
	category: '',
	time_commitment: '' as string,
	instructors: [] as string[],
	// The course has no name yet, so the design is held here and posted with it.
	// `reference_name` is filled in server side once the row exists.
	certificate: blankTemplate('LMS Course', ''),
})

const stepIndex = ref(0)
const creating = ref(false)
const certificateSelection = ref(-1)
const titleInput = ref<{ $el?: HTMLElement } | null>(null)

interface CertificateMeta {
	variables: CertificateVariable[]
	date_formats: string[]
	organisation_name: string
}

// Fetched rather than hard-coded: which fields are mandatory is the server's
// rule, and the gate that enforces it reads the same list. A copy here would be
// a second rule waiting to disagree with the first.
const certificateMeta = createResource({
	url: 'lms.lms.certificates.get_certificate_variables',
	makeParams: () => ({ reference_doctype: 'LMS Course' }),
	auto: true,
}) as { data: CertificateMeta | null }

const hasCertificateWork = computed(
	() =>
		Boolean(draft.certificate.background_image) ||
		draft.certificate.elements.length > 0
)

const certificateMissing = computed(() =>
	certificateMeta.data
		? missingRequirements(
				certificateMeta.data.variables,
				draft.certificate.background_image,
				draft.certificate.elements
			)
		: []
)

// The learner's own details are not known until a certificate is issued, so the
// canvas is laid out against stand-ins. The course title is the one value that
// is already real, and seeing it in place is how a moderator judges the size.
const sampleValues = computed(() => ({
	participant_name: __('Participant Name'),
	course_name: draft.title || __('Course Name'),
	course_start_date: new Date().toISOString().slice(0, 10),
	course_end_date: new Date().toISOString().slice(0, 10),
	issue_date: new Date().toISOString().slice(0, 10),
	certificate_id: 'LRN-SAMPLE-0000',
	verification_url: `${window.location.origin}${getLmsRoute('/verify/LRN-SAMPLE-0000')}`,
	organisation_name: certificateMeta.data?.organisation_name || '',
	instructor_name: __('Instructor Name'),
	batch_name: '',
	expiry_date: null,
}))

const current = computed<WizardStep>(() => STEPS[stepIndex.value])
const isLastStep = computed(() => stepIndex.value === STEPS.length - 1)

// Every step but the category gate has a required answer. Category is
// deliberately skippable: the copy tells the author they can change it later,
// so blocking on it would contradict the page.
const canContinue = computed(() => {
	switch (current.value.key) {
		case 'type':
			return Boolean(draft.course_type)
		case 'title':
			return draft.title.trim().length > 0
		case 'category':
			return true
		case 'time':
			return Boolean(draft.time_commitment)
		// Passable while unfinished on purpose. A moderator building the course
		// themselves needs no certificate today, and losing the four answers
		// already given because the artwork is not ready would be the wrong
		// trade. The gate is on the invitation, not on getting past this step.
		case 'certificate':
			return true
		// Skippable on purpose: a course creator building their own course has
		// nobody to invite, and the copy on the step says as much.
		case 'instructors':
			return true
		default:
			return false
	}
})

onMounted(() => {
	if (!canCreateCourse()) {
		toast.error(__('You are not permitted to create a course.'))
		router.replace({ name: 'Courses' })
	}
})

function previous() {
	if (stepIndex.value > 0) stepIndex.value -= 1
}

function goToStep(key: WizardStep['key']) {
	const index = STEPS.findIndex((step) => step.key === key)
	if (index >= 0) stepIndex.value = index
}

async function next() {
	if (!canContinue.value || creating.value) return
	if (!isLastStep.value) {
		stepIndex.value += 1
		// The title step is the only one with a text field; focusing it saves a
		// click and keeps keyboard-only progress through the wizard unbroken.
		if (current.value.key === 'title') {
			await nextTick()
			titleInput.value?.$el?.querySelector('input')?.focus()
		}
		return
	}
	await createCourse()
}

async function createCourse() {
	creating.value = true
	try {
		const courseName = await call('lms.lms.course_creation.create_course_draft', {
			title: draft.title.trim(),
			course_type: draft.course_type,
			category: draft.category || null,
			time_commitment: draft.time_commitment || null,
			instructors: draft.instructors,
			// Sent whenever there is anything to keep. A half-finished design is
			// still worth storing: the moderator picks it up from the course's
			// certificate screen rather than starting the artwork again.
			certificate: hasCertificateWork.value ? draft.certificate : null,
		})
		toast.success(__('Course created'))
		// A brand-new course has nothing to edit yet, so land on Settings with
		// the audience fields in view — the first thing the setup checklist
		// asks for.
		router.replace({
			name: 'CourseDetail',
			params: { courseName },
			hash: '#settings',
			query: { focus: 'audience' },
		})
	} catch (error) {
		toast.error(errorMessage(error, __('Could not create the course')))
	} finally {
		creating.value = false
	}
}

function createCategory(name: string, done?: () => void) {
	if (!name) return
	createLMSCategory(name).then((categoryName?: string) => {
		if (!categoryName) return
		draft.category = categoryName
		done?.()
	})
}

function onCreateCategory(value: string | null, done?: () => void) {
	createHandler(value, done, (name) => createCategory(name, done))
}

function exit() {
	router.push({ name: 'Courses' })
}

usePageMeta(() => ({
	title: __('Create a course'),
	icon: brand.favicon,
}))
</script>
