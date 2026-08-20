<!--
	Read-only render of a lesson's authored content.

	Lessons carry content in one of two fields depending on how old they are:
	`content` (EditorJS JSON, the current authoring path) and `body` (the legacy
	macro/markdown text). Both have to render, and both already have a renderer
	in this app — EditorJS in read-only mode and LessonContent respectively. This
	wraps the pair so the student page does not have to know which era a lesson
	is from.

	The EditorJS instance is created and torn down per lesson: it mutates the DOM
	node it is handed, so reusing one across lessons leaves the previous lesson's
	blocks behind.
-->
<template>
	<div>
		<div
			v-show="hasEditorContent"
			:id="holderId"
			class="ProseMirror prose prose-sm max-w-none !whitespace-normal learno-prose"
		/>

		<LessonContent
			v-if="!hasEditorContent && lesson.body"
			:key="lesson.name"
			:content="lesson.body"
			:youtube="lesson.youtube"
			:quizId="lesson.quiz_id"
		/>
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, watch, nextTick } from 'vue'
import EditorJS from '@editorjs/editorjs'
import { getEditorTools, sanitizeEditorJs, enablePlyr } from '@/utils'
import LessonContent from '@/components/LessonContent.vue'

const props = defineProps<{ lesson: Record<string, any> }>()

// Unique per mount so two LessonBody instances on one page (they never coexist
// today, but nothing stops it) cannot fight over the same holder element.
const holderId = `learno-lesson-${Math.random().toString(36).slice(2, 10)}`

let editor: any = null

const hasEditorContent = computed(() => Boolean(props.lesson?.content))

function destroy() {
	// EditorJS only exposes destroy() once it has finished initialising; calling
	// it earlier throws and would leave the holder populated.
	try {
		editor?.destroy?.()
	} catch {
		/* already gone */
	}
	editor = null
}

async function render() {
	destroy()
	if (!hasEditorContent.value) return

	let data
	try {
		data = sanitizeEditorJs(JSON.parse(props.lesson.content))
	} catch {
		// A lesson edited from the desk form can hold non-JSON here. Falling back
		// to the legacy renderer is better than blanking the page.
		return
	}

	await nextTick()
	editor = new EditorJS({
		holder: holderId,
		tools: getEditorTools(false, {}, { studentView: true }),
		data,
		readOnly: true,
		defaultBlock: 'embed',
		i18n: {
			direction: document.documentElement.dir === 'rtl' ? 'rtl' : 'ltr',
		},
		async onReady() {
			const root = document.getElementById(holderId)
			root?.querySelectorAll('a').forEach((anchor) => {
				anchor.setAttribute('target', '_blank')
				anchor.setAttribute('rel', 'noopener noreferrer')
			})
			// Embedded players are inert markup until Plyr adopts them; the same
			// call the admin lesson page makes after its editor is ready.
			await enablePlyr()
		},
	})
}

onMounted(render)
onBeforeUnmount(destroy)

watch(() => props.lesson?.name, render)
</script>
