/**
 * Tests for SwipeCard component.
 *
 * Verifies that the card renders job data correctly including
 * title, company, location, salary range, score, and confidence.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import type { MatchData } from '../../../types/matches';

// Mock framer-motion to avoid animation complexity in tests
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...filterMotionProps(props)}>{children}</div>,
  },
  AnimatePresence: ({ children }: any) => children,
  useMotionValue: () => ({ get: () => 0, set: () => {} }),
  useTransform: () => ({ get: () => 0 }),
}));

// Filter out motion-specific props that aren't valid DOM attributes
function filterMotionProps(props: Record<string, any>) {
  const invalidProps = [
    'drag', 'dragConstraints', 'dragElastic', 'onDragEnd',
    'whileTap', 'initial', 'animate', 'exit', 'transition',
    'style', 'layout',
  ];
  const filtered: Record<string, any> = {};
  for (const [key, val] of Object.entries(props)) {
    if (!invalidProps.includes(key)) {
      filtered[key] = val;
    }
  }
  return filtered;
}

import SwipeCard from '../SwipeCard';

const mockMatch: MatchData = {
  id: '1',
  score: 85,
  status: 'new',
  rationale: {
    summary: 'Great match for your skills',
    top_reasons: ['Strong Python experience', 'Remote friendly'],
    concerns: ['Salary slightly below target'],
    confidence: 'High',
  },
  job: {
    id: 'j1',
    title: 'Senior Software Engineer',
    company: 'TechCorp',
    location: 'San Francisco, CA',
    remote: true,
    salary_min: 150000,
    salary_max: 200000,
    url: 'https://example.com/job',
    description: 'Build great software',
  },
  created_at: '2025-06-15T12:00:00Z',
};

describe('SwipeCard', () => {
  const defaultProps = {
    match: mockMatch,
    onSwipeLeft: vi.fn(),
    onSwipeRight: vi.fn(),
    onTap: vi.fn(),
    isExpanded: false,
  };

  it('renders the job title', () => {
    render(<SwipeCard {...defaultProps} />);
    expect(screen.getByTestId('job-title')).toHaveTextContent('Senior Software Engineer');
  });

  it('renders the company name', () => {
    render(<SwipeCard {...defaultProps} />);
    expect(screen.getByTestId('company')).toHaveTextContent('TechCorp');
  });

  it('renders the location', () => {
    render(<SwipeCard {...defaultProps} />);
    expect(screen.getByTestId('location')).toHaveTextContent('San Francisco, CA');
  });

  it('renders the remote badge when job is remote', () => {
    render(<SwipeCard {...defaultProps} />);
    expect(screen.getByTestId('remote-badge')).toHaveTextContent('Remote');
  });

  it('does not render remote badge when job is not remote', () => {
    const nonRemoteMatch = {
      ...mockMatch,
      job: { ...mockMatch.job, remote: false },
    };
    render(<SwipeCard {...defaultProps} match={nonRemoteMatch} />);
    expect(screen.queryByTestId('remote-badge')).toBeNull();
  });

  it('renders the salary range', () => {
    render(<SwipeCard {...defaultProps} />);
    expect(screen.getByTestId('salary')).toHaveTextContent('$150k - $200k');
  });

  it('renders "Not specified" when no salary', () => {
    const noSalaryMatch = {
      ...mockMatch,
      job: { ...mockMatch.job, salary_min: null, salary_max: null },
    };
    render(<SwipeCard {...defaultProps} match={noSalaryMatch} />);
    expect(screen.getByTestId('salary')).toHaveTextContent('Not specified');
  });

  it('renders the score badge with percentage', () => {
    render(<SwipeCard {...defaultProps} />);
    expect(screen.getByTestId('score-badge')).toHaveTextContent('85%');
  });

  it('renders the confidence badge', () => {
    render(<SwipeCard {...defaultProps} />);
    expect(screen.getByTestId('confidence-badge')).toHaveTextContent('High confidence');
  });

  it('renders Medium confidence correctly', () => {
    const medMatch = {
      ...mockMatch,
      rationale: { ...mockMatch.rationale, confidence: 'Medium' as const },
    };
    render(<SwipeCard {...defaultProps} match={medMatch} />);
    expect(screen.getByTestId('confidence-badge')).toHaveTextContent('Medium confidence');
  });

  it('renders Low confidence correctly', () => {
    const lowMatch = {
      ...mockMatch,
      rationale: { ...mockMatch.rationale, confidence: 'Low' as const },
    };
    render(<SwipeCard {...defaultProps} match={lowMatch} />);
    expect(screen.getByTestId('confidence-badge')).toHaveTextContent('Low confidence');
  });
});
