// Temporary, for visual checks only — not part of the build.
//
// Two things stop `yarn dev` from running outside a bench checkout:
//  1. the frappe-ui plugin pins the dev server to 8080 from its own `config`
//     hook, so overriding server.port in the config object is not enough — the
//     plugin's value is merged in afterwards. A plugin whose `config` hook runs
//     last is what actually wins.
//  2. src/socket.js imports ../../../../sites/common_site_config.json, which
//     only exists inside a bench. Resolved to a stub here.
import base from './vite.config.js'

const COMMON_SITE_CONFIG = /sites\/common_site_config\.json$/

// `post`, so its config hook runs after frappe-ui's and wins the merge.
const forcePort = {
	name: 'preview-force-port',
	enforce: 'post',
	config: () => ({ server: { port: 8085, strictPort: true } }),
}

const previewShims = {
	name: 'preview-shims',
	enforce: 'pre',
	resolveId(id) {
		return COMMON_SITE_CONFIG.test(id) ? '\0common_site_config' : null
	},
	load(id) {
		return id === '\0common_site_config'
			? 'export const socketio_port = 9000; export default { socketio_port: 9000 }'
			: null
	},
}

export default async (env) => {
	const config = typeof base === 'function' ? await base(env) : base
	return { ...config, plugins: [...config.plugins, previewShims, forcePort] }
}
