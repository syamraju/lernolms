import { beforeEach, describe, expect, it, vi } from 'vitest'
import {
	resolveDwellSeconds,
	isVideoComplete,
	shouldStartDwellTimer,
	shouldAttachVideoFallback,
	completionBlockerMessage,
	quizRequirementSentence,
} from '@/utils/lessonProgress'
import { installTranslate, translate } from './translateStub'

describe('resolveDwellSeconds', () => {
	it('returns the parsed number for a positive integer', () => {
		expect(resolveDwellSeconds(30)).toBe(30)
		expect(resolveDwellSeconds(45)).toBe(45)
	})

	it('coerces numeric strings (Frappe Check fields can come back as strings)', () => {
		expect(resolveDwellSeconds('30')).toBe(30)
		expect(resolveDwellSeconds('45.5')).toBe(45.5)
	})

	it('returns the fallback default when value is null or undefined', () => {
		expect(resolveDwellSeconds(null)).toBe(30)
		expect(resolveDwellSeconds(undefined)).toBe(30)
	})

	it('honors a custom fallback', () => {
		expect(resolveDwellSeconds(null, 60)).toBe(60)
		expect(resolveDwellSeconds(undefined, 60)).toBe(60)
	})

	it('returns null when value is 0 or negative (dwell disabled)', () => {
		expect(resolveDwellSeconds(0)).toBeNull()
		expect(resolveDwellSeconds(-5)).toBeNull()
		expect(resolveDwellSeconds('0')).toBeNull()
	})

	it('returns null when value is non-numeric', () => {
		expect(resolveDwellSeconds('abc')).toBeNull()
		expect(resolveDwellSeconds(NaN)).toBeNull()
	})
})

describe('isVideoComplete', () => {
	it('returns true when currentTime is within 1 second of duration', () => {
		expect(isVideoComplete(99, 100)).toBe(true)
		expect(isVideoComplete(99.5, 100)).toBe(true)
		expect(isVideoComplete(100, 100)).toBe(true)
	})

	it('returns false when currentTime is more than 1s short', () => {
		expect(isVideoComplete(98, 100)).toBe(false)
		expect(isVideoComplete(0, 100)).toBe(false)
	})

	it('returns false when duration is 0 (video not loaded; avoids false-positive on init)', () => {
		expect(isVideoComplete(0, 0)).toBe(false)
		expect(isVideoComplete(100, 0)).toBe(false)
	})

	it('returns false when duration is negative or NaN', () => {
		expect(isVideoComplete(50, -10)).toBe(false)
		expect(isVideoComplete(NaN, 100)).toBe(false)
		expect(isVideoComplete(50, NaN)).toBe(false)
	})

	it('handles YouTube last-frame skip', () => {
		expect(isVideoComplete(299.04, 300)).toBe(true)
	})
})

describe('shouldStartDwellTimer', () => {
	it('starts when there is no video', () => {
		expect(
			shouldStartDwellTimer({ hasVideo: false, enforceVideo: false })
		).toBe(true)
		expect(shouldStartDwellTimer({ hasVideo: false, enforceVideo: true })).toBe(
			true
		)
		expect(shouldStartDwellTimer({ hasVideo: false, enforceVideo: 1 })).toBe(
			true
		)
	})

	it('starts when there is video but enforcement is off (legacy 30s behavior)', () => {
		expect(shouldStartDwellTimer({ hasVideo: true, enforceVideo: false })).toBe(
			true
		)
		expect(shouldStartDwellTimer({ hasVideo: true, enforceVideo: 0 })).toBe(
			true
		)
	})

	it('does NOT start when video is present and enforcement is on', () => {
		expect(shouldStartDwellTimer({ hasVideo: true, enforceVideo: true })).toBe(
			false
		)
		expect(shouldStartDwellTimer({ hasVideo: true, enforceVideo: 1 })).toBe(
			false
		)
	})
})

describe('shouldAttachVideoFallback', () => {
	it('does not attach without a video', () => {
		expect(
			shouldAttachVideoFallback({ hasVideo: false, enforceVideo: false })
		).toBe(false)
		expect(
			shouldAttachVideoFallback({ hasVideo: false, enforceVideo: true })
		).toBe(false)
	})

	it('does not attach when enforcement is off (no recovery needed)', () => {
		expect(
			shouldAttachVideoFallback({ hasVideo: true, enforceVideo: false })
		).toBe(false)
		expect(shouldAttachVideoFallback({ hasVideo: true, enforceVideo: 0 })).toBe(
			false
		)
	})

	it('attaches only when both flags are true', () => {
		expect(
			shouldAttachVideoFallback({ hasVideo: true, enforceVideo: true })
		).toBe(true)
		expect(shouldAttachVideoFallback({ hasVideo: true, enforceVideo: 1 })).toBe(
			true
		)
	})
})

