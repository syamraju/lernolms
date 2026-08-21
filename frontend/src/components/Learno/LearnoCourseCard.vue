<!--
	Course card. Figma: node 100:9986.

	Field mapping, and where the design asks for something LMS Course does not
	store:

	  "Subject Name"        → course.category
	  "New Course"          → published within the last 30 days
	  "Beginner Level"      → the first entry in the comma-separated `tags` field
	  "Organisation badge"  → the first instructor's name (the LMS has no
	                          organisation doctype; the instructor is the closest
	                          real attribution the card can show)
	  "Skills You Earn: …"  → course.short_introduction
	  "16 hrs"              → NOT stored. LMS Course has no duration field, so
	                          the slot shows the chapter count instead of an
	                          invented number.
	  "21 Sessions"         → course.lessons
	  "99+ Enrolments"      → course.enrollments

	The Enroll button is only an enroll button when the viewer is not already a
	member; once `membership` exists the same slot becomes "Continue", which is
	what the student actually needs there.
-->
<template>
	<article class="learno-card flex flex-col gap-[9px] overflow-hidden p-2">
		<!-- Cover -->
		<div
			class="relative h-[191px] w-full shrink-0 overflow-hidden rounded-lg"
			:class="!course.image && 'bg-[var(--learno-primary-soft)]'"
		>
			<img
				v-if="course.image"
				:src="safeUrl(course.image)"
				:alt="''"
				class="size-full object-cover"
				loading="lazy"
			/>
			<div
				v-else
				class="grid size-full place-items-center text-[var(--learno-primary)]"
			>
				<span class="lucide-book-open size-10" aria-hidden="true" />
			</div>

			<span
				v-if="isNew"
				class="learno-tag absolute start-[7px] top-[7px] bg-white/90 text-[#1f1f1f] backdrop-blur"
			>
				<span
					class="lucide-star size-3 text-[#ffc800]"
					aria-hidden="true"
				/>
				{{ __('New Course') }}
			</span>

			<span
				v-if="course.category"
				class="learno-tag absolute bottom-[7px] end-[7px] max-w-[60%] bg-white/90 text-[#1f1f1f] backdrop-blur"
			>
				<span class="truncate">{{ course.category }}</span>
			</span>
		</div>

		<!-- Body -->
		<div class="flex flex-1 flex-col gap-[19px] px-[9px]">
			<div class="flex flex-col gap-[9px]">
				<div class="flex flex-col items-start gap-1">
					<div class="flex flex-wrap items-center gap-1">
						<span v-if="level" class="learno-tag bg-[#bedbff] text-[#11279a]">
							{{ level }}
						</span>
						<!-- The course's completion deadline, shown only while it is
						     still something the student can act on. -->
						<span
							v-if="deadline"
							class="learno-tag"
							:class="PACING_TONE_CLASS[deadline.tone]"
						>
							{{ deadline.text }}
						</span>
					</div>

					<span
						v-if="organisation"
						class="flex max-w-full items-center gap-1 rounded-[23px] bg-white py-1 text-[9px] text-black"
					>
						<LearnoMark
							class="size-[17px] shrink-0 text-[var(--learno-primary)]"
							label=""
						/>
						<span class="truncate">{{ organisation }}</span>
					</span>

					<h3
						class="learno-clamp-2 text-[16px] font-semibold leading-[1.2] text-[var(--learno-ink-title)]"
					>
						{{ course.title }}
					</h3>
				</div>

				<p
					v-if="course.short_introduction"
					class="learno-clamp-3 text-[9px] leading-[1.2] text-[var(--learno-ink-muted)]"
				>
					<span class="font-semibold text-[#2e2e2e]">
						{{ __('Skills You Earn') }}
					</span>
					: {{ course.short_introduction }}
				</p>
			</div>

			<!-- Stats -->
			<div class="mt-auto flex items-start justify-between gap-2">
				<div class="flex items-end gap-[11px]">
					<span class="learno-stat">
						<span class="lucide-layers size-3" aria-hidden="true" />
						{{ chapterLabel }}
					</span>
					<span class="learno-stat">
						<span class="lucide-video size-3" aria-hidden="true" />
						{{ sessionLabel }}
					</span>
				</div>
				<span class="learno-stat">
					<span class="lucide-users size-3" aria-hidden="true" />
					{{ enrolmentLabel }}
				</span>
			</div>
		</div>

		<!-- Actions -->
		<div class="flex w-full items-center gap-1">
			<button
				v-if="!course.membership"
				type="button"
				class="learno-btn learno-btn-primary flex-1"
				:disabled="enrolling"
				@click="$emit('enroll', course)"
			>
				<span
					:class="[
						enrolling ? 'lucide-loader-circle animate-spin' : 'lucide-plus',
						'size-4',
					]"
					aria-hidden="true"
				/>
				{{ __('Enroll') }}
			</button>
			<router-link
				v-else
				:to="continueTarget"
				class="learno-btn learno-btn-primary flex-1"
			>
				<span class="lucide-play size-4" aria-hidden="true" />
				{{ __('Continue') }}
			</router-link>

			<router-link
				:to="{
					name: 'StudentCourseDetail',
					params: { courseName: course.name },
				}"
				class="learno-btn learno-btn-secondary"
			>
				<span class="lucide-eye size-4" aria-hidden="true" />
				{{ __('View') }}
			</router-link>
		</div>
	</article>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import LearnoMark from '@/components/Learno/LearnoMark.vue'
