"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { getResearchJob, ResearchJobState } from "@/lib/api";
import JobStatusStepper from "@/components/JobStatusStepper";

const POLL_INTERVAL_MS = 7000; // 5-10s range: light on the backend, still feels live
const TERMINAL_STATUSES = new Set(["needs_review", "completed", "failed"]);

export default function MonitorPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [job, setJob] = useState<ResearchJobState | null>(null);
  const [error, setError] = useState<string | null>(null);

  const poll = useCallback(async () => {
    try {
      const data = await getResearchJob(jobId);
      setJob(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load job.");
    }
  }, [jobId]);

  useEffect(() => {
    poll();
    const interval = setInterval(() => {
      setJob((current) => {
        if (current && TERMINAL_STATUSES.has(current.status)) {
          clearInterval(interval);
        }
        return current;
      });
      poll();
    }, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [poll]);

  if (error) {
    return <p className="rounded-md bg-status-error/10 px-4 py-3 text-sm text-status-error">{error}</p>;
  }

  if (!job) {
    return <p className="font-mono text-sm text-ink-soft">Loading job...</p>;
  }

  const isTerminal = TERMINAL_STATUSES.has(job.status);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-ink">{job.request.query}</h1>
        <p className="mt-2 text-sm text-ink-soft">
          {!isTerminal && "Updating every few seconds while the pipeline runs..."}
          {job.status === "needs_review" && "Report ready for review â€” see the Report tab."}
          {job.status === "failed" && "This job failed to complete."}
        </p>
      </div>

      {job.status === "failed" && (
        <div className="rounded-xl border border-status-error/30 bg-status-error/5 p-6">
          <p className="text-sm font-semibold text-status-error">Error</p>
          <p className="mt-1 text-sm text-ink-soft">{job.error_message}</p>
        </div>
      )}

      <div className="rounded-xl border border-border bg-surface p-6">
        <JobStatusStepper currentStage={job.stage} status={job.status} />
      </div>
    </div>
  );
}