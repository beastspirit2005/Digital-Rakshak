import type { Metadata } from "next";
import Link from "next/link";
import { FileText, ShieldAlert, Scale, CheckCircle2, AlertTriangle } from "lucide-react";

export const metadata: Metadata = {
  title: "Terms & Conditions | Digital Rakshak",
  description: "Terms and conditions governing the use of Digital Rakshak's cybersecurity threat intelligence platform.",
};

export default function TermsPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
      
      {/* Page Header */}
      <div className="mb-12 border-b border-[#253540] pb-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-400 font-mono text-xs mb-4">
          <Scale className="w-3.5 h-3.5" />
          <span>Platform Agreement</span>
        </div>
        <h1 className="font-display font-extrabold text-3xl sm:text-5xl tracking-tight text-white mb-4">
          Terms & Conditions
        </h1>
        <p className="text-sm sm:text-base text-[#94A3B8] leading-relaxed">
          Effective Date: January 1, 2026 • Last Updated: October 2026
        </p>
      </div>

      {/* Main Content */}
      <div className="space-y-10 text-sm sm:text-base text-[#CBD5E1] leading-relaxed font-sans">
        
        {/* Section 1 */}
        <section className="space-y-3">
          <h2 className="font-display font-bold text-xl sm:text-2xl text-white">
            1. Agreement to Terms
          </h2>
          <p>
            These Terms & Conditions (&quot;Terms&quot;) constitute a legally binding agreement between you (&quot;User&quot; or &quot;you&quot;) and <strong>Digital Rakshak Cyber Defense Core Pvt. Ltd.</strong> (&quot;Digital Rakshak&quot;, &quot;we&quot;, &quot;us&quot;, or &quot;our&quot;). By creating an account, accessing our website, executing threat scans, or subscribing to our Pro services, you signify your unreserved agreement to these Terms.
          </p>
          <p>
            If you do not agree with any part of these Terms, you must immediately terminate access to and cease using the platform.
          </p>
        </section>

        {/* Section 2 */}
        <section className="space-y-3">
          <h2 className="font-display font-bold text-xl sm:text-2xl text-white">
            2. Eligibility & Account Security
          </h2>
          <p>
            You must be at least 18 years of age (or have explicit parental/guardian consent if between 13 and 18) to use Digital Rakshak. You agree to provide true, accurate, and current information during registration.
          </p>
          <p>
            You are exclusively responsible for safeguarding the credentials associated with your account. You agree to notify us immediately of any unauthorized account access via our <Link href="/contact?category=Security+Vulnerability+(VDP)" className="text-[#F59E0B] underline font-semibold">Security & Breach Incident Desk</Link>.
          </p>
        </section>

        {/* Section 3 */}
        <section className="space-y-3">
          <h2 className="font-display font-bold text-xl sm:text-2xl text-white">
            3. Permitted & Prohibited Use
          </h2>
          <div className="p-4 rounded-xl bg-[#121B22] border border-[#253540] space-y-2">
            <h3 className="font-bold text-white flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>Permitted Uses:</span>
            </h3>
            <p className="text-xs text-[#94A3B8]">
              You may use Digital Rakshak to inspect suspicious messages, examine suspicious links/APKs, review transaction risks, build fraud incident dossiers, and monitor threat intelligence for your personal or enterprise defense.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 space-y-2">
            <h3 className="font-bold text-rose-400 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-rose-400" />
              <span>Strictly Prohibited Uses:</span>
            </h3>
            <ul className="list-disc pl-5 space-y-1.5 text-xs text-[#E2E8F0]">
              <li>Submitting malicious payloads or exploits intended to compromise Digital Rakshak or third-party targets.</li>
              <li>Performing automated mass scraping, brute-forcing, or denial-of-service attacks against our APIs.</li>
              <li>Attempting to reverse-engineer, decompile, or extract the proprietary weights of our offline AI models or graph algorithms.</li>
              <li>Using the platform to conduct unauthorized reconnaissance or harassment against innocent individuals.</li>
              <li>Reselling API quotas or accounts without an authorized Enterprise reseller agreement.</li>
            </ul>
          </div>
        </section>

        {/* Section 4 */}
        <section className="space-y-3">
          <h2 className="font-display font-bold text-xl sm:text-2xl text-white">
            4. Nature of Automated Threat Analysis & No Guarantee
          </h2>
          <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 space-y-2 text-[#FDE68A]">
            <p className="font-bold">CRITICAL DISCLAIMER ON HEURISTIC & PROBABILISTIC AI:</p>
            <p className="text-xs sm:text-sm text-[#FEF3C7] leading-relaxed">
              Digital Rakshak utilizes advanced machine learning heuristics, optical character recognition (OCR), neural network threat models, and real-time graph correlation. <strong>All risk scores, threat verdicts, and anomaly classifications are probabilistic assessments.</strong>
            </p>
          </div>
          <p>
            Cybercriminals continuously invent novel evasion strategies, polymorphic payloads, and social-engineering vectors. Consequently:
          </p>
          <ul className="list-disc pl-6 space-y-2">
            <li><strong>No Zero False-Negative Guarantee:</strong> A &quot;Low Risk&quot; or &quot;Safe&quot; indicator does <em>not</em> guarantee absolute safety or absence of malicious intent.</li>
            <li><strong>No Zero False-Positive Guarantee:</strong> Legitimate applications, websites, or phone numbers may occasionally be flagged with cautionary indicators due to aggressive anti-abuse heuristics.</li>
            <li><strong>User Due Diligence:</strong> You must always independently verify high-value fund transfers, bank instructions, or legal summons through verified, official institutional telephone channels.</li>
          </ul>
        </section>

        {/* Section 5 */}
        <section className="space-y-3">
          <h2 className="font-display font-bold text-xl sm:text-2xl text-white">
            5. Institutional Boundaries & Clarification of Role
          </h2>
          <p>
            Digital Rakshak provides technological intelligence, automated fraud triage, and forensic dossier generation. <strong>We are an independent cybersecurity technology provider, not a law enforcement agency or banking authority.</strong>
          </p>
          <ul className="list-disc pl-6 space-y-2">
            <li>Digital Rakshak <strong>cannot independently freeze bank accounts</strong>, debit accounts, or initiate mandatory fund reversals without formal escalation by accredited financial institutions.</li>
            <li>Digital Rakshak <strong>cannot automatically file an official criminal First Information Report (FIR)</strong> on your behalf. We provide structured evidence packages that you or investigating officers can present to police stations or on <a href="https://cybercrime.gov.in" target="_blank" rel="noopener noreferrer" className="text-[#F59E0B] underline">cybercrime.gov.in</a>.</li>
            <li>Citizens experiencing live active financial theft must dial the National Cybercrime Reporting Helpline <strong>1930</strong> immediately.</li>
          </ul>
        </section>

        {/* Section 6 */}
        <section className="space-y-3">
          <h2 className="font-display font-bold text-xl sm:text-2xl text-white">
            6. Subscriptions, Payments & Invoices
          </h2>
          <p>
            Access to premium capabilities (such as Personal Pro, Family Shield, and Pro Annual) requires a valid paid subscription governed by our published <Link href="/billing-policy" className="text-[#F59E0B] underline font-semibold">Subscription & Billing Policy</Link>:
          </p>
          <ul className="list-disc pl-6 space-y-2">
            <li><strong>Personal Pro:</strong> ₹149.00/month base + 18% GST (₹26.82) = <strong>₹175.82 gross payable</strong> per month.</li>
            <li><strong>Family Shield:</strong> ₹249.00/month base + 18% GST (₹44.82) = <strong>₹293.82 gross payable</strong> per month.</li>
            <li><strong>Pro Annual:</strong> ₹1,299.00/year base + 18% GST (₹233.82) = <strong>₹1,532.82 gross payable</strong> per year.</li>
            <li><strong>GST Invoices:</strong> Official tax invoices under SAC 998313 are automatically generated and downloadable from your account dashboard.</li>
          </ul>
        </section>

        {/* Section 7 */}
        <section className="space-y-3">
          <h2 className="font-display font-bold text-xl sm:text-2xl text-white">
            7. Limitation of Liability
          </h2>
          <p>
            To the maximum extent permitted by applicable Indian law, Digital Rakshak, its directors, officers, employees, and licensors shall not be liable for any indirect, incidental, special, punitive, or consequential damages, including loss of profits, data loss, or monetary loss suffered due to cyber fraud, phishing attacks, or social engineering scams.
          </p>
          <p>
            In no event shall Digital Rakshak&apos;s aggregate liability arising out of or related to these Terms exceed the total subscription fees actually paid by you to Digital Rakshak during the twelve (12) months preceding the incident giving rise to liability.
          </p>
        </section>

        {/* Section 8 */}
        <section className="space-y-3">
          <h2 className="font-display font-bold text-xl sm:text-2xl text-white">
            8. Governing Law & Dispute Resolution
          </h2>
          <p>
            These Terms are governed by and construed in accordance with the substantive laws of the Republic of India. Any legal suit, action, or proceeding arising out of or related to these Terms shall be instituted exclusively in the competent courts located in <strong>New Delhi, India</strong>.
          </p>
        </section>

        {/* Section 9 */}
        <section className="space-y-3">
          <h2 className="font-display font-bold text-xl sm:text-2xl text-white">
            9. Changes to Terms
          </h2>
          <p>
            We may revise these Terms from time to time to reflect operational, legal, or regulatory updates. We will notify users of material modifications by updating the &quot;Last Updated&quot; date and broadcasting an in-app alert. Continued use of the platform after the revised terms become effective constitutes agreement to the updated Terms.
          </p>
        </section>

      </div>

    </div>
  );
}
