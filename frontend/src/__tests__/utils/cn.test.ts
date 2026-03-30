import { describe, it, expect } from 'vitest'
import { cn } from '../../lib/utils'

describe('cn', () => {
  it('merges class names', () => {
    expect(cn('foo', 'bar')).toBe('foo bar')
  })

  it('handles conditional classes', () => {
    expect(cn('base', null, 'visible')).toBe('base visible')
  })

  it('resolves tailwind conflicts (last wins)', () => {
    const result = cn('px-4', 'px-2')
    expect(result).toBe('px-2')
  })

  it('handles empty/undefined inputs', () => {
    expect(cn()).toBe('')
    expect(cn(undefined, null, '')).toBe('')
  })

  it('handles arrays', () => {
    expect(cn(['foo', 'bar'])).toBe('foo bar')
  })
})
