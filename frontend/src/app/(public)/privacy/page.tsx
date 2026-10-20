import type { Metadata } from "next";
import Link from "next/link";
import { ShieldCheck, Lock, Trash2, Eye, Server, AlertCircle } from "lucide-react";

export const metadata: Metadata = {
  title: "Privacy Policy | Digital Rakshak",
  description: "Learn how Digital Rakshak collects, processes, protects, and deletes personal data in accordance with India's DPDP Act 2023.",
};

export default function PrivacyPolicyPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
      
      {/* Page Header */}
      <div className="mb-12 border-b border-[#253540] pb-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 font-mono text-xs mb-4">
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>DPDP Act 2023 Compliant Notice</span>
        </div>
        <h1 className="font-display font-extrabold text-3xl sm:text-5xl tracking-tight text-white mb-4">
          Privacy Policy
        </h1>
        <p className="text-sm sm:text-base text-[#94A3B8] leading-relaxed">
          Effective Date: January 1, 2026 • Last Updated: October 2026
        </p>
      </div>

      {/* Main Legal Content */}
      <div className="space-y-10 text-sm sm:text-base text-[#CBD5E1] leading-relaxed font-sans">
        
        {/* Section 1 */}
        <section className="space-y-3">
          <h2 className="font-display font-bold text-xl sm:text-2xl text-white">
            1. Introduction & Scope
          </h2>
          <p>
            Digital Rakshak is operated by <strong>Digital Rakshak Cyber Defense Core Pvt. Ltd.</strong> (&quot;we&quot;, &quot;us&quot;, or &quot;our&quot;), incorporated under the laws of India. We operate the Digital Rakshak website, mobile applications, APIs, and threat intelligence services (collectively, the &quot;Platform&quot;).
          </p>
          <p>
            This Privacy Policy explains how we collect, process, retain, share, and protect personal data when you interact with our citizen defense tools, enter indicators for scam verification, or use our enterprise intelligence consoles. We align our data governance practices with the <strong>Digital Personal Data Protection Act, 2023 (DPDP Act)</strong> and the Information Technology Act, 2000.
          </p>
        </section>

        {/* Section 2 */}
        <section className="space-y-3">
          <h2 className="font-display font-bold text-xl sm:text-2xl text-white">
            2. Information We Collect
          </h2>
          <p>We only collect data necessary to provide and secure our cybersecurity defense services:</p>
          <ul className="list-disc pl-6 space-y-2">
            <li>
              <strong>Account & Identification Data:</strong> Full name, verified email address, phone number (if supplied for SMS threat monitoring or authentication), and hashed password credentials.
            </li>
            <li>
              <strong>Submitted Threat Indicators:</strong> URLs, domain names, suspect phone numbers, UPI Virtual Payment Addresses (VPAs), APK application packages, email headers, and suspicious text message bodies submitted by you for threat analysis.
            </li>
            <li>
              <strong>Automated Analysis Telemetry:</strong> Machine learning risk scores, heuristic flags, OCR-extracted screenshot text, APK permission manifests, and network domain footprints generated during scans.
            </li>
            <li>
              <strong>Billing & Transaction Records:</strong> Razorpay payment identifiers, subscription plan codes (<code className="text-[#F59E0B]">b2c_pro_149</code>, <code className="text-[#F59E0B]">b2c_pro_249</code>, <code className="text-[#F59E0B]">b2c_pro_annual</code>), invoice records, and GST billing addresses. We <em>never</em> collect or store full credit/debit card numbers or UPI PINs.
            </li>
            <li>
              <strong>Enterprise Event Ingestion:</strong> Security event logs, anomaly telemetry, and authentication logs ingested via authorized enterprise organization API keys.
            </li>
            <li>
              <strong>Technical & Diagnostic Data:</strong> IP addresses, browser user-agent, session identifiers, and audit logs required for platform security and rate limiting.
            </li>
          </ul>
        </section>

        {/* Section 3 */}
        <section className="space-y-3">
          <h2 className="font-display font-bold text-xl sm:text-2xl text-white">
            3. Legal Grounds & How We Use Your Data
          </h2>
          <p>We process your personal data for specific, lawful purposes:</p>
          <ul className="list-disc pl-6 space-y-2">
            <li><strong>Threat Detection & Prevention:</strong> Evaluating indicators against 11 specialized AI engines and threat graph databases to calculate real-time scam risk scores.</li>
            <li><strong>Service Delivery:</strong> Providing scan history, personalized risk alerts, and downloadable intelligence reports.</li>
            <li><strong>Subscription Management:</strong> Processing recurring renewals, issuing GST-compliant tax invoices, and honoring cancellations or refunds.</li>
            <li><strong>Platform Security & Abuse Mitigation:</strong> Detecting denial-of-service attempts, credential stuffing, and unauthorized scraping through rate-limiting safeguards.</li>
            <li><strong>AI Accuracy Enhancement:</strong> Anonymized threat metadata (such as malicious domain patterns or APK indicators) is used to refine threat detection models. No unmasked personal contact information is used for AI model training.</li>
          </ul>
        </section>

        {/* Section 4 */}
        <section className="space-y-3">
          <h2 className="font-display font-bold text-xl sm:text-2xl text-white">
            4. AI Engines & Third-Party Processors
          </h2>
          <p>
            Digital Rakshak employs a hybrid processing architecture:
          </p>
          <ul className="list-disc pl-6 space-y-2">
            <li>
              <strong>Sovereign Local Processing:</strong> Threat heuristic algorithms, APK manifest decompilation, and on-premise PyTorch neural models run locally on our secured cloud infrastructure within Indian data centers.
            </li>
            <li>
              <strong>Cloud LLM Fallbacks:</strong> For complex multilingual scam reasoning, sanitized and anonymized text segments may be processed via secure cloud inference endpoints (e.g., Groq, Google Cloud Gemini) under strict zero-data-retention agreements where prompts are not retained for external model training.
            </li>
            <li>
              <strong>Payment Infrastructure:</strong> Subscription billing is processed via Razorpay Software Private Limited (RBI-licensed Payment Aggregator). Payment credentials are tokenized directly through Razorpay in accordance with PCI-DSS Level 1 standards.
            </li>
          </ul>
        </section>

        {/* Section 5 */}
        <section className="space-y-3">
          <h2 className="font-display font-bold text-xl sm:text-2xl text-white">
            5. Data Sharing & Institutional Disclosure
          </h2>
          <p>
            Digital Rakshak does not sell, rent, or trade citizen personal data to advertisers or third-party brokers. Disclosures only take place in the following bounded scenarios:
          </p>
          <ul className="list-disc pl-6 space-y-2">
            <li>
              <strong>Enterprise Organization Administrators:</strong> If your account was provisioned by an employer or sponsoring institution, that organization&apos;s authorized security admins have visibility into enterprise events.
            </li>
            <li>
              <strong>Law Enforcement & Statutory Requests:</strong> When required by a valid judicial warrant, summons, or statutory order issued by an authorized Indian court or law enforcement agency under Section 69 of the Information Technology Act.
            </li>
            <li>
              <strong>Essential Cloud Infrastructure:</strong> Strictly vetted infrastructure providers (database hosting, transactional email) bound by strict confidentiality and data protection covenants.
            </li>
          </ul>
        </section>

        {/* Section 6 */}
        <section className="space-y-3">
          <h2 className="font-display font-bold text-xl sm:text-2xl text-white">
            6. Retention & User-Driven Deletion
          </h2>
          <p>
            We adhere to strict data minimization and purpose limitation principles:
          </p>
          <ul className="list-disc pl-6 space-y-2">
            <li>
              <strong>Scan History Deletion:</strong> You can permanently wipe your personal scan history at any time directly through your Personal Shield dashboard or via the <code className="text-[#F59E0B]">DELETE /v1/scan/history</code> API endpoint. Once deleted, historical scan logs are expunged from primary active storage.
            </li>
            <li>
              <strong>Account Deletion:</strong> Upon receiving an account termination request, account credentials and personal profiles are purged within thirty (30) days.
            </li>
            <li>
              <strong>Statutory Billing Exceptions:</strong> In compliance with the Central Goods and Services Tax Act, 2017 (CGST) and Indian accounting laws, official tax invoices and transaction records must be retained for the statutory period (typically 7 years) and cannot be expunged prematurely.
            </li>
          </ul>
        </section>

        {/* Section 7 */}
        <section className="space-y-3">
          <h2 className="font-display font-bold text-xl sm:text-2xl text-white">
            7. Your Rights Under DPDP Act 2023
          </h2>
          <p>
            Under India&apos;s Digital Personal Data Protection Act, 2023, data principals enjoy the following enforceable rights:
          </p>
          <div className="grid sm:grid-cols-2 gap-4 pt-2">
            <div className="p-4 rounded-xl bg-[#121B22] border border-[#253540]">
              <span className="font-bold text-white block mb-1">Right to Access</span>
              <span className="text-xs text-[#94A3B8]">Request a summary of your personal data processed by Digital Rakshak and identities of third parties with whom data was shared.</span>
            </div>
            <div className="p-4 rounded-xl bg-[#121B22] border border-[#253540]">
              <span className="font-bold text-white block mb-1">Right to Correction & Erasure</span>
              <span className="text-xs text-[#94A3B8]">Correct inaccurate or incomplete personal records, or request complete erasure subject to statutory retention obligations.</span>
            </div>
            <div className="p-4 rounded-xl bg-[#121B22] border border-[#253540]">
              <span className="font-bold text-white block mb-1">Right to Grievance Redressal</span>
              <span className="text-xs text-[#94A3B8]">Seek speedy redressal of privacy complaints through our designated Grievance Officer.</span>
            </div>
            <div className="p-4 rounded-xl bg-[#121B22] border border-[#253540]">
              <span className="font-bold text-white block mb-1">Right to Nominate</span>
              <span className="text-xs text-[#94A3B8]">Nominate an individual to exercise your data rights in the event of death or incapacity.</span>
            </div>
          </div>
        </section>

        {/* Section 8 */}
        <section className="space-y-3">
          <h2 className="font-display font-bold text-xl sm:text-2xl text-white">
            8. Data Security Safeguards
          </h2>
          <p>
            We implement robust administrative, physical, and technical safeguards including TLS 1.3 encryption in transit, AES-256 encryption at rest, role-based access control (RBAC), and continuous vulnerability audits. However, no internet transmission or electronic storage method is infallible, and we cannot guarantee absolute immunity from all emerging zero-day vulnerabilities.
          </p>
        </section>

        {/* Section 9 */}
        <section className="space-y-3">
          <h2 className="font-display font-bold text-xl sm:text-2xl text-white">
            9. Grievance Officer Contact Details
          </h2>
          <p>
            In compliance with Rule 3(2) of the Information Technology (Intermediary Guidelines and Digital Media Ethics Code) Rules, 2021 and the DPDP Act 2023, the details of our Data Grievance Redressal Officer are as follows:
          </p>
          <div className="p-5 rounded-xl bg-[#121B22] border border-[#253540] space-y-1.5 text-xs sm:text-sm font-mono">
            <p><strong className="text-white">Designation:</strong> Grievance Redressal Officer</p>
            <p><strong className="text-white">Entity:</strong> Digital Rakshak Cyber Defense Core Pvt. Ltd.</p>
            <p><strong className="text-white">Grievance Desk:</strong> <Link href="/contact?category=Privacy+%26+DPDP+Request" className="text-[#F59E0B] underline font-semibold">Submit to Data Grievance Officer via Secure Helpdesk &rarr;</Link></p>
            <p><strong className="text-white">Address:</strong> Cyber Command Block, Connaught Place, New Delhi 110001, India</p>
            <p><strong className="text-white">Response Turnaround:</strong> Within 48 hours for acknowledgment; final resolution within 30 days.</p>
          </div>
        </section>

      </div>

    </div>
  );
}
