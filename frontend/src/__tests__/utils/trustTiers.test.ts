import { describe, it, expect } from 'vitest'
import { getTrustTier, TRUST_TIERS } from '../../utils/trustTiers'

describe('getTrustTier', () => {
  it('returns "Trusted" for scores >= 75', () => {
    expect(getTrustTier(75)).toEqual(TRUST_TIERS[0])
    expect(getTrustTier(100)).toEqual(TRUST_TIERS[0])
    expect(getTrustTier(75).label).toBe('Trusted')
  })

  it('returns "Emerging" for scores 55-74', () => {
    expect(getTrustTier(55)).toEqual(TRUST_TIERS[1])
    expect(getTrustTier(74)).toEqual(TRUST_TIERS[1])
    expect(getTrustTier(60).label).toBe('Emerging')
  })

  it('returns "Use Caution" for scores 40-54', () => {
    expect(getTrustTier(40)).toEqual(TRUST_TIERS[2])
    expect(getTrustTier(54)).toEqual(TRUST_TIERS[2])
    expect(getTrustTier(45).label).toBe('Use Caution')
  })

  it('returns "Avoid" for scores < 40', () => {
    expect(getTrustTier(0)).toEqual(TRUST_TIERS[3])
    expect(getTrustTier(39)).toEqual(TRUST_TIERS[3])
    expect(getTrustTier(10).label).toBe('Avoid')
  })

  it('returns correct colors', () => {
    expect(getTrustTier(80).color).toBe('#16a34a')
    expect(getTrustTier(60).color).toBe('#2563eb')
    expect(getTrustTier(45).color).toBe('#ca8a04')
    expect(getTrustTier(20).color).toBe('#dc2626')
  })
})
