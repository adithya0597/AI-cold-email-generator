/**
 * TypeScript types for the onboarding flow.
 * These match the backend Pydantic schemas from the onboarding API.
 */

export interface WorkExperience {
  company: string;
  title: string;
  startDate: string | null;
  endDate: string | null;
  description: string | null;
}

export interface Education {
  institution: string;
  degree: string | null;
  field: string | null;
  graduationYear: string | null;
}

export interface ExtractedProfile {
  name: string;
  email: string | null;
  phone: string | null;
  headline: string | null;
  skills: string[];
  experience: WorkExperience[];
  education: Education[];
}

export type OnboardingStatus =
  | 'not_started'
  | 'profile_pending'
  | 'profile_complete'
  | 'preferences_pending'
  | 'complete';

export interface ProfileConfirmRequest {
  name: string;
  headline: string | null;
  phone: string | null;
  skills: string[];
  experience: Record<string, unknown>[];
  education: Record<string, unknown>[];
  extraction_source: string;
}

export interface OnboardingStatusResponse {
  onboarding_status: OnboardingStatus;
  display_name: string | null;
}
