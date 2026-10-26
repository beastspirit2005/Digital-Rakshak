"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import {
  PhoneCall,
  ExternalLink,
  MapPin,
  Lock,
  Sparkles,
  Search,
  Navigation,
  Building,
  CheckCircle2,
  FileText,
  ArrowRight,
  Compass,
  X
} from "lucide-react";
import { useAuthStore } from "@/lib/auth-store";
import { BrandLogo } from "@/components/brand-logo";

interface OfficialLocationItem {
  id: string;
  name: string;
  jurisdiction_level: string;
  state: string;
  district: string;
  city?: string;
  pincode?: string;
  address: string;
  latitude: number;
  longitude: number;
  helpline_number?: string;
  landline_number?: string;
  official_email?: string;
  nodal_officer_designation?: string;
  source_url: string;
  source_authority: string;
  verification_status: string;
  distance_km?: number;
}

const PREVIEW_LOCATIONS = [
  {
    name: "Cyber Crime Police Station, CID Headquarters",
    state: "Karnataka",
    city: "Bengaluru",
    district: "Bengaluru Urban",
    jurisdiction_level: "state",
    landline: "080-22094498",
    authority: "Karnataka State Police / CID",
  },
  {
    name: "IFSO (Intelligence Fusion & Strategic Operations), Special Cell",
    state: "Delhi",
    city: "New Delhi",
    district: "South West Delhi",
    jurisdiction_level: "state",
    landline: "011-20892633",
    authority: "Delhi Police, MHA",
  },
  {
    name: "Maharashtra State Cyber Police Headquarters",
    state: "Maharashtra",
    city: "Mumbai",
    district: "Mumbai City",
    jurisdiction_level: "state",
    landline: "022-22160080",
    authority: "Maharashtra State Cyber Crime Branch",
  },
];

