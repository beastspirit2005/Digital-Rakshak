import type { Metadata } from "next";
import Link from "next/link";
import { Cookie, ShieldCheck, CheckCircle2, Lock, Trash2 } from "lucide-react";

export const metadata: Metadata = {
  title: "Cookie Policy | Digital Rakshak",
  description: "Learn how Digital Rakshak uses strictly necessary cookies and local storage for security authentication without third-party tracking.",
};

export default function CookiePolicyPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
      
      {/* Header */}
      <div className="mb-12 border-b border-[#253540] pb-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-400 font-mono text-xs mb-4">
          <Cookie className="w-3.5 h-3.5" />
          <span>Storage & Cookies Notice</span>
        </div>
        <h1 className="font-display font-extrabold text-3xl sm:text-5xl tracking-tight text-white mb-4">
          Cookie Policy
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
            1. What Are Cookies & Local Storage?
          </h2>
          <p>
            Cookies are small text files stored on your computer or mobile device when you visit a website. In modern web applications, browsers also provide &quot;Local Storage&quot; and &quot;Session Storage&quot; to remember state and session data securely across page reloads.
          </p>
        </section>

        {/* Section 2: Zero Ad Trackers */}
        <section className="space-y-3">
          <h2 className="font-display font-bold text-xl sm:text-2xl text-white">
            2. Our Zero-Ad-Tracker Commitment
          </h2>
          <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 space-y-1.5">
            <div className="flex items-center gap-2 font-bold">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>No Third-Party Advertising Pixels or Data Brokers</span>
            </div>
            <p className="text-xs sm:text-sm text-emerald-200/90 leading-relaxed">
              Digital Rakshak is an Indian sovereign cybersecurity defense platform. We do not sell your behavioral data, nor do we load third-party ad networks, surveillance beacons, or cross-site commercial profiling cookies.
            </p>
          </div>
        </section>

        {/* Section 3: Categories of Cookies */}
        <section className="space-y-4">
          <h2 className="font-display font-bold text-xl sm:text-2xl text-white">
            3. Technologies We Utilize & Why
          </h2>
          
          <div className="space-y-3">
            <div className="p-5 rounded-xl bg-[#121B22] border border-[#253540] space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-white text-sm">Essential Authentication Token (dr_token)</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400">Strictly Necessary</span>
              </div>
              <p className="text-xs text-[#94A3B8] leading-relaxed">
                Stores your encrypted JSON Web Token (JWT) session upon logging in. This enables you to navigate securely between your Personal Shield, scan consoles, and billing dashboard without re-authenticating on every click.
              </p>
            </div>

            <div className="p-5 rounded-xl bg-[#121B22] border border-[#253540] space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-white text-sm">Interface Theme Preference (theme)</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-sky-500/20 text-sky-400">Functional</span>
              </div>
              <p className="text-xs text-[#94A3B8] leading-relaxed">
                Remembers your chosen color scheme preference (Dark Cyber Mode or High-Contrast Light Mode) via Local Storage to prevent screen flicker upon page load.
              </p>
            </div>

            <div className="p-5 rounded-xl bg-[#121B22] border border-[#253540] space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-white text-sm">Security & Rate Limiting Guardrails</span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-amber-500/20 text-amber-400">Platform Security</span>
              </div>
              <p className="text-xs text-[#94A3B8] leading-relaxed">
                Transient tokens and anti-abuse cookies to prevent automated brute-forcing, distributed denial-of-service, and credential stuffing attacks against our public threat scanners.
              </p>
            </div>
          </div>
        </section>

        {/* Section 4: Managing Cookies */}
        <section className="space-y-3">
          <h2 className="font-display font-bold text-xl sm:text-2xl text-white">
            4. Managing & Clearing Storage
          </h2>
          <p>
            You can control or clear cookies at any time through your browser settings. If you disable strictly necessary cookies or clear Local Storage, you will be signed out of your account and will need to log back in.
          </p>
          <ul className="list-disc pl-6 space-y-1.5 text-xs sm:text-sm text-[#94A3B8]">
            <li><strong>Google Chrome / Brave:</strong> Settings &rarr; Privacy and security &rarr; Cookies and other site data.</li>
            <li><strong>Mozilla Firefox:</strong> Settings &rarr; Privacy & Security &rarr; Cookies and Site Data.</li>
            <li><strong>Apple Safari:</strong> Preferences &rarr; Privacy &rarr; Manage Website Data.</li>
          </ul>
        </section>

        {/* Section 5: Questions */}
        <section className="space-y-2 pt-4 border-t border-[#253540]">
          <h3 className="font-bold text-white">Questions Regarding Cookies</h3>
          <p className="text-xs sm:text-sm text-[#94A3B8]">
            If you have questions about our cookie or local storage policies, please contact our privacy desk through our{" "}
            <Link href="/contact?category=Privacy+%26+DPDP+Request" className="text-[#F59E0B] underline font-semibold">
              Data Privacy Helpdesk &rarr;
            </Link>.
          </p>
        </section>

      </div>

    </div>
  );
}
