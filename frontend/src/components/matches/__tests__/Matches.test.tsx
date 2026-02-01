/**
 * Tests for the Matches page component.
 *
 * Tests keyboard shortcuts, empty state, and detail expansion.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import type { MatchData, MatchListResponse } from '../../../types/matches';

// Mock framer-motion
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => {
      const filtered: Record<string, any> = {};
      const skipProps = [
        'drag', 'dragConstraints', 'dragElastic', 'onDragEnd',
        'whileTap', 'initial', 'animate', 'exit', 'transition',
        'style', 'layout',
      ];
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

// Mock services
const mockMutate = vi.fn();
vi.mock('../../../services/matches', () => ({
  useMatches: vi.fn(),
  useTopPick: () => ({ data: null, isLoading: false, isError: false }),
  useUpdateMatchStatus: () => ({
    mutate: mockMutate,
    isPending: false,
  }),
}));

import Matches from '../../../pages/Matches';
import { useMatches } from '../../../services/matches';

const mockMatchData: MatchData[] = [
  {
    id: 'm1',
    score: 90,
    status: 'new',
    rationale: {
      summary: 'Excellent match',
      top_reasons: ['Great skills fit', 'Location match'],
      concerns: ['Fast-paced environment'],
      confidence: 'High',
    },
    job: {
      id: 'j1',
      title: 'Frontend Developer',
      company: 'StartupCo',
      location: 'Remote',
      remote: true,
      salary_min: 120000,
      salary_max: 160000,
      url: 'https://example.com/job1',
      description: 'Build beautiful user interfaces for our platform.',
      employment_type: null,
      h1b_sponsor_status: null,
      posted_at: null,
      source: null,
    },
    created_at: '2025-06-15T12:00:00Z',
  },
  {
    id: 'm2',
    score: 72,
    status: 'new',
    rationale: {
      summary: 'Good match',
      top_reasons: ['Relevant experience'],
      concerns: ['Below target salary'],
      confidence: 'Medium',
    },
    job: {
      id: 'j2',
      title: 'Backend Engineer',
      company: 'BigCorp',
      location: 'New York, NY',
      remote: false,
      salary_min: 100000,
      salary_max: 130000,
      url: null,
      description: null,
      employment_type: null,
      h1b_sponsor_status: null,
      posted_at: null,
      source: null,
    },
    created_at: '2025-06-14T12:00:00Z',
  },
];

const mockResponse: MatchListResponse = {
  data: mockMatchData,
  meta: {
    pagination: {
      page: 1,
      per_page: 20,
      total: 2,
      total_pages: 1,
    },
  },
};

describe('Matches Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows empty state when no matches', () => {
    (useMatches as ReturnType<typeof vi.fn>).mockReturnValue({
      data: { data: [], meta: { pagination: { page: 1, per_page: 20, total: 0, total_pages: 0 } } },
      isLoading: false,
      isError: false,
    });

    render(<Matches />);
    expect(screen.getByTestId('empty-state')).toBeDefined();
    expect(screen.getByText('All caught up!')).toBeDefined();
    expect(screen.getByText('Adjust Preferences')).toBeDefined();
  });

  it('renders the first match card', () => {
    (useMatches as ReturnType<typeof vi.fn>).mockReturnValue({
      data: mockResponse,
      isLoading: false,
      isError: false,
    });

    render(<Matches />);
    expect(screen.getByText('Frontend Developer')).toBeDefined();
    expect(screen.getByText('StartupCo')).toBeDefined();
  });

  it('shows keyboard hint', () => {
    (useMatches as ReturnType<typeof vi.fn>).mockReturnValue({
      data: mockResponse,
      isLoading: false,
      isError: false,
    });

    render(<Matches />);
    expect(screen.getByTestId('keyboard-hint')).toBeDefined();
  });

  it('handles ArrowRight to save match', () => {
    (useMatches as ReturnType<typeof vi.fn>).mockReturnValue({
      data: mockResponse,
      isLoading: false,
      isError: false,
    });

    render(<Matches />);

    act(() => {
      fireEvent.keyDown(window, { key: 'ArrowRight' });
    });

    expect(mockMutate).toHaveBeenCalledWith({
      matchId: 'm1',
      status: 'saved',
    });
  });

  it('handles ArrowLeft to dismiss match', () => {
    (useMatches as ReturnType<typeof vi.fn>).mockReturnValue({
      data: mockResponse,
      isLoading: false,
      isError: false,
    });

    render(<Matches />);

    act(() => {
      fireEvent.keyDown(window, { key: 'ArrowLeft' });
    });

    expect(mockMutate).toHaveBeenCalledWith({
      matchId: 'm1',
      status: 'dismissed',
    });
  });

  it('shows loading skeleton while fetching', () => {
    (useMatches as ReturnType<typeof vi.fn>).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    });

    render(<Matches />);
    // Should have skeleton elements (animated pulse divs)
    const skeletons = document.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it('shows error state on API failure', () => {
    (useMatches as ReturnType<typeof vi.fn>).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    });

    render(<Matches />);
    expect(screen.getByText('Unable to load matches')).toBeDefined();
  });

  it('shows match count in header', () => {
    (useMatches as ReturnType<typeof vi.fn>).mockReturnValue({
      data: mockResponse,
      isLoading: false,
      isError: false,
    });

    render(<Matches />);
    expect(screen.getByText('2 matches to review')).toBeDefined();
  });
});