export default function CyberCellLocatorPage() {
  const { user, token, isHydrated, hydrate } = useAuthStore();
  const [mounted, setMounted] = useState(false);
  const [locations, setLocations] = useState<OfficialLocationItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedState, setSelectedState] = useState<string>("ALL");
  const [checklistOpen, setChecklistOpen] = useState(false);
  const [isProUser, setIsProUser] = useState(false);

  const fetchLocations = useCallback(async (lat?: number, lng?: number) => {
    setLoading(true);
    setError(null);
    try {
      let url = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/official-locations`;
      const params = new URLSearchParams();
      if (lat !== undefined && lng !== undefined) {
        params.append("lat", lat.toString());
        params.append("lng", lng.toString());
        params.append("radius_km", "150");
      }
      if (selectedState !== "ALL") {
        params.append("state", selectedState);
      }
      if (params.toString()) {
        url += `?${params.toString()}`;
      }

      const res = await fetch(url, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });

      if (res.status === 402) {
        setIsProUser(false);
        return;
      }

      if (!res.ok) {
        throw new Error("Failed to load verified cyber police stations.");
      }

      const data = await res.json();
      setLocations(data.locations || []);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to retrieve directory.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [token, selectedState]);

  useEffect(() => {
    setMounted(true);
    if (!isHydrated) {
      hydrate();
    }
  }, [hydrate, isHydrated]);

  useEffect(() => {
    if (!mounted) return;
    const isPro = Boolean(
      user &&
      (["admin", "police", "cyber_cell", "banker", "bank_employee"].includes(user.role) ||
        user.b2c_plan_code === "b2c_pro" ||
        user.is_pro === true)
    );
    setIsProUser(isPro);

    if (isPro) {
      fetchLocations();
    }
  }, [mounted, user, fetchLocations]);

  const handleFindNearMe = () => {
    if (!navigator.geolocation) {
      alert("Geolocation is not supported by your browser.");
      return;
    }
    setLoading(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude, longitude } = pos.coords;
        fetchLocations(latitude, longitude);
      },
      (err) => {
        setLoading(false);
        alert(`Location access denied or unavailable: ${err.message}`);
      },
      { timeout: 10000 }
    );
  };

  const filteredLocations = locations.filter((loc) => {
    const q = searchQuery.toLowerCase();
    const matchesSearch =
      loc.name.toLowerCase().includes(q) ||
      loc.district.toLowerCase().includes(q) ||
      loc.state.toLowerCase().includes(q) ||
      (loc.city && loc.city.toLowerCase().includes(q)) ||
      (loc.pincode && loc.pincode.includes(q));

    const matchesState = selectedState === "ALL" || loc.state === selectedState;
    return matchesSearch && matchesState;
  });

  const availableStates = ["ALL", "Karnataka", "Delhi", "Maharashtra", "Telangana", "Tamil Nadu", "Uttar Pradesh", "West Bengal"];

  if (!mounted) {
    return (
      <div className="min-h-screen bg-[#070b12] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#070b12] text-[#e2e8f0] pb-24">
      {/* 1. Sovereign Public Safety Lifeline Banner (ALWAYS FREE FOR ALL CITIZENS) */}
      <div className="bg-gradient-to-r from-red-950/80 via-[#13111c] to-amber-950/60 border-b border-red-500/30 sticky top-16 z-40 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex flex-wrap items-center justify-between gap-3 text-xs sm:text-sm">
          <div className="flex items-center gap-2.5">
            <span className="flex h-2.5 w-2.5 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-red-500" />
            </span>
            <span className="font-semibold text-red-200 uppercase tracking-wider">
              Emergency Financial Cybercrime Lifeline:
            </span>
            <span className="text-gray-300 hidden md:inline">
              Within 2 hours of UPI/Bank fraud, dial 1930 to freeze stolen funds.
            </span>
          </div>

          <div className="flex items-center gap-2">
            <a
              href="tel:1930"
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md bg-red-600 hover:bg-red-500 text-white font-bold transition shadow-sm"
            >
              <PhoneCall className="w-3.5 h-3.5" />
              Dial 1930
            </a>
            <a
              href="https://cybercrime.gov.in"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md bg-white/10 hover:bg-white/15 text-gray-200 transition border border-white/10"
            >
              cybercrime.gov.in
              <ExternalLink className="w-3 h-3 text-gray-400" />
            </a>
          </div>
        </div>
      </div>

      {/* 2. Hero Section */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-10 pb-8">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-6 pb-6 border-b border-white/10">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs font-semibold uppercase tracking-wider mb-3">
              <BrandLogo variant="shield" className="w-4 h-4" />
              Investigator Connect • Directory Service
            </div>
            <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
              Official Cyber Police Station & Cell Locator
            </h1>
            <p className="mt-2 text-sm sm:text-base text-gray-400 max-w-2xl">
              Authoritative directory of state Cyber Police Stations, CID divisions, and jurisdictional cyber crime cells. Verified against state police gazettes and MHA directories.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setChecklistOpen(true)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-gray-200 border border-white/10 text-xs font-semibold transition"
            >
              <FileText className="w-4 h-4 text-amber-400" />
              What to Bring to Station
            </button>
            {isProUser && (
              <button
                onClick={handleFindNearMe}
                disabled={loading}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-amber-500 hover:bg-amber-400 text-black font-semibold text-xs transition shadow-lg shadow-amber-500/20"
              >
                <Navigation className="w-4 h-4" />
                Find Near Me
              </button>
            )}
          </div>
        </div>

        {/* 3. Pro Preview Gate (If not subscribed to Pro) */}
        {!isProUser && (
          <div className="mt-10">
            {/* Upgrade Banner */}
            <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[#121829] via-[#0f1422] to-[#181d33] border border-amber-500/30 p-6 sm:p-10 mb-10 shadow-2xl">
              <div className="absolute top-0 right-0 translate-x-8 -translate-y-8 w-64 h-64 bg-amber-500/10 rounded-full blur-3xl pointer-events-none" />
              <div className="relative z-10 flex flex-col md:flex-row items-center justify-between gap-8">
                <div className="space-y-3">
                  <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-500/15 border border-amber-500/40 text-amber-300 text-xs font-bold tracking-wide">
                    <Sparkles className="w-3.5 h-3.5 text-amber-400" />
                    DIGITAL RAKSHAK PRO EXCLUSIVE (₹149 / MONTH)
                  </div>
                  <h2 className="text-2xl sm:text-3xl font-extrabold text-white">
                    Unlock Verified State Cyber Cell Direct Contacts
                  </h2>
                  <p className="text-sm text-gray-300 max-w-xl leading-relaxed">
                    Gain immediate access to verified station landlines, state nodal officer designations, physical walk-in procedures, and automated GPS proximity routing.
                  </p>
                  <div className="flex flex-wrap gap-4 pt-2 text-xs text-gray-300">
                    <span className="flex items-center gap-1.5">
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      Direct Station Landlines & Helplines
                    </span>
                    <span className="flex items-center gap-1.5">
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      Nodal Officer Information
                    </span>
                    <span className="flex items-center gap-1.5">
                      <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                      One-Click Maps Turn-by-Turn Routing
                    </span>
                  </div>
                </div>

                <div className="flex flex-col items-center gap-3 w-full sm:w-auto">
                  <Link
                    href="/personal"
                    className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-6 py-3.5 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-black font-extrabold text-sm transition-all shadow-xl shadow-amber-500/25 hover:scale-[1.02]"
                  >
                    <Lock className="w-4 h-4" />
                    Upgrade to Pro — ₹149/mo
                    <ArrowRight className="w-4 h-4 ml-1" />
                  </Link>
                  <span className="text-[11px] text-gray-400">
                    Institutional users (Police, Bankers, Admins) log in for complimentary access.
                  </span>
                </div>
              </div>
            </div>

            {/* Blurred Preview Grid */}
            <div className="relative">
              <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-[#070b12]/60 backdrop-blur-[6px] rounded-2xl p-6 text-center">
                <div className="w-14 h-14 rounded-2xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center mb-4">
                  <Lock className="w-7 h-7 text-amber-400" />
                </div>
                <h3 className="text-xl font-bold text-white mb-2">
                  Full Directory Hidden Behind Pro Gate
                </h3>
                <p className="text-xs sm:text-sm text-gray-300 max-w-md mb-5">
                  Over 75+ state police cyber stations and jurisdictional divisions cataloged with official government verification records.
                </p>
                <Link
                  href="/personal"
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-black font-bold text-xs transition"
                >
                  Unlock Access Now
                </Link>
              </div>

              {/* Sample Preview Cards (Blurred Background) */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 filter blur-sm pointer-events-none select-none opacity-50">
                {PREVIEW_LOCATIONS.map((loc, idx) => (
                  <div key={idx} className="rounded-xl border border-white/10 bg-[#0e1320] p-6 space-y-4">
                    <div className="flex items-start justify-between">
                      <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300">
                        {loc.jurisdiction_level} Cyber Police
                      </span>
                      <span className="text-xs text-gray-400">{loc.state}</span>
                    </div>
                    <h4 className="font-bold text-white text-base">{loc.name}</h4>
                    <p className="text-xs text-gray-400">Carlton House, Palace Road, {loc.city}</p>
                    <div className="pt-2 border-t border-white/5 text-xs text-amber-400 font-mono">
                      Phone: {loc.landline}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* 4. Pro Directory View (Active Pro / Institutional User) */}
        {isProUser && (
          <div className="mt-8 space-y-6">
            {/* Search & State Filter Bar */}
            <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
              <div className="md:col-span-8 relative">
                <Search className="w-4 h-4 text-gray-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Search by Station Name, District, City, or Pincode..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2.5 rounded-lg bg-[#0e1320] border border-white/10 text-white placeholder-gray-500 text-sm focus:outline-none focus:border-amber-500 transition"
                />
              </div>

              <div className="md:col-span-4">
                <select
                  value={selectedState}
                  onChange={(e) => setSelectedState(e.target.value)}
                  className="w-full px-3 py-2.5 rounded-lg bg-[#0e1320] border border-white/10 text-white text-sm focus:outline-none focus:border-amber-500 transition"
                >
                  {availableStates.map((st) => (
                    <option key={st} value={st}>
                      {st === "ALL" ? "All States / Territories" : st}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Error or Loading state */}
            {loading && (
              <div className="py-16 text-center text-gray-400">
                <div className="w-8 h-8 border-2 border-amber-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
                <p className="text-xs">Querying authoritative police station database...</p>
              </div>
            )}

            {error && (
              <div className="p-4 rounded-xl bg-red-950/40 border border-red-500/30 text-red-200 text-xs">
                {error}
              </div>
            )}

            {/* Station List */}
            {!loading && filteredLocations.length === 0 && (
              <div className="py-16 text-center text-gray-400 rounded-xl bg-[#0e1320] border border-white/5">
                <Building className="w-10 h-10 text-gray-600 mx-auto mb-3" />
                <p className="text-sm font-semibold text-gray-300">No stations found matching criteria.</p>
                <p className="text-xs text-gray-500 mt-1">Try clearing filters or switching states.</p>
              </div>
            )}

            {!loading && filteredLocations.length > 0 && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {filteredLocations.map((loc) => (
                  <div
                    key={loc.id}
                    className="rounded-xl border border-white/10 bg-gradient-to-br from-[#0e1320] to-[#0a0e18] p-5 sm:p-6 space-y-4 hover:border-amber-500/30 transition shadow-lg"
                  >
                    {/* Header: Badges & Distance */}
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider bg-amber-500/15 text-amber-300 border border-amber-500/30">
                          {loc.jurisdiction_level} level
                        </span>
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
                          <CheckCircle2 className="w-3 h-3" />
                          Verified Official Listing
                        </span>
                      </div>
                      {loc.distance_km !== undefined && (
                        <span className="text-xs font-mono text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                          {loc.distance_km} km away
                        </span>
                      )}
                    </div>

                    {/* Station Name & Physical Address */}
                    <div>
                      <h3 className="font-bold text-white text-base leading-snug">{loc.name}</h3>
                      <p className="text-xs text-gray-400 mt-1 flex items-start gap-1.5">
                        <MapPin className="w-3.5 h-3.5 text-gray-500 shrink-0 mt-0.5" />
                        <span>{loc.address}</span>
                      </p>
                    </div>

                    {/* Officer & Contacts Grid */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs pt-2 border-t border-white/5">
                      {loc.nodal_officer_designation && (
                        <div>
                          <span className="text-[10px] uppercase font-bold text-gray-500 block">Nodal Officer</span>
                          <span className="text-gray-300 text-[11px]">{loc.nodal_officer_designation}</span>
                        </div>
                      )}
                      {loc.landline_number && (
                        <div>
                          <span className="text-[10px] uppercase font-bold text-gray-500 block">Landline</span>
                          <a href={`tel:${loc.landline_number}`} className="text-amber-400 hover:underline font-mono">
                            {loc.landline_number}
                          </a>
                        </div>
                      )}
                      {loc.official_email && (
                        <div className="sm:col-span-2">
                          <span className="text-[10px] uppercase font-bold text-gray-500 block">Official Email</span>
                          <span className="text-gray-300 font-mono text-[11px]">{loc.official_email}</span>
                        </div>
                      )}
                    </div>

                    {/* Footer Actions & Source Link */}
                    <div className="pt-3 border-t border-white/5 flex flex-wrap items-center justify-between gap-3 text-xs">
                      <a
                        href={loc.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[11px] text-gray-400 hover:text-gray-200 inline-flex items-center gap-1"
                      >
                        Source: {loc.source_authority}
                        <ExternalLink className="w-3 h-3 text-gray-500" />
                      </a>

                      <a
                        href={`https://www.google.com/maps/search/?api=1&query=${loc.latitude},${loc.longitude}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 font-semibold transition"
                      >
                        <Compass className="w-3.5 h-3.5" />
                        Get Directions
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* 5. Station Walk-In Checklist Modal */}
      {checklistOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
          <div className="bg-[#0e1320] border border-white/10 rounded-2xl max-w-lg w-full p-6 space-y-4 shadow-2xl relative">
            <button
              onClick={() => setChecklistOpen(false)}
              className="absolute top-4 right-4 text-gray-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-2.5">
              <div className="w-10 h-10 rounded-xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center">
                <FileText className="w-5 h-5 text-amber-400" />
              </div>
              <div>
                <h3 className="text-base font-bold text-white">Police Station Walk-In Checklist</h3>
                <p className="text-xs text-gray-400">Required evidence to file an FIR in person</p>
              </div>
            </div>

            <div className="space-y-3 text-xs text-gray-300 pt-2">
              <div className="p-3 rounded-lg bg-white/5 border border-white/5 flex items-start gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <strong className="text-white block">Digital Rakshak FIR Dossier (Printed)</strong>
                  Generate and download your A4 Incident Dossier PDF from your case dashboard with Section 63 BSA certificate.
                </div>
              </div>

              <div className="p-3 rounded-lg bg-white/5 border border-white/5 flex items-start gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <strong className="text-white block">Bank Account Statement</strong>
                  Stamped bank statement of the past 3 months highlighting the debited fraudulent transactions.
                </div>
              </div>

              <div className="p-3 rounded-lg bg-white/5 border border-white/5 flex items-start gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <strong className="text-white block">Transaction Reference / UTR Numbers</strong>
                  12-digit UPI reference numbers or IMPS/NEFT UTR numbers for every transfer made.
                </div>
              </div>

              <div className="p-3 rounded-lg bg-white/5 border border-white/5 flex items-start gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <strong className="text-white block">Screenshots & Audio/Video Call Logs</strong>
                  Color printouts of chats, extortion threats, video call IDs (Skype/WhatsApp), or fraudulent payment screens.
                </div>
              </div>

              <div className="p-3 rounded-lg bg-white/5 border border-white/5 flex items-start gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                <div>
                  <strong className="text-white block">Government Photo Identity</strong>
                  Original and photocopy of Aadhaar Card, PAN Card, or Voter ID.
                </div>
              </div>
            </div>

            <div className="pt-2">
              <button
                onClick={() => setChecklistOpen(false)}
                className="w-full py-2.5 rounded-lg bg-white/10 hover:bg-white/15 text-white font-semibold text-xs transition"
              >
                Understood & Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
