import type { Metadata } from "next";
import Link from "next/link";
import { ShieldAlert, AlertTriangle, CheckCircle, Bug, Lock, HelpCircle, CheckCircle2, XCircle } from "lucide-react";

export const metadata: Metadata = {
  title: "Security Disclaimer & Vulnerability Disclosure | Digital Rakshak",
  description: "Operational scope, AI heuristic boundaries, and responsible vulnerability disclosure policy (VDP) for Digital Rakshak.",
};

export default function SecurityDisclaimerPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
      
      {/* Header */}
      <div className="mb-12 border-b border-[#253540] pb-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-rose-500/10 border border-rose-500/30 text-rose-400 font-mono text-xs mb-4">
          <ShieldAlert className="w-3.5 h-3.5" />
          <span>Operational Boundaries & Disclaimers</span>
        </div>
        <h1 className="font-display font-extrabold text-3xl sm:text-5xl tracking-tight text-white mb-4">
          Security Disclaimer & Vulnerability Disclosure
        </h1>
        <p className="text-sm sm:text-base text-[#94A3B8] leading-relaxed">
          Transparent operational disclosures regarding automated AI heuristics, risk evaluation limits, and responsible researcher reporting.
        </p>
      </div>

      {/* Main Content */}
      <div className="space-y-10 text-sm sm:text-base text-[#CBD5E1] leading-relaxed font-sans">
        
        {/* Section 1: AI Heuristics & Probabilistic Risk */}
        <section className="space-y-3">
          <h2 className="font-display font-bold text-xl sm:text-2xl text-white">
            1. Nature of Automated Risk Scoring
          </h2>
          <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-[#FEF3C7] space-y-2">
            <div className="flex items-center gap-2 font-bold text-[#F59E0B]">
              <AlertTriangle className="w-5 h-5 shrink-0" />
              <span>Probabilistic Evaluation, Not Absolute Guarantee</span>
            </div>
            <p className="text-xs sm:text-sm text-[#FDE68A] leading-relaxed">
              Digital Rakshak employs machine learning, heuristics, visual OCR, APK disassembly, and threat graph networks to evaluate digital artifacts. <strong>These scores represent statistical probabilities of risk, not definitive legal or forensic proof.</strong>
            </p>
          </div>
          <p>
            Scammers frequently register brand-new domains, obfuscate polymorphic APK code, and cycle disposable mule bank accounts. Therefore:
          </p>
          <ul className="list-disc pl-6 space-y-2">
            <li>
              <strong>False Negatives May Occur:</strong> A score of &quot;Low Risk&quot; (0–20%) does <em>not</em> guarantee that a link, app, or person is benign. It merely indicates that no known indicators of compromise or malicious heuristics were triggered during that scan.
            </li>
            <li>
              <strong>False Positives May Occur:</strong> High-security heuristics may flag brand new startups, obscure developer APKs, or legitimate domains if their hosting infrastructure matches common threat patterns.
            </li>
            <li>
              <strong>User Verification Is Essential:</strong> Digital Rakshak provides an investigative layer to aid your decisions, but you must independently verify critical financial instructions, bank branch calls, or law enforcement notices.
            </li>
          </ul>
        </section>

        {/* Section 2: No Autonomous Banking or Police Powers */}
        <section className="space-y-3">
          <h2 className="font-display font-bold text-xl sm:text-2xl text-white">
            2. Scope of Protective Functions
          </h2>
          <p>
            To prevent confusion, Digital Rakshak explicitly clarifies what the platform <strong>can</strong> and <strong>cannot</strong> do:
          </p>
          <div className="grid sm:grid-cols-2 gap-4 pt-2">
            <div className="p-4 rounded-xl bg-[#121B22] border border-[#253540] space-y-2">
              <span className="font-bold text-emerald-400 block">What Digital Rakshak Does:</span>
              <ul className="space-y-1.5 text-xs text-[#94A3B8]">
                <li className="flex items-start gap-2"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" /><span>Classifies phishing links and scam SMS messages.</span></li>
                <li className="flex items-start gap-2"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" /><span>Disassembles APK files to inspect dangerous permissions.</span></li>
                <li className="flex items-start gap-2"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" /><span>Maps suspect accounts against known cybercrime clusters.</span></li>
                <li className="flex items-start gap-2"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" /><span>Formats forensic evidence for official 1930 reporting.</span></li>
                <li className="flex items-start gap-2"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" /><span>Alerts citizens to active national cyber fraud waves.</span></li>
              </ul>
            </div>
            <div className="p-4 rounded-xl bg-[#121B22] border border-[#253540] space-y-2">
              <span className="font-bold text-rose-400 block">What Digital Rakshak Does NOT Do:</span>
              <ul className="space-y-1.5 text-xs text-[#94A3B8]">
                <li className="flex items-start gap-2"><XCircle className="w-3.5 h-3.5 text-rose-400 shrink-0 mt-0.5" /><span>Cannot independently freeze bank accounts or UPI wallets.</span></li>
                <li className="flex items-start gap-2"><XCircle className="w-3.5 h-3.5 text-rose-400 shrink-0 mt-0.5" /><span>Cannot reverse unauthorized financial debit transfers.</span></li>
                <li className="flex items-start gap-2"><XCircle className="w-3.5 h-3.5 text-rose-400 shrink-0 mt-0.5" /><span>Cannot autonomously file criminal police FIRs on your behalf.</span></li>
                <li className="flex items-start gap-2"><XCircle className="w-3.5 h-3.5 text-rose-400 shrink-0 mt-0.5" /><span>Cannot monitor all applications or private phone calls.</span></li>
                <li className="flex items-start gap-2"><XCircle className="w-3.5 h-3.5 text-rose-400 shrink-0 mt-0.5" /><span>Cannot guarantee reimbursement for financial losses.</span></li>
              </ul>
            </div>
          </div>
        </section>

        {/* Section 3: Data Source Dependencies */}
        <section className="space-y-3">
          <h2 className="font-display font-bold text-xl sm:text-2xl text-white">
            3. Data Source Dependencies & Latency
          </h2>
          <p>
            Threat intelligence relies upon real-time data feeds, OSINT databases, DNS registries, and community incident reports. Latencies in third-party registrar databases or regional network disruptions may temporarily affect scanner response times or result completeness. Digital Rakshak continuously enhances redundant engine fallbacks to minimize disruption.
          </p>
        </section>

        {/* Section 4: Vulnerability Disclosure Program (VDP) */}
        <section id="vdp" className="space-y-4 pt-4 border-t border-[#253540]">
          <div className="flex items-center gap-2">
            <Bug className="w-5 h-5 text-[#F59E0B]" />
            <h2 className="font-display font-bold text-xl sm:text-2xl text-white">
              4. Responsible Vulnerability Disclosure Program (VDP)
            </h2>
          </div>
          <p>
            Digital Rakshak welcomes cooperation from the ethical cybersecurity research community. If you discover a potential security flaw in our public systems, APIs, or infrastructure, we ask you to report it to us immediately and responsibly.
          </p>

          <div className="p-5 rounded-xl bg-[#121B22] border border-[#253540] space-y-3">
            <h3 className="font-bold text-white text-sm">Safe Harbor Guidelines for Ethical Researchers:</h3>
            <ul className="list-disc pl-5 space-y-2 text-xs text-[#94A3B8]">
              <li>Do not access, modify, or destroy citizen or enterprise data belonging to others.</li>
              <li>Do not execute denial-of-service (DoS/DDoS) attacks against production servers.</li>
              <li>Provide reasonable time (at least 30 days) for us to patch the reported issue before any public disclosure.</li>
              <li>Submit detailed reproduction steps and proofs-of-concept (POC) securely via our <Link href="/contact?category=Security+Vulnerability+(VDP)" className="text-[#F59E0B] underline font-semibold">Responsible Vulnerability Disclosure Portal &rarr;</Link></li>
            </ul>
          </div>

          <p className="text-xs text-[#94A3B8]">
            We commit to acknowledging valid security reports within 48 business hours and will not pursue legal action against researchers acting in good faith under these safe harbor guidelines.
          </p>
        </section>

      </div>

    </div>
  );
}
