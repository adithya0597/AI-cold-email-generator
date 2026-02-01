/**
 * Tests for MatchDetail component.
 *
 * Verifies full description display, extended metadata fields,
 * H1B sponsorship badge, and graceful handling of null fields.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import type { MatchData } from '../../../types/matches';

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => {
      const skipProps = [
        'drag', 'dragConstraints', 'dragElastic', 'onDragEnd',
        'whileTap', 'initial', 'animate', 'exit', 'transition',
        'style', 'layout',
      ];
      const filtered: Record<string, any> = {};
      for (const [key, val] of Object.entries(props)) {
        if (!skipProps.includes(key)) filtered[key] = val;
      }
      return <div {...filtered}>{children}</div>;
    },
  },
  AnimatePresence: ({ children }: any) => children,
}));

import MatchDetail from '../MatchDetail';

// ---------------------------------------------------------------------------
// Shared test data
// ---------------------------------------------------------------------------

const baseMatch: MatchData = {
  id: 'md1',
  score: 88,
  status: 'new',
  rationale: {
    summary: 'Strong overall match',
    top_reasons: ['Skills alignment', 'Location preference'],
    concerns: ['Fast-paced environment'],
    confidence: 'High',
  },
  job: {
    id: 'j1',
    title: 'Software Engineer',
    company: 'Acme Corp',
    location: 'San Francisco, CA',
    remote: true,
    salary_min: 150000,
    salary_max: 200000,
    url: 'https://example.com/job',
    description: 'This is a long job description that goes on and on. '.repeat(30),
    employment_type: 'Full-time',
    h1b_sponsor_status: 'verified',
    posted_at: '2025-06-10T08:00:00Z',
    source: 'indeed',
  },
  created_at: '2025-06-15T12:00:00Z',
};

// ---------------------------------------------------------------------------
// Tests: Full description (AC1)
// ---------------------------------------------------------------------------

describe('MatchDetail - Full description', () => {
  it('renders full job description without truncation', () => {
    render(<MatchDetail match={baseMatch} />);
    const desc = screen.getByTestId('job-description');
    // Full description should NOT contain "..." truncation
    expect(desc.textContent).not.toContain('...');
    // Should contain the full repeated text
    expect(desc.textContent!.length).toBeGreaterThan(500);
  });

  it('renders "No description available." when description is null', () => {
    const match = {
      ...baseMatch,
      job: { ...baseMatch.job, description: null },
    };
    render(<MatchDetail match={match} />);
    expect(screen.getByTestId('job-description')).toHaveTextContent(
      'No description available.',
    );
  });
});

// ---------------------------------------------------------------------------
// Tests: Extended metadata (AC2)
// ---------------------------------------------------------------------------

describe('MatchDetail - Extended metadata', () => {
  it('renders employment type when available', () => {
    render(<MatchDetail match={baseMatch} />);
    const el = screen.getByTestId('employment-type');
    expect(el.textContent).toContain('Full-time');
  });

  it('renders posted date in relative format', () => {
    render(<MatchDetail match={baseMatch} />);
    const el = screen.getByTestId('posted-at');
    // Should contain "Posted" prefix and some relative time
    expect(el.textContent).toContain('Posted');
  });

  it('renders job source capitalized', () => {
    render(<MatchDetail match={baseMatch} />);
    const el = screen.getByTestId('job-source');
    expect(el.textContent).toContain('Indeed');
  });

  it('hides metadata section when all fields are null', () => {
    const match = {
      ...baseMatch,
      job: {
        ...baseMatch.job,
        employment_type: null,
        posted_at: null,
        source: null,
      },
    };
    render(<MatchDetail match={match} />);
    expect(screen.queryByTestId('job-metadata')).toBeNull();
  });

  it('hides individual metadata fields when null', () => {
    const match = {
      ...baseMatch,
      job: {
        ...baseMatch.job,
        employment_type: null,
        posted_at: null,
        source: 'linkedin',
      },
    };
    render(<MatchDetail match={match} />);
    expect(screen.queryByTestId('employment-type')).toBeNull();
    expect(screen.queryByTestId('posted-at')).toBeNull();
    expect(screen.getByTestId('job-source')).toBeDefined();
  });
});

// ---------------------------------------------------------------------------
// Tests: H1B Sponsorship badge (AC3)
// ---------------------------------------------------------------------------

describe('MatchDetail - H1B badge', () => {
  it('renders green badge for verified H1B sponsor', () => {
    render(<MatchDetail match={baseMatch} />);
    const badge = screen.getByTestId('h1b-badge');
    expect(badge.textContent).toContain('Verified H1B Sponsor');
  });

  it('renders amber badge for unverified sponsorship', () => {
    const match = {
      ...baseMatch,
      job: { ...baseMatch.job, h1b_sponsor_status: 'unverified' },
    };
    render(<MatchDetail match={match} />);
    const badge = screen.getByTestId('h1b-badge');
    expect(badge.textContent).toContain('Unverified Sponsorship');
  });

  it('hides H1B badge when status is unknown', () => {
    const match = {
      ...baseMatch,
      job: { ...baseMatch.job, h1b_sponsor_status: 'unknown' },
    };
    render(<MatchDetail match={match} />);
    expect(screen.queryByTestId('h1b-badge')).toBeNull();
  });

  it('hides H1B badge when status is null', () => {
    const match = {
      ...baseMatch,
      job: { ...baseMatch.job, h1b_sponsor_status: null },
    };
    render(<MatchDetail match={match} />);
    expect(screen.queryByTestId('h1b-badge')).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// Tests: Existing behavior preserved (AC5, AC6)
// ---------------------------------------------------------------------------

describe('MatchDetail - Existing behavior', () => {
  it('renders top reasons', () => {
    render(<MatchDetail match={baseMatch} />);
    const reasons = screen.getByTestId('top-reasons');
    expect(reasons.textContent).toContain('Skills alignment');
    expect(reasons.textContent).toContain('Location preference');
  });

  it('renders concerns', () => {
    render(<MatchDetail match={baseMatch} />);
    const concerns = screen.getByTestId('concerns');
    expect(concerns.textContent).toContain('Fast-paced environment');
  });

  it('renders confidence badge', () => {
    render(<MatchDetail match={baseMatch} />);
    expect(screen.getByTestId('detail-confidence')).toHaveTextContent('High');
  });

  it('renders view full posting link', () => {
    render(<MatchDetail match={baseMatch} />);
    const link = screen.getByTestId('job-link');
    expect(link).toHaveTextContent('View Full Posting');
    expect(link.getAttribute('href')).toBe('https://example.com/job');
  });
});
