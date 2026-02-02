/**
 * Mock data for EnterpriseMetricsDashboard testing and Storybook.
 */

export interface MetricsSummary {
  enrolled_count: number;
  active_count: number;
  jobs_reviewed_count: number;
  applications_submitted_count: number;
  interviews_scheduled_count: number;
  placements_count: number;
  placement_rate: number;
  avg_time_to_placement_days: number | null;
}

export interface DailyBreakdown {
  date: string;
  applications: number;
  interviews: number;
  placements: number;
}

export const mockSummary: MetricsSummary = {
  enrolled_count: 48,
  active_count: 35,
  jobs_reviewed_count: 1240,
  applications_submitted_count: 312,
  interviews_scheduled_count: 67,
  placements_count: 22,
  placement_rate: 7.05,
  avg_time_to_placement_days: 34.2,
};

export const mockDailyBreakdown: DailyBreakdown[] = [
  { date: "2026-01-03", applications: 12, interviews: 3, placements: 1 },
  { date: "2026-01-04", applications: 8, interviews: 2, placements: 0 },
  { date: "2026-01-05", applications: 15, interviews: 4, placements: 2 },
  { date: "2026-01-06", applications: 10, interviews: 1, placements: 0 },
  { date: "2026-01-07", applications: 14, interviews: 5, placements: 1 },
  { date: "2026-01-08", applications: 9, interviews: 2, placements: 0 },
  { date: "2026-01-09", applications: 11, interviews: 3, placements: 1 },
];

export const mockDateRange = {
  start: "2026-01-01",
  end: "2026-01-31",
};
