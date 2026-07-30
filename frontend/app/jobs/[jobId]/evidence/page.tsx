"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getResearchJob, ResearchJobState } from "@/lib/api";
import EvidenceCard from "@/components/EvidenceCard";

export default function EvidencePage() {
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

  if (job.evidence.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-border p-6 text-center">
        <p className="text-sm text-ink-soft">
          No evidence collected yet. Check the Monitor tab for live progress.
        </p>
      </div>
    );
  }

  const supportedCount = job.evidence.filter((e) => e.is_supported).length;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-ink">Evidence</h1>
        <p className="text-sm text-ink-soft">
          {supportedCount} of {job.evidence.length} claims passed validation.
        </p>
      </div>
      {job.evidence.map((evidence) => (
        <EvidenceCard key={evidence.evidence_id} evidence={evidence} />
      ))}
    </div>
  );
}