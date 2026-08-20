<!--
	Chats. The Figma sidebar carries a Chats row with an unread badge but the
	file has no chat frame, so this is built on what the LMS actually has:
	batch discussions. A student picks one of their batches on the left and the
	existing Discussions component carries the thread on the right — the same
	thread the batch page shows, not a second, parallel inbox.
-->
<template>
	<div class="flex h-full min-h-0 flex-col">
		<header
			class="shrink-0 border-b border-[var(--learno-line-soft)] bg-white px-6 py-[22px] lg:px-10"
		>
			<h1 class="text-[27px] font-semibold leading-[1.2] text-black max-lg:ps-12">
				{{ __('Chats') }}
			</h1>
			<p class="mt-1 text-[13px] text-[var(--learno-ink-muted)]">
				{{ __('Discussions from the batches you are part of.') }}
			</p>
		</header>

		<div class="flex min-h-0 flex-1">
			<aside
				class="learno-scroll w-[280px] shrink-0 overflow-y-auto border-e border-[var(--learno-line-soft)] bg-white p-3"
			>
				<p
					v-if="!myBatches.length && !batches.loading"
					class="px-2 py-6 text-[13px] text-[var(--learno-ink-muted)]"
				>
					{{ __('You are not enrolled in any batch yet.') }}
				</p>

				<button
					v-for="batch in myBatches"
					:key="batch.name"
					type="button"
					class="mb-1 flex w-full flex-col gap-1 rounded-[var(--learno-r-md)] px-3 py-2.5 text-start transition"
					:class="
						selected === batch.name
							? 'bg-[var(--learno-primary-soft)] text-[var(--learno-primary)]'
							: 'hover:bg-[var(--learno-canvas)]'
					"
					@click="selected = batch.name"
				>
					<span class="truncate text-[13px] font-medium">
						{{ batch.title }}
					</span>
					<span
						v-if="batch.start_date"
						class="text-[11px] text-[var(--learno-ink-subtle)]"
					>
						{{ batch.start_date }}
					</span>
				</button>
			</aside>

			<div
				class="learno-scroll min-w-0 flex-1 overflow-y-auto bg-[var(--learno-canvas)] p-6 lg:p-8"
			>
				<div v-if="selected" class="rounded-[var(--learno-r-lg)] bg-white p-6">
					<Discussions
						:key="selected"
						:title="__('Discussions')"
						doctype="LMS Batch"
						:docname="selected"
						:emptyStateTitle="__('No messages yet')"
						:emptyStateText="__('Start a discussion')"
					/>
				</div>

				<p
					v-else
					class="py-20 text-center text-[14px] text-[var(--learno-ink-muted)]"
				>
					{{ __('Pick a batch to open its discussion.') }}
				</p>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { createResource, usePageMeta } from 'frappe-ui'
import Discussions from '@/components/Discussions.vue'

usePageMeta(() => ({ title: __('Chats') }))

const selected = ref('')

// The student_api variant, not lms.lms.api's: that one substitutes upcoming
// published batches when the student has none, which would list threads they
// are not a member of.
const batches = createResource({
	url: 'lms.lms.student_api.get_my_batches',
	auto: true,
})

const myBatches = computed(() =>
	(batches.data || []).map((batch: any) => ({
		name: batch.name,
		title: batch.title || batch.name,
		start_date: batch.start_date,
	}))
)

// Open the first batch automatically: a two-pane view whose right pane is empty
// on arrival reads as broken rather than as a prompt.
watch(myBatches, (rows) => {
	if (!selected.value && rows.length) selected.value = rows[0].name
})
</script>
