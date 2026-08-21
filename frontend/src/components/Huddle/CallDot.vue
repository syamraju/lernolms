<!-- "A call is happening in this thread" — the sidebar's smallest possible
     statement of it. -->
<template>
	<span
		class="grid size-5 shrink-0 place-items-center rounded-full bg-[var(--learno-primary)] text-white"
		:title="__('Call in progress')"
	>
		<Headphones class="size-3" />
	</span>
</template>

<script setup lang="ts">
import { Headphones } from 'lucide-vue-next'
</script>
