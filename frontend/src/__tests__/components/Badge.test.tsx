import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Badge } from '../../components/ui/badge'

describe('Badge', () => {
  it('renders with default variant', () => {
    render(<Badge>Default</Badge>)
    const badge = screen.getByText('Default')
    expect(badge).toBeTruthy()
    expect(badge.getAttribute('data-slot')).toBe('badge')
    expect(badge.getAttribute('data-variant')).toBe('default')
  })

  it('renders with destructive variant', () => {
    render(<Badge variant="destructive">Error</Badge>)
    const badge = screen.getByText('Error')
    expect(badge.getAttribute('data-variant')).toBe('destructive')
  })

  it('renders with success variant', () => {
    render(<Badge variant="success">OK</Badge>)
    const badge = screen.getByText('OK')
    expect(badge.getAttribute('data-variant')).toBe('success')
  })

  it('renders with warning variant', () => {
    render(<Badge variant="warning">Warn</Badge>)
    const badge = screen.getByText('Warn')
    expect(badge.getAttribute('data-variant')).toBe('warning')
  })

  it('applies custom className', () => {
    render(<Badge className="custom-class">Custom</Badge>)
    const badge = screen.getByText('Custom')
    expect(badge.className).toContain('custom-class')
  })

  it('renders as span by default', () => {
    render(<Badge>Span</Badge>)
    const badge = screen.getByText('Span')
    expect(badge.tagName).toBe('SPAN')
  })
})
