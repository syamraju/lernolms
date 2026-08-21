<!--
	"Assigned Courses ————————————— 21 Items". Figma: node 100:9981.
	The rule is a flex spacer rather than a border on the heading so it fills
	whatever gap is left between the two labels at any width.
-->
<template>
	<div class="mb-[19px] flex items-center gap-[6px]">
		<h2
			class="text-[16px] font-semibold leading-[19px] text-[var(--learno-ink-strong)]"
		>
			{{ title }}
		</h2>
		<span class="learno-rule" aria-hidden="true" />
		<span class="text-[16px] leading-[19px] text-[var(--learno-ink-muted)]">
			{{ count === 1 ? __('1 Item') : `${count} ${__('Items')}` }}
		</span>
	</div>
</template>

<script setup lang="ts">
defineProps<{ title: string; count: number }>()
</script>
