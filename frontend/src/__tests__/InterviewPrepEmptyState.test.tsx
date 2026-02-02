import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { InterviewPrepEmptyState } from '../components/interview/InterviewPrepEmptyState';

describe('InterviewPrepEmptyState', () => {
  it('renders "No interviews scheduled yet" message', () => {
    render(<InterviewPrepEmptyState />);

    expect(
      screen.getByText(/No interviews scheduled yet/i)
    ).toBeInTheDocument();
  });

  it('displays calendar connection tip', () => {
    render(<InterviewPrepEmptyState />);

    expect(
      screen.getByText(/connect your calendar to auto-detect interviews/i)
    ).toBeInTheDocument();
  });

  it('displays practice questions tip', () => {
    render(<InterviewPrepEmptyState />);

    expect(
      screen.getByText(/practice with common interview questions/i)
    ).toBeInTheDocument();
  });

  it('displays encouraging tone message', () => {
    render(<InterviewPrepEmptyState />);

    expect(screen.getByText(/You've got this!/i)).toBeInTheDocument();
  });

  it('renders Connect Calendar button', () => {
    render(<InterviewPrepEmptyState />);

    const btn = screen.getByRole('button', { name: /connect calendar/i });
    expect(btn).toBeInTheDocument();
  });

  it('renders Practice Questions button', () => {
    render(<InterviewPrepEmptyState />);

    const btn = screen.getByRole('button', { name: /practice questions/i });
    expect(btn).toBeInTheDocument();
  });

  it('Connect Calendar button disabled when no handler', () => {
    render(<InterviewPrepEmptyState />);

    const btn = screen.getByRole('button', { name: /connect calendar/i });
    expect(btn).toBeDisabled();
  });

  it('Connect Calendar button calls handler when provided', () => {
    const handler = vi.fn();
    render(<InterviewPrepEmptyState onConnectCalendar={handler} />);

    const btn = screen.getByRole('button', { name: /connect calendar/i });
    expect(btn).not.toBeDisabled();
    fireEvent.click(btn);
    expect(handler).toHaveBeenCalledOnce();
  });

  it('Practice Questions button calls handler when provided', () => {
    const handler = vi.fn();
    render(<InterviewPrepEmptyState onPracticeQuestions={handler} />);

    const btn = screen.getByRole('button', { name: /practice questions/i });
    expect(btn).not.toBeDisabled();
    fireEvent.click(btn);
    expect(handler).toHaveBeenCalledOnce();
  });

  it('displays briefing delivery info', () => {
    render(<InterviewPrepEmptyState />);

    expect(
      screen.getByText(/briefings are delivered 24 hours before/i)
    ).toBeInTheDocument();
  });
});
