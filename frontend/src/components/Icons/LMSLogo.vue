<template>
	<!-- Learno mark. An "L" monogram with a rising dot, set in a rounded tile on
	     the Cloudscape primary blue (color-variable:
	     background/button/primary/default). The geometry is deliberately heavy —
	     the mark renders at 28–32px in the sidebar and user menu, where the thin
	     strokes of the previous mark closed up.

	     Keep in step with public/learning.svg and tailwind/cds/render-logo.py,
	     which redraws this as PNG for the favicon and app icons. -->
	<svg
		width="80"
		height="79"
		viewBox="0 0 80 79"
		fill="none"
		role="img"
		aria-label="Learno"
		xmlns="http://www.w3.org/2000/svg"
	>
		<rect width="80" height="79" rx="21" fill="#006ce0" />
		<path d="M26.5 19.5h11.2v29.4h17.8v10.6H26.5V19.5Z" fill="#ffffff" />
		<circle cx="53.5" cy="26.5" r="6.6" fill="#ffffff" fill-opacity="0.85" />
	</svg>
</template>
