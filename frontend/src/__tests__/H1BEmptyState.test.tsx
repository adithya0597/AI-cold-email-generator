import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { H1BEmptyState } from '../components/h1b/H1BEmptyState';

describe('H1BEmptyState', () => {
  it('renders company name in message', () => {
    render(<H1BEmptyState company="Acme Corp" />);

    expect(screen.getByText(/No sponsorship data found for Acme Corp/i)).toBeInTheDocument();
  });

  it('displays helpful suggestions', () => {
    render(<H1BEmptyState company="Acme Corp" />);

    expect(screen.getByText(/new company or one that hasn't sponsored recently/i)).toBeInTheDocument();
    expect(screen.getByText(/careers page for sponsorship policy/i)).toBeInTheDocument();
    expect(screen.getByText(/ask during the interview/i)).toBeInTheDocument();
  });

  it('renders notify me button', () => {
    render(<H1BEmptyState company="Acme Corp" />);

    expect(screen.getByRole('button', { name: /notify me/i })).toBeInTheDocument();
  });

  it('renders share tip button', () => {
    render(<H1BEmptyState company="Acme Corp" />);

    expect(screen.getByRole('button', { name: /share anonymous tip/i })).toBeInTheDocument();
  });
});
