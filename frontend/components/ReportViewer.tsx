"use client";

import { Report } from "@/lib/api";

/**
 * Renders the finished report's sections. Each section shows which
 * evidence_ids it cited, so the report stays traceable back to the
 * Evidence tab rather than reading as an opaque final document.
 */
export default function ReportViewer({ report }: { report: Report }) {
  return (
    <div className="space-y-6">
      {report.sections.map((section) => (
        <div key={section.heading} className="rounded-xl border border-border bg-surface p-6">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-accent">
            {section.heading.replace(/_/g, " ")}
          </h2>
          <p className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-ink">
            {section.content}
          </p>
          {section.cited_evidence_ids.length > 0 && (
            <p className="mt-3 font-mono text-xs text-ink-soft">
              Cited evidence: {section.cited_evidence_ids.join(", ")}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}