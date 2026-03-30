import { describe, it, expect } from 'vitest'
import { getCategoryCount, CATEGORIES } from '../../utils/categories'
import type { NeighborhoodScoreResponse } from '../../types'

function makeData(details: { category: string }[]): NeighborhoodScoreResponse {
  const emptyDim = { score: 0, label: '', details: [] as { category: string; label: string; value: string }[] }
  return {
    walkability: { ...emptyDim, details: [] },
    safety: { ...emptyDim, details: [] },
    hospital_access: { ...emptyDim, details: [] },
    school_access: { ...emptyDim, details: [] },
    transit_access: { ...emptyDim, details: details.map(d => ({ ...d, label: '', value: '' })) },
    air_quality: { ...emptyDim, details: [] },
    future_infrastructure: { ...emptyDim, details: [] },
    commute: { ...emptyDim, details: [] },
    flood_risk: { ...emptyDim, details: [] },
  } as unknown as NeighborhoodScoreResponse
}

describe('getCategoryCount', () => {
  it('returns 0 for unknown category id', () => {
    const data = makeData([])
    expect(getCategoryCount('nonexistent', data)).toBe(0)
  })

  it('returns 0 when no matching details exist', () => {
    const data = makeData([{ category: 'something_else' }])
    expect(getCategoryCount('metro', data)).toBe(0)
  })

  it('counts matching details for metro category', () => {
    const data = makeData([
      { category: 'metro_station_1' },
      { category: 'metro_line_2' },
      { category: 'bus_stop_3' },
    ])
    expect(getCategoryCount('metro', data)).toBe(2)
  })

  it('counts exact matches for bus category', () => {
    const data = makeData([
      { category: 'bus_stop' },
      { category: 'bus_stop_nearby' },
    ])
    expect(getCategoryCount('bus', data)).toBe(2)
  })

  it('CATEGORIES has expected ids', () => {
    const ids = CATEGORIES.map(c => c.id)
    expect(ids).toContain('metro')
    expect(ids).toContain('school')
    expect(ids).toContain('flood')
  })
})
