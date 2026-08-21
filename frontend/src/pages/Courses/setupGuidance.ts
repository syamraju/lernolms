/**
 * Advisory copy for the course setup checklist.
 *
 * These blocks used to be whole steps in the standalone creation wizard
 * (`/courses/:name/manage/:step`). The wizard duplicated the editing surfaces
 * the course tabs already own, so it was collapsed into a read-only checklist
 * — but the guidance was the one thing it had that nothing else did. It lives
 * here, apart from the panel, so the panel stays about state and this stays
 * about prose.
 *
 * Exported as functions rather than constants: `__()` reads the translation
 * dictionary at call time, and a module-level constant would be frozen at
 * import, before the user's language is known.
 */

export interface GuidanceItem {
	title?: string
	body: string
}

export interface GuidanceBlock {
	title: string
	items: GuidanceItem[]
	variant?: 'definitions' | 'bullets'
}

export function intendedLearnersGuidance(): GuidanceBlock[] {
	return [
		{
			title: __('Writing for the right learner'),
			items: [
				{
					title: __('Lead with outcomes, not topics.'),
					body: __(
						'"Estimate project timelines and budgets" tells a learner what they will be able to do; "Project estimation" only tells them what you will talk about.'
					),
				},
				{
					title: __('State the prerequisites plainly.'),
					body: __(
						'Naming the tools and prior knowledge needed stops learners committing to a course they cannot finish. If there are none, say so — it lowers the barrier for beginners.'
					),
				},
				{
					title: __('Describe the person, not the demographic.'),
					body: __(
						'"Beginner photographers curious about landscape work" is easier to recognise yourself in than "photography enthusiasts".'
					),
				},
			],
		},
	]
}

export function structureGuidance(): GuidanceBlock[] {
	return [
		{
			title: __('Here are our best practices'),
			items: [
				{
					title: __('Start with your goals.'),
					body: __(
						'Setting goals for what learners will accomplish in your course helps you determine what content to include and how you will teach it.'
					),
				},
				{
					title: __('Create an outline.'),
					body: __(
						'Decide what skills you will teach and how you will teach them. Group related lectures into sections, and give each section at least three lectures with a single clear learning objective.'
					),
				},
				{
					title: __('Introduce yourself and create momentum.'),
					body: __(
						'People online want to start learning quickly. Structure the first section so it builds excitement and gets learners moving.'
					),
				},
				{
					title: __('Sections have a clear learning objective.'),
					body: __(
						'Introduce each section with a short description of the outcome, and summarise what was covered at the end.'
					),
				},
				{
					title: __('Lectures cover one concept.'),
					body: __(
						'A focused lecture of two to seven minutes gives learners something to complete in a single sitting.'
					),
				},
				{
					title: __('Mix and match your lecture types.'),
					body: __(
						'Alternate between filming yourself, your screen, and slides or other visuals. Showing yourself helps learners feel connected.'
					),
				},
				{
					title: __('Practice activities create hands-on learning.'),
					body: __(
						'Help learners apply your lessons to their own work with projects, assignments, coding exercises or worksheets.'
					),
				},
			],
		},
		{
			title: __('Requirements'),
			variant: 'bullets',
			items: [
				{ body: __('Your course must have at least 5 lectures') },
				{
					body: __(
						'All lectures must add up to at least 30+ minutes of total video'
					),
				},
				{
					body: __(
						'Your course is composed of valuable educational content and free of promotional or distracting material'
					),
				},
			],
		},
	]
}

export function filmEditGuidance(): GuidanceBlock[] {
	return [
		{
			title: __('Film with confidence'),
			items: [
				{
					title: __('Use natural or soft light.'),
					body: __(
						'Face a window or place two soft lights at 45 degrees to your left and right. Avoid overhead lighting, which casts shadows under the eyes.'
					),
				},
				{
					title: __('Get the microphone close.'),
					body: __(
						'Audio quality matters more to learners than video quality. A lapel or USB microphone within an arm’s length of you beats a camera’s built-in mic every time.'
					),
				},
				{
					title: __('Film in a quiet, soft room.'),
					body: __(
						'Carpets, curtains and bookshelves absorb echo. Turn off fans and air conditioning while recording.'
					),
				},
				{
					title: __('Talk to one person.'),
					body: __(
						'Address the camera as though a single learner were in the room. It reads as warmer than presenting to an audience.'
					),
				},
			],
		},
		{
			title: __('Technical requirements'),
			variant: 'bullets',
			items: [
				{
					body: __(
						'Film and export in HD — 1080p at 16:9 is the safe default'
					),
				},
				{ body: __('Export video as MP4 with H.264 encoding') },
				{ body: __('Record audio at 44.1 kHz or higher, in stereo') },
				{ body: __('Keep audio free of background hum, clipping and echo') },
			],
		},
		{
			title: __('Editing your lectures'),
			items: [
				{
					title: __('Cut the dead air.'),
					body: __(
						'Trim long pauses, false starts and setup time. Learners feel every wasted second.'
					),
				},
				{
					title: __('Show, then tell.'),
					body: __(
						'Cut to your screen, slides or the object you are describing while you talk about it.'
					),
				},
				{
					title: __('Keep lectures short.'),
					body: __(
						'Two to seven minutes per lecture is the sweet spot. Split anything longer at a natural boundary.'
					),
				},
			],
		},
	]
}

export function accessibilityGuidance(): GuidanceBlock[] {
	return [
		{
			title: __('While you film and edit'),
			variant: 'bullets',
			items: [
				{
					body: __(
						'Describe out loud anything you show on screen, so learners who cannot see it still follow along'
					),
				},
				{
					body: __(
						'Keep on-screen text large, high contrast and on screen long enough to read'
					),
				},
				{ body: __('Avoid conveying meaning through colour alone') },
				{
					body: __(
						'Speak clearly and at a steady pace, and avoid heavy background music'
					),
				},
			],
		},
	]
}

export function promotionsGuidance(): GuidanceBlock[] {
	return [
		{
			title: __('Getting the most from a promotion'),
			items: [
				{
					title: __('Announce the end date.'),
					body: __(
						'A deadline is what turns interest into an enrolment. Say when the offer closes wherever you share the code.'
					),
				},
				{
					title: __('Keep the code short and readable.'),
					body: __(
						'Codes get typed by hand and read aloud in videos. Avoid characters that look alike.'
					),
				},
				{
					title: __('One code per channel.'),
					body: __(
						'Separate codes for your newsletter, social posts and partners tell you which channel actually converts.'
					),
				},
			],
		},
	]
}
