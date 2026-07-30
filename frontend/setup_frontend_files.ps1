# Auto-generates the full frontend/ folder with every file already filled in.
# Run this from INSIDE your frontend/ directory in PowerShell:
#   .\setup_frontend_files.ps1
# If PowerShell blocks it, first run:
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass

# Every path below is anchored to $PSScriptRoot (the folder this .ps1
# file itself lives in) instead of a bare relative path. This avoids a
# real bug where [System.IO.File]::WriteAllText resolves relative paths
# against .NET's process working directory, which can silently differ
# from the folder your PowerShell prompt shows you're in after `cd`.
$Root = $PSScriptRoot
$Utf8NoBom = New-Object System.Text.UTF8Encoding $false

@'
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
'@ | ForEach-Object {
    [System.IO.File]::WriteAllText((Join-Path $Root ".env.local.example"), $_, $Utf8NoBom)
}
Write-Host "  created .env.local.example"

New-Item -ItemType Directory -Force -Path (Join-Path $Root "app\jobs\[jobId]\evidence") | Out-Null
@'
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
'@ | ForEach-Object {
    [System.IO.File]::WriteAllText((Join-Path $Root "app\jobs\[jobId]\evidence\page.tsx"), $_, $Utf8NoBom)
}
Write-Host "  created app\jobs\[jobId]\evidence\page.tsx"

New-Item -ItemType Directory -Force -Path (Join-Path $Root "app\jobs\[jobId]") | Out-Null
@'
"use client";

import Link from "next/link";
import { usePathname, useParams } from "next/navigation";

const TABS = [
  { slug: "plan", label: "Plan" },
  { slug: "monitor", label: "Monitor" },
  { slug: "evidence", label: "Evidence" },
  { slug: "report", label: "Report" },
];

/**
 * Shared shell for all 4 job sub-pages: header with the job id, and tab
 * navigation between Plan / Monitor / Evidence / Report. Each tab page
 * fetches its own slice of job data independently -- kept simple rather
 * than sharing one fetch via context, since only one tab is mounted at
 * a time anyway.
 */
export default function JobLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { jobId } = useParams<{ jobId: string }>();

  return (
    <main className="min-h-screen">
      <div className="mx-auto max-w-4xl px-6 py-16">
        <div className="mb-8">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-accent">
            Job {jobId}
          </p>
        </div>

        <nav className="mb-8 flex gap-1 border-b border-border">
          {TABS.map((tab) => {
            const href = `/jobs/${jobId}/${tab.slug}`;
            const isActive = pathname === href;
            return (
              <Link
                key={tab.slug}
                href={href}
                className={`border-b-2 px-4 py-2.5 text-sm font-medium transition ${
                  isActive
                    ? "border-accent text-accent"
                    : "border-transparent text-ink-soft hover:text-ink"
                }`}
              >
                {tab.label}
              </Link>
            );
          })}
        </nav>

        {children}
      </div>
    </main>
  );
}
'@ | ForEach-Object {
    [System.IO.File]::WriteAllText((Join-Path $Root "app\jobs\[jobId]\layout.tsx"), $_, $Utf8NoBom)
}
Write-Host "  created app\jobs\[jobId]\layout.tsx"

New-Item -ItemType Directory -Force -Path (Join-Path $Root "app\jobs\[jobId]\monitor") | Out-Null
@'
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
          {job.status === "needs_review" && "Report ready for review — see the Report tab."}
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
'@ | ForEach-Object {
    [System.IO.File]::WriteAllText((Join-Path $Root "app\jobs\[jobId]\monitor\page.tsx"), $_, $Utf8NoBom)
}
Write-Host "  created app\jobs\[jobId]\monitor\page.tsx"

New-Item -ItemType Directory -Force -Path (Join-Path $Root "app\jobs\[jobId]\plan") | Out-Null
@'
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
'@ | ForEach-Object {
    [System.IO.File]::WriteAllText((Join-Path $Root "app\jobs\[jobId]\plan\page.tsx"), $_, $Utf8NoBom)
}
Write-Host "  created app\jobs\[jobId]\plan\page.tsx"

New-Item -ItemType Directory -Force -Path (Join-Path $Root "app\jobs\[jobId]\report") | Out-Null
@'
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
'@ | ForEach-Object {
    [System.IO.File]::WriteAllText((Join-Path $Root "app\jobs\[jobId]\report\page.tsx"), $_, $Utf8NoBom)
}
Write-Host "  created app\jobs\[jobId]\report\page.tsx"

New-Item -ItemType Directory -Force -Path (Join-Path $Root "app") | Out-Null
@'
import type { Metadata } from "next";
import { Space_Grotesk, Inter, JetBrains_Mono } from "next/font/google";
import "../styles/globals.css";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  variable: "--font-space-grotesk",
});

const inter = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-inter",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-jetbrains-mono",
});

