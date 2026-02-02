import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { NetworkDashboard } from '../components/network/NetworkDashboard';

const mockData = {
  targetCompanies: [
    { name: 'Acme Corp', warmPathCount: 3 },
    { name: 'Globex Inc', warmPathCount: 1 },
  ],
  contacts: [
    { name: 'Alice Smith', company: 'Acme Corp', temperature: 'warm' as const, readyForOutreach: true },
    { name: 'Bob Jones', company: 'Globex Inc', temperature: 'cold' as const, readyForOutreach: false },
  ],
  pendingDrafts: [
    { id: 'd1', recipient: 'Alice Smith', company: 'Acme Corp', messagePreview: 'Hi Alice! I noticed...' },
  ],
  recentActivity: [
    { contactName: 'Alice Smith', type: 'comment', description: 'Commented on AI post', date: '2025-12-01' },
  ],
  suggestedActions: [
    { action: 'Comment on latest post', contact: 'Bob Jones', reason: 'Build familiarity' },
  ],
};

describe('NetworkDashboard', () => {
  // AC1: All 5 dashboard sections render
  it('renders Target Companies section', () => {
    render(<NetworkDashboard {...mockData} />);
    expect(screen.getByText(/Target Companies/i)).toBeInTheDocument();
  });

  it('renders Contacts by Temperature section', () => {
    render(<NetworkDashboard {...mockData} />);
    expect(screen.getByText(/Contacts by Temperature/i)).toBeInTheDocument();
  });

  it('renders Pending Outreach section', () => {
    render(<NetworkDashboard {...mockData} />);
    expect(screen.getByText(/Pending Outreach/i)).toBeInTheDocument();
  });

  it('renders Recent Activity section', () => {
    render(<NetworkDashboard {...mockData} />);
    expect(screen.getByText(/Recent Activity/i)).toBeInTheDocument();
  });

  it('renders Suggested Actions section', () => {
    render(<NetworkDashboard {...mockData} />);
    expect(screen.getByText(/Suggested Actions This Week/i)).toBeInTheDocument();
  });

  // AC1: Target companies show warm path counts
  it('displays company names with warm path counts', () => {
    render(<NetworkDashboard {...mockData} />);
    const section = screen.getByLabelText('Target Companies');
    expect(section).toHaveTextContent('Acme Corp');
    expect(section).toHaveTextContent('3 paths');
    expect(section).toHaveTextContent('Globex Inc');
    expect(section).toHaveTextContent('1 path');
  });

  // AC1: Contacts show temperature indicators
  it('displays contact temperature indicators', () => {
    render(<NetworkDashboard {...mockData} />);
    expect(screen.getByText('warm')).toBeInTheDocument();
    expect(screen.getByText('cold')).toBeInTheDocument();
  });

  // AC1: Ready for outreach indicator
  it('shows ready for outreach when warm/hot', () => {
    render(<NetworkDashboard {...mockData} />);
    expect(screen.getByText('Ready for outreach')).toBeInTheDocument();
  });

  // AC1: Pending outreach
  it('renders pending outreach drafts', () => {
    render(<NetworkDashboard {...mockData} />);
    expect(screen.getByText('Hi Alice! I noticed...')).toBeInTheDocument();
  });

  // AC1: Recent activity
  it('renders recent engagement events', () => {
    render(<NetworkDashboard {...mockData} />);
    expect(screen.getByText('Commented on AI post')).toBeInTheDocument();
  });

  // AC1: Suggested actions
  it('renders suggested actions', () => {
    render(<NetworkDashboard {...mockData} />);
    expect(screen.getByText('Comment on latest post')).toBeInTheDocument();
  });

  // Empty data messages
  it('shows appropriate messages when data is empty', () => {
    render(<NetworkDashboard />);
    expect(screen.getByText(/No target companies yet/i)).toBeInTheDocument();
    expect(screen.getByText(/No contacts tracked yet/i)).toBeInTheDocument();
    expect(screen.getByText(/No pending outreach drafts/i)).toBeInTheDocument();
    expect(screen.getByText(/No recent engagement activity/i)).toBeInTheDocument();
    expect(screen.getByText(/No suggested actions right now/i)).toBeInTheDocument();
  });

  // AC2: Drill-down click handlers
  it('calls onCompanyClick when company is clicked', () => {
    const handler = vi.fn();
    render(<NetworkDashboard {...mockData} onCompanyClick={handler} />);
    const section = screen.getByLabelText('Target Companies');
    const companyButton = section.querySelector('button');
    fireEvent.click(companyButton!);
    expect(handler).toHaveBeenCalledWith('Acme Corp');
  });

  it('calls onContactClick when contact is clicked', () => {
    const handler = vi.fn();
    render(<NetworkDashboard {...mockData} onContactClick={handler} />);
    const section = screen.getByLabelText('Contacts by Temperature');
    const contactButton = section.querySelector('button');
    fireEvent.click(contactButton!);
    expect(handler).toHaveBeenCalledWith('Alice Smith');
  });

  it('calls onDraftClick when draft is clicked', () => {
    const handler = vi.fn();
    render(<NetworkDashboard {...mockData} onDraftClick={handler} />);
    const section = screen.getByLabelText('Pending Outreach');
    const draftButton = section.querySelector('button');
    fireEvent.click(draftButton!);
    expect(handler).toHaveBeenCalledWith('d1');
  });
});
