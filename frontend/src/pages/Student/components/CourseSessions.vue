<!--
	Sessions panel. Figma: node 100:9718 — a radio-ish marker, a "Chapter 1"
	chip, the title, a blurb, and a disclosure chevron per row.

	The design draws a flat list of chapters; the real outline is two levels
	(chapter → lessons), so the chevron expands the chapter into its lessons.
	That is the only way the row can be the affordance the design shows AND lead
	somewhere, since a chapter itself is not openable.
-->
<template>
	<div class="flex flex-col">
		<div v-if="loading" class="flex flex-col gap-4">
			<div
				v-for="n in 4"
				:key="n"
				class="h-20 animate-pulse rounded-[var(--learno-r-md)] bg-black/5"
			/>
		</div>

		<p
			v-else-if="!outline.length"
			class="py-16 text-center text-[14px] text-[var(--learno-ink-muted)]"
		>
			{{ __('No sessions have been published for this course yet.') }}
		</p>

		<div
			v-for="chapter in outline"
			:key="chapter.name"
			class="border-b border-[var(--learno-line)] py-6 last:border-b-0"
		>
			<button
				type="button"
				class="flex w-full items-start gap-4 text-start"
				:aria-expanded="isOpen(chapter.name)"
				@click="toggle(chapter.name)"
			>
				<span
					class="mt-0.5 grid size-5 shrink-0 place-items-center rounded-full border-2 transition"
					:class="
						chapterDone(chapter)
							? 'border-[var(--learno-primary)] bg-[var(--learno-primary)] text-white'
							: 'border-[#d6d6d6]'
					"
				>
					<span
						v-if="chapterDone(chapter)"
						class="lucide-check size-3"
						aria-hidden="true"
					/>
				</span>

				<span class="flex min-w-0 flex-1 flex-col gap-1.5">
					<span class="learno-tag w-fit bg-[#dcfce7] text-[#166534]">
						{{ __('Chapter') }} {{ chapter.idx }}
					</span>
					<span
						class="text-[15px] font-semibold text-[var(--learno-ink-strong)]"
					>
						{{ chapter.title }}
					</span>
					<span class="text-[11px] text-[var(--learno-ink-muted)]">
						{{ completedIn(chapter) }} / {{ chapter.lessons?.length || 0 }}
						{{ __('sessions complete') }}
					</span>
				</span>

				<span
					class="lucide-chevron-down mt-2 size-5 shrink-0 text-[var(--learno-ink-subtle)] transition-transform"
					:class="isOpen(chapter.name) && 'rotate-180'"
					aria-hidden="true"
				/>
			</button>

			<ul v-if="isOpen(chapter.name)" class="mt-5 flex flex-col gap-1 ps-9">
				<li v-for="lesson in chapter.lessons || []" :key="lesson.name">
					<component
						:is="lesson.locked ? 'div' : 'router-link'"
						:to="
							lesson.locked
								? undefined
								: {
										name: 'StudentSession',
										params: {
											courseName,
											chapterNumber: String(lesson.number).split('-')[0],
											lessonNumber: String(lesson.number).split('-')[1],
										},
								  }
						"
						class="flex items-center gap-3 rounded-[var(--learno-r-sm)] px-3 py-2.5 text-[13px] transition"
						:class="
							lesson.locked
								? 'cursor-not-allowed text-[var(--learno-ink-subtle)]'
								: 'text-[var(--learno-ink)] hover:bg-[var(--learno-canvas)]'
						"
					>
						<span
							:class="[
								lesson.locked
									? 'lucide-lock'
									: lesson.is_complete
									? 'lucide-circle-check-big'
									: 'lucide-circle-play',
								'size-4 shrink-0',
								lesson.is_complete && 'text-[var(--learno-primary)]',
							]"
							aria-hidden="true"
						/>
						<span class="min-w-0 flex-1 truncate">{{ lesson.title }}</span>
						<span
							v-if="lesson.include_in_preview && !isMember"
							class="learno-tag bg-[#ddf4ff] text-[#2b70c9]"
						>
							{{ __('Preview') }}
						</span>
					</component>
				</li>

				<li
					v-if="!chapter.lessons?.length"
					class="px-3 py-2.5 text-[12px] text-[var(--learno-ink-muted)]"
				>
					{{ __('No sessions in this chapter yet.') }}
				</li>
			</ul>
		</div>
	</div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

const props = defineProps<{
	courseName: string
	outline: any[]
	loading?: boolean
	isMember?: boolean
}>()

const open = ref<Set<string>>(new Set())

// The first chapter opens by default: a list of collapsed chapters is a wall of
// chevrons with nothing to act on, and the first chapter is where a new student
// starts anyway.
watch(
	() => props.outline,
	(value) => {
		if (value?.length && !open.value.size) {
			open.value = new Set([value[0].name])
		}
	},
	{ immediate: true }
)

function isOpen(name: string) {
	return open.value.has(name)
}

function toggle(name: string) {
	const next = new Set(open.value)
	next.has(name) ? next.delete(name) : next.add(name)
	open.value = next
}

function completedIn(chapter: any) {
	return (chapter.lessons || []).filter((lesson: any) => lesson.is_complete)
		.length
}

function chapterDone(chapter: any) {
	const lessons = chapter.lessons || []
	return lessons.length > 0 && completedIn(chapter) === lessons.length
}
</script>
