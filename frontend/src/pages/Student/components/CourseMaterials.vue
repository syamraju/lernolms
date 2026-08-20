<!--
	Materials panel. Figma: node 112:11071 — "Chapter 1  Introduction to Designs"
	then a four-up grid of file rows, each with a download and a preview action.

	The file-type glyph is coloured by extension family rather than by a per-type
	icon set: the design uses distinct icons per type, and inventing SVGs for
	them would be drawing assets we do not have. A tinted, labelled badge carries
	the same information honestly.
-->
<template>
	<div class="flex flex-col gap-10">
		<div v-if="loading" class="flex flex-col gap-6">
			<div
				v-for="n in 3"
				:key="n"
				class="h-24 animate-pulse rounded-[var(--learno-r-md)] bg-black/5"
			/>
		</div>

		<p
			v-else-if="!chapters.length"
			class="py-16 text-center text-[14px] text-[var(--learno-ink-muted)]"
		>
			{{ __('No downloadable materials in this course.') }}
		</p>

		<section v-for="chapter in chapters" :key="chapter.chapter">
			<div class="mb-5 flex items-center gap-3">
				<span class="learno-tag bg-[#dcfce7] text-[#166534]">
					{{ __('Chapter') }} {{ chapter.idx }}
				</span>
				<h3 class="text-[15px] font-semibold text-[var(--learno-ink-strong)]">
					{{ chapter.chapter_title }}
				</h3>
			</div>

			<ul class="grid gap-x-8 gap-y-4 lg:grid-cols-2 2xl:grid-cols-3">
				<li
					v-for="file in chapter.files"
					:key="`${file.lesson}-${file.file_url}`"
					class="flex items-center gap-3 border-b border-[var(--learno-line)] pb-3"
				>
					<span
						class="grid size-9 shrink-0 place-items-center rounded-[6px] text-[9px] font-semibold uppercase"
						:style="badgeStyle(file)"
					>
						{{ extension(file) }}
					</span>

					<span class="flex min-w-0 flex-1 flex-col">
						<span
							class="truncate text-[13px] font-medium text-[var(--learno-ink-strong)]"
						>
							{{ file.file_name }}
						</span>
						<span class="truncate text-[10px] text-[var(--learno-ink-muted)]">
							{{ formatSize(file.file_size) }} ·
							{{ file.lesson_title }}
						</span>
					</span>

					<a
						:href="safeUrl(file.file_url)"
						download
						class="rounded p-1.5 text-[#2b70c9] transition hover:bg-[#ddf4ff]"
						:aria-label="__('Download {0}').format(file.file_name)"
						v-external
					>
						<span class="lucide-download size-4" aria-hidden="true" />
					</a>
					<a
						:href="safeUrl(file.file_url)"
						v-external
						class="rounded p-1.5 text-[var(--learno-ink-subtle)] transition hover:bg-black/5"
						:aria-label="__('Preview {0}').format(file.file_name)"
					>
						<span class="lucide-eye size-4" aria-hidden="true" />
					</a>
				</li>
			</ul>
		</section>
	</div>
</template>

<script setup lang="ts">
import { safeUrl } from '@/utils/safeUrl'

defineProps<{ chapters: any[]; loading?: boolean }>()

const FAMILIES: Record<string, { bg: string; fg: string }> = {
	pdf: { bg: '#fee2e2', fg: '#991b1b' },
	doc: { bg: '#dbeafe', fg: '#1e40af' },
	sheet: { bg: '#dcfce7', fg: '#166534' },
	slide: { bg: '#ffedd5', fg: '#9a3412' },
	image: { bg: '#f3e8ff', fg: '#6b21a8' },
	video: { bg: '#e0f2fe', fg: '#075985' },
	audio: { bg: '#fef9c3', fg: '#854d0e' },
	other: { bg: '#f1f5f9', fg: '#475569' },
}

const BY_EXTENSION: Record<string, keyof typeof FAMILIES> = {
	pdf: 'pdf',
	doc: 'doc',
	docx: 'doc',
	txt: 'doc',
	md: 'doc',
	xls: 'sheet',
	xlsx: 'sheet',
	csv: 'sheet',
	ppt: 'slide',
	pptx: 'slide',
	png: 'image',
	jpg: 'image',
	jpeg: 'image',
	gif: 'image',
	svg: 'image',
	webp: 'image',
	mp4: 'video',
	mov: 'video',
	webm: 'video',
	mp3: 'audio',
	wav: 'audio',
	m4a: 'audio',
}

function extension(file: any) {
	const name = String(file.file_name || file.file_url || '')
	const dot = name.lastIndexOf('.')
	if (dot === -1) return file.file_type || '?'
	return name.slice(dot + 1).slice(0, 4)
}

function badgeStyle(file: any) {
	const family = BY_EXTENSION[extension(file).toLowerCase()] || 'other'
	const { bg, fg } = FAMILIES[family]
	return { backgroundColor: bg, color: fg }
}

// Base-10 units, matching what Frappe's own file list shows, so a size here
// agrees with the size on the desk.
function formatSize(bytes?: number) {
	const size = Number(bytes || 0)
	if (!size) return __('Unknown size')
	const units = ['B', 'KB', 'MB', 'GB']
	let index = 0
	let value = size
	while (value >= 1000 && index < units.length - 1) {
		value /= 1000
		index += 1
	}
	return `${value < 10 && index > 0 ? value.toFixed(1) : Math.round(value)} ${units[index]}`
}
</script>