export const metadata: Metadata = {
  title: "AI Market Research & Strategy Engine",
  description: "Agentic research workflow from query intake to client-ready strategy brief.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${spaceGrotesk.variable} ${inter.variable} ${jetbrainsMono.variable}`}>
      <body>{children}</body>
    </html>
  );
}
'@ | ForEach-Object {
    [System.IO.File]::WriteAllText((Join-Path $Root "app\layout.tsx"), $_, $Utf8NoBom)
}
Write-Host "  created app\layout.tsx"

New-Item -ItemType Directory -Force -Path (Join-Path $Root "app") | Out-Null
@'
import IntakeForm from "@/components/IntakeForm";

export default function IntakePage() {
  return (
    <main className="min-h-screen">
      <div className="mx-auto max-w-2xl px-6 py-16">
        <div className="mb-10">
          <p className="font-mono text-xs uppercase tracking-[0.2em] text-accent">
            Research Intake
          </p>
          <h1 className="mt-3 text-3xl font-semibold text-ink">
            Start a new research brief
          </h1>
          <p className="mt-2 text-sm text-ink-soft">
            Describe what you need answered. The planning agent will break it into a
            structured research plan before any sources are gathered.
          </p>
        </div>

        <IntakeForm />
      </div>
    </main>
  );
}
'@ | ForEach-Object {
    [System.IO.File]::WriteAllText((Join-Path $Root "app\page.tsx"), $_, $Utf8NoBom)
}
Write-Host "  created app\page.tsx"

New-Item -ItemType Directory -Force -Path (Join-Path $Root "components") | Out-Null
@'
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
'@ | ForEach-Object {
    [System.IO.File]::WriteAllText((Join-Path $Root "components\EvidenceCard.tsx"), $_, $Utf8NoBom)
}
Write-Host "  created components\EvidenceCard.tsx"

New-Item -ItemType Directory -Force -Path (Join-Path $Root "components") | Out-Null
@'
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { submitResearchJob } from "@/lib/api";

const OUTPUT_FORMATS = [
  { value: "market_entry_scan", label: "Market Entry Scan" },
  { value: "competitor_landscape", label: "Competitor Landscape" },
  { value: "trend_brief", label: "Trend Brief" },
  { value: "proposal_support", label: "Proposal Support" },
];

/**
 * The research intake form. On submit, navigates to the new job's
 * monitor tab so the person immediately sees live stage progress.
 */
export default function IntakeForm() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [sector, setSector] = useState("");
  const [geography, setGeography] = useState("");
  const [competitors, setCompetitors] = useState("");
  const [timeframe, setTimeframe] = useState("");
  const [outputFormat, setOutputFormat] = useState(OUTPUT_FORMATS[0].value);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const result = await submitResearchJob({
        query,
        sector: sector || undefined,
        geography: geography || undefined,
        competitors: competitors
          .split(",")
          .map((c) => c.trim())
          .filter(Boolean),
        timeframe: timeframe || undefined,
        output_format: outputFormat,
      });
      router.push(`/jobs/${result.job_id}/monitor`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong submitting the brief.");
      setSubmitting(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-6 rounded-xl border border-border bg-surface p-8 shadow-sm"
    >
      <Field label="Research question" required>
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          required
          minLength={12}
          rows={4}
          placeholder="e.g. Assess the market entry opportunity for EV charging infrastructure in Southeast Asia"
          className={inputClass}
        />
      </Field>

      <div className="grid grid-cols-2 gap-4">
        <Field label="Sector">
          <input
            value={sector}
            onChange={(e) => setSector(e.target.value)}
            placeholder="e.g. EV infrastructure"
            className={inputClass}
          />
        </Field>
        <Field label="Geography">
          <input
            value={geography}
            onChange={(e) => setGeography(e.target.value)}
            placeholder="e.g. Southeast Asia"
            className={inputClass}
          />
        </Field>
      </div>

      <Field label="Named competitors" hint="Comma-separated">
        <input
          value={competitors}
          onChange={(e) => setCompetitors(e.target.value)}
          placeholder="e.g. ChargePoint, Shell Recharge"
          className={inputClass}
        />
      </Field>

      <div className="grid grid-cols-2 gap-4">
        <Field label="Timeframe">
          <input
            value={timeframe}
            onChange={(e) => setTimeframe(e.target.value)}
            placeholder="e.g. last 12 months"
            className={inputClass}
          />
        </Field>
        <Field label="Output format">
          <select
            value={outputFormat}
            onChange={(e) => setOutputFormat(e.target.value)}
            className={inputClass}
          >
            {OUTPUT_FORMATS.map((f) => (
              <option key={f.value} value={f.value}>
                {f.label}
              </option>
            ))}
          </select>
        </Field>
      </div>

      {error && (
        <p className="rounded-md bg-status-error/10 px-3 py-2 text-sm text-status-error">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={submitting}
        className="w-full rounded-md bg-accent px-4 py-3 text-sm font-semibold text-white transition hover:bg-accent-dark disabled:opacity-60"
      >
        {submitting ? "Submitting brief..." : "Start research"}
      </button>
    </form>
  );
}

const inputClass =
  "w-full rounded-md border border-border bg-white px-3 py-2 text-sm text-ink placeholder:text-ink-soft/60 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20";

function Field({
  label,
  hint,
  required,
  children,
}: {
  label: string;
  hint?: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 flex items-baseline justify-between">
        <span className="text-sm font-medium text-ink">
          {label} {required && <span className="text-accent">*</span>}
        </span>
        {hint && <span className="text-xs text-ink-soft">{hint}</span>}
      </span>
      {children}
    </label>
  );
}
'@ | ForEach-Object {
    [System.IO.File]::WriteAllText((Join-Path $Root "components\IntakeForm.tsx"), $_, $Utf8NoBom)
}
Write-Host "  created components\IntakeForm.tsx"

New-Item -ItemType Directory -Force -Path (Join-Path $Root "components") | Out-Null
@'
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
'@ | ForEach-Object {
    [System.IO.File]::WriteAllText((Join-Path $Root "components\JobStatusStepper.tsx"), $_, $Utf8NoBom)
}
Write-Host "  created components\JobStatusStepper.tsx"

