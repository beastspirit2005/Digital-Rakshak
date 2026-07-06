import Link from "next/link";
import { Shield } from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ConfidenceDial } from "@/components/ui/stat";

const STEPS = [
  {
    title: "Tell us what happened",
    body: "Paste the message, upload a screenshot, or just speak. Reporting takes about two minutes and works in your language.",
  },
  {
    title: "Eleven AI engines take it apart",
    body: "The report is classified, fingerprinted, and cross-referenced against national intelligence — phone numbers, accounts, and domains included.",
  },
  {
    title: "The right people act",
    body: "Linked cases surface organized networks. Investigators get the full analysis; banks get freeze requests; you get updates.",
  },
];

const STATS = [
  { value: "1.2M+", label: "threats detected" },
  { value: "98.7%", label: "detection accuracy" },
  { value: "50K+", label: "cases investigated" },
  { value: "28", label: "states covered" },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-bg">
      {/* nav */}
      <nav className="sticky top-0 z-50 bg-bg/90 backdrop-blur-sm">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Shield className="w-6 h-6 text-ink" strokeWidth={2.2} />
            <span className="font-display font-semibold text-base tracking-tight text-ink">
              Digital Rakshak
            </span>
          </div>
          <div className="hidden md:flex items-center gap-8">
            <a href="#how-it-works" className="text-sm text-ink-2 hover:text-ink transition-colors">
              How it works
            </a>
            <Link href="/report" className="text-sm text-ink-2 hover:text-ink transition-colors">
              Report a scam
            </Link>
            <Link href="/prevention" className="text-sm text-ink-2 hover:text-ink transition-colors">
              Check a link
            </Link>
          </div>
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <Link
              href="/auth/login"
              className="inline-flex items-center h-9 px-4 rounded-control text-sm font-medium bg-surface-2 text-ink hover:bg-surface-3 transition-colors duration-150"
            >
              Sign in
            </Link>
          </div>
        </div>
      </nav>

      <main className="max-w-6xl mx-auto px-6">
        {/* hero */}
        <section className="grid lg:grid-cols-2 gap-12 lg:gap-8 items-center pt-16 pb-20 sm:pt-24 sm:pb-28">
          <div className="rise-in">
            <p className="font-serif italic text-ink-2 mb-5">Cyber threat intelligence for India</p>
            <h1 className="font-display font-semibold text-2xl sm:text-display leading-none tracking-tight text-ink">
              One report can take down an entire scam network.
            </h1>
            <p className="text-base text-ink-2 mt-6 max-w-md leading-relaxed">
              Digital Rakshak reads every scam report with a swarm of AI engines, links it to
              related cases across the country, and puts the evidence in front of the people who
              can act.
            </p>
            <div className="flex flex-col sm:flex-row gap-3 mt-9">
              <Link
                href="/report"
                className="inline-flex items-center justify-center h-12 px-6 rounded-control bg-accent text-accent-ink font-semibold text-sm hover:bg-accent-hover transition-colors duration-150 active:scale-[0.98]"
              >
                Report a scam
              </Link>
              <Link
                href="/prevention"
                className="inline-flex items-center justify-center h-12 px-6 rounded-control bg-surface text-ink font-medium text-sm shadow-card hover:bg-surface-2 transition-colors duration-150"
              >
                Check a suspicious link
              </Link>
            </div>
          </div>

          {/* product vignette — real components, real states */}
          <div className="relative hidden sm:block" aria-hidden>
            <div className="bg-surface-2 rounded-card p-6 sm:p-10">
              <Card className="p-6 flex items-center gap-6 max-w-sm mx-auto">
                <ConfidenceDial value={0.89} size={104} label="AI confidence" />
                <div>
                  <p className="text-xs text-ink-3 mb-1">Case DR-2481</p>
                  <p className="font-display font-semibold text-base text-ink leading-snug">
                    Courier scam,
                    <br />
                    12 linked victims
                  </p>
                  <Badge tone="peach" className="mt-2.5">High priority</Badge>
                </div>
              </Card>
              <Card className="px-5 py-4 max-w-xs mx-auto -mt-3 translate-x-6 sm:translate-x-14">
                <p className="text-xs text-ink-3">Recommended action</p>
                <p className="text-sm font-medium text-ink mt-1">
                  Freeze account ····5563 · Block fake-courier.in
                </p>
              </Card>
            </div>
          </div>
        </section>

        {/* stats */}
        <section className="border-y border-line py-10">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {STATS.map((stat) => (
              <div key={stat.label}>
                <p className="font-display font-semibold text-xl sm:text-2xl tracking-tight text-ink tabular">
                  {stat.value}
                </p>
                <p className="text-sm text-ink-2 mt-1">{stat.label}</p>
              </div>
            ))}
          </div>
        </section>

        {/* how it works */}
        <section id="how-it-works" className="py-20 sm:py-28">
          <p className="font-serif italic text-ink-2 mb-4">How it works</p>
          <h2 className="font-display font-semibold text-xl sm:text-2xl tracking-tight text-ink max-w-xl">
            From a two-minute report to organized-crime intelligence.
          </h2>
          <div className="grid md:grid-cols-3 gap-4 mt-12">
            {STEPS.map((step) => (
              <Card key={step.title} className="p-7">
                <h3 className="font-display font-semibold text-base text-ink">{step.title}</h3>
                <p className="text-sm text-ink-2 mt-2.5 leading-relaxed">{step.body}</p>
              </Card>
            ))}
          </div>
        </section>

        {/* closing CTA */}
        <section className="pb-24">
          <div className="bg-surface-2 rounded-card px-8 py-12 sm:px-14 sm:py-16 flex flex-col sm:flex-row sm:items-center justify-between gap-8">
            <div>
              <h2 className="font-display font-semibold text-xl sm:text-2xl tracking-tight text-ink max-w-md">
                Seen something suspicious today?
              </h2>
              <p className="text-sm text-ink-2 mt-2 max-w-md">
                Your report protects the next person the scammer calls.
              </p>
            </div>
            <Link
              href="/report"
              className="inline-flex items-center justify-center h-12 px-6 rounded-control bg-accent text-accent-ink font-semibold text-sm hover:bg-accent-hover transition-colors duration-150 shrink-0 active:scale-[0.98]"
            >
              Report a scam
            </Link>
          </div>
        </section>
      </main>

      <footer className="border-t border-line">
        <div className="max-w-6xl mx-auto px-6 py-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-ink-2" />
            <span className="text-sm text-ink-2">Digital Rakshak</span>
          </div>
          <p className="text-xs text-ink-3">
            AI-assisted analysis supports, but does not replace, official investigation.
          </p>
        </div>
      </footer>
    </div>
  );
}
