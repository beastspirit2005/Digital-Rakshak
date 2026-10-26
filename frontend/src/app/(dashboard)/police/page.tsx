"use client";

import React from "react";
import Link from "next/link";
import {
  Siren,
  MapPin,
  FileText,
  CreditCard,
  Map,
  Network,
  Bot,
  LifeBuoy,
  ShieldAlert,
  ArrowRight,
  Radio,
  Flame,
  ShieldCheck,
  Building
} from "lucide-react";
import { useAuthStore } from "@/lib/auth-store";

export default function PoliceCommandDashboard() {
  const { user } = useAuthStore();

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-12 font-sans">
      {/* Hero Banner */}
      <div className="relative overflow-hidden rounded-3xl p-6 sm:p-10 border border-white/10 bg-gradient-to-br from-slate-900 via-[#0d1527] to-[#0a101d] shadow-2xl text-white">
        <div className="absolute top-0 right-0 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 max-w-2xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/20 border border-cyan-500/30 text-cyan-300 text-xs font-bold uppercase tracking-wider mb-4">
            <Radio className="w-3.5 h-3.5 animate-pulse text-cyan-400" />
            <span>Digital Rakshak Law Enforcement Portal</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-black tracking-tight">
            Law Enforcement Command Center
          </h1>
          <p className="text-slate-300 text-sm sm:text-base mt-2 leading-relaxed">
            Welcome, Officer {user?.full_name || "Investigator"}. Coordinate localized victim response, triage golden-hour cyber incidents, analyze threat graphs, and maintain immutable chain-of-custody.
          </p>

          <div className="flex flex-wrap items-center gap-3 mt-6">
            <Link
              href="/police/victims-map"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl font-bold text-sm bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-slate-950 transition-all shadow-lg active:scale-95"
            >
              <MapPin className="w-4 h-4" />
              <span>Launch Victims Proximity Radar</span>
              <ArrowRight className="w-4 h-4" />
            </Link>

            <Link
              href="/workbench/reports"
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl font-semibold text-sm bg-slate-800/80 hover:bg-slate-700/80 border border-white/10 text-slate-200 transition-all"
            >
              <FileText className="w-4 h-4 text-amber-400" />
              <span>Open Case Workbench</span>
            </Link>
          </div>
        </div>
      </div>

      {/* Primary Action Modules Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {/* Module 1: Victims Proximity Map */}
        <Link
          href="/police/victims-map"
          className="group p-6 rounded-2xl bg-surface-2 hover:bg-surface-3 border border-border transition-all duration-200 hover:-translate-y-1 hover:shadow-xl flex flex-col justify-between"
        >
          <div>
            <div className="w-12 h-12 rounded-2xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
              <MapPin className="w-6 h-6" />
            </div>
            <div className="flex items-center gap-2 mb-1">
              <h3 className="font-bold text-lg text-ink">Victims Proximity Map</h3>
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-300">
                NEW
              </span>
            </div>
            <p className="text-xs text-ink-3 leading-relaxed">
              Interactive MapLibre GL radar scanning citizen distress requests within 10–100km of your station with ~300m differential privacy protection.
            </p>
          </div>
          <div className="mt-5 pt-3 border-t border-border flex items-center justify-between text-xs font-semibold text-accent-text">
            <span>Explore Local Incidents</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </div>
        </Link>

        {/* Module 2: Investigation Workbench */}
        <Link
          href="/workbench/reports"
          className="group p-6 rounded-2xl bg-surface-2 hover:bg-surface-3 border border-border transition-all duration-200 hover:-translate-y-1 hover:shadow-xl flex flex-col justify-between"
        >
          <div>
            <div className="w-12 h-12 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-400 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
              <FileText className="w-6 h-6" />
            </div>
            <div className="flex items-center gap-2 mb-1">
              <h3 className="font-bold text-lg text-ink">Investigation Workbench</h3>
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300">
                CORE
              </span>
            </div>
            <p className="text-xs text-ink-3 leading-relaxed">
              Assigned case register, evidence analysis, zero-trust integrity verification (ZTIVF), and direct monitored investigator chat.
            </p>
          </div>
          <div className="mt-5 pt-3 border-t border-border flex items-center justify-between text-xs font-semibold text-accent-text">
            <span>Access Case Files</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </div>
        </Link>

        {/* Module 3: Fraud Intelligence & Mule Accounts */}
        <Link
          href="/banker/transactions"
          className="group p-6 rounded-2xl bg-surface-2 hover:bg-surface-3 border border-border transition-all duration-200 hover:-translate-y-1 hover:shadow-xl flex flex-col justify-between"
        >
          <div>
            <div className="w-12 h-12 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
              <CreditCard className="w-6 h-6" />
            </div>
            <div className="flex items-center gap-2 mb-1">
              <h3 className="font-bold text-lg text-ink">Fraud Intelligence & Mules</h3>
              <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-300">
                LE COMM
              </span>
            </div>
            <p className="text-xs text-ink-3 leading-relaxed">
              Trace suspicious bank transfers, frozen mule accounts, and coordinate freeze holds with nodal banking desk officers.
            </p>
          </div>
          <div className="mt-5 pt-3 border-t border-border flex items-center justify-between text-xs font-semibold text-accent-text">
            <span>Review Mules & Transactions</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </div>
        </Link>

        {/* Module 4: Spatial Scam Heatmap */}
        <Link
          href="/workbench/map"
          className="group p-6 rounded-2xl bg-surface-2 hover:bg-surface-3 border border-border transition-all duration-200 hover:-translate-y-1 hover:shadow-xl flex flex-col justify-between"
        >
          <div>
            <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
              <Map className="w-6 h-6" />
            </div>
            <h3 className="font-bold text-lg text-ink mb-1">National Heatmap</h3>
            <p className="text-xs text-ink-3 leading-relaxed">
              Macro spatial density analysis displaying high-risk scam corridors, impersonation hotspots, and jurisdictional cross-overs across India.
            </p>
          </div>
          <div className="mt-5 pt-3 border-t border-border flex items-center justify-between text-xs font-semibold text-accent-text">
            <span>View Heatmap</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </div>
        </Link>

        {/* Module 5: Graph Explorer */}
        <Link
          href="/workbench/graph"
          className="group p-6 rounded-2xl bg-surface-2 hover:bg-surface-3 border border-border transition-all duration-200 hover:-translate-y-1 hover:shadow-xl flex flex-col justify-between"
        >
          <div>
            <div className="w-12 h-12 rounded-2xl bg-purple-500/10 border border-purple-500/20 text-purple-400 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
              <Network className="w-6 h-6" />
            </div>
            <h3 className="font-bold text-lg text-ink mb-1">Graph Link Explorer</h3>
            <p className="text-xs text-ink-3 leading-relaxed">
              Uncover criminal syndicate networks by connecting shared phone numbers, beneficiary UPI IDs, and domain registries across multiple cases.
            </p>
          </div>
          <div className="mt-5 pt-3 border-t border-border flex items-center justify-between text-xs font-semibold text-accent-text">
            <span>Explore Syndicate Graph</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </div>
        </Link>

        {/* Module 6: AI Investigation Co-Pilot */}
        <Link
          href="/copilot"
          className="group p-6 rounded-2xl bg-surface-2 hover:bg-surface-3 border border-border transition-all duration-200 hover:-translate-y-1 hover:shadow-xl flex flex-col justify-between"
        >
          <div>
            <div className="w-12 h-12 rounded-2xl bg-blue-500/10 border border-blue-500/20 text-blue-400 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
              <Bot className="w-6 h-6" />
            </div>
            <h3 className="font-bold text-lg text-ink mb-1">Investigative Co-Pilot</h3>
            <p className="text-xs text-ink-3 leading-relaxed">
              AI-assisted legal framing under Bharatiya Nyaya Sanhita (BNS) & IT Act 2000, draft FIR generation, and evidence correlation.
            </p>
          </div>
          <div className="mt-5 pt-3 border-t border-border flex items-center justify-between text-xs font-semibold text-accent-text">
            <span>Consult Co-Pilot</span>
            <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
          </div>
        </Link>
      </div>
    </div>
  );
}
