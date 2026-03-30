import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import ScoreRing from '../../components/ScoreRing'

// Mock framer-motion to avoid animation complexities in tests
vi.mock('framer-motion', () => {
  const actual = {
    motion: {
      circle: (props: Record<string, unknown>) => {
        const { style: _, ...rest } = props as { style?: Record<string, unknown>; [key: string]: unknown }
        void _;
        return <circle {...rest} />
      },
    },
    useMotionValue: (initial: number) => ({
      set: () => {},
      get: () => initial,
      on: () => () => {},
    }),
    useTransform: (_mv: unknown, fn: (v: number) => unknown) => {
      const val = typeof fn === 'function' ? fn(0) : 0
      return {
        get: () => val,
        on: (_event: string, cb: (v: unknown) => void) => { cb(val); return () => {} },
      }
    },
    animate: () => ({ stop: () => {} }),
  }
  return actual
})

describe('ScoreRing', () => {
  it('renders with default size', () => {
    const { container } = render(<ScoreRing score={72} animated={false} />)
    const svg = container.querySelector('svg')
    expect(svg).toBeTruthy()
    expect(svg?.getAttribute('width')).toBe('80')
    expect(svg?.getAttribute('height')).toBe('80')
  })

  it('renders with custom size', () => {
    const { container } = render(<ScoreRing score={50} size={120} animated={false} />)
    const svg = container.querySelector('svg')
    expect(svg?.getAttribute('width')).toBe('120')
  })

  it('renders the score number when showLabel is true and animated is false', () => {
    render(<ScoreRing score={72} showLabel={true} animated={false} />)
    expect(screen.getByText('72')).toBeTruthy()
  })

  it('hides label when showLabel is false', () => {
    const { container } = render(<ScoreRing score={72} showLabel={false} animated={false} />)
    // Should have no text content outside svg
    const divs = container.querySelectorAll('.absolute')
    expect(divs.length).toBe(0)
  })

  it('shows displayValue when provided', () => {
    render(<ScoreRing score={72} displayValue="A+" animated={false} />)
    expect(screen.getByText('A+')).toBeTruthy()
  })

  it('applies colorOverride when provided', () => {
    const { container } = render(<ScoreRing score={72} colorOverride="#ff00ff" animated={false} />)
    const track = container.querySelector('.score-ring-track')
    expect(track?.getAttribute('stroke')).toBe('#ff00ff')
  })
})
