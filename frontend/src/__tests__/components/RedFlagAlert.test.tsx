import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import RedFlagAlert from '../../components/RedFlagAlert'
import type { RiskFlag } from '../../types'

describe('RedFlagAlert', () => {
  it('renders critical flag with title and detail', () => {
    const flag: RiskFlag = {
      severity: 'critical',
      title: 'Flood Zone',
      detail: 'This area is prone to flooding.',
    }
    render(<RedFlagAlert flag={flag} />)
    expect(screen.getByText('Flood Zone')).toBeTruthy()
    expect(screen.getByText('This area is prone to flooding.')).toBeTruthy()
  })

  it('renders warning flag', () => {
    const flag: RiskFlag = {
      severity: 'warning',
      title: 'High AQI',
      detail: 'Air quality index exceeds safe levels.',
    }
    const { container } = render(<RedFlagAlert flag={flag} />)
    expect(screen.getByText('High AQI')).toBeTruthy()
    // Check for warning border class
    const wrapper = container.firstElementChild
    expect(wrapper?.className).toContain('border-amber-500')
  })

  it('renders info flag', () => {
    const flag: RiskFlag = {
      severity: 'info',
      title: 'New Metro Planned',
      detail: 'A new metro line is under construction.',
    }
    const { container } = render(<RedFlagAlert flag={flag} />)
    expect(screen.getByText('New Metro Planned')).toBeTruthy()
    const wrapper = container.firstElementChild
    expect(wrapper?.className).toContain('border-blue-500')
  })

  it('falls back to info config for unknown severity', () => {
    const flag = {
      severity: 'unknown' as 'info',
      title: 'Test',
      detail: 'Detail',
    }
    const { container } = render(<RedFlagAlert flag={flag} />)
    const wrapper = container.firstElementChild
    expect(wrapper?.className).toContain('border-blue-500')
  })
})
