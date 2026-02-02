import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { H1BFilter, H1B_FILTER_KEY, type H1BFilterValue } from '../components/h1b/H1BFilter';

describe('H1BFilter', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('renders all filter options', () => {
    render(<H1BFilter onFilterChange={vi.fn()} />);

    expect(screen.getByLabelText(/All jobs/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Verified sponsors only/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/High approval rate/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Any sponsorship history/i)).toBeInTheDocument();
  });

  it('defaults to "all" when no localStorage', () => {
    render(<H1BFilter onFilterChange={vi.fn()} />);

    const allRadio = screen.getByLabelText(/All jobs/i) as HTMLInputElement;
    expect(allRadio.checked).toBe(true);
  });

  it('persists selection to localStorage', () => {
    render(<H1BFilter onFilterChange={vi.fn()} />);

    fireEvent.click(screen.getByLabelText(/Verified sponsors only/i));

    expect(localStorage.getItem(H1B_FILTER_KEY)).toBe('verified_only');
  });

  it('loads persisted selection from localStorage', () => {
    localStorage.setItem(H1B_FILTER_KEY, 'high_approval');

    render(<H1BFilter onFilterChange={vi.fn()} />);

    const highRadio = screen.getByLabelText(/High approval rate/i) as HTMLInputElement;
    expect(highRadio.checked).toBe(true);
  });

  it('calls onFilterChange callback on selection', () => {
    const callback = vi.fn();
    render(<H1BFilter onFilterChange={callback} />);

    fireEvent.click(screen.getByLabelText(/Any sponsorship history/i));

    expect(callback).toHaveBeenCalledWith('any_history');
  });
});
