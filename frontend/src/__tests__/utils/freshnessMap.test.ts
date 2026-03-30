import { describe, it, expect, vi, afterEach } from 'vitest'
import { getFreshnessForDimension, type FreshnessData } from '../../utils/freshnessMap'

describe('getFreshnessForDimension', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('returns null for unknown dimension', () => {
    expect(getFreshnessForDimension('unknown', {})).toBeNull()
  })

  it('returns null when no freshness data for the tables', () => {
    expect(getFreshnessForDimension('walkability', {})).toBeNull()
  })

  it('returns null when table info has no dates', () => {
    const data: FreshnessData = {
      walkability_zones: {
        source: null,
        last_seeded: null,
        last_refreshed: null,
        record_count: null,
        status: null,
      },
    }
    expect(getFreshnessForDimension('walkability', data)).toBeNull()
  })

  it('returns "Updated today" for same-day data', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-03-30T12:00:00Z'))
    const data: FreshnessData = {
      walkability_zones: {
        source: 'test',
        last_seeded: null,
        last_refreshed: '2026-03-30T06:00:00Z',
        record_count: 10,
        status: 'ok',
      },
    }
    expect(getFreshnessForDimension('walkability', data)).toBe('Updated today')
  })

  it('returns "Updated yesterday" for 1-day-old data', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-03-30T12:00:00Z'))
    const data: FreshnessData = {
      walkability_zones: {
        source: 'test',
        last_seeded: '2026-03-29T06:00:00Z',
        last_refreshed: null,
        record_count: 10,
        status: 'ok',
      },
    }
    expect(getFreshnessForDimension('walkability', data)).toBe('Updated yesterday')
  })

  it('returns days ago for 2-6 day old data', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-03-30T12:00:00Z'))
    const data: FreshnessData = {
      walkability_zones: {
        source: 'test',
        last_seeded: null,
        last_refreshed: '2026-03-27T06:00:00Z',
        record_count: 10,
        status: 'ok',
      },
    }
    expect(getFreshnessForDimension('walkability', data)).toBe('Updated 3d ago')
  })

  it('returns weeks ago for 7-29 day old data', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-03-30T12:00:00Z'))
    const data: FreshnessData = {
      walkability_zones: {
        source: 'test',
        last_seeded: null,
        last_refreshed: '2026-03-16T06:00:00Z',
        record_count: 10,
        status: 'ok',
      },
    }
    expect(getFreshnessForDimension('walkability', data)).toBe('Updated 2w ago')
  })

  it('returns month/year for 30+ day old data', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-03-30T12:00:00Z'))
    const data: FreshnessData = {
      walkability_zones: {
        source: 'test',
        last_seeded: null,
        last_refreshed: '2026-01-15T06:00:00Z',
        record_count: 10,
        status: 'ok',
      },
    }
    const result = getFreshnessForDimension('walkability', data)
    expect(result).toMatch(/Updated Jan 2026/)
  })

  it('picks the most recent date across multiple tables', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-03-30T12:00:00Z'))
    const data: FreshnessData = {
      metro_stations: {
        source: 'test',
        last_seeded: '2026-03-20T00:00:00Z',
        last_refreshed: null,
        record_count: 5,
        status: 'ok',
      },
      bus_stops: {
        source: 'test',
        last_seeded: null,
        last_refreshed: '2026-03-29T00:00:00Z',
        record_count: 20,
        status: 'ok',
      },
      train_stations: {
        source: 'test',
        last_seeded: '2026-03-25T00:00:00Z',
        last_refreshed: null,
        record_count: 3,
        status: 'ok',
      },
    }
    expect(getFreshnessForDimension('transit_access', data)).toBe('Updated yesterday')
  })
})
