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
    apiBaseUrl: `http://127.0.0.1:${configuredPorts.core_port}`,
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
    expect(screen.getByText('记忆数据')).toBeDefined()
    expect(screen.getByRole('dialog', { name: '记忆数据' })).toHaveAttribute('aria-modal', 'true')
    await waitFor(() => expect(global.fetch).toHaveBeenCalled())
  })

  it('does not render when closed', () => {
    const { container } = render(<DataViewer {...defaultProps} isOpen={false} />)
    expect(container.firstChild).toBeNull()
  })

  it('calls onClose when close button is clicked', async () => {
    render(<DataViewer {...defaultProps} />)
    await waitFor(() => expect(global.fetch).toHaveBeenCalled())
    fireEvent.click(screen.getByRole('button', { name: '关闭记忆数据' }))
    expect(defaultProps.onClose).toHaveBeenCalled()
  })

  it('closes with Escape', async () => {
    render(<DataViewer {...defaultProps} />)
    await waitFor(() => expect(global.fetch).toHaveBeenCalled())
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(defaultProps.onClose).toHaveBeenCalled()
  })
})
