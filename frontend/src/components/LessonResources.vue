<template>
	<section v-if="resources.length" class="space-y-4 border-t pt-6">
		<h2 class="text-base-semibold text-ink-gray-9">{{ __('Resources') }}</h2>

		<div v-if="downloads.length" class="space-y-1.5">
			<h3 class="text-p-sm-medium text-ink-gray-7">
				{{ __('Downloadable materials') }}
			</h3>
			<ul class="divide-y border-y">
				<li v-for="row in downloads" :key="row.name">
					<a
						:href="safeUrl(row.file ?? '')"
						v-external
						class="flex items-center gap-2 py-2 text-p-base text-ink-gray-9 hover:underline"
					>
						<span class="lucide-file-down size-4 shrink-0 text-ink-gray-5" />
						<span class="min-w-0 truncate">{{ row.title }}</span>
					</a>
				</li>
			</ul>
		</div>

		<div v-if="links.length" class="space-y-1.5">
			<h3 class="text-p-sm-medium text-ink-gray-7">
				{{ __('External resources') }}
			</h3>
			<ul class="divide-y border-y">
				<li v-for="row in links" :key="row.name">
					<a
						:href="safeUrl(row.url ?? '')"
						v-external
						class="flex items-center gap-2 py-2 text-p-base text-ink-gray-9 hover:underline"
					>
						<span
							class="lucide-external-link size-4 shrink-0 text-ink-gray-5"
						/>
						<span class="min-w-0 truncate">{{ row.title }}</span>
					</a>
				</li>
			</ul>
		</div>
	</section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { safeUrl } from '@/utils/safeUrl'
import type { LessonResourceRow } from '@/types'

/**
 * The files and links attached to a curriculum item, shown to learners under
 * the lesson body. Split into downloads and links because the two behave
 * differently: one saves to disk, the other leaves the site.
 */
const props = withDefaults(defineProps<{ resources?: LessonResourceRow[] }>(), {
	resources: () => [],
})

const resources = computed(() => props.resources ?? [])
const downloads = computed(() =>
	resources.value.filter((row) => row.resource_type !== 'External Resource')
)
const links = computed(() =>
	resources.value.filter((row) => row.resource_type === 'External Resource')
)
</script>
