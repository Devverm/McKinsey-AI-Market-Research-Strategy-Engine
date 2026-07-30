"use client";

import { EvidenceRecord } from "@/lib/api";

const FLAG_LABELS: Record<string, string> = {
  low_credibility_source: "Low credibility source",
  stale: "Stale",
  duplicate: "Duplicate",
  contradicted: "Contradicted",
  unsupported_by_excerpt: "Unsupported by excerpt",
  insufficient_coverage: "Insufficient coverage",
};

/**
 * A single piece of evidence, shown with its claim, the verbatim excerpt
 * that grounds it, and any validation flags -- this is the "traceability"
 * view: every claim the report cites should be inspectable back to here.
 */
export default function EvidenceCard({ evidence }: { evidence: EvidenceRecord }) {
  const confidencePercent = Math.round(evidence.confidence_score * 100);

  return (
    <div className="rounded-xl border border-border bg-surface p-5">
      <div className="flex items-start justify-between gap-4">
        <p className="text-sm font-medium text-ink">{evidence.claim}</p>
        <span
          className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-mono ${
            evidence.is_supported
              ? "bg-status-success/10 text-status-success"
              : "bg-status-error/10 text-status-error"
          }`}
        >
          {confidencePercent}%
        </span>
      </div>

      <blockquote className="mt-3 border-l-2 border-border pl-3 text-xs italic text-ink-soft">
        "{evidence.excerpt}"
      </blockquote>

      <div className="mt-3 flex flex-wrap items-center gap-2">
        {evidence.entity && (
          <span className="rounded-full bg-accent-soft px-2 py-0.5 text-xs text-accent">
            {evidence.entity}
          </span>
        )}
        {evidence.topic && (
          <span className="rounded-full bg-canvas px-2 py-0.5 text-xs text-ink-soft">
            {evidence.topic}
          </span>
        )}
        {evidence.validation_flags.map((flag) => (
          <span
            key={flag}
            className="rounded-full bg-status-warning/10 px-2 py-0.5 text-xs text-status-warning"
          >
            {FLAG_LABELS[flag] || flag}
          </span>
        ))}
      </div>
    </div>
  );
}