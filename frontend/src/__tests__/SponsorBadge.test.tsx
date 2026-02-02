import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SponsorBadge } from '../components/h1b/SponsorBadge';

describe('SponsorBadge', () => {
  it('renders green badge for 80%+ approval rate', () => {
    render(<SponsorBadge approvalRate={0.85} />);
    const badge = screen.getByTestId('sponsor-badge');
    expect(badge).toHaveTextContent(/Verified H1B Sponsor/i);
    expect(badge.className).toMatch(/green/);
  });

  it('renders yellow badge for 50-79% approval rate', () => {
    render(<SponsorBadge approvalRate={0.65} />);
    const badge = screen.getByTestId('sponsor-badge');
    expect(badge).toHaveTextContent(/Verified H1B Sponsor/i);
    expect(badge.className).toMatch(/yellow/);
  });

  it('renders orange badge for <50% approval rate', () => {
    render(<SponsorBadge approvalRate={0.30} />);
    const badge = screen.getByTestId('sponsor-badge');
    expect(badge).toHaveTextContent(/Verified H1B Sponsor/i);
    expect(badge.className).toMatch(/orange/);
  });

  it('renders unknown state when no data', () => {
    render(<SponsorBadge approvalRate={null} />);
    expect(screen.getByTestId('sponsor-badge')).toHaveTextContent(/Sponsorship Unknown/i);
  });

  it('renders unknown state for undefined', () => {
    render(<SponsorBadge />);
    expect(screen.getByTestId('sponsor-badge')).toHaveTextContent(/Sponsorship Unknown/i);
  });
});
