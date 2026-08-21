<!--
	Pick someone to message.

	The list is people you share a batch with, not every account on the site:
	"who can I message" should not double as a directory.
-->
<template>
	<Dialog v-model="open" :options="{ title: __('New message'), size: 'sm' }">
		<template #body-content>
			<input
				v-model="search"
				type="search"
				:placeholder="__('Search people')"
				class="mb-3 w-full rounded-[var(--learno-r-md)] border border-[var(--learno-line)] px-3 py-2 text-[13px] outline-none focus:border-[var(--learno-primary)]"
			/>

			<p
				v-if="!people.loading && !(people.data || []).length"
				class="py-8 text-center text-[13px] text-[var(--learno-ink-subtle)]"
			>
				{{ __('Nobody to message yet — join a batch first.') }}
			</p>

			<ul class="learno-scroll max-h-72 overflow-y-auto">
				<li v-for="person in people.data || []" :key="person.user">
					<button
						type="button"
						class="flex w-full items-center gap-3 rounded-[var(--learno-r-md)] px-2 py-2 text-start hover:bg-[var(--learno-canvas)]"
						@click="pick(person)"
					>
						<Avatar
							:label="person.full_name"
							:image="person.avatar || undefined"
							size="lg"
						/>
						<span class="min-w-0 flex-1">
							<span class="block truncate text-[13px] font-medium">
								{{ person.full_name }}
							</span>
							<span
								class="block truncate text-[11px] text-[var(--learno-ink-subtle)]"
							>
								{{ person.user }}
							</span>
						</span>
					</button>
				</li>
			</ul>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { Avatar, Dialog, call, createResource } from 'frappe-ui'

const open = defineModel<boolean>({ required: true })
const emit = defineEmits<{
	(e: 'picked', conversation: string, person: any): void
}>()

const search = ref('')

const people = createResource({
	url: 'lms.lms.direct_message.get_people',
	makeParams: () => ({ search: search.value }),
	auto: true,
})

let debounce: number | undefined
watch(search, () => {
	if (debounce) window.clearTimeout(debounce)
	debounce = window.setTimeout(() => people.reload(), 200)
})

async function pick(person: any) {
	const result = await call('lms.lms.direct_message.start_dm', {
		user: person.user,
	})
	open.value = false
	search.value = ''
	emit('picked', result.conversation, result.peer)
}
</script>
