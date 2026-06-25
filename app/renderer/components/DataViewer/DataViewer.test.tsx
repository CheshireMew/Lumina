import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import React from 'react'
import DataViewer from './DataViewer'
import configuredPorts from '../../../../config/ports.json'

// Mock fetch
global.fetch = vi.fn()

describe('DataViewer Component', () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    activeCharacterId: 'hiyori',
    apiBaseUrl: `http://127.0.0.1:${configuredPorts.memory_port}`,
  }

  beforeEach(() => {
    vi.clearAllMocks()
    ;(global.fetch as any).mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify({ tables: [] }),
    })
  })

  it('renders correctly when open', async () => {
    render(<DataViewer {...defaultProps} />)
    expect(screen.getByText('Memory Architecture')).toBeDefined()
    await waitFor(() => expect(global.fetch).toHaveBeenCalled())
  })

  it('does not render when closed', () => {
    const { container } = render(<DataViewer {...defaultProps} isOpen={false} />)
    expect(container.firstChild).toBeNull()
  })

  it('calls onClose when close button is clicked', async () => {
    render(<DataViewer {...defaultProps} />)
    await waitFor(() => expect(global.fetch).toHaveBeenCalled())
    // The close button has the X icon, but we can find it by its parent or the X
    // In our case, the button doesn't have an aria-label, so we might need to find it differently.
    // Let's use the X icon's container or just look for the button.
    const closeButtons = screen.getAllByRole('button')
    // The X button is the first one in header
    fireEvent.click(closeButtons[0])
    expect(defaultProps.onClose).toHaveBeenCalled()
  })
})
