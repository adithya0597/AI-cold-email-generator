/**
 * H1B Sponsor Intelligence page — search and review company sponsorship data.
 *
 * Composes existing H1B components into a single page with a company search bar.
 */

import { useState } from 'react';
import { SponsorScorecard } from '../components/h1b/SponsorScorecard';
import { H1BFilter, type H1BFilterValue } from '../components/h1b/H1BFilter';
import { ApprovalRateChart, type YearlyData } from '../components/h1b/ApprovalRateChart';
import { SponsorBadge } from '../components/h1b/SponsorBadge';
import { H1BEmptyState } from '../components/h1b/H1BEmptyState';

export default function H1B() {
  const [company, setCompany] = useState('');
  const [searchedCompany, setSearchedCompany] = useState('');
  const [_filter, setFilter] = useState<H1BFilterValue>('all');

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = company.trim();
    if (trimmed) {
      setSearchedCompany(trimmed);
    }
  }

  // Placeholder data for the chart when no real API is connected
  const placeholderChartData: YearlyData[] = [];

  return (
    <div className="space-y-8">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">H1B Sponsor Intelligence</h1>
        <p className="mt-1 text-sm text-gray-500">
          Research company H1B sponsorship history, approval rates, and wage data
        </p>
      </div>

      {/* Search + Filter row */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <form onSubmit={handleSearch} className="flex gap-2">
            <input
              type="text"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              placeholder="Search company name (e.g. Google, Microsoft)"
              className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
            <button
              type="submit"
              className="rounded-lg bg-indigo-600 px-6 py-2 text-sm font-medium text-white hover:bg-indigo-700"
            >
              Search
            </button>
          </form>
        </div>

        <div>
          <H1BFilter onFilterChange={setFilter} />
        </div>
      </div>

      {/* Results */}
      {searchedCompany ? (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="space-y-4">
            <SponsorScorecard company={searchedCompany} />
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-500">Badge preview:</span>
              <SponsorBadge approvalRate={null} />
            </div>
          </div>
          <div>
            <ApprovalRateChart data={placeholderChartData} />
          </div>
        </div>
      ) : (
        <H1BEmptyState company="a company" />
      )}
    </div>
  );
}
