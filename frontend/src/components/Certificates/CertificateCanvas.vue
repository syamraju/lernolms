<template>
	<div
		ref="frame"
		class="relative mx-auto w-full select-none overflow-hidden rounded-md"
		:class="background ? 'shadow-sm ring-1 ring-outline-gray-2' : ''"
		:style="{ aspectRatio: `${canvasWidth} / ${canvasHeight}` }"
	>
		<img
			v-if="background"
			:src="background"
			alt=""
			class="pointer-events-none absolute inset-0 h-full w-full object-fill"
			draggable="false"
		/>
		<div
			v-else
			class="absolute inset-0 grid place-items-center border-2 border-dashed border-outline-gray-3 bg-surface-gray-1 text-p-sm text-ink-gray-5"
		>
			{{ __('No background uploaded yet') }}
		</div>

		<component
			:is="editable ? 'button' : 'div'"
			v-for="(element, index) in template.elements"
			:key="index"
			:type="editable ? 'button' : undefined"
			class="flex items-center overflow-hidden"
			:class="[
				justifyClass(element.align),
				editable ? 'cursor-move' : 'pointer-events-none',
				editable && index === selectedIndex
					? 'outline outline-2 outline-offset-1 outline-blue-500'
					: editable
					  ? 'outline-dashed outline-1 outline-outline-gray-3'
					  : '',
			]"
			:style="elementStyle(element, scale)"
			:aria-label="editable ? describe(element) : undefined"
			@pointerdown="startDrag($event, index)"
			@keydown="onKeydown($event, index)"
		>
			<img
				v-if="element.element_type === 'Image' && element.image"
				:src="element.image"
				alt=""
				class="h-full w-full object-contain"
				draggable="false"
			/>
			<span
				v-else-if="element.element_type === 'Image'"
				class="w-full text-center text-ink-gray-5"
				:style="{ fontSize: `${12 * Math.max(scale, 0.5)}px` }"
			>
				{{ __('No image') }}
			</span>
			<span v-else class="w-full truncate">{{ text(element) }}</span>

			<!--
				The resize grip is inside the element so it travels with it. It is
				only rendered for the selected element: eight always-on grips over
				a dozen fields turns the canvas into a field of dots.
			-->
			<span
				v-if="editable && index === selectedIndex"
				class="absolute -bottom-1 -end-1 size-3 cursor-se-resize rounded-full border border-white bg-blue-500"
				@pointerdown.stop="startResize($event, index)"
			/>
		</component>
	</div>
</template>