New-Item -ItemType Directory -Force -Path (Join-Path $Root "components") | Out-Null
@'
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
'@ | ForEach-Object {
    [System.IO.File]::WriteAllText((Join-Path $Root "components\ReportViewer.tsx"), $_, $Utf8NoBom)
}
Write-Host "  created components\ReportViewer.tsx"

New-Item -ItemType Directory -Force -Path (Join-Path $Root "lib") | Out-Null
@'
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
'@ | ForEach-Object {
    [System.IO.File]::WriteAllText((Join-Path $Root "lib\api.ts"), $_, $Utf8NoBom)
}
Write-Host "  created lib\api.ts"

@'
/// <reference types="next" />
/// <reference types="next/image-types/global" />

// NOTE: This file should not be edited
// see https://nextjs.org/docs/basic-features/typescript for more information.
'@ | ForEach-Object {
    [System.IO.File]::WriteAllText((Join-Path $Root "next-env.d.ts"), $_, $Utf8NoBom)
}
Write-Host "  created next-env.d.ts"

@'
/** @type {import('next').NextConfig} */
const nextConfig = {};
module.exports = nextConfig;
'@ | ForEach-Object {
    [System.IO.File]::WriteAllText((Join-Path $Root "next.config.js"), $_, $Utf8NoBom)
}
Write-Host "  created next.config.js"

@'
{
  "name": "ai-research-engine-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "14.2.5",
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "typescript": "^5.5.4",
    "@types/node": "^20.14.15",
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "tailwindcss": "^3.4.7",
    "postcss": "^8.4.40",
    "autoprefixer": "^10.4.19"
  }
}
'@ | ForEach-Object {
    [System.IO.File]::WriteAllText((Join-Path $Root "package.json"), $_, $Utf8NoBom)
}
Write-Host "  created package.json"

@'
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
'@ | ForEach-Object {
    [System.IO.File]::WriteAllText((Join-Path $Root "postcss.config.js"), $_, $Utf8NoBom)
}
Write-Host "  created postcss.config.js"

New-Item -ItemType Directory -Force -Path (Join-Path $Root "styles") | Out-Null
@'
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  body {
    @apply bg-canvas text-ink font-body antialiased;
  }
  h1, h2, h3 {
    @apply font-display;
  }
}

@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
'@ | ForEach-Object {
    [System.IO.File]::WriteAllText((Join-Path $Root "styles\globals.css"), $_, $Utf8NoBom)
}
Write-Host "  created styles\globals.css"

@'
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#10131A",
        "ink-soft": "#5B6472",
        canvas: "#F7F8FA",
        surface: "#FFFFFF",
        border: "#E4E7EC",
        accent: {
          DEFAULT: "#2F5DD3",
          dark: "#1F44A8",
          soft: "#EAF0FD",
        },
        status: {
          pending: "#8A93A3",
          running: "#2F5DD3",
          success: "#1F9D6B",
          warning: "#C9821E",
          error: "#C4432B",
        },
      },
      fontFamily: {
        display: ["var(--font-space-grotesk)", "sans-serif"],
        body: ["var(--font-inter)", "sans-serif"],
        mono: ["var(--font-jetbrains-mono)", "monospace"],
      },
    },
  },
  plugins: [],
};
'@ | ForEach-Object {
    [System.IO.File]::WriteAllText((Join-Path $Root "tailwind.config.js"), $_, $Utf8NoBom)
}
Write-Host "  created tailwind.config.js"

@'
{
  "compilerOptions": {
    "target": "es2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
'@ | ForEach-Object {
    [System.IO.File]::WriteAllText((Join-Path $Root "tsconfig.json"), $_, $Utf8NoBom)
}
Write-Host "  created tsconfig.json"

Write-Host ""
Write-Host "All frontend files created (UTF-8, no BOM). Next steps:"
Write-Host "  npm install"
Write-Host "  cp .env.local.example .env.local"
Write-Host "  npm run dev"