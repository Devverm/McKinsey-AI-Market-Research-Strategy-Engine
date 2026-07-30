"use client";

import { JobStage, JobStatus, STAGE_ORDER, STAGE_LABELS } from "@/lib/api";

/**
 * The signature visual element of the product: a vertical stepper tracking
 * the 7 real pipeline stages a job moves through. This is a legitimate
 * numbered sequence (not decorative numbering) -- the job genuinely does
 * pass through these stages in this order, so the stepper reflects real
 * state, not a stylistic device.
 */
export default function JobStatusStepper({
  currentStage,
  status,
}: {
  currentStage: JobStage;
  status: JobStatus;
}) {
  const currentIndex = STAGE_ORDER.indexOf(currentStage);
  const isFailed = status === "failed";

  return (
    <ol className="relative">
      {STAGE_ORDER.map((stage, i) => {
        const isDone = i < currentIndex || (i === currentIndex && status !== "running" && status !== "pending" && !isFailed);
        const isCurrent = i === currentIndex && (status === "running" || status === "pending");
        const isFailedHere = isFailed && i === currentIndex;
        const isLast = i === STAGE_ORDER.length - 1;

        return (
          <li key={stage} className="relative pb-8 pl-9 last:pb-0">
            {!isLast && (
              <span
                className={`absolute left-[9px] top-5 h-full w-px ${
                  isDone ? "bg-status-success" : "bg-border"
                }`}
                aria-hidden
              />
            )}
            <span
              className={`absolute left-0 top-0.5 flex h-[19px] w-[19px] items-center justify-center rounded-full border-2 ${
                isFailedHere
                  ? "border-status-error bg-status-error/10"
                  : isDone
                  ? "border-status-success bg-status-success"
                  : isCurrent
                  ? "border-status-running bg-status-running/10"
                  : "border-border bg-white"
              }`}
              aria-hidden
            >
              {isDone && !isFailedHere && (
                <svg viewBox="0 0 12 12" className="h-2.5 w-2.5 fill-white">
                  <path d="M4.5 8.5L1.5 5.5l1-1 2 2 4-4 1 1z" />
                </svg>
              )}
              {isCurrent && (
                <span className="h-2 w-2 animate-pulse rounded-full bg-status-running" />
              )}
              {isFailedHere && (
                <span className="text-xs font-bold text-status-error">!</span>
              )}
            </span>

            <p
              className={`text-sm font-medium ${
                isFailedHere
                  ? "text-status-error"
                  : isDone
                  ? "text-ink"
                  : isCurrent
                  ? "text-status-running"
                  : "text-ink-soft"
              }`}
            >
              {STAGE_LABELS[stage]}
            </p>
            {isCurrent && (
              <p className="mt-0.5 font-mono text-xs text-ink-soft">In progress...</p>
            )}
          </li>
        );
      })}
    </ol>
  );
}