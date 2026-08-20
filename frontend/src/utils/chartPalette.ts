/**
 * Cloudscape's categorical chart palette, as a plain array for ECharts.
 *
 * The rest of the theme reaches components through CSS custom properties, but
 * ECharts is canvas: it takes concrete colour strings at render time and cannot
 * resolve `var(--cds-chart-categorical-1)`. So the values are read out of the
 * stylesheet once per theme change and handed over as literals.
 *
 * CDS defines exactly five categorical roles (colorChartsPaletteCategorical1–5)
 * plus the threshold colours; anything beyond five series wraps, which is what
 * ECharts does with a short palette anyway.
 *
 * Source: Figma `color-charts-palette`, mirrored into tailwind/cds/cds-source.json
 * so the two cannot drift.
 */
import { computed } from 'vue'
import { theme } from '@/utils/theme'

const CATEGORICAL = [1, 2, 3, 4, 5] as const

/** Read a custom property off the document root, trimmed. */
function token(name: string): string {
	if (typeof document === 'undefined') return ''
	return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

/**
 * The categorical series colours for the active theme.
 *
 * Depends on `theme` so it recomputes when the user switches: the custom
 * properties resolve differently under `[data-theme="dark"]`, and a cached
 * array would keep the light values on a canvas that no longer matches.
 */
export const chartColors = computed<string[]>(() => {
	// Referenced so the computed tracks theme changes; the value itself is not
	// needed because the custom properties already carry the per-theme value.
	void theme.value
	return CATEGORICAL.map((n) => token(`--cds-chart-categorical-${n}`)).filter(Boolean)
})

/** Threshold colours, for charts that mark a target or a pass/fail line. */
export const chartThresholds = computed(() => {
	void theme.value
	return {
		positive: token('--cds-chart-threshold-positive'),
		negative: token('--cds-chart-threshold-negative'),
		info: token('--cds-chart-threshold-info'),
		neutral: token('--cds-chart-threshold-neutral'),
	}
})
