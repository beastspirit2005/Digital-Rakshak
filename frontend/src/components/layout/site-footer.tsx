"use client";

import Link from "next/link";
import { BrandLogo } from "@/components/brand-logo";
import { ShieldAlert, PhoneCall, ExternalLink, ArrowUpRight } from "lucide-react";

export function SiteFooter() {
  return (
    <footer className="bg-[#050D12] text-[#A7B4BD] border-t border-[#253540]/40 transition-colors">
      
      {/* Emergency Cybercrime Helpline Banner */}
      <div className="bg-[#121B22] border-b border-[#253540]/40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2.5 text-[#F59E0B]">
            <ShieldAlert className="w-4 h-4 shrink-0 text-[#F59E0B]" />
            <span className="font-semibold text-white">
              Immediate Financial Cyber Fraud Emergency?
            </span>
            <span className="hidden md:inline text-[#A7B4BD]">
              Call the Ministry of Home Affairs National Cyber Helpline immediately.
            </span>
          </div>
          <div className="flex items-center gap-3">
            <a
              href="tel:1930"
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md bg-[#F59E0B]/10 hover:bg-[#F59E0B]/20 text-[#F59E0B] font-bold transition-colors"
            >
              <PhoneCall className="w-3.5 h-3.5" />
              <span>Dial 1930</span>
            </a>
            <a
              href="https://cybercrime.gov.in"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-[#CBD5E1] hover:text-white transition-colors"
            >
              <span>cybercrime.gov.in</span>
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </div>
      </div>

      {/* Main 4-Column Navigation Grid */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 sm:py-16">
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-8 lg:gap-12">
          
          {/* Brand & Mission Column */}
          <div className="col-span-2 md:col-span-4 lg:col-span-2 space-y-4">
            <Link href="/" className="inline-flex items-center gap-3 group">
              <div className="w-10 h-10 rounded-xl bg-[#18181c] border border-white/10 flex items-center justify-center group-hover:border-[#F59E0B]/40 transition-colors">
                <BrandLogo size={28} />
              </div>
              <div className="flex flex-col">
                <span className="font-display font-bold text-lg text-white tracking-tight">
                  Digital Rakshak
                </span>
                <span className="text-[11px] font-mono tracking-wider uppercase text-[#A7B4BD]">
                  Cyber Threat Intelligence
                </span>
              </div>
            </Link>

            <p className="text-xs text-[#94A3B8] leading-relaxed max-w-sm">
              Sovereign real-time cyber defense platform for India. Powered by 11 specialized AI engines 
              to identify digital arrest rackets, malicious APKs, phishing domains, and mule account clusters 
              before citizens lose their hard-earned money.
            </p>

            <div className="pt-2 flex flex-wrap items-center gap-2 text-[11px] text-[#64748B] font-mono">
              <span className="px-2 py-0.5 rounded bg-white/5 border border-white/10 text-emerald-400">
                11 AI ENGINES
              </span>
              <span className="px-2 py-0.5 rounded bg-white/5 border border-white/10 text-amber-400">
                DPDP 2023 READY
              </span>
              <span className="px-2 py-0.5 rounded bg-white/5 border border-white/10 text-sky-400">
                SAC 998313
              </span>
            </div>
          </div>

          {/* Column 1: Product & Defense */}
          <div className="space-y-3">
            <p className="font-mono text-xs uppercase tracking-wider font-bold text-white">
              Platform & Tools
            </p>
            <ul className="space-y-2 text-xs">
              <li>
                <Link href="/personal" className="hover:text-white transition-colors">
                  Personal Shield
                </Link>
              </li>
              <li>
                <Link href="/business" className="hover:text-white transition-colors">
                  Business Console
                </Link>
              </li>
              <li>
                <Link href="/prevention" className="hover:text-white transition-colors">
                  Prevention & Scanners
                </Link>
              </li>
              <li>
                <Link href="/report" className="hover:text-white transition-colors">
                  Report Threat / Scam
                </Link>
              </li>
              <li>
                <Link href="/faq" className="hover:text-white transition-colors">
                  Platform FAQ
                </Link>
              </li>
            </ul>
          </div>

          {/* Column 2: Legal & Governance */}
          <div className="space-y-3">
            <p className="font-mono text-xs uppercase tracking-wider font-bold text-white">
              Legal & Policies
            </p>
            <ul className="space-y-2 text-xs">
              <li>
                <Link href="/privacy" className="hover:text-white transition-colors">
                  Privacy Policy
                </Link>
              </li>
              <li>
                <Link href="/terms" className="hover:text-white transition-colors">
                  Terms & Conditions
                </Link>
              </li>
              <li>
                <Link href="/billing-policy" className="hover:text-white transition-colors">
                  Subscription & Billing
                </Link>
              </li>
              <li>
                <Link href="/cookies" className="hover:text-white transition-colors">
                  Cookie Policy
                </Link>
              </li>
              <li>
                <Link href="/security-disclaimer" className="hover:text-white transition-colors">
                  Security Disclaimer
                </Link>
              </li>
            </ul>
          </div>

          {/* Column 3: Support & Company */}
          <div className="space-y-3">
            <p className="font-mono text-xs uppercase tracking-wider font-bold text-white">
              Support & Company
            </p>
            <ul className="space-y-2 text-xs">
              <li>
                <Link href="/contact" className="hover:text-white transition-colors">
                  Contact Support
                </Link>
              </li>
              <li>
                <Link href="/about" className="hover:text-white transition-colors">
                  About Digital Rakshak
                </Link>
              </li>
              <li>
                <Link href="/accessibility" className="hover:text-white transition-colors">
                  Accessibility Statement
                </Link>
              </li>
              <li>
                <Link href="/security-disclaimer#vdp" className="hover:text-white transition-colors flex items-center gap-1">
                  <span>Vulnerability Disclosure</span>
                  <ArrowUpRight className="w-3 h-3 text-[#64748B]" />
                </Link>
              </li>
              <li>
                <Link 
                  href="/contact?category=Privacy+%26+DPDP+Request" 
                  className="hover:text-white transition-colors"
                >
                  Grievance Officer
                </Link>
              </li>
            </ul>
          </div>

        </div>

        {/* Disclaimer Line */}
        <div className="mt-12 pt-6 border-t border-[#253540]/30 text-center sm:text-left">
          <p className="text-[11px] text-[#64748B] leading-relaxed max-w-4xl">
            <strong className="text-[#94A3B8]">Notice & Operational Scope:</strong> Digital Rakshak provides probabilistic threat scores, heuristic anomaly indicators, and structured case intelligence to assist citizens, enterprise compliance teams, and law enforcement. The platform does not independently freeze banking accounts, reverse UPI transactions, or initiate criminal FIRs without institutional escalation.
          </p>
        </div>

        {/* Bottom Credits & Copyright */}
        <div className="mt-6 pt-6 border-t border-[#253540]/30 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-[#64748B]">
          <p>© 2026 Digital Rakshak Cyber Defense Core Pvt. Ltd. All rights reserved.</p>
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5 text-xs text-[#A7B4BD]">
              <span>Made with sovereign pride for India</span>
              <span className="inline-block w-2.5 h-1.5 rounded-xs bg-[#FF9933]" />
              <span className="inline-block w-2.5 h-1.5 rounded-xs bg-white" />
              <span className="inline-block w-2.5 h-1.5 rounded-xs bg-[#138808]" />
            </span>
          </div>
        </div>

      </div>
    </footer>
  );
}
