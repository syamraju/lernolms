import { beforeEach, describe, expect, it } from 'vitest'
import { PACING_TONE_CLASS, pacingChip } from '@/utils/pacing'
import { installTranslate } from './translateStub'

describe('pacingChip', () => {
	beforeEach(installTranslate)

	// A due date only means something against work in progress. Saying nothing is
	// the honest output for a course with no deadline, one already finished, or
	// one the student is only browsing.
	it('says nothing without a deadline', () => {
		expect(pacingChip(null)).toBeNull()
		expect(pacingChip(undefined)).toBeNull()
		expect(pacingChip({ due_date: null, status: 'No deadline' })).toBeNull()
	})

	it('says nothing once the course is complete', () => {
		expect(
			pacingChip({
				due_date: '2026-01-01',
				days_left: -200,
				is_overdue: false,
				status: 'Completed',
			}),
		).toBeNull()
	})

	it('counts the days remaining', () => {
		expect(
			pacingChip({
				due_date: '2026-09-01',
				days_left: 11,
				is_overdue: false,
				status: 'On track',
			}),
		).toEqual({ text: '11 days left', tone: 'neutral' })
	})

	// "Due soon" is the server's judgement of when the date starts mattering, so
	// the chip takes the tone from it rather than re-deriving a threshold that
	// could drift out of step.
	it('warns on the days the server calls due soon', () => {
		expect(
			pacingChip({
				due_date: '2026-08-24',
				days_left: 3,
				is_overdue: false,
				status: 'Due soon',
			}),
		).toEqual({ text: '3 days left', tone: 'warning' })
	})

	it('names today and tomorrow rather than counting them', () => {
		expect(
			pacingChip({
				due_date: '2026-08-21',
				days_left: 0,
				is_overdue: false,
				status: 'Due soon',
			}),
		).toEqual({ text: 'Due today', tone: 'warning' })
		expect(
			pacingChip({
				due_date: '2026-08-22',
				days_left: 1,
				is_overdue: false,
				status: 'Due soon',
			}),
		).toEqual({ text: 'Due tomorrow', tone: 'warning' })
	})

	it('reports how far past the date an overdue course is', () => {
		expect(
			pacingChip({
				due_date: '2026-08-11',
				days_left: -10,
				is_overdue: true,
				status: 'Overdue',
			}),
		).toEqual({ text: 'Overdue by 10 day(s)', tone: 'overdue' })
	})

	// The server may report the overdue flag without a usable day count; the chip
	// still has to say the thing that matters.
	it('still says overdue without a day count', () => {
		expect(
			pacingChip({ due_date: '2026-08-11', is_overdue: true, status: 'Overdue' }),
		).toEqual({ text: 'Overdue', tone: 'overdue' })
	})

	it('has a class for every tone it can return', () => {
		for (const tone of ['overdue', 'warning', 'neutral'] as const) {
			expect(PACING_TONE_CLASS[tone]).toBeTruthy()
		}
	})
})
