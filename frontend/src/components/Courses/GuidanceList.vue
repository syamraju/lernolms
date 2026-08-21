<template>
	<section class="space-y-3">
		<h3 v-if="title" class="text-p-base-semibold text-ink-gray-9">
			{{ title }}
		</h3>

		<ul v-if="variant === 'bullets'" class="space-y-1.5 ps-5">
			<li
				v-for="(item, index) in items"
				:key="index"
				class="list-disc text-p-base text-ink-gray-7"
			>
				<span v-if="item.title" class="font-medium text-ink-gray-9">
					{{ item.title }}
				</span>
				{{ item.body }}
			</li>
		</ul>

		<dl v-else class="space-y-4">
			<div v-for="(item, index) in items" :key="index">
				<dt v-if="item.title" class="text-p-base-medium text-ink-gray-9">
					{{ item.title }}
				</dt>
				<dd class="text-p-base text-ink-gray-7">{{ item.body }}</dd>
			</div>
		</dl>
	</section>
</template>

<script setup lang="ts">
/**
 * The advisory copy blocks that carry the non-interactive steps of the
 * creation flow (course structure, filming, accessibility). A shared component
 * rather than repeated markup so the three read as one voice and a spacing or
 * type change lands everywhere at once.
 */
withDefaults(
	defineProps<{
		title?: string
		items: { title?: string; body: string }[]
		variant?: 'definitions' | 'bullets'
	}>(),
	{ title: '', variant: 'definitions' }
)
</script>
