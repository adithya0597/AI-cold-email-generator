/**
 * TypeScript types and Zod validation schemas for preference wizard steps.
 * Types match the backend Pydantic schemas from preferences API.
 * Zod schemas are used with react-hook-form for per-step validation.
 */

import { z } from 'zod';

// ============================================================
// TypeScript types (matching backend Pydantic schemas)
// ============================================================

export interface JobTypePreferences {
  categories: string[];
  target_titles: string[];
  seniority_levels: string[];
}

export interface LocationPreferences {
  work_arrangement: string | null;
  target_locations: string[];
  excluded_locations: string[];
  willing_to_relocate: boolean;
}

export interface SalaryPreferences {
  minimum: number | null;
  target: number | null;
  flexibility: string | null;
  comp_preference: string | null;
}

export interface DealBreakers {
  min_company_size: number | null;
  excluded_companies: string[];
  excluded_industries: string[];
  must_have_benefits: string[];
  max_travel_percent: number | null;
  no_oncall: boolean;
}

export interface H1BPreferences {
  requires_h1b: boolean;
  requires_greencard: boolean;
  current_visa_type: string | null;
  visa_expiration: string | null;
}

export interface AutonomyPreference {
  level: string;
}

export interface FullPreferences {
  job_type: JobTypePreferences;
  location: LocationPreferences;
  salary: SalaryPreferences;
  deal_breakers: DealBreakers;
  h1b: H1BPreferences;
  autonomy: AutonomyPreference;
  extra_preferences: Record<string, unknown>;
}

export interface PreferenceSummary extends FullPreferences {
  is_complete: boolean;
  missing_sections: string[];
}

export interface DealBreakerResponse {
  must_haves: Record<string, unknown>;
  never_haves: Record<string, unknown>;
}

// ============================================================
// Constants for option values
// ============================================================

export const JOB_CATEGORIES = [
  'Engineering',
  'Product',
  'Design',
  'Data Science',
  'Marketing',
  'Sales',
  'Operations',
  'Finance',
  'HR',
  'Legal',
  'Other',
] as const;

export const SENIORITY_LEVELS = [
  'Entry',
  'Mid',
  'Senior',
  'Staff',
  'Principal',
  'Director',
  'VP',
  'C-Level',
] as const;

export const WORK_ARRANGEMENTS = [
  { value: 'remote', label: 'Remote Only' },
  { value: 'hybrid', label: 'Hybrid' },
  { value: 'onsite', label: 'On-site Only' },
  { value: 'open', label: 'Open to All' },
] as const;

export const BENEFITS_OPTIONS = [
  '401k Match',
  'Health Insurance',
  'Unlimited PTO',
  'Remote Option',
  'Equity/Stock Options',
  'Parental Leave',
  'Professional Development Budget',
] as const;

export const VISA_TYPES = [
  'H1B',
  'OPT',
  'OPT STEM',
  'L1',
  'J1',
  'TN',
  'Other',
] as const;

export const AUTONOMY_LEVELS = [
  {
    value: 'l0',
    title: 'Suggestions Only',
    description: 'Your agent suggests, you do everything',
    recommended: true,
  },
  {
    value: 'l1',
    title: 'Draft Mode',
    description: 'Your agent drafts emails and resumes, you review and send',
    recommended: false,
  },
  {
    value: 'l2',
    title: 'Supervised',
    description: 'Your agent acts on your behalf, you approve via daily digest',
    recommended: false,
  },
  {
    value: 'l3',
    title: 'Autonomous',
    description: 'Your agent acts freely within your deal-breakers',
    recommended: false,
  },
] as const;

// ============================================================
// Zod schemas for form validation per wizard step
// ============================================================

export const jobTypeSchema = z.object({
  categories: z.array(z.string()).min(1, 'Select at least one job category'),
  target_titles: z.array(z.string()).min(1, 'Add at least one target job title'),
  seniority_levels: z.array(z.string()).min(1, 'Select at least one seniority level'),
});
export type JobTypeFormData = z.infer<typeof jobTypeSchema>;

export const locationSchema = z.object({
  work_arrangement: z.string().min(1, 'Select a work arrangement'),
  target_locations: z.array(z.string()).default([]),
  excluded_locations: z.array(z.string()).default([]),
  willing_to_relocate: z.boolean().default(false),
});
export type LocationFormData = z.infer<typeof locationSchema>;

export const salarySchema = z.object({
  minimum: z.number().nullable().optional(),
  target: z.number().nullable().optional(),
  flexibility: z.string().nullable().optional(),
  comp_preference: z.string().nullable().optional(),
});
export type SalaryFormData = z.infer<typeof salarySchema>;

export const dealBreakerSchema = z.object({
  min_company_size: z.number().nullable().optional(),
  excluded_companies: z.array(z.string()).default([]),
  excluded_industries: z.array(z.string()).default([]),
  must_have_benefits: z.array(z.string()).default([]),
  max_travel_percent: z.number().min(0).max(100).nullable().optional(),
  no_oncall: z.boolean().default(false),
});
export type DealBreakerFormData = z.infer<typeof dealBreakerSchema>;

export const h1bSchema = z.object({
  requires_h1b: z.boolean().default(false),
  requires_greencard: z.boolean().default(false),
  current_visa_type: z.string().nullable().optional(),
  visa_expiration: z.string().nullable().optional(),
});
export type H1BFormData = z.infer<typeof h1bSchema>;

export const autonomySchema = z.object({
  level: z.enum(['l0', 'l1', 'l2', 'l3'], {
    required_error: 'Select an autonomy level',
  }),
});
export type AutonomyFormData = z.infer<typeof autonomySchema>;
