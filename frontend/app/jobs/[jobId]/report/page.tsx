"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getResearchJob, ResearchJobState } from "@/lib/api";
import ReportViewer from "@/components/ReportViewer";

export default function ReportPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [job, setJob] = useState<ResearchJobState | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getResearchJob(jobId)
      .then(setJob)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load job."));
  }, [jobId]);

  if (error) {
    return <p className="rounded-md bg-status-error/10 px-4 py-3 text-sm text-status-error">{error}</p>;
  }

  if (!job) {
    return <p className="font-mono text-sm text-ink-soft">Loading...</p>;
  }

  if (!job.report) {
    return (
      <div className="rounded-xl border border-dashed border-border p-6 text-center">
        <p className="text-sm text-ink-soft">
          Report will appear here once generation is complete. Check the Monitor tab for progress.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold text-ink">Strategy Brief</h1>
      <ReportViewer report={job.report} />
    </div>
  );
}