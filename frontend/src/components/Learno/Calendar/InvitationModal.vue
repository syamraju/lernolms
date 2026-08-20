<!--
	Participant picker. Figma: node 144:93460 — an invited list with per-row
	Cancel, over a search field.

	Who can be invited is decided by the server, not here:
	`calendar_api.get_event_invitees` returns only people the caller shares a
	course with, so this cannot be used to enumerate the user table. The
	"This Event / All Events" radio in the design applies to a recurring series;
	it is only shown when the event actually repeats.
-->
<template>
	<LearnoDialog
		:open="open"
		:title="__('Invitation')"
		:width="564"
		@update:open="$emit('update:open', $event)"
		@save="save"
	>
		<div class="flex flex-col">
			<fieldset v-if="repeats" class="flex flex-col gap-4 pb-5">
				<label class="flex items-center gap-4">
					<input v-model="scope" type="radio" value="this" class="size-5 accent-[#1e3a8a]" />
					<span class="text-[16px]">{{ __('This Event') }}</span>
				</label>
				<label class="flex items-center gap-4">
					<input v-model="scope" type="radio" value="all" class="size-5 accent-[#1e3a8a]" />
					<span class="text-[16px]">{{ __('All Events') }}</span>
				</label>
			</fieldset>

			<div v-if="draft.length" class="border-t border-[var(--learno-line-soft)] pt-5">
				<p class="mb-4 text-[14px] text-[var(--learno-ink-muted)]">
					{{ __('Invited') }}
				</p>
				<ul class="flex flex-col gap-4">
					<li
						v-for="person in draft"
						:key="person.participant"
						class="flex items-center gap-4"
					>
						<img
							v-if="person.user_image"
							:src="safeUrl(person.user_image)"
							alt=""
							class="size-10 shrink-0 rounded-full object-cover"
						/>
						<span
							v-else
							class="grid size-10 shrink-0 place-items-center rounded-full bg-[var(--learno-primary-soft)] text-[13px] font-semibold text-[var(--learno-primary)]"
						>
							{{ (person.full_name || person.participant).charAt(0).toUpperCase() }}
						</span>
						<span class="flex min-w-0 flex-1 flex-col">
							<span class="truncate text-[15px] text-[var(--learno-ink-strong)]">
								{{ person.full_name || person.participant }}
							</span>
							<span class="text-[12px] text-[var(--learno-ink-subtle)]">
								{{ person.participant_role === 'Instructor' ? __('Instructor') : __('Student') }}
							</span>
						</span>
						<button
							type="button"
							class="text-[14px] text-[#9f1239] transition hover:underline"
							@click="remove(person.participant)"
						>
							{{ __('Cancel') }}
						</button>
					</li>
				</ul>
			</div>

			<div class="mt-5 border-t border-[var(--learno-line-soft)] pt-5">
				<div class="flex items-center gap-3">
					<span
						class="lucide-users size-6 shrink-0 text-[var(--learno-ink-subtle)]"
						aria-hidden="true"
					/>
					<input
						v-model="search"
						type="search"
						class="flex-1 rounded-[var(--learno-r-sm)] border border-[var(--learno-line)] px-4 py-3 text-[14px]"
						:placeholder="__('Add Participants')"
					/>
				</div>

				<ul
					v-if="candidates.length"
					class="learno-scroll mt-3 max-h-[220px] overflow-y-auto rounded-[var(--learno-r-md)] border border-[var(--learno-line)]"
				>
					<li v-for="person in candidates" :key="person.name">
						<button
							type="button"
							class="flex w-full items-center gap-3 px-4 py-2.5 text-start transition hover:bg-[var(--learno-canvas)]"
							@click="add(person)"
						>
							<span
								class="grid size-8 shrink-0 place-items-center rounded-full bg-[var(--learno-primary-soft)] text-[12px] font-semibold text-[var(--learno-primary)]"
							>
								{{ (person.full_name || person.name).charAt(0).toUpperCase() }}
							</span>
							<span class="min-w-0 flex-1 truncate text-[14px]">
								{{ person.full_name || person.name }}
							</span>
							<span class="text-[11px] text-[var(--learno-ink-subtle)]">
								{{ person.participant_role === 'Instructor' ? __('Instructor') : __('Student') }}
							</span>
						</button>
					</li>
				</ul>

				<p
					v-else-if="invitees.loading"
					class="mt-3 text-[13px] text-[var(--learno-ink-subtle)]"
				>
					{{ __('Loading…') }}
				</p>
				<p
					v-else-if="search"
					class="mt-3 text-[13px] text-[var(--learno-ink-subtle)]"
				>
					{{ __('Nobody in your courses matches that.') }}
				</p>
			</div>
		</div>
	</LearnoDialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { createResource } from 'frappe-ui'
import LearnoDialog from '@/components/Learno/LearnoDialog.vue'
import { safeUrl } from '@/utils/safeUrl'

const props = defineProps<{
	open: boolean
	participants: any[]
	course?: string
	repeats?: boolean
}>()

const emit = defineEmits<{
	(e: 'update:open', value: boolean): void
	(e: 'apply', participants: any[], scope: 'this' | 'all'): void
}>()

const draft = ref<any[]>([])
const search = ref('')
const scope = ref<'this' | 'all'>('this')

const invitees = createResource({
	url: 'lms.lms.calendar_api.get_event_invitees',
	makeParams: () => ({ course: props.course || undefined, search: search.value || undefined }),
})

watch(
	() => props.open,
	(isOpen) => {
		if (!isOpen) return
		draft.value = (props.participants || []).map((person) => ({ ...person }))
		search.value = ''
		scope.value = 'this'
		invitees.reload()
	},
	{ immediate: true }
)

// The list is server-filtered so a long roster stays usable; 300ms matches the
// debounce the course search uses.
let timer: ReturnType<typeof setTimeout> | undefined
watch(search, () => {
	clearTimeout(timer)
	timer = setTimeout(() => invitees.reload(), 300)
})

// Re-fetch when the event's course changes, since that changes who is reachable.
watch(
	() => props.course,
	() => {
		if (props.open) invitees.reload()
	}
)

const candidates = computed(() => {
	const already = new Set(draft.value.map((person) => person.participant))
	return (invitees.data || []).filter((person: any) => !already.has(person.name))
})

function add(person: any) {
	draft.value = [
		...draft.value,
		{
			participant: person.name,
			full_name: person.full_name,
			user_image: person.user_image,
			participant_role: person.participant_role,
		},
	]
	search.value = ''
}

function remove(participant: string) {
	draft.value = draft.value.filter((person) => person.participant !== participant)
}

function save() {
	emit('apply', draft.value, scope.value)
	emit('update:open', false)
}
</script>
