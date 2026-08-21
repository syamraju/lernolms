<template>
	<ListPage
		:breadcrumbs="breadcrumbs"
		:title="__('Evaluations')"
		layout="list"
		:columns="columns"
		:rows="rows"
		:loading="queue.loading"
		:total-count="queue.data?.total ?? null"
		:list-options="{
			showTooltip: false,
			selectable: false,
			getRowRoute: (row) => ({
				name: 'EvaluationReview',
				params: { submission: row.name },
			}),
		}"
		v-model:page-length="pageLength"
		empty-name="Evaluations"
		empty-icon="lucide-clipboard-pen-line"
	>
		<template #actions>
			<HeaderButton
				v-if="user.data?.is_moderator"
				:label="__('Assign evaluators')"
				icon="lucide-users"
				@click="showAssignments = true"
			/>
		</template>

		<template #filters>
			<div class="flex flex-wrap items-center gap-2">
				<!--
					Pending first and selected by default: this page exists to be
					emptied, so the work is what it opens on.
				-->
				<div class="flex rounded-md border border-outline-gray-2 p-0.5">
					<button
						v-for="tab in STATUS_TABS"
						:key="tab.value"
						type="button"
						class="rounded px-3 py-1 text-p-sm transition-colors"
						:class="
							status === tab.value
								? 'bg-surface-gray-3 text-ink-gray-9'
								: 'text-ink-gray-7 hover:bg-surface-gray-1'
						"
						:aria-pressed="status === tab.value"
						@click="status = tab.value"
					>
						{{ __(tab.label) }}
						<span
							v-if="tab.value === 'Pending' && pendingCount"
							class="ms-1 tabular-nums text-ink-gray-5"
						>
							{{ pendingCount }}
						</span>
					</button>
				</div>

				<FormControl
					v-if="courseOptions.length > 1"
					type="select"
					class="w-56"
					:options="courseOptions"
					:modelValue="course"
					:aria-label="__('Course')"
					@update:modelValue="course = $event"
				/>

				<FormControl
					type="text"
					class="w-56"
					:placeholder="__('Search learner or quiz')"
					:aria-label="__('Search')"
					v-model="search"
				/>
			</div>
		</template>

		<template #cell="{ row, column }">
			<Badge
				v-if="column.key === 'evaluation_status'"
				:label="
					row.evaluation_status === 'Pending' ? __('Pending') : __('Evaluated')
				"
				variant="subtle"
				:theme="row.evaluation_status === 'Pending' ? 'orange' : 'green'"
			/>
			<span v-else-if="column.key === 'result'" class="text-ink-gray-7">
				{{
					row.evaluation_status === 'Pending'
						? '—'
						: __('{0} / {1}').format(row.score, row.score_out_of)
				}}
			</span>
			<span v-else-if="column.key === 'creation'" class="text-ink-gray-7">
				{{ timeAgo(row.creation) }}
			</span>
			<span v-else>{{ row[column.key] ?? '—' }}</span>
		</template>
	</ListPage>

	<EvaluatorAssignments
		v-if="user.data?.is_moderator"
		v-model="showAssignments"
		@saved="queue.reload()"
	/>
</template>

<script setup lang="ts">
import { computed, inject, onMounted, ref, watch } from 'vue'
import { Badge, FormControl, createResource, usePageMeta } from 'frappe-ui'
import { useRouter } from 'vue-router'
import ListPage from '@/components/Layouts/ListPage.vue'
import HeaderButton from '@/components/HeaderButton.vue'
import EvaluatorAssignments from '@/components/Modals/EvaluatorAssignments.vue'
import { sessionStore } from '@/stores/session'
import { timeAgo } from '@/utils'
import type { EvaluationQueueRow, ListColumn, Resource } from '@/types'

type QueueStatus = 'Pending' | 'Evaluated'

interface QueuePayload {
	submissions: EvaluationQueueRow[]
	total: number
	courses: { name: string; title: string }[]
	pending_count: number
}

const STATUS_TABS: { value: QueueStatus; label: string }[] = [
	{ value: 'Pending', label: 'To mark' },
	{ value: 'Evaluated', label: 'Marked' },
]

const { brand } = sessionStore()
const router = useRouter()
const user = inject('$user') as { data?: Record<string, boolean> }

onMounted(() => {
	// The server refuses an unassigned user anyway; this only saves them from
	// landing on an empty page they had no way to know was not for them.
	if (
		!user.data?.is_evaluator &&
		!user.data?.is_moderator &&
		!user.data?.is_instructor
	) {
		router.push({ name: 'Courses' })
	}
})

const status = ref<QueueStatus>('Pending')
const course = ref('')
const search = ref('')
const pageLength = ref(24)

const queue = createResource({
	url: 'lms.lms.evaluation.list_evaluation_queue',
	makeParams: () => ({
		status: status.value,
		course: course.value || null,
		search: search.value.trim() || null,
		limit: pageLength.value,
	}),
	auto: true,
}) as Resource<QueuePayload | null>

let searchTimer: ReturnType<typeof setTimeout> | undefined

watch([status, course, pageLength], () => queue.reload())
watch(search, () => {
	// Debounced: the query hits three indexed columns and the reader is still typing.
	clearTimeout(searchTimer)
	searchTimer = setTimeout(() => queue.reload(), 300)
})

const rows = computed(() => queue.data?.submissions ?? [])
const pendingCount = computed(() => queue.data?.pending_count ?? 0)

const courseOptions = computed(() => [
	{ label: __('All courses'), value: '' },
	...(queue.data?.courses ?? []).map((row) => ({
		label: row.title,
		value: row.name,
	})),
])

const columns = computed<ListColumn[]>(() => [
	{ label: __('Learner'), key: 'member_name', width: 1 },
	{ label: __('Quiz'), key: 'quiz_title', width: 1 },
	{ label: __('Submitted'), key: 'creation', width: 1, align: 'left' },
	{ label: __('Score'), key: 'result', width: 1, align: 'left' },
	{ label: __('Status'), key: 'evaluation_status', width: 1, align: 'left' },
])

const breadcrumbs = computed(() => [
	{ label: __('Evaluations'), route: { name: 'Evaluations' } },
])

usePageMeta(() => ({
	title: __('Evaluations'),
	icon: brand.favicon,
}))
</script>
