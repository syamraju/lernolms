/**
 * Every FileUploader must state, in its own markup, whether the File it creates
 * is public or private.
 *
 * Two defaults conspire against that. frappe-ui's FileUploader fills in
 * `{ private: true }` whenever uploadArgs says nothing about it
 * (FileUploader.vue:82-86), and frappe's upload_file defaults is_private to 1
 * (handler.py:152). A File that lands private and unattached is readable only by
 * its owner and Administrator (File.has_permission), so everyone else —
 * including the Guest rendering /login, and the crawler fetching an Open Graph
 * image — gets a broken image with no error anywhere.
 *
 * The ratchet below deliberately has NO exemption list. An exemption keyed on a
 * filename goes stale silently: the entry outlives the reason for it, and it
 * disables the check for every uploader in that file rather than the one that
 * was justified. Requiring an explicit `private:` instead means a genuinely
 * private uploader — the SCORM zip, a résumé, an assignment submission — says so
 * in the markup a reviewer is already reading.
 */
import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { readFileSync, readdirSync } from 'node:fs'
import { join, relative, resolve } from 'node:path'

vi.mock('frappe-ui', () => ({
	FileUploader: {
		name: 'FileUploader',
		props: ['uploadArgs', 'fileTypes', 'fileType', 'validateFile'],
		template: '<div />',
	},
	Button: { template: '<button><slot /></button>' },
	FormLabel: { props: ['label', 'required'], template: '<label />' },
	toast: { success: vi.fn(), error: vi.fn() },
}))

vi.mock('@/utils', () => ({ validateFile: () => undefined }))

vi.stubGlobal('__', (s: string) => s)

const uploadArgsOf = (wrapper: ReturnType<typeof mount>): unknown =>
	wrapper.findComponent({ name: 'FileUploader' }).props('uploadArgs')

describe('public uploaders declare private: false', () => {
	it('ImageUploader — brand logo and favicon, rendered on /login for Guest', async () => {
		const ImageUploader = (
			await import('@/components/Controls/ImageUploader.vue')
		).default
		const w = mount(ImageUploader, {
			global: { mocks: { __: (s: string) => s } },
		})
		expect(uploadArgsOf(w)).toMatchObject({ private: false })
	})

	it('Uploader — profile, badge, company logo, batch meta image, course image', async () => {
		const Uploader = (await import('@/components/Controls/Uploader.vue'))
			.default
		const w = mount(Uploader, {
			props: { modelValue: null },
			global: { mocks: { __: (s: string) => s } },
		})
		expect(uploadArgsOf(w)).toMatchObject({ private: false })
	})
})

// SettingFields renders whatever the backend labels type 'Upload', and
// get_transformed_fields maps EVERY Attach / Attach Image field of a
// third-party <Gateway> Settings doctype to that type. Only a field that opts
// in may be public.
describe('SettingFields leaves privacy to the field', () => {
	const mountFields = async (field: Record<string, unknown>) => {
		const SettingFields = (
			await import('@/components/Settings/SettingFields.vue')
		).default
		return mount(SettingFields, {
			props: {
				sections: [{ columns: [{ fields: [field] }] }],
				data: {},
			},
			global: { mocks: { __: (s: string) => s } },
		})
	}

	it('uploads public only when the field opts in', async () => {
		const w = await mountFields({
			label: 'Meta Image',
			name: 'meta_image',
			type: 'Upload',
			public: true,
		})
		expect(uploadArgsOf(w)).toMatchObject({ private: false })
	})

	it('keeps a gateway attachment private by default', async () => {
		const w = await mountFields({
			label: 'Merchant QR',
			name: 'merchant_qr',
			type: 'Upload',
		})
		expect(uploadArgsOf(w)).toMatchObject({ private: true })
	})
})

// tsconfig sets `types: []`, so node's globals aren't ambient here.
declare const process: { cwd(): string }

