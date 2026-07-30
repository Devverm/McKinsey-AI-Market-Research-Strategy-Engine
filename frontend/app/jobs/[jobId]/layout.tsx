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