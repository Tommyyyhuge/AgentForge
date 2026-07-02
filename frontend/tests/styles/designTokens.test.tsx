import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import Button from '../../src/components/ui/Button'
import Card from '../../src/components/ui/Card'
import { AGENT_STATUS_COLORS } from '../../src/stores/agentStore'
import { STATUS_COLORS, STEP_TYPE_COLORS } from '../../src/stores/taskStore'

describe('design token usage', () => {
  it('maps Task status badges to semantic color tokens', () => {
    expect(STATUS_COLORS).toEqual({
      pending: 'bg-semantic-pending/10 text-semantic-pending border-semantic-pending/20',
      planning: 'bg-semantic-planning/10 text-semantic-planning border-semantic-planning/20',
      executing: 'bg-semantic-executing/10 text-semantic-executing border-semantic-executing/20',
      completed: 'bg-semantic-completed/10 text-semantic-completed border-semantic-completed/20',
      failed: 'bg-semantic-failed/10 text-semantic-failed border-semantic-failed/20',
      cancelled: 'bg-semantic-cancelled/10 text-semantic-cancelled border-semantic-cancelled/20',
    })
  })

  it('maps Agent status badges to semantic color tokens', () => {
    expect(AGENT_STATUS_COLORS).toEqual({
      idle: 'bg-semantic-idle/10 text-semantic-idle border-semantic-idle/20',
      busy: 'bg-semantic-busy/10 text-semantic-busy border-semantic-busy/20',
      error: 'bg-semantic-error/10 text-semantic-error border-semantic-error/20',
    })
  })

  it('maps Step timeline badges to semantic color tokens', () => {
    expect(STEP_TYPE_COLORS).toEqual({
      thought: 'border-semantic-thought/30 bg-semantic-thought/10 text-semantic-thought',
      action: 'border-semantic-action/30 bg-semantic-action/10 text-semantic-action',
      observation: 'border-semantic-observation/30 bg-semantic-observation/10 text-semantic-observation',
      final: 'border-semantic-final/30 bg-semantic-final/10 text-semantic-final',
      error: 'border-semantic-error/30 bg-semantic-error/10 text-semantic-error',
    })
  })

  it('keeps primitive component radii at the documented 8px token', () => {
    render(
      <>
        <Button>Save</Button>
        <Card>Panel</Card>
      </>,
    )

    expect(screen.getByRole('button', { name: 'Save' }).className).toContain('rounded-forge')
    expect(screen.getByText('Panel').className).toContain('rounded-forge')
  })
})
