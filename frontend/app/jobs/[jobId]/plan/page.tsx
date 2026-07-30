"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getResearchJob, ResearchJobState } from "@/lib/api";

export default function PlanPage() {
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

  if (!job.plan) {
    return (
      <div className="rounded-xl border border-dashed border-border p-6 text-center">
        <p className="text-sm text-ink-soft">
          The research plan hasn't been generated yet. Check the Monitor tab for live progress.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold text-ink">Research Plan</h1>
      <p className="text-sm text-ink-soft">
        {job.plan.tasks.length} sub-question{job.plan.tasks.length !== 1 ? "s" : ""} the
        planner broke this request into.
      </p>

      {job.plan.tasks.map((task) => (
        <div key={task.task_id} className="rounded-xl border border-border bg-surface p-5">
          <p className="text-sm font-medium text-ink">{task.sub_question}</p>

          {task.source_categories.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {task.source_categories.map((cat) => (
                <span key={cat} className="rounded-full bg-accent-soft px-2 py-0.5 text-xs text-accent">
                  {cat.replace(/_/g, " ")}
                </span>
              ))}
            </div>
          )}

          {task.validation_rules.length > 0 && (
            <ul className="mt-3 list-inside list-disc space-y-1 text-xs text-ink-soft">
              {task.validation_rules.map((rule, i) => (
                <li key={i}>{rule}</li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </div>
  );
}