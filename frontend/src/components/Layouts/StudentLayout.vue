<!--
	The shell every /learn route renders inside. Figma: the outer composition of
	frames 7:2, 90:4279, 90:5108 and friends — a grey gutter with two floating
	panels, the sidebar on the inline-start edge and the page on the rest.

	The `.learno` class on the root is what switches the design layer on; see
	src/styles/learno.css for why the student app carries its own tokens rather
	than re-pointing the app-wide ones.
-->
<template>
	<div class="learno flex h-dvh w-full gap-1.5 overflow-hidden p-1.5">
		<a
			href="#learno-main"
			class="sr-only focus:not-sr-only focus:absolute focus:start-4 focus:top-4 focus:z-50 focus:rounded focus:bg-white focus:px-4 focus:py-2 focus:shadow-md focus:outline-none"
			@click.prevent="skipToContent('learno-main')"
		>
			{{ __('Skip to main content') }}
		</a>

		<!-- Off-canvas on small screens; the design is desktop-only, so the phone
		     gets the same panel as a drawer rather than a second layout. -->
		<div
			v-if="drawerOpen"
			class="fixed inset-0 z-40 bg-black/30 lg:hidden"
			@click="drawerOpen = false"
		/>
		<div
			class="z-50 max-lg:fixed max-lg:inset-y-1.5 max-lg:start-1.5 max-lg:transition-transform"
			:class="
				drawerOpen
					? 'max-lg:translate-x-0'
					: 'max-lg:-translate-x-[110%] rtl:max-lg:translate-x-[110%]'
			"
		>
			<LearnoSidebar />
		</div>

		<main
			id="learno-main"
			tabindex="-1"
			class="learno-scroll relative flex min-w-0 flex-1 flex-col overflow-hidden rounded-[var(--learno-r-sm)] bg-white focus:outline-none"
		>
			<button
				type="button"
				class="learno-btn learno-btn-secondary absolute start-4 top-4 z-30 lg:hidden"
				:aria-label="__('Open navigation')"
				@click="drawerOpen = true"
			>
				<span class="lucide-menu size-4" aria-hidden="true" />
			</button>

			<slot />
		</main>
	</div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { skipToContent } from '@/utils/a11y'
import LearnoSidebar from '@/components/Learno/LearnoSidebar.vue'

const route = useRoute()
const drawerOpen = ref(false)

// Navigating is the drawer's dismiss: on a phone the panel covers the page it
// just navigated to, and leaving it open reads as "nothing happened".
watch(
	() => route.fullPath,
	() => {
		drawerOpen.value = false
	}
)
</script>