/** Same walk as vueFilesUnder, for the .ts modules that can upload from script. */
const tsFilesUnder = (dir: string): string[] => {
	const found: string[] = []
	for (const entry of readdirSync(dir, { withFileTypes: true })) {
		const full = join(dir, entry.name)
		if (entry.isDirectory()) found.push(...tsFilesUnder(full))
		else if (entry.name.endsWith('.ts') && !entry.name.endsWith('.d.ts'))
			found.push(full)
	}
	return found
}

const vueFilesUnder = (dir: string): string[] => {
	const found: string[] = []
	for (const entry of readdirSync(dir, { withFileTypes: true })) {
		const full = join(dir, entry.name)
		if (entry.isDirectory()) found.push(...vueFilesUnder(full))
		else if (entry.name.endsWith('.vue')) found.push(full)
	}
	return found
}

/**
 * Every opening uploader tag, ending at the first `>` that is NOT
 * inside an attribute value. RichTextEditor counts: it uploads pasted and
 * dragged images too (its uploadFile defaults them to private), so a lesson body
 * written in one decides privacy exactly as a FileUploader does. The app has no
 * <TextEditor — that name matched nothing at all. A naive /[^>]*>/ stops at the `>` of the first
 * `=>` in an arrow-function attribute, which makes the whole check depend on
 * the order the attributes happen to be written in.
 */
const UPLOADER_TAGS = ['<FileUploader', '<RichTextEditor']

const openingTags = (source: string): string[] =>
	UPLOADER_TAGS.flatMap((marker) => openingTagsFor(source, marker))

const openingTagsFor = (source: string, marker: string): string[] => {
	const tags: string[] = []

	for (
		let i = source.indexOf(marker);
		i !== -1;
		i = source.indexOf(marker, i + 1)
	) {
		// Guard against matching a longer component name that starts the same way.
		if (/[\w-]/.test(source[i + marker.length] ?? '')) continue

		let quote: string | null = null
		for (let j = i + marker.length; j < source.length; j++) {
			const char = source[j]
			if (quote) {
				if (char === quote) quote = null
			} else if (char === '"' || char === "'") {
				quote = char
			} else if (char === '>') {
				tags.push(source.slice(i, j + 1))
				break
			}
		}
	}
	return tags
}

