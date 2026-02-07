/**
 * Enterprise Admin page -- tab-based layout composing enterprise dashboards.
 *
 * Tabs: Metrics, ROI Reports, Billing.
 * Uses useApiClient hook for authenticated data fetching.
 */

import { useState, useEffect, useCallback } from 'react';
import { useApiClient } from '../services/api';
import { EnterpriseMetricsDashboard } from '../components/enterprise/EnterpriseMetricsDashboard';
import { ROIReportDashboard } from '../components/enterprise/ROIReportDashboard';
import { BillingDashboard } from '../components/enterprise/BillingDashboard';
import { EnterpriseEmptyState } from '../components/enterprise/EnterpriseEmptyState';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type TabId = 'metrics' | 'roi' | 'billing';

interface TabDef {
  id: TabId;
  label: string;
}

const TABS: TabDef[] = [
  { id: 'metrics', label: 'Metrics' },
  { id: 'roi', label: 'ROI Reports' },
  { id: 'billing', label: 'Billing' },
];

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function EnterpriseAdmin() {
  const apiClient = useApiClient();
  const [activeTab, setActiveTab] = useState<TabId>('metrics');

  // Shared loading / error state
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Setup state (for EnterpriseEmptyState)
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set());
  const [isSetupComplete, setIsSetupComplete] = useState(true);

  // Metrics state
  const [metricsData, setMetricsData] = useState<{
    summary?: Record<string, unknown>;
    daily_breakdown?: Array<Record<string, unknown>>;
    date_range?: { start: string; end: string };
  } | null>(null);
  const [metricsDateRange, setMetricsDateRange] = useState<{ start: string; end: string }>({
    start: '',
    end: '',
  });

  // ROI state
  const [roiMetrics, setRoiMetrics] = useState<Record<string, unknown> | undefined>();
  const [roiSchedule, setRoiSchedule] = useState<{ enabled: boolean; recipients: string[] } | undefined>();
  const [roiDateRange, setRoiDateRange] = useState<{ start: string; end: string }>({
    start: '',
    end: '',
  });

  // Billing state
  const [billingSummary, setBillingSummary] = useState<Record<string, unknown> | undefined>();
  const [invoices, setInvoices] = useState<Array<Record<string, unknown>>>([]);
  const [costTrend, setCostTrend] = useState<Array<Record<string, unknown>>>([]);

  // ---------------------------------------------------------------------------
  // Data fetching
  // ---------------------------------------------------------------------------

  const fetchMetrics = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string> = {};
      if (metricsDateRange.start) params.start_date = metricsDateRange.start;
      if (metricsDateRange.end) params.end_date = metricsDateRange.end;

      const res = await apiClient.get('/api/v1/admin/metrics', { params });
      setMetricsData(res.data);
      if (res.data.date_range) {
        setMetricsDateRange(res.data.date_range);
      }
      setIsSetupComplete(true);
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 403 || status === 404) {
        setIsSetupComplete(false);
      } else {
        setError('Failed to load metrics. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  }, [apiClient, metricsDateRange.start, metricsDateRange.end]);

  const fetchROI = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string> = {};
      if (roiDateRange.start) params.start_date = roiDateRange.start;
      if (roiDateRange.end) params.end_date = roiDateRange.end;

      const [metricsRes, scheduleRes] = await Promise.all([
        apiClient.get('/api/v1/admin/reports/roi', { params }),
        apiClient.get('/api/v1/admin/reports/roi/schedule'),
      ]);
      setRoiMetrics(metricsRes.data);
      setRoiSchedule(scheduleRes.data);
    } catch {
      setError('Failed to load ROI reports. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [apiClient, roiDateRange.start, roiDateRange.end]);

  const fetchBilling = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [summaryRes, invoicesRes, trendRes] = await Promise.all([
        apiClient.get('/api/v1/admin/billing'),
        apiClient.get('/api/v1/admin/billing/invoices'),
        apiClient.get('/api/v1/admin/billing/cost-trend'),
      ]);
      setBillingSummary(summaryRes.data);
      setInvoices(invoicesRes.data.invoices ?? []);
      setCostTrend(trendRes.data);
    } catch {
      setError('Failed to load billing data. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [apiClient]);

  // Fetch data when tab changes
  useEffect(() => {
    if (activeTab === 'metrics') fetchMetrics();
    else if (activeTab === 'roi') fetchROI();
    else if (activeTab === 'billing') fetchBilling();
  }, [activeTab, fetchMetrics, fetchROI, fetchBilling]);

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------

  const handleMetricsDateRangeChange = (start: string, end: string) => {
    setMetricsDateRange({ start, end });
  };

  const handleMetricsExport = async () => {
    try {
      const params: Record<string, string> = { export_format: 'csv' };
      if (metricsDateRange.start) params.start_date = metricsDateRange.start;
      if (metricsDateRange.end) params.end_date = metricsDateRange.end;

      const res = await apiClient.get('/api/v1/admin/metrics', {
        params,
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'org_metrics.csv');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      setError('Failed to export metrics.');
    }
  };

  const handleRoiDateRangeChange = (start: string, end: string) => {
    setRoiDateRange({ start, end });
  };

  const handleScheduleChange = async (schedule: { enabled: boolean; recipients: string[] }) => {
    try {
      const res = await apiClient.post('/api/v1/admin/reports/roi/schedule', schedule);
      setRoiSchedule(res.data);
    } catch {
      setError('Failed to update report schedule.');
    }
  };

  const handleUpdateSeats = async (seatCount: number) => {
    try {
      const res = await apiClient.put('/api/v1/admin/billing/seats', {
        seat_count: seatCount,
      });
      setBillingSummary(res.data);
    } catch {
      setError('Failed to update seats.');
    }
  };

  const handleStepAction = (stepNumber: number) => {
    setCompletedSteps((prev) => new Set([...prev, stepNumber]));
  };

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Enterprise Administration</h1>
        <p className="mt-1 text-sm text-gray-500">
          Manage your organization's metrics, ROI reports, and billing
        </p>
      </div>

      {/* Empty state (setup wizard) */}
      {!isSetupComplete && (
        <EnterpriseEmptyState
          completedSteps={completedSteps}
          onStepAction={handleStepAction}
        />
      )}

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8" aria-label="Admin tabs">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`whitespace-nowrap border-b-2 px-1 py-4 text-sm font-medium ${
                activeTab === tab.id
                  ? 'border-indigo-500 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Error banner */}
      {error && (
        <div className="rounded-md bg-red-50 p-4">
          <p className="text-sm text-red-700">{error}</p>
          <button
            onClick={() => setError(null)}
            className="mt-2 text-sm font-medium text-red-600 hover:text-red-500"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Loading state */}
      {loading && (
        <div className="space-y-4">
          <div className="h-8 animate-pulse rounded bg-gray-200 w-1/3" />
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-24 animate-pulse rounded-lg bg-gray-200" />
            ))}
          </div>
          <div className="h-48 animate-pulse rounded-lg bg-gray-200" />
        </div>
      )}

      {/* Tab content */}
      {!loading && (
        <>
          {activeTab === 'metrics' && (
            <EnterpriseMetricsDashboard
              metrics={metricsData?.summary as Parameters<typeof EnterpriseMetricsDashboard>[0]['metrics']}
              dailyBreakdown={metricsData?.daily_breakdown as Parameters<typeof EnterpriseMetricsDashboard>[0]['dailyBreakdown']}
              dateRange={metricsDateRange.start ? metricsDateRange : undefined}
              onDateRangeChange={handleMetricsDateRangeChange}
              onExport={handleMetricsExport}
            />
          )}

          {activeTab === 'roi' && (
            <ROIReportDashboard
              metrics={roiMetrics as Parameters<typeof ROIReportDashboard>[0]['metrics']}
              schedule={roiSchedule}
              dateRange={roiDateRange.start ? roiDateRange : undefined}
              onDateRangeChange={handleRoiDateRangeChange}
              onScheduleChange={handleScheduleChange}
            />
          )}

          {activeTab === 'billing' && (
            <BillingDashboard
              summary={billingSummary as Parameters<typeof BillingDashboard>[0]['summary']}
              invoices={invoices as Parameters<typeof BillingDashboard>[0]['invoices']}
              costTrend={costTrend as Parameters<typeof BillingDashboard>[0]['costTrend']}
              onUpdateSeats={handleUpdateSeats}
            />
          )}
        </>
      )}
    </div>
  );
}
