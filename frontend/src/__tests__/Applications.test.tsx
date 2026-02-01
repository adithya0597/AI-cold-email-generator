/**
 * Tests for the Applications page component (Story 5-14).
 *
 * Covers empty state message, CTA link, and tip text.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';

// Mock react-router-dom
vi.mock('react-router-dom', () => ({
  Link: ({ children, to, ...props }: any) => <a href={to} {...props}>{children}</a>,
}));

// Mock the applications service
vi.mock('../services/applications', () => ({
  useApplications: vi.fn(),
}));

import Applications from '../pages/Applications';
import { useApplications } from '../services/applications';

const mockUseApplications = useApplications as ReturnType<typeof vi.fn>;

describe('Applications page', () => {
  describe('empty state', () => {
    it('shows empty state message when no applications exist', () => {
      mockUseApplications.mockReturnValue({
        data: { applications: [], total: 0, has_more: false },
        isLoading: false,
        isError: false,
      });

      render(<Applications />);

      expect(screen.getByTestId('empty-state')).toBeDefined();
      expect(screen.getByText("No applications yet. Let's change that!")).toBeDefined();
    });

    it('shows CTA linking to /matches', () => {
      mockUseApplications.mockReturnValue({
        data: { applications: [], total: 0, has_more: false },
        isLoading: false,
        isError: false,
      });

      render(<Applications />);

      const cta = screen.getByTestId('review-matches-cta');
      expect(cta).toBeDefined();
      expect(cta.textContent).toBe('Review your matches');
      expect(cta.getAttribute('href')).toBe('/matches');
    });

    it('shows helpful tip text', () => {
      mockUseApplications.mockReturnValue({
        data: { applications: [], total: 0, has_more: false },
        isLoading: false,
        isError: false,
      });

      render(<Applications />);

      const tip = screen.getByTestId('empty-tip');
      expect(tip).toBeDefined();
      expect(tip.textContent).toContain(
        'Save jobs you like, then approve applications in your briefing'
      );
    });
  });

  describe('loading state', () => {
    it('shows spinner when loading', () => {
      mockUseApplications.mockReturnValue({
        data: undefined,
        isLoading: true,
        isError: false,
      });

      const { container } = render(<Applications />);

      expect(container.querySelector('.animate-spin')).toBeDefined();
    });
  });

  describe('with applications', () => {
    it('renders application list instead of empty state', () => {
      mockUseApplications.mockReturnValue({
        data: {
          applications: [
            {
              id: 'app-1',
              job_id: 'job-1',
              job_title: 'Backend Engineer',
              company: 'TechCo',
              status: 'applied',
              applied_at: '2026-02-01T12:00:00Z',
              resume_version_id: null,
            },
          ],
          total: 1,
          has_more: false,
        },
        isLoading: false,
        isError: false,
      });

      render(<Applications />);

      expect(screen.queryByTestId('empty-state')).toBeNull();
      expect(screen.getByText('Backend Engineer')).toBeDefined();
      expect(screen.getByText('TechCo')).toBeDefined();
    });
  });
});