/** The raw expression bound to :uploadArgs / v-bind:uploadArgs, if any. */
const uploadArgsExpression = (tag: string): string | null => {
	const match = tag.match(/(?::|v-bind:)uploadArgs\s*=\s*("|')([\s\S]*?)\1/)
	return match ? match[2].trim() : null
}

type Privacy = 'public' | 'private' | 'per-field' | 'computed' | 'undeclared'

const privacyOf = (tag: string): Privacy => {
	const expression = uploadArgsExpression(tag)
	if (expression === null) return 'undeclared'
	if (!expression.startsWith('{')) return 'computed'
	if (/\b(private|is_private)\s*:\s*(false|0)\b/.test(expression))
		return 'public'
	if (/\b(private|is_private)\s*:\s*(true|1)\b/.test(expression))
		return 'private'
	if (/\b(private|is_private)\s*:/.test(expression)) return 'per-field'
	return 'undeclared'
}

/**
 * Every uploader in the app, in document order, with the privacy it must have.
 *
 * This is an assertion list, not an exemption list: a new uploader makes the
 * count mismatch and fails, rather than slipping through unnoticed. Flipping an
 * existing one fails too. Adding an entry here is the deliberate act of saying
 * who is allowed to read the file.
 */
const MANIFEST: Record<string, Privacy[]> = {
	// Learner- and crawler-facing: these must stay readable without a session.
	'components/Controls/ImageUploader.vue': ['public'],
	'components/Controls/Uploader.vue': ['public'],
	'components/Controls/VideoPreviewField.vue': ['public', 'public'],
	'components/Modals/EditCoverImage.vue': ['public'],
	'components/UnsplashImageBrowser.vue': ['public'],
	'components/Courses/CourseThumbnailField.vue': ['public', 'public'],
	// A caption track is fetched by the video player alongside the lecture, on
	// the same terms as the poster image — it has to be readable without the
	// player holding a session for the File itself.
	'components/Courses/CourseCaptionsSection.vue': ['public'],
	// The certificate's artwork and any signature or seal placed on it. Both are
	// drawn on the public verification page, which a stranger with no account
	// opens from a link on a printed certificate — so a private File here would
	// be readable by its uploader and Administrator alone, and every employer
	// checking a certificate would get a broken image with no error anywhere.
	// Public is what the feature requires, not a default that slipped through:
	// the background is organisation artwork and the seal is meant to be seen by
	// exactly the people the certificate is shown to. Nothing personal to the
	// learner is uploaded here — their name is drawn as text from the frozen
	// snapshot, never as an image.
	'components/Certificates/CertificateDesigner.vue': ['public', 'public'],
	// Deliberately not readable by other users.
	'components/Assignment.vue': ['private', 'private', 'private'],
	'pages/Forms/ChapterForm.vue': ['private'],
	'components/Notes/Notes.vue': ['private'],
	// Lecture video, uploaded from the curriculum editor. Private and attached
	// to its Course Lesson, so access follows the lesson's own permission —
	// the same shape UploadPlugin uses for video dropped into a lesson body,
	// and what keeps paid course content out of reach of a bare URL.
	// Two uploaders. The scanner groups by tag, not document position, so the
	// FileUploader (the lecture video) is listed before the RichTextEditor (the
	// item's description, `undeclared` like every other one).
	'components/Curriculum/CurriculumItemBody.vue': ['private', 'undeclared'],
	// Course materials a learner downloads: worksheets, source bundles. Private
	// and attached to the lesson for the same reason as the video — they are
	// part of the paid content, not public collateral.
	'components/Curriculum/ResourceList.vue': ['private'],
	// Neither literal. `per-field` reads the field's own `public` flag and
	// `computed` is any other expression. `undeclared` passes no uploadArgs at
	// all — for a RichTextEditor that means private, because its uploadFile
	// defaults `private: true`. Safe by exposure, but it is why an image pasted
	// into a lesson body can end up invisible to everyone but its author.
	// Auditing those call sites is separate work, deliberately not done here;
	// the manifest exists so the next person sees the whole list at once rather
	// than discovering it one broken image at a time.
	'components/ContactUsEmail.vue': ['undeclared'],
	'components/DiscussionReplies.vue': ['undeclared', 'undeclared'],
	'components/Modals/DiscussionModal.vue': ['undeclared'],
	'components/Quiz.vue': ['undeclared'],
	'components/Settings/EmailTemplate/EmailTemplateAdd.vue': ['undeclared'],
	'components/Settings/EmailTemplate/EmailTemplateEdit.vue': ['undeclared'],
	'components/Settings/SettingFields.vue': ['per-field'],
	'components/UploadPlugin.vue': ['computed'],
	'pages/Forms/AssignmentForm.vue': ['undeclared'],
	'pages/Forms/AnnouncementForm.vue': ['undeclared'],
	'pages/Batches/BatchForm.vue': ['undeclared'],
	'pages/Forms/EmailTemplateForm.vue': ['undeclared'],
	'pages/Forms/NewBatchForm.vue': ['undeclared'],
	'components/Courses/CourseOverviewSection.vue': ['undeclared'],
	// RichTextEditor bodies across the guided creation and curriculum flows:
	// the course description, the two automated course messages, a quiz
	// question, the assignment's instructions/questions/solution, and the
	// exercise's problem statement and hints. Same standing caveat as the other
	// `undeclared` rows — a pasted image lands private.
	'components/Courses/CourseMessagesSection.vue': ['undeclared', 'undeclared'],
	'components/Curriculum/QuizBuilder.vue': ['undeclared'],
	'pages/Courses/Manage/AssignmentEditor.vue': [
		'undeclared',
		'undeclared',
		'undeclared',
	],
	'pages/Courses/Manage/ExerciseEditor.vue': ['undeclared', 'undeclared'],
	'pages/Forms/NewCourseForm.vue': ['undeclared'],
	'pages/Forms/ProfileEditForm.vue': ['undeclared'],
	'pages/Forms/ProgrammingExerciseForm.vue': ['undeclared'],
	'pages/Forms/QuizQuestionForm.vue': ['undeclared'],
}

describe('every uploader has the privacy the manifest states', () => {
	const SRC = resolve(process.cwd(), 'src')
	const files = vueFilesUnder(SRC)

	const found: Record<string, Privacy[]> = {}
	for (const file of files) {
		const tags = openingTags(readFileSync(file, 'utf8'))
		if (!tags.length) continue
		found[relative(SRC, file).split(/[\\/]/).join('/')] = tags.map(privacyOf)
	}

	it('found uploaders to scan', () => {
		expect(files.length).toBeGreaterThan(100)
		expect(Object.keys(found).length).toBeGreaterThan(5)
	})

	it('captures the whole opening tag, not just up to the first arrow function', () => {
		// A naive /[^>]*>/ stops at the `>` of the first `=>`, which would make
		// the check depend on the order attributes happen to be written in.
		const withArrow = files
			.flatMap((f) => openingTags(readFileSync(f, 'utf8')))
			.filter((tag) => tag.includes('=>'))
		expect(withArrow.length).toBeGreaterThan(0)
		for (const tag of withArrow) {
			expect(tag.trimEnd().slice(-1)).toBe('>')
		}
	})

	it('matches the manifest exactly — no new, moved or flipped uploader', () => {
		expect(found).toEqual(MANIFEST)
	})
})

/**
 * The scanner above only sees markup. An upload driven from script — `new
 * FileUploadHandler().upload(file, opts)` — creates a File exactly the same
 * way but has no tag to match, so it slipped past the manifest entirely. The
 * bulk uploader added one; this closes the gap before there are three.
 *
 * Coarser than the tag scan by necessity: the options object is not adjacent
 * to the constructor, so this asserts that a file constructing a handler
 * declares privacy *somewhere* in that file, and pins which files those are.
 * That is enough to force the decision to be written down and reviewed.
 */
const PROGRAMMATIC_UPLOADERS: Record<string, Privacy> = {
	// Course ZIP awaiting import — never served to anyone, only unpacked.
	'pages/Forms/CourseImportForm.vue': 'private',
	// Bulk-uploaded lecture video. Private for the same reason as every other
	// lecture video: it is paid course content, reachable only through the
	// lesson it gets attached to.
	'components/Curriculum/BulkUploader.vue': 'private',
}

describe('script-driven uploads declare their privacy too', () => {
	const SRC = resolve(process.cwd(), 'src')
	const sources = [
		...vueFilesUnder(SRC),
		...tsFilesUnder(SRC),
	]

	const found: Record<string, Privacy> = {}
	for (const file of sources) {
		const src = readFileSync(file, 'utf8')
		if (!/new\s+FileUploadHandler\s*\(/.test(src)) continue
		const key = relative(SRC, file).split(/[\\/]/).join('/')
		if (/\b(private|is_private)\s*:\s*(false|0)\b/.test(src)) found[key] = 'public'
		else if (/\b(private|is_private)\s*:\s*(true|1)\b/.test(src)) found[key] = 'private'
		else found[key] = 'undeclared'
	}

	it('finds the handlers it is meant to scan', () => {
		expect(Object.keys(found).length).toBeGreaterThan(0)
	})

	it('matches the manifest exactly — no new or flipped script uploader', () => {
		expect(found).toEqual(PROGRAMMATIC_UPLOADERS)
	})

	it('never leaves a script upload undeclared', () => {
		const undeclared = Object.entries(found)
			.filter(([, p]) => p === 'undeclared')
			.map(([f]) => f)
		expect(undeclared, undeclared.join('\n')).toEqual([])
	})
})