// The message goes through the app's translation global, which only exists at
// runtime. The faithful stub rather than identity: the specific wording formats
// a placeholder, and identity would fail on a difference the app does not have.
vi.stubGlobal('__', translate)

describe('completionBlockerMessage', () => {
	beforeEach(installTranslate)
	// save_progress records nothing while a lesson's quiz is unpassed or its
	// assignment unsubmitted, but it returns the course percentage either way —
	// so the page used to toast "Marked as complete" over a write that never
	// happened. get_lesson now ships the reason and this turns it into a
	// sentence; '' doubles as the "nothing outstanding" signal.
	it('is empty when nothing is outstanding', () => {
		expect(completionBlockerMessage([])).toBe('')
		expect(completionBlockerMessage(undefined)).toBe('')
		expect(completionBlockerMessage(null)).toBe('')
	})

	it('names the quiz on its own', () => {
		expect(completionBlockerMessage(['quiz'])).toBe(
			'Pass the quiz to complete this session.'
		)
	})

	it('names the assignment on its own', () => {
		expect(completionBlockerMessage(['assignment'])).toBe(
			'Submit the assignment to complete this session.'
		)
	})

	it('names both when both are outstanding, in one sentence', () => {
		expect(completionBlockerMessage(['quiz', 'assignment'])).toBe(
			'Pass the quiz and submit the assignment to complete this session.'
		)
		// Order comes from the server; the sentence must not depend on it.
		expect(completionBlockerMessage(['assignment', 'quiz'])).toBe(
			'Pass the quiz and submit the assignment to complete this session.'
		)
	})

	it('ignores a blocker key it does not know', () => {
		expect(completionBlockerMessage(['scorm'])).toBe('')
	})

	// The pass mark is what makes a section-ending quiz a gate. A student told
	// only to "pass the quiz" cannot tell whether their 55% was close or hopeless.
	it('names the pass mark when the server sends the requirement', () => {
		expect(
			completionBlockerMessage(['quiz'], [
				{ passing_percentage: 60, best_percentage: null, attempts: 0 },
			])
		).toBe('Score at least 60% on the quiz to complete this session.')
	})

	it('names the best score once the student has attempted it', () => {
		expect(
			completionBlockerMessage(['quiz'], [
				{ passing_percentage: 60, best_percentage: 40, attempts: 2 },
			])
		).toBe('Your best score is 40%. You need 60% to complete this session.')
	})

	it('keeps the specific wording when the assignment is outstanding too', () => {
		expect(
			completionBlockerMessage(['quiz', 'assignment'], [
				{ passing_percentage: 60, best_percentage: 40, attempts: 1 },
			])
		).toBe(
			'Your best score is 40%. You need 60% to complete this session. You also need to submit the assignment.'
		)
	})

	// An older backend sends no detail, and the generic sentences still have to
	// be what the student reads.
	it('falls back to the generic wording with no requirement detail', () => {
		expect(completionBlockerMessage(['quiz'], [])).toBe(
			'Pass the quiz to complete this session.'
		)
		expect(completionBlockerMessage(['quiz', 'assignment'], null)).toBe(
			'Pass the quiz and submit the assignment to complete this session.'
		)
	})
})

describe('quizRequirementSentence', () => {
	beforeEach(installTranslate)

	it('is empty with nothing to be specific about', () => {
		expect(quizRequirementSentence(undefined)).toBe('')
		expect(quizRequirementSentence([])).toBe('')
	})

	// A pass mark of 0 is an author saying "attempt it", not "score on it", so
	// quoting a bar of 0% would misdescribe what the quiz asks.
	it('asks only for a submission when the pass mark is zero', () => {
		expect(
			quizRequirementSentence([
				{ passing_percentage: 0, best_percentage: null, attempts: 0 },
			])
		).toBe('Submit the quiz to complete this session.')
	})

	// A learner who scored 0 has attempted it; best_percentage 0 must not read
	// as "no attempt yet".
	it('reports a zero score as a score, not as an untried quiz', () => {
		expect(
			quizRequirementSentence([
				{ passing_percentage: 50, best_percentage: 0, attempts: 1 },
			])
		).toBe('Your best score is 0%. You need 50% to complete this session.')
	})
})
