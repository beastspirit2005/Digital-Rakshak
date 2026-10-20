import Link from "next/link";
import { ShieldAlert, Home, Shield, Building2, HelpCircle, ArrowRight } from "lucide-react";
import { SiteHeader } from "@/components/layout/site-header";
import { SiteFooter } from "@/components/layout/site-footer";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "404 — Page Not Found | Digital Rakshak",
  description: "The requested cyber resource could not be found or has moved.",
};

export default function NotFound() {
  return (
    <div className="min-h-screen flex flex-col bg-[#050D12] text-[#E7EEF3]">
      <SiteHeader />

      <main className="flex-1 flex items-center justify-center px-4 sm:px-6 lg:px-8 py-16 sm:py-24">
        <div className="max-w-2xl w-full text-center space-y-8">
          
          {/* Status Indicator */}
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-rose-500/10 border border-rose-500/30 text-rose-400 font-mono text-xs tracking-wider uppercase">
            <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping" />
            <span>HTTP Status 404 • Resource Not Found</span>
          </div>

          {/* Heading and Copy */}
          <div className="space-y-3">
            <h1 className="font-display font-extrabold text-4xl sm:text-6xl tracking-tight text-white">
              Lost in the digital space?
            </h1>
            <p className="text-base sm:text-lg text-[#94A3B8] max-w-lg mx-auto leading-relaxed">
              The page you are looking for doesn&apos;t exist, may have been relocated, or is no longer accessible.
            </p>
          </div>

          {/* Navigation Action Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 max-w-xl mx-auto pt-4">
            <Link
              href="/"
              className="flex flex-col items-center justify-center p-4 rounded-xl bg-[#121B22] border border-[#253540] hover:border-[#F59E0B] hover:bg-[#18232c] text-white transition-all group"
            >
              <Home className="w-5 h-5 text-[#F59E0B] mb-2 group-hover:scale-110 transition-transform" />
              <span className="font-bold text-sm">Return Home</span>
              <span className="text-[11px] text-[#94A3B8] mt-1">National Landing</span>
            </Link>

            <Link
              href="/personal"
              className="flex flex-col items-center justify-center p-4 rounded-xl bg-[#121B22] border border-[#253540] hover:border-[#F59E0B] hover:bg-[#18232c] text-white transition-all group"
            >
              <Shield className="w-5 h-5 text-emerald-400 mb-2 group-hover:scale-110 transition-transform" />
              <span className="font-bold text-sm">Personal Shield</span>
              <span className="text-[11px] text-[#94A3B8] mt-1">Citizen Protection</span>
            </Link>

            <Link
              href="/business"
              className="flex flex-col items-center justify-center p-4 rounded-xl bg-[#121B22] border border-[#253540] hover:border-[#F59E0B] hover:bg-[#18232c] text-white transition-all group"
            >
              <Building2 className="w-5 h-5 text-sky-400 mb-2 group-hover:scale-110 transition-transform" />
              <span className="font-bold text-sm">Business Console</span>
              <span className="text-[11px] text-[#94A3B8] mt-1">API & Threat Feed</span>
            </Link>
          </div>

          {/* Secondary Assist */}
          <div className="pt-6 border-t border-[#253540]/40 flex flex-col sm:flex-row items-center justify-center gap-4 text-xs text-[#94A3B8]">
            <span>Need help tracking down an incident or feature?</span>
            <Link
              href="/contact"
              className="inline-flex items-center gap-1 text-[#F59E0B] hover:underline font-semibold"
            >
              <span>Contact Support</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
            <span className="hidden sm:inline">•</span>
            <Link
              href="/faq"
              className="text-[#CBD5E1] hover:underline"
            >
              Browse FAQs
            </Link>
          </div>

        </div>
      </main>

      <SiteFooter />
    </div>
  );
}
