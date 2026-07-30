/**
 * lib/api.ts
 *
 * Thin fetch wrapper around the FastAPI backend. Types here mirror the
 * Pydantic schemas in ai/state.py exactly (same field names, same enum
 * string values) so no translation layer is needed between backend JSON
 * and the frontend.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000";

export type JobStage =
  | "intake"
  | "planning"
  | "browsing"
  | "extraction"
  | "validation"
  | "aggregation"
  | "report_generation"
  | "review"
  | "done"
  | "failed";

export type JobStatus = "pending" | "running" | "needs_review" | "completed" | "failed";

export const STAGE_ORDER: JobStage[] = [
  "intake",
  "planning",
  "browsing",
  "extraction",
  "validation",
  "aggregation",
  "report_generation",
  "review",
];

export const STAGE_LABELS: Record<JobStage, string> = {
  intake: "Query Intake",
  planning: "Planning",
  browsing: "Web Browsing",
  extraction: "Extraction",
  validation: "Validation",
  aggregation: "Aggregation + Memory",
  report_generation: "Report Generation",
  review: "Ready for Review",
  done: "Done",
  failed: "Failed",
};

export interface ResearchRequestInput {
  query: string;
  sector?: string;
  geography?: string;
  competitors?: string[];
  timeframe?: string;
  output_format?: string;
}

export interface ResearchTask {
  task_id: string;
  sub_question: string;
  source_categories: string[];
  expected_evidence_types: string[];
  validation_rules: string[];
}

export interface ResearchPlan {
  plan_id: string;
  tasks: ResearchTask[];
  output_sections: string[];
  approved_by_user: boolean;
}

export interface EvidenceRecord {
  evidence_id: string;
  claim: string;
  excerpt: string;
  entity?: string | null;
  topic?: string | null;
  confidence_score: number;
  validation_flags: string[];
  is_supported: boolean;
}

export interface ReportSection {
  heading: string;
  content: string;
  cited_evidence_ids: string[];
}

export interface Report {
  report_id: string;
  sections: ReportSection[];
  version: number;
}

export interface ResearchJobState {
  job_id: string;
  status: JobStatus;
  stage: JobStage;
  request: ResearchRequestInput;
  plan?: ResearchPlan | null;
  evidence: EvidenceRecord[];
  error_message?: string | null;
  stage_history: string[];
  report?: Report | null;
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed with status ${res.status}`);
  }
  return res.json();
}

export async function submitResearchJob(
  input: ResearchRequestInput
): Promise<{ job_id: string; status: string; stage: string }> {
  const res = await fetch(`${API_BASE_URL}/research-jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return handleResponse(res);
}

export async function getResearchJob(jobId: string): Promise<ResearchJobState> {
  const res = await fetch(`${API_BASE_URL}/research-jobs/${jobId}`, {
    cache: "no-store",
  });
  return handleResponse(res);
}