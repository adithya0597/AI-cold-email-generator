/**
 * Pipeline list view — sortable, filterable table of applications.
 *
 * Story 6-6: Alternative to Kanban board with sort, filter, search, and bulk actions.
 */

import { useState, useMemo, useCallback } from 'react';
import { useUpdateApplicationStatus } from '../../services/applications';
import type { ApplicationItem } from '../../services/applications';

type SortField = 'company' | 'job_title' | 'status' | 'applied_at' | 'updated_at';
type SortDirection = 'asc' | 'desc';

const ALL_STATUSES = ['applied', 'screening', 'interview', 'offer', 'closed', 'rejected'];

interface PipelineListViewProps {
  applications: ApplicationItem[];
  onCardClick: (app: ApplicationItem) => void;
}

function compareValues(a: string | null | undefined, b: string | null | undefined, dir: SortDirection): number {
  const av = (a ?? '').toLowerCase();
  const bv = (b ?? '').toLowerCase();
  if (av < bv) return dir === 'asc' ? -1 : 1;
  if (av > bv) return dir === 'asc' ? 1 : -1;
  return 0;
}

export default function PipelineListView({ applications, onCardClick }: PipelineListViewProps) {
  const [sortField, setSortField] = useState<SortField>('applied_at');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkStatus, setBulkStatus] = useState('');

  const updateStatus = useUpdateApplicationStatus();

  const handleSort = useCallback((field: SortField) => {
    setSortField((prev) => {
      if (prev === field) {
        setSortDirection((d) => (d === 'asc' ? 'desc' : 'asc'));
        return prev;
      }
      setSortDirection('asc');
      return field;
    });
  }, []);

  const filtered = useMemo(() => {
    let result = applications;

    if (statusFilter) {
      result = result.filter((app) => app.status.toLowerCase() === statusFilter);
    }

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (app) =>
          (app.company ?? '').toLowerCase().includes(q) ||
          (app.job_title ?? '').toLowerCase().includes(q),
      );
    }

    return result;
  }, [applications, statusFilter, searchQuery]);

  const sorted = useMemo(() => {
    return [...filtered].sort((a, b) => {
      switch (sortField) {
        case 'company':
          return compareValues(a.company, b.company, sortDirection);
        case 'job_title':
          return compareValues(a.job_title, b.job_title, sortDirection);
        case 'status':
          return compareValues(a.status, b.status, sortDirection);
        case 'applied_at':
          return compareValues(a.applied_at, b.applied_at, sortDirection);
        case 'updated_at':
          return compareValues(a.updated_at, b.updated_at, sortDirection);
        default:
          return 0;
      }
    });
  }, [filtered, sortField, sortDirection]);

  const toggleSelect = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const toggleSelectAll = useCallback(() => {
    setSelectedIds((prev) => {
      if (prev.size === sorted.length) return new Set();
      return new Set(sorted.map((a) => a.id));
    });
  }, [sorted]);

  const handleBulkStatusChange = useCallback(() => {
    if (!bulkStatus) return;
    for (const id of selectedIds) {
      updateStatus.mutate({ applicationId: id, status: bulkStatus });
    }
    setSelectedIds(new Set());
    setBulkStatus('');
  }, [bulkStatus, selectedIds, updateStatus]);

  function sortIndicator(field: SortField) {
    if (sortField !== field) return null;
    return sortDirection === 'asc' ? ' \u25B2' : ' \u25BC';
  }

  const headerClass =
    'cursor-pointer select-none px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 hover:text-gray-700';

  return (
    <div data-testid="pipeline-list-view">
      {/* Filter bar */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <select
          data-testid="status-filter"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-md border border-gray-300 px-3 py-1.5 text-sm"
        >
          <option value="">All statuses</option>
          {ALL_STATUSES.map((s) => (
            <option key={s} value={s}>
              {s.charAt(0).toUpperCase() + s.slice(1)}
            </option>
          ))}
        </select>

        <input
          data-testid="search-input"
          type="text"
          placeholder="Search company or title..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="rounded-md border border-gray-300 px-3 py-1.5 text-sm"
        />
      </div>

      {/* Bulk action bar */}
      {selectedIds.size > 0 && (
        <div data-testid="bulk-action-bar" className="mb-3 flex items-center gap-3 rounded-md bg-indigo-50 px-4 py-2">
          <span className="text-sm font-medium text-indigo-700">
            {selectedIds.size} selected
          </span>
          <select
            data-testid="bulk-status-select"
            value={bulkStatus}
            onChange={(e) => setBulkStatus(e.target.value)}
            className="rounded-md border border-gray-300 px-2 py-1 text-sm"
          >
            <option value="">Change status to...</option>
            {ALL_STATUSES.map((s) => (
              <option key={s} value={s}>
                {s.charAt(0).toUpperCase() + s.slice(1)}
              </option>
            ))}
          </select>
          <button
            data-testid="bulk-apply-btn"
            onClick={handleBulkStatusChange}
            disabled={!bulkStatus}
            className="rounded-md bg-indigo-600 px-3 py-1 text-sm font-medium text-white disabled:opacity-50"
          >
            Apply
          </button>
        </div>
      )}

      {/* Table */}
      <div className="overflow-hidden rounded-lg bg-white shadow">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3">
                <input
                  data-testid="select-all"
                  type="checkbox"
                  checked={sorted.length > 0 && selectedIds.size === sorted.length}
                  onChange={toggleSelectAll}
                  className="h-4 w-4 rounded border-gray-300"
                />
              </th>
              <th data-testid="sort-company" className={headerClass} onClick={() => handleSort('company')}>
                Company{sortIndicator('company')}
              </th>
              <th data-testid="sort-title" className={headerClass} onClick={() => handleSort('job_title')}>
                Title{sortIndicator('job_title')}
              </th>
              <th data-testid="sort-status" className={headerClass} onClick={() => handleSort('status')}>
                Status{sortIndicator('status')}
              </th>
              <th data-testid="sort-applied" className={headerClass} onClick={() => handleSort('applied_at')}>
                Applied{sortIndicator('applied_at')}
              </th>
              <th data-testid="sort-updated" className={headerClass} onClick={() => handleSort('updated_at')}>
                Last Update{sortIndicator('updated_at')}
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 bg-white">
            {sorted.map((app) => (
              <tr
                key={app.id}
                data-testid={`list-row-${app.id}`}
                className="cursor-pointer hover:bg-gray-50"
                onClick={() => onCardClick(app)}
              >
                <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                  <input
                    type="checkbox"
                    checked={selectedIds.has(app.id)}
                    onChange={() => toggleSelect(app.id)}
                    className="h-4 w-4 rounded border-gray-300"
                  />
                </td>
                <td className="whitespace-nowrap px-4 py-3 text-sm font-medium text-gray-900">
                  {app.company ?? '—'}
                </td>
                <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500">
                  {app.job_title ?? 'Untitled'}
                </td>
                <td className="whitespace-nowrap px-4 py-3">
                  <span className="inline-flex rounded-full bg-green-100 px-2 text-xs font-semibold leading-5 text-green-800">
                    {app.status}
                  </span>
                </td>
                <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500">
                  {app.applied_at ? new Date(app.applied_at).toLocaleDateString() : '—'}
                </td>
                <td className="whitespace-nowrap px-4 py-3 text-sm text-gray-500">
                  {app.updated_at ? new Date(app.updated_at).toLocaleDateString() : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
