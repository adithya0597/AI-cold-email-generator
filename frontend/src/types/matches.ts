export interface JobSummary {
  id: string;
  title: string;
  company: string;
  location: string | null;
  remote: boolean;
  salary_min: number | null;
  salary_max: number | null;
  url: string | null;
  description: string | null;
  employment_type: string | null;
  h1b_sponsor_status: string | null;
  posted_at: string | null;
  source: string | null;
}

export interface Rationale {
  summary: string;
  top_reasons: string[];
  concerns: string[];
  confidence: "High" | "Medium" | "Low";
}

export interface MatchData {
  id: string;
  score: number;
  status: "new" | "saved" | "dismissed" | "applied";
  rationale: Rationale;
  job: JobSummary;
  created_at: string;
}

export interface LearnedPreference {
  id: string;
  pattern_type: string;
  pattern_value: string;
  confidence: number;
  occurrences: number;
  status: 'pending' | 'acknowledged' | 'rejected';
  created_at: string;
}

export interface LearnedPreferenceListResponse {
  data: LearnedPreference[];
}

export interface MatchListResponse {
  data: MatchData[];
  meta: {
    pagination: {
      page: number;
      per_page: number;
      total: number;
      total_pages: number;
    };
  };
}