import { safeUrl } from '@/utils/safeUrl'
import { PACING_TONE_CLASS, pacingChip } from '@/utils/pacing'

const props = defineProps<{
	course: Record<string, any>
	enrolling?: boolean
}>()

defineEmits<{ (e: 'enroll', course: Record<string, any>): void }>()

const NEW_FOR_DAYS = 30

const deadline = computed(() => pacingChip(props.course.pacing))

const isNew = computed(() => {
	if (!props.course.published_on) return false
	const published = new Date(props.course.published_on).getTime()
	if (Number.isNaN(published)) return false
	return Date.now() - published < NEW_FOR_DAYS * 24 * 60 * 60 * 1000
})

// `tags` is a free-text, comma-separated Data field. The card shows the first
// entry as the level chip because that is where authors put "Beginner" etc.;
// anything else in there simply reads as the course's headline tag.
const level = computed(() => {
	const first = String(props.course.tags || '')
		.split(',')
		.map((tag) => tag.trim())
		.filter(Boolean)[0]
	return first || ''
})

const organisation = computed(() => {
	const instructor = props.course.instructors?.[0]
	return instructor?.full_name || instructor?.name || ''
})

const chapterLabel = computed(() => {
	const count = Number(props.course.chapters_count ?? 0)
	return count === 1 ? __('1 Chapter') : `${count} ${__('Chapters')}`
})

const sessionLabel = computed(() => {
	const count = Number(props.course.lessons ?? 0)
	return count === 1 ? __('1 Session') : `${count} ${__('Sessions')}`
})

const enrolmentLabel = computed(() => {
	const count = Number(props.course.enrollments ?? 0)
	const shown = count > 99 ? '99+' : String(count)
	return `${shown} ${__('Enrolments')}`
})

// Deliberately the detail page and not the player: the enrollment row carries
// `current_lesson` as a Course Lesson docname, and only `get_course_details`
// resolves it to the chapter-lesson index the player route needs (and only it
// applies the lock gate, so a resume never lands on a lesson the student may
// not open). The list endpoint hands over the raw docname, so resuming from
// here would have to guess. Landing on Sessions is one click from the real
// resume and cannot be wrong.
const continueTarget = computed(() => ({
	name: 'StudentCourseDetail',
	params: { courseName: props.course.name },
	query: { tab: 'sessions' },
}))
</script>

<style scoped>
.learno-stat {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	gap: 4px;
	padding: 3px 0;
	font-size: 9px;
	line-height: 1.2;
	white-space: nowrap;
	color: var(--learno-ink-muted);
}
</style>
