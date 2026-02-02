import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { NetworkEmptyState } from '../components/network/NetworkEmptyState';

describe('NetworkEmptyState', () => {
  // AC1: Empty message
  it('renders "Build your professional network strategically" heading', () => {
    render(<NetworkEmptyState />);
    expect(
      screen.getByText(/Build your professional network strategically/i)
    ).toBeInTheDocument();
  });

  // AC2: Warm introductions explanation
  it('displays warm introductions explanation', () => {
    render(<NetworkEmptyState />);
    expect(
      screen.getByText(/Warm introductions are the most effective way/i)
    ).toBeInTheDocument();
  });

  it('explains warm path discovery', () => {
    render(<NetworkEmptyState />);
    expect(
      screen.getByText(/Discover warm paths to target companies/i)
    ).toBeInTheDocument();
  });

  it('explains AI-crafted messages', () => {
    render(<NetworkEmptyState />);
    expect(
      screen.getByText(/AI-crafted introduction messages/i)
    ).toBeInTheDocument();
  });

  it('explains relationship tracking', () => {
    render(<NetworkEmptyState />);
    expect(
      screen.getByText(/Track relationship warmth/i)
    ).toBeInTheDocument();
  });

  // AC3: LinkedIn CTA
  it('renders "Import your LinkedIn connections" CTA', () => {
    render(<NetworkEmptyState />);
    const btn = screen.getByRole('button', {
      name: /Import your LinkedIn connections/i,
    });
    expect(btn).toBeInTheDocument();
  });

  it('LinkedIn CTA disabled when no handler', () => {
    render(<NetworkEmptyState />);
    const btn = screen.getByRole('button', {
      name: /Import your LinkedIn connections/i,
    });
    expect(btn).toBeDisabled();
  });

  it('LinkedIn CTA calls handler when provided', () => {
    const handler = vi.fn();
    render(<NetworkEmptyState onImportLinkedIn={handler} />);
    const btn = screen.getByRole('button', {
      name: /Import your LinkedIn connections/i,
    });
    expect(btn).not.toBeDisabled();
    fireEvent.click(btn);
    expect(handler).toHaveBeenCalledOnce();
  });

  // AC4: Target companies CTA
  it('renders "Save target companies" CTA', () => {
    render(<NetworkEmptyState />);
    const btn = screen.getByRole('button', {
      name: /Save target companies to find warm paths/i,
    });
    expect(btn).toBeInTheDocument();
  });

  it('Target companies CTA disabled when no handler', () => {
    render(<NetworkEmptyState />);
    const btn = screen.getByRole('button', {
      name: /Save target companies to find warm paths/i,
    });
    expect(btn).toBeDisabled();
  });

  it('Target companies CTA calls handler when provided', () => {
    const handler = vi.fn();
    render(<NetworkEmptyState onSaveTargetCompanies={handler} />);
    const btn = screen.getByRole('button', {
      name: /Save target companies to find warm paths/i,
    });
    expect(btn).not.toBeDisabled();
    fireEvent.click(btn);
    expect(handler).toHaveBeenCalledOnce();
  });

  // AC5: Encouraging tone / quality over quantity
  it('emphasizes quality over quantity', () => {
    render(<NetworkEmptyState />);
    expect(
      screen.getByText(/Quality connections matter more than quantity/i)
    ).toBeInTheDocument();
  });

  // Accessibility
  it('has accessible button labels', () => {
    render(<NetworkEmptyState />);
    expect(
      screen.getByLabelText(/Import your LinkedIn connections/i)
    ).toBeInTheDocument();
    expect(
      screen.getByLabelText(/Save target companies to find warm paths/i)
    ).toBeInTheDocument();
  });
});
