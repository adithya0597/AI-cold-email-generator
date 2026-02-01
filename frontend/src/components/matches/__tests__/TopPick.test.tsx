/**
 * Tests for TopPickCard component, Matches page top-pick integration,
 * and BriefingCard top-pick highlight.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import type { MatchData, MatchListResponse } from '../../../types/matches';

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
  useMotionValue: () => ({ get: () => 0, set: () => {} }),
  useTransform: () => ({ get: () => 0 }),
}));

// Mock react-router-dom
vi.mock('react-router-dom', () => ({
  Link: ({ children, to, ...props }: any) => <a href={to} {...props}>{children}</a>,
  useNavigate: () => vi.fn(),
}));

// Mock services/matches
const mockMutate = vi.fn();
const mockUseTopPick = vi.fn();
vi.mock('../../../services/matches', () => ({
  useMatches: vi.fn(),
  useTopPick: (...args: any[]) => mockUseTopPick(...args),
  useUpdateMatchStatus: () => ({
    mutate: mockMutate,
    isPending: false,
  }),
}));

// Mock services/briefings
vi.mock('../../../services/briefings', () => ({
  useMarkBriefingRead: () => ({
    mutate: vi.fn(),
    isPending: false,
  }),
}));

import TopPickCard from '../TopPickCard';
import Matches from '../../../pages/Matches';
import { useMatches } from '../../../services/matches';
import BriefingCard from '../../briefing/BriefingCard';

// ---------------------------------------------------------------------------
// Shared test data
// ---------------------------------------------------------------------------

const mockMatch: MatchData = {
  id: 'tp1',
  score: 95,
  status: 'new',
  rationale: {
    summary: 'Exceptional match for your background',
    top_reasons: ['Perfect skills alignment', 'Ideal location', 'Great salary'],
    concerns: ['Competitive hiring process'],
    confidence: 'High',
  },
  job: {
    id: 'j1',
    title: 'Staff Engineer',
    company: 'TopTech Inc',
    location: 'San Francisco, CA',
    remote: true,
    salary_min: 200000,
    salary_max: 280000,
    url: 'https://example.com/job',
    description: 'Lead engineering initiatives.',
  },
  created_at: '2025-06-15T12:00:00Z',
};

const mockResponse: MatchListResponse = {
  data: [
    {
      id: 'm1',
      score: 80,
      status: 'new',
      rationale: {
        summary: 'Good match',
        top_reasons: ['Skills fit'],
        concerns: [],
        confidence: 'Medium',
      },
      job: {
        id: 'j2',
        title: 'Frontend Developer',
        company: 'StartupCo',
        location: 'Remote',
        remote: true,
        salary_min: 120000,
        salary_max: 160000,
        url: null,
        description: null,
      },
      created_at: '2025-06-15T12:00:00Z',
    },
  ],
  meta: { pagination: { page: 1, per_page: 20, total: 1, total_pages: 1 } },
};

// ---------------------------------------------------------------------------
// TopPickCard component tests
// ---------------------------------------------------------------------------

describe('TopPickCard', () => {
  const defaultProps = {
    match: mockMatch,
    onSave: vi.fn(),
    onDismiss: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders star badge and Top Pick label', () => {
    render(<TopPickCard {...defaultProps} />);
    const badge = screen.getByTestId('top-pick-badge');
    expect(badge.textContent).toContain('Top Pick');
  });

  it('renders job title and company', () => {
    render(<TopPickCard {...defaultProps} />);
    expect(screen.getByTestId('top-pick-title')).toHaveTextContent('Staff Engineer');
    expect(screen.getByTestId('top-pick-company')).toHaveTextContent('TopTech Inc');
  });

  it('renders extended rationale with summary and reasons', () => {
    render(<TopPickCard {...defaultProps} />);
    expect(screen.getByTestId('top-pick-rationale-summary')).toHaveTextContent(
      'Exceptional match for your background',
    );
    const reasons = screen.getByTestId('top-pick-reasons');
    expect(reasons.textContent).toContain('Perfect skills alignment');
    expect(reasons.textContent).toContain('Ideal location');
    expect(reasons.textContent).toContain('Great salary');
  });

  it('renders save and dismiss buttons', () => {
    render(<TopPickCard {...defaultProps} />);
    expect(screen.getByTestId('top-pick-save')).toBeDefined();
    expect(screen.getByTestId('top-pick-dismiss')).toBeDefined();
  });

  it('calls onSave when save button clicked', () => {
    const onSave = vi.fn();
    render(<TopPickCard {...defaultProps} onSave={onSave} />);
    fireEvent.click(screen.getByTestId('top-pick-save'));
    expect(onSave).toHaveBeenCalledOnce();
  });

  it('calls onDismiss when dismiss button clicked', () => {
    const onDismiss = vi.fn();
    render(<TopPickCard {...defaultProps} onDismiss={onDismiss} />);
    fireEvent.click(screen.getByTestId('top-pick-dismiss'));
    expect(onDismiss).toHaveBeenCalledOnce();
  });
});

// ---------------------------------------------------------------------------
// Matches page with top pick integration
// ---------------------------------------------------------------------------

describe('Matches Page - Top Pick integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows top pick section when top pick data exists', () => {
    mockUseTopPick.mockReturnValue({ data: mockMatch, isLoading: false, isError: false });
    (useMatches as ReturnType<typeof vi.fn>).mockReturnValue({
      data: mockResponse,
      isLoading: false,
      isError: false,
    });

    render(<Matches />);
    expect(screen.getByTestId('top-pick-card')).toBeDefined();
    expect(screen.getByText('Staff Engineer')).toBeDefined();
  });

  it('hides top pick section when no top pick', () => {
    mockUseTopPick.mockReturnValue({ data: null, isLoading: false, isError: false });
    (useMatches as ReturnType<typeof vi.fn>).mockReturnValue({
      data: mockResponse,
      isLoading: false,
      isError: false,
    });

    render(<Matches />);
    expect(screen.queryByTestId('top-pick-card')).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// BriefingCard top pick highlight
// ---------------------------------------------------------------------------

describe('BriefingCard - Top Pick highlight', () => {
  it('highlights highest-scored match as top pick', () => {
    const briefing = {
      id: 'b1',
      user_id: 'u1',
      content: {
        summary: 'Your daily briefing',
        new_matches: [
          { title: 'Junior Dev', company: 'SmallCo', match_score: 60 },
          { title: 'Staff Engineer', company: 'BigCorp', match_score: 95 },
          { title: 'Mid Dev', company: 'MedCo', match_score: 75 },
        ],
        metrics: { total_matches: 3 },
      },
      briefing_type: 'full' as const,
      generated_at: new Date().toISOString(),
      delivered_at: null,
      delivery_channels: [],
      read_at: null,
      schema_version: 1,
    };

    render(
      <BriefingCard briefing={briefing} userName="Test" userId="u1" />,
    );

    // Expand the "New Matches" expandable section (defaults to collapsed)
    // The metric card also has "New Matches" text, so find the button element
    const expandBtns = screen.getAllByText('New Matches');
    // The expandable section button is the one inside a <button> element
    const sectionBtn = expandBtns.find((el) => el.closest('button'));
    fireEvent.click(sectionBtn!);

    const topPickEl = screen.getByTestId('briefing-top-pick');
    expect(topPickEl).toBeDefined();
    // The top pick should be the Staff Engineer (highest score)
    expect(topPickEl.textContent).toContain('Staff Engineer');
    expect(topPickEl.textContent).toContain('Top Pick');
    expect(topPickEl.textContent).toContain('Review Now');
  });
});
