<!--
	One navigation row. Figma: node I68:11759;55:9930 (neutral) and
	I68:11759;55:10226 (selected — white card, #e6f6fe hairline, the file's one
	elevation).

	`match` exists because a section's row has to stay lit on the section's
	detail pages: opening a course must not un-light "Courses". vue-router's own
	`exact`/`active-class` keys off the path prefix, which is the wrong test here
	(the student routes are siblings under /learn, not nested), so the row names
	the routes it owns instead.
-->
<template>
	<a v-if="href" :href="safeUrl(href)" class="learno-nav-row" v-external>
		<span :class="[icon, 'size-6 shrink-0']" aria-hidden="true" />
		<span class="flex-1 truncate text-start">{{ label }}</span>
		<span
			class="lucide-arrow-up-right size-4 shrink-0 text-[var(--learno-ink-subtle)]"
			aria-hidden="true"
		/>
	</a>

	<router-link
		v-else
		:to="to"
		class="learno-nav-row"
		:class="{ 'is-active': isActive }"
		:aria-current="isActive ? 'page' : undefined"
	>
		<span :class="[icon, 'size-6 shrink-0']" aria-hidden="true" />
		<span class="flex-1 truncate text-start">{{ label }}</span>
		<span
			v-if="count"
			class="grid min-w-5 place-items-center rounded-[5px] bg-[var(--learno-badge)] px-[5px] py-px text-[14px] font-medium leading-none text-white"
		>
			{{ count > 99 ? '99+' : count }}
		</span>
	</router-link>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { safeUrl } from '@/utils/safeUrl'

const props = defineProps<{
	label: string
	icon: string
	to?: any
	href?: string
	count?: number
	match?: string[]
}>()

const route = useRoute()

const isActive = computed(() => {
	if (props.href) return false
	const names = props.match?.length ? props.match : [props.to?.name]
	return names.includes(route.name as string)
})
</script>

<style scoped>
.learno-nav-row {
	display: flex;
	height: 48px;
	width: 100%;
	align-items: center;
	gap: 10px;
	border-radius: var(--learno-r-md);
	border: 1px solid transparent;
	padding: 12px 16px;
	font-size: 16px;
	line-height: 1.2;
	color: var(--learno-ink);
	transition: background-color 120ms ease, border-color 120ms ease,
		box-shadow 120ms ease;
}

.learno-nav-row:hover {
	background: #fafbfd;
}

.learno-nav-row.is-active {
	background: #fff;
	border-color: #e6f6fe;
	box-shadow: var(--learno-shadow);
	font-weight: 600;
}

.learno-nav-row.is-active [aria-hidden='true'] {
	color: var(--learno-primary);
}
</style>
