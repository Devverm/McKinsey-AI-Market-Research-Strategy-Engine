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