/**
 * The real `__`, for tests of code that formats placeholders.
 *
 * Most suites stub `__` as identity, which is fine until the code under test
 * calls `.format(...)` — the app's translate returns a formatter object for any
 * message containing `{n}`, and an identity stub returns a string, so the test
 * fails on a difference the app does not have. This mirrors
 * `src/translation.js` exactly.
 *
 * Install it per test rather than once per file: `window.__` is a shared global
 * and other suites in the same worker assign their own.
 */
export function translate(message: string): any {
	if (!/{\d+}/.test(message)) return message
	return {
		format: (...args: unknown[]) =>
			message.replace(/{(\d+)}/g, (match, index) =>
				typeof args[Number(index)] !== 'undefined'
					? String(args[Number(index)])
					: match,
			),
	}
}

export function installTranslate(): void {
	;(globalThis as any).__ = translate
	if (typeof window !== 'undefined') (window as any).__ = translate
}
