import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { EnterpriseEmptyState } from '../components/enterprise/EnterpriseEmptyState';

describe('EnterpriseEmptyState', () => {
  const defaultProps = {
    completedSteps: new Set<number>(),
    onStepAction: vi.fn(),
  };

  // AC1: Heading
  it('renders the setup heading', () => {
    render(<EnterpriseEmptyState {...defaultProps} />);
    expect(
      screen.getByText(
        /Set up your organization's career transition program/i
      )
    ).toBeInTheDocument();
  });

  // AC2: Four setup steps with titles and descriptions
  it('renders all four setup steps with titles', () => {
    render(<EnterpriseEmptyState {...defaultProps} />);
    expect(screen.getByText('Upload company logo')).toBeInTheDocument();
    expect(screen.getByText('Customize welcome message')).toBeInTheDocument();
    expect(screen.getByText('Set autonomy defaults')).toBeInTheDocument();
    expect(screen.getByText('Upload employee list')).toBeInTheDocument();
  });

  it('renders descriptions for each step', () => {
    render(<EnterpriseEmptyState {...defaultProps} />);
    expect(
      screen.getByText(/Add your organization's logo/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Write a supportive message/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Choose how much automation/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Import your employees/i)
    ).toBeInTheDocument();
  });

  // AC3: Progress tracker - 0%
  it('shows "0 of 4 steps complete — 0%" when no steps done', () => {
    render(<EnterpriseEmptyState {...defaultProps} />);
    expect(
      screen.getByText(/0 of 4 steps complete/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/0%/)).toBeInTheDocument();
  });

  // AC3: Progress tracker - 50%
  it('shows "2 of 4 steps complete — 50%" when two steps done', () => {
    render(
      <EnterpriseEmptyState
        completedSteps={new Set([1, 2])}
        onStepAction={vi.fn()}
      />
    );
    expect(
      screen.getByText(/2 of 4 steps complete/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/50%/)).toBeInTheDocument();
  });

  // AC6: Returns null when all steps complete
  it('returns null when all steps complete', () => {
    const { container } = render(
      <EnterpriseEmptyState
        completedSteps={new Set([1, 2, 3, 4])}
        onStepAction={vi.fn()}
      />
    );
    expect(container.firstChild).toBeNull();
  });

  // AC4: Completed step shows checkmark styling
  it('shows completed styling for finished steps', () => {
    render(
      <EnterpriseEmptyState
        completedSteps={new Set([1])}
        onStepAction={vi.fn()}
      />
    );
    // Step 1 should have green background (completed)
    const listItems = screen.getAllByRole('listitem');
    expect(listItems[0].className).toMatch(/green/);
    // Step 2 should not have green background
    expect(listItems[1].className).not.toMatch(/green/);
  });

  // AC4: Step action button calls callback
  it('calls onStepAction with correct step number when button clicked', () => {
    const handler = vi.fn();
    render(
      <EnterpriseEmptyState
        completedSteps={new Set<number>()}
        onStepAction={handler}
      />
    );
    // Click the first step's action button
    const btn = screen.getByRole('button', { name: /Upload company logo/i });
    fireEvent.click(btn);
    expect(handler).toHaveBeenCalledWith(1);
  });

  it('calls onStepAction with step 3 when third step button clicked', () => {
    const handler = vi.fn();
    render(
      <EnterpriseEmptyState
        completedSteps={new Set<number>()}
        onStepAction={handler}
      />
    );
    const btn = screen.getByRole('button', { name: /Set autonomy defaults/i });
    fireEvent.click(btn);
    expect(handler).toHaveBeenCalledWith(3);
  });

  // AC5: Help link
  it('renders help link with correct text', () => {
    render(<EnterpriseEmptyState {...defaultProps} />);
    const link = screen.getByText(/Need help getting started\?/i);
    expect(link).toBeInTheDocument();
    expect(link.closest('a')).toHaveAttribute('href', '#');
  });

  it('renders help link with custom URL', () => {
    render(
      <EnterpriseEmptyState
        completedSteps={new Set<number>()}
        onStepAction={vi.fn()}
        helpUrl="https://help.example.com"
      />
    );
    const link = screen.getByText(/Need help getting started\?/i);
    expect(link.closest('a')).toHaveAttribute(
      'href',
      'https://help.example.com'
    );
  });

  // AC7: Accessibility - aria-label on buttons
  it('has aria-label on action buttons', () => {
    render(<EnterpriseEmptyState {...defaultProps} />);
    expect(
      screen.getByLabelText(/Upload company logo/i)
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText(/Customize welcome message/i)
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText(/Set autonomy defaults/i)
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText(/Upload employee list/i)
    ).toBeInTheDocument();
  });

  // AC7: Accessibility - progress bar aria attributes
  it('has aria-valuenow, aria-valuemin, aria-valuemax on progress bar', () => {
    render(<EnterpriseEmptyState {...defaultProps} />);
    const progressBar = screen.getByRole('progressbar');
    expect(progressBar).toHaveAttribute('aria-valuenow', '0');
    expect(progressBar).toHaveAttribute('aria-valuemin', '0');
    expect(progressBar).toHaveAttribute('aria-valuemax', '100');
  });

  it('progress bar aria-valuenow updates with completion', () => {
    render(
      <EnterpriseEmptyState
        completedSteps={new Set([1, 3])}
        onStepAction={vi.fn()}
      />
    );
    const progressBar = screen.getByRole('progressbar');
    expect(progressBar).toHaveAttribute('aria-valuenow', '50');
  });

  // AC7: Accessibility - aria-current on active step
  it('sets aria-current="step" on the first incomplete step', () => {
    render(
      <EnterpriseEmptyState
        completedSteps={new Set([1])}
        onStepAction={vi.fn()}
      />
    );
    const listItems = screen.getAllByRole('listitem');
    // Step 1 is complete, no aria-current
    expect(listItems[0]).not.toHaveAttribute('aria-current');
    // Step 2 is first incomplete, should have aria-current
    expect(listItems[1]).toHaveAttribute('aria-current', 'step');
    // Step 3 is incomplete but not first
    expect(listItems[2]).not.toHaveAttribute('aria-current');
  });

  // Completed steps don't show action button
  it('does not show action button for completed steps', () => {
    render(
      <EnterpriseEmptyState
        completedSteps={new Set([1])}
        onStepAction={vi.fn()}
      />
    );
    // Should not find a button for step 1
    expect(
      screen.queryByRole('button', { name: /Upload company logo/i })
    ).not.toBeInTheDocument();
    // Should still find button for step 2
    expect(
      screen.getByRole('button', { name: /Customize welcome message/i })
    ).toBeInTheDocument();
  });
});