<script setup lang="ts">
/**
 * Draws a certificate: the uploaded background, with every placed element on
 * top of it.
 *
 * The same component renders the designer's editing surface and the public
 * verification page, which is the point — a moderator who lines a name up
 * against the artwork here sees it in exactly that spot on the page an employer
 * opens. `editable` is the only difference between the two.
 *
 * Positions arrive in the background image's own pixels and are converted to
 * screen pixels here, once, through `scale`. Nothing upstream knows how wide the
 * canvas happens to be rendered.
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import dayjs from '@/utils/dayjs'
import {
	clampElement,
	elementStyle,
	renderValue,
	scaleFor,
} from '@/utils/certificate'
import type {
	CertificateElement,
	CertificateTemplate,
	CertificateVariable,
	TextAlign,
} from '@/utils/certificate'

const props = withDefaults(
	defineProps<{
		template: CertificateTemplate
		variables: CertificateVariable[]
		values?: Record<string, unknown>
		editable?: boolean
		selectedIndex?: number
	}>(),
	{ values: () => ({}), editable: false, selectedIndex: -1 }
)

const emit = defineEmits<{
	select: [index: number]
	change: [index: number, patch: Partial<CertificateElement>]
}>()

const frame = ref<HTMLElement | null>(null)
const renderedWidth = ref(0)

const canvasWidth = computed(() => props.template.canvas_width || 1754)
const canvasHeight = computed(() => props.template.canvas_height || 1240)
const background = computed(() => props.template.background_image || '')
const scale = computed(() => scaleFor(canvasWidth.value, renderedWidth.value))

let observer: ResizeObserver | null = null

onMounted(() => {
	if (!frame.value) return
	// Measured rather than assumed: the designer's canvas shares a row with a
	// properties panel that opens and closes, and a certificate that only lines
	// up until the panel appears is not lined up.
	observer = new ResizeObserver((entries) => {
		renderedWidth.value = entries[0]?.contentRect.width ?? 0
	})
	observer.observe(frame.value)
	renderedWidth.value = frame.value.clientWidth
})

onBeforeUnmount(() => observer?.disconnect())

function justifyClass(align: TextAlign) {
	if (align === 'left') return 'justify-start'
	if (align === 'right') return 'justify-end'
	return 'justify-center'
}

function text(element: CertificateElement): string {
	const value = renderValue(element, props.variables, props.values, (raw, format) =>
		dayjs(raw).format(format)
	)
	if (value) return value
	// An empty box in the editor is unclickable and looks like a bug. On the
	// issued certificate the same element renders genuinely blank.
	if (!props.editable) return ''
	const label = props.variables.find((entry) => entry.key === element.variable)?.label
	return label || __('Empty')
}

function describe(element: CertificateElement): string {
	if (element.element_type === 'Image') return __('Image')
	return text(element)
}

function move(index: number, x: number, y: number) {
	const element = props.template.elements[index]
	const clamped = clampElement(
		{ ...element, x, y },
		canvasWidth.value,
		canvasHeight.value
	)
	emit('change', index, { x: clamped.x, y: clamped.y })
}

function startDrag(event: PointerEvent, index: number) {
	if (!props.editable) return
	emit('select', index)

	const element = props.template.elements[index]
	const startX = event.clientX
	const startY = event.clientY
	const originX = element.x
	const originY = element.y
	const factor = scale.value || 1
	const target = event.currentTarget as HTMLElement

	function onMove(moveEvent: PointerEvent) {
		move(
			index,
			originX + (moveEvent.clientX - startX) / factor,
			originY + (moveEvent.clientY - startY) / factor
		)
	}

	function onUp() {
		target.removeEventListener('pointermove', onMove)
		target.removeEventListener('pointerup', onUp)
		target.removeEventListener('pointercancel', onUp)
	}

	// Pointer capture keeps the drag alive when the cursor outruns the box,
	// which it always does on a fast drag.
	target.setPointerCapture?.(event.pointerId)
	target.addEventListener('pointermove', onMove)
	target.addEventListener('pointerup', onUp)
	target.addEventListener('pointercancel', onUp)
}

function startResize(event: PointerEvent, index: number) {
	if (!props.editable) return
	const element = props.template.elements[index]
	const startX = event.clientX
	const startY = event.clientY
	const originWidth = element.width
	const originHeight = element.height
	const factor = scale.value || 1
	const target = event.currentTarget as HTMLElement

	function onMove(moveEvent: PointerEvent) {
		const clamped = clampElement(
			{
				...element,
				width: originWidth + (moveEvent.clientX - startX) / factor,
				height: originHeight + (moveEvent.clientY - startY) / factor,
			},
			canvasWidth.value,
			canvasHeight.value
		)
		emit('change', index, {
			width: clamped.width,
			height: clamped.height,
			x: clamped.x,
			y: clamped.y,
		})
	}

	function onUp() {
		target.removeEventListener('pointermove', onMove)
		target.removeEventListener('pointerup', onUp)
		target.removeEventListener('pointercancel', onUp)
	}

	target.setPointerCapture?.(event.pointerId)
	target.addEventListener('pointermove', onMove)
	target.addEventListener('pointerup', onUp)
	target.addEventListener('pointercancel', onUp)
}

// Dragging with a mouse is not the only way to place a field. Arrow keys move
// the selected element a pixel at a time, ten with Shift.
const NUDGE = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }

function onKeydown(event: KeyboardEvent, index: number) {
	if (!props.editable) return
	const nudge = NUDGE[event.key as keyof typeof NUDGE]
	if (!nudge) return
	event.preventDefault()
	const step = event.shiftKey ? 10 : 1
	const element = props.template.elements[index]
	move(index, element.x + nudge[0] * step, element.y + nudge[1] * step)
}
</script>
