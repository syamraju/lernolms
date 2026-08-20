import frappeUIPreset from 'frappe-ui/tailwind'
import { safeAreaPlugin } from './tailwind/safeArea.js'
import { fontSizeTheme, FONT_SANS, FONT_MONO } from './tailwind/cds/type-scale.mjs'

export default {
  presets: [frappeUIPreset],
  content: [
    './index.html',
    './src/**/*.{vue,js,ts,jsx,tsx}',
    './node_modules/frappe-ui/src/**/*.{vue,js,ts,jsx,tsx}',
    '../node_modules/frappe-ui/src/**/*.{vue,js,ts,jsx,tsx}',
    './node_modules/frappe-ui/frappe/**/*.{vue,js,ts,jsx,tsx}',
    '../node_modules/frappe-ui/frappe/**/*.{vue,js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      strokeWidth: {
        1.5: '1.5',
      },
      screens: {
        '2xl': '1600px',
        '3xl': '1920px',
      },
      // Cloudscape type ramp. `text-<size>` and `text-p-<size>` are utilities
      // generated from this map, and utilities outrank the components layer —
      // so this is the only place they can be moved off frappe-ui's Inter
      // scale. The weight variants (`text-lg-semibold` and friends) are
      // components and are re-declared in src/styles/cds-typography.css
      // instead; both read the same numbers from tailwind/cds/type-scale.mjs.
      fontSize: fontSizeTheme(),
      fontFamily: {
        sans: FONT_SANS,
        text: FONT_SANS,
        mono: FONT_MONO,
      },
    },
  },
  plugins: [safeAreaPlugin],
}
