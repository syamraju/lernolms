<!--
	About panel. Figma: node 90:5108 — "Learning Path and Course Inclusions"
	beside a media panel, then "Skills you Unlock".

	The design's right-hand media panel is a course preview; when the course has
	a video link that is what goes there, otherwise the preview image, otherwise
	nothing at all rather than a placeholder box.
-->
<template>
	<div class="flex flex-col gap-12">
		<section>
			<h2 class="mb-7 text-[16px] font-semibold text-[var(--learno-ink-strong)]">
				{{ __('Learning Path and Course Inclusions') }}
			</h2>

			<div class="grid gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
				<ol class="flex flex-col gap-7">
					<li
						v-for="chapter in outline.slice(0, 6)"
						:key="chapter.name"
						class="flex flex-col gap-1.5"
					>
						<span class="learno-tag w-fit bg-[#dcfce7] text-[#166534]">
							{{ __('Chapter') }} {{ chapter.idx }}
						</span>
						<h3 class="text-[14px] font-semibold text-[var(--learno-ink-strong)]">
							{{ chapter.title }}
						</h3>
						<p class="text-[11px] leading-[1.6] text-[var(--learno-ink-muted)]">
							{{
								chapter.lessons?.length === 1
									? __('1 session')
									: __('{0} sessions').format(chapter.lessons?.length || 0)
							}}
							<template v-if="chapter.lessons?.length">
								· {{ chapter.lessons.map((l) => l.title).slice(0, 3).join(' · ') }}
							</template>
						</p>
					</li>

					<li
						v-if="!outline.length"
						class="text-[12px] text-[var(--learno-ink-muted)]"
					>
						{{ __('The syllabus for this course is not published yet.') }}
					</li>
				</ol>

				<div
					v-if="course.video_link || course.image"
					class="self-start overflow-hidden rounded-[var(--learno-r-md)]"
				>
					<VideoPreview
						v-if="course.video_link"
						:videoLink="course.video_link"
						:fallbackImage="course.image"
					/>
					<img
						v-else
						:src="safeUrl(course.image)"
						alt=""
						class="w-full object-cover"
					/>
				</div>
			</div>
		</section>

		<section v-if="course.description">
			<h2 class="mb-4 text-[16px] font-semibold text-[var(--learno-ink-strong)]">
				{{ __('About this course') }}
			</h2>
			<!-- v-safe-html:rich, not v-html: the directive is where this app's
			     sanitiser and its anchor-target hook live. -->
			<div class="learno-prose max-w-[80ch]" v-safe-html:rich="course.description" />
		</section>

		<section v-if="skills.length">
			<h2 class="mb-7 text-[16px] font-semibold text-[var(--learno-ink-strong)]">
				{{ __('Skills you Unlock') }}
			</h2>
			<div class="grid gap-8 sm:grid-cols-2">
				<div v-for="skill in skills" :key="skill" class="flex items-start gap-4">
					<span
						class="grid size-11 shrink-0 place-items-center rounded-full bg-[var(--learno-primary-soft)] text-[var(--learno-primary)]"
					>
						<span class="lucide-sparkles size-5" aria-hidden="true" />
					</span>
					<div class="flex flex-col gap-1">
						<h3 class="text-[13px] font-semibold text-[var(--learno-ink-strong)]">
							{{ skill }}
						</h3>
						<p class="text-[11px] leading-[1.6] text-[var(--learno-ink-muted)]">
							{{ __('Covered across this course.') }}
						</p>
					</div>
				</div>
			</div>
		</section>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import VideoPreview from '@/components/VideoPreview.vue'
import { safeUrl } from '@/utils/safeUrl'

const props = defineProps<{
	course: Record<string, any>
	outline: any[]
}>()

// `tags` is the only place an author records what a course teaches, and it is
// what the card already reads as the level chip. Everything after the first
// entry is a skill.
const skills = computed(() =>
	String(props.course.tags || '')
		.split(',')
		.map((tag: string) => tag.trim())
		.filter(Boolean)
		.slice(1)
)
</script>
