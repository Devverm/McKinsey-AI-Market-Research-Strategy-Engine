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