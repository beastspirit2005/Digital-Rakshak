"use client";

import React, { useState, useEffect, useCallback, useMemo } from "react";
import dynamic from "next/dynamic";
import { useAuthStore } from "@/lib/auth-store";
import { api, formatApiError } from "@/lib/api";
import axios from "axios";
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  Radio,
  MapPin,
  Compass,
  Filter,
  Search,
  CheckCircle2,
  RefreshCw,
  Lock,
  ArrowRight,
  Loader2,
  Building,
  Flame,
  Layers,
  ChevronRight,
  Info
} from "lucide-react";
import { useToast } from "@/components/ui/toast";
import Link from "next/link";
import { VictimFeature } from "@/components/map/officer-victim-map";

// Dynamically import MapLibre map with SSR disabled to prevent hydration / canvas errors
const OfficerVictimMap = dynamic(
  () => import("@/components/map/officer-victim-map"),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-full min-h-[480px] rounded-2xl border border-white/10 bg-[#090d16] flex flex-col items-center justify-center p-8 space-y-4">
        <Loader2 className="w-8 h-8 text-cyan-400 animate-spin" />
        <p className="text-sm font-medium text-slate-300">
          Initializing Jurisdictional Spatial Grid & Differential Privacy Engine...
        </p>
      </div>
    ),
  }
);

interface StationPreset {
  id: string;
  name: string;
  city: string;
  lat: number;
  lng: number;
}

const STATION_PRESETS: StationPreset[] = [
  {
    id: "blr-hq",
    name: "Bengaluru Cyber Crime Police Station (CID HQ)",
    city: "Bengaluru, Karnataka",
    lat: 12.9818,
    lng: 77.5898,
  },
  {
    id: "delhi-cell",
    name: "Special Cell Cyber Police Station, Dwarka",
    city: "New Delhi",
    lat: 28.5921,
    lng: 77.0460,
  },
  {
    id: "mum-bkc",
    name: "Mumbai Cyber Police Station, Bandra Kurla Complex",
    city: "Mumbai, Maharashtra",
    lat: 19.0657,
    lng: 72.8687,
  },
  {
    id: "hyd-cell",
    name: "Cyberabad Cyber Crime Police Station, Gachibowli",
    city: "Hyderabad, Telangana",
    lat: 17.4401,
    lng: 78.3489,
  },
];

export default function PoliceVictimsMapPage() {
  const { token, user } = useAuthStore();
  const pushToast = useToast();

  const [selectedStation, setSelectedStation] = useState<StationPreset>(STATION_PRESETS[0]);
  const [radiusKm, setRadiusKm] = useState<number>(50);
  const [urgencyFilter, setUrgencyFilter] = useState<string>("all");
  const [isOngoingOnly, setIsOngoingOnly] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>("");

  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [claimingId, setClaimingId] = useState<string | null>(null);

  const [victims, setVictims] = useState<VictimFeature[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [mobileTab, setMobileTab] = useState<"map" | "list">("map");

  // Fetch nearby victims based on station coordinates and radius
  const fetchNearbyVictims = useCallback(
    async (isBackground = false) => {
      if (!isBackground) setLoading(true);
      else setRefreshing(true);

      try {
        const params = new URLSearchParams({
          lat: selectedStation.lat.toString(),
          lng: selectedStation.lng.toString(),
          radius_km: radiusKm.toString(),
        });

        if (urgencyFilter !== "all") {
          params.append("urgency", urgencyFilter);
        }
        if (isOngoingOnly) {
          params.append("is_ongoing_only", "true");
        }

        const headers: Record<string, string> = {};
        if (token) {
          headers["Authorization"] = `Bearer ${token}`;
        }

        const response = await axios.get(
          api(`/police/nearby-victims?${params.toString()}`),
          { headers, withCredentials: true }
        );

        const data = response.data;
        if (data && Array.isArray(data.features)) {
          setVictims(data.features);
        } else {
          setVictims([]);
        }
      } catch (err: any) {
        console.error("Failed to fetch nearby victims:", err);
        pushToast("danger", `Spatial query failed: ${formatApiError(err, "Could not load victim features.")}`);
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [selectedStation, radiusKm, urgencyFilter, isOngoingOnly, token, pushToast]
  );

  useEffect(() => {
    fetchNearbyVictims();
  }, [fetchNearbyVictims]);

  // Handle Station GPS Locate
  const handleUseCurrentGPS = () => {
    if (!navigator.geolocation) {
      pushToast("warning", "Your browser does not support Geolocation.");
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const userPreset: StationPreset = {
          id: "custom-gps",
          name: "Your Duty Field Location (GPS Anchor)",
          city: "Field Patrol Coordinates",
          lat: Number(pos.coords.latitude.toFixed(4)),
          lng: Number(pos.coords.longitude.toFixed(4)),
        };
        setSelectedStation(userPreset);
        pushToast("success", `Duty coordinates updated: Lat ${userPreset.lat}, Lng ${userPreset.lng}`);
      },
      (err) => {
        pushToast("info", "Location access denied. Using default station coordinates.");
      }
    );
  };

  // Claim / Undertake a case
  const handleClaimCase = async (victim: VictimFeature) => {
    const caseId = victim.properties.case_id;
    const caseNum = victim.properties.case_number || victim.properties.reference;
    setClaimingId(caseId);

    try {
      const headers: Record<string, string> = {};
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      await axios.post(
        api(`/cases/${caseNum}/undertake`),
        {},
        { headers, withCredentials: true }
      );

      pushToast("success", `Case Undertaken Successfully: ${victim.properties.reference} is now under your direct investigation. Exact coordinates unlocked.`);

      // Optimistically update victim feature
      setVictims((prev) =>
        prev.map((v) =>
          v.properties.case_id === caseId
            ? {
                ...v,
                properties: {
                  ...v.properties,
                  is_assigned_to_me: true,
                  is_exact_location: true,
                },
              }
            : v
        )
      );
    } catch (err: any) {
      console.error("Failed to undertake case:", err);
      pushToast("danger", `Failed to undertake case: ${formatApiError(err, "Please try again or check case permissions.")}`);
    } finally {
      setClaimingId(null);
    }
  };

  // Filtered victims by search query (reference, scam type, city)
  const filteredVictims = useMemo(() => {
    if (!searchQuery.trim()) return victims;
    const q = searchQuery.toLowerCase();
    return victims.filter(
      (v) =>
        v.properties.reference?.toLowerCase().includes(q) ||
        v.properties.incident_type?.toLowerCase().includes(q) ||
        v.properties.city?.toLowerCase().includes(q) ||
        v.properties.narrative?.toLowerCase().includes(q)
    );
  }, [victims, searchQuery]);

  // Aggregate Metrics
  const metrics = useMemo(() => {
    const total = victims.length;
    const critical = victims.filter(
      (v) => v.properties.urgency_level === "critical" || v.properties.is_ongoing_fraud
    ).length;
    const totalLoss = victims.reduce(
      (acc, v) => acc + (v.properties.estimated_loss_inr || 0),
      0
    );
    const assignedToMe = victims.filter((v) => v.properties.is_assigned_to_me).length;
    return { total, critical, totalLoss, assignedToMe };
  }, [victims]);

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto pb-12 font-sans">
      {/* Page Title & Tactical Breadcrumb */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-border">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-accent-text uppercase tracking-wider mb-1">
            <Radio className="w-4 h-4 text-rose-500 animate-pulse" />
            <span>Law Enforcement Proximity Radar & Tactical Command</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-ink">
            Victims Proximity & Jurisdictional Response Map
          </h1>
          <p className="text-sm text-ink-3 mt-1">
            Real-time geolocation intelligence connecting nearby citizens in distress with duty cyber cell investigators.
          </p>
        </div>

        {/* Refresh & Anchor Info */}
        <div className="flex items-center gap-3">
          <button
            onClick={() => fetchNearbyVictims(true)}
            disabled={refreshing || loading}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium border border-border bg-surface-2 hover:bg-surface-3 text-ink transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin text-accent-text" : ""}`} />
            <span>{refreshing ? "Refreshing..." : "Sync Radar"}</span>
          </button>

          <Link
            href="/workbench/reports"
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold bg-accent hover:bg-accent/90 text-white transition-colors shadow-sm"
          >
            <span>All Workbench Cases</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>

      {/* Differential Privacy Security Strip */}
      <div className="rounded-xl p-3.5 bg-gradient-to-r from-amber-500/10 via-sky-500/10 to-indigo-500/10 border border-amber-500/20 flex flex-col md:flex-row items-start md:items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-lg bg-amber-500/20 text-amber-400">
            <Lock className="w-4 h-4" />
          </div>
          <div>
            <span className="font-bold text-amber-300 mr-1.5">
              Differential Privacy Standard Active:
            </span>
            <span className="text-ink-2">
              Unassigned victim coordinates have ~300m randomized Gaussian jitter applied. Exact residence unlocks upon 1-click Case Undertaking.
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-400/20 text-amber-300 border border-amber-400/30">
            DP-300m Enabled
          </span>
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
            BSA-2023 Compliant
          </span>
        </div>
      </div>

      {/* Quick Tactical Metrics Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <div className="p-4 rounded-xl bg-surface-2 border border-border shadow-sm">
          <div className="flex items-center justify-between text-xs text-ink-3 mb-1">
            <span>Nearby Distress Calls</span>
            <Radio className="w-4 h-4 text-sky-400" />
          </div>
          <div className="text-2xl font-black text-ink">{metrics.total}</div>
          <div className="text-[11px] text-ink-3 mt-1">Within {radiusKm}km radius ring</div>
        </div>

        <div className="p-4 rounded-xl bg-surface-2 border border-border shadow-sm">
          <div className="flex items-center justify-between text-xs text-rose-400 mb-1">
            <span>Critical / Live Fraud</span>
            <Flame className="w-4 h-4 text-rose-500 animate-pulse" />
          </div>
          <div className="text-2xl font-black text-rose-400">{metrics.critical}</div>
          <div className="text-[11px] text-rose-400/80 mt-1">Golden Hour immediate intervention</div>
        </div>

        <div className="p-4 rounded-xl bg-surface-2 border border-border shadow-sm">
          <div className="flex items-center justify-between text-xs text-amber-400 mb-1">
            <span>Threat Financial Exposure</span>
            <AlertTriangle className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-black text-amber-300">
            ₹{metrics.totalLoss.toLocaleString("en-IN")}
          </div>
          <div className="text-[11px] text-ink-3 mt-1">Aggregate reported loss</div>
        </div>

        <div className="p-4 rounded-xl bg-surface-2 border border-border shadow-sm">
          <div className="flex items-center justify-between text-xs text-emerald-400 mb-1">
            <span>Assigned To You</span>
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-black text-emerald-400">{metrics.assignedToMe}</div>
          <div className="text-[11px] text-ink-3 mt-1">Active under your investigation</div>
        </div>
      </div>

      {/* Control Filter Bar */}
      <div className="p-4 rounded-2xl bg-surface-2 border border-border shadow-sm space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-3 sm:gap-4 items-center">
          {/* Station Preset Picker */}
          <div className="md:col-span-5 space-y-1">
            <label className="text-[11px] font-bold uppercase tracking-wider text-ink-3 flex items-center justify-between">
              <span>Jurisdictional Anchor Station</span>
              <button
                onClick={handleUseCurrentGPS}
                className="text-cyan-400 hover:text-cyan-300 lowercase text-[11px] flex items-center gap-1"
              >
                <Compass className="w-3 h-3" />
                <span>use my gps</span>
              </button>
            </label>
            <select
              value={selectedStation.id}
              onChange={(e) => {
                const found = STATION_PRESETS.find((s) => s.id === e.target.value);
                if (found) setSelectedStation(found);
              }}
              className="w-full px-3 py-2 rounded-xl text-xs bg-surface-1 border border-border text-ink focus:outline-none focus:ring-2 focus:ring-accent"
            >
              {STATION_PRESETS.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.city})
                </option>
              ))}
              {selectedStation.id === "custom-gps" && (
                <option value="custom-gps">Your Duty Field Location (GPS Anchor)</option>
              )}
            </select>
          </div>

          {/* Radar Radius Ring Selector */}
          <div className="md:col-span-3 space-y-1">
            <label className="text-[11px] font-bold uppercase tracking-wider text-ink-3">
              Radius: {radiusKm} km
            </label>
            <div className="grid grid-cols-4 gap-1">
              {[10, 25, 50, 100].map((r) => (
                <button
                  key={r}
                  onClick={() => setRadiusKm(r)}
                  className={`py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                    radiusKm === r
                      ? "bg-accent text-white shadow-sm"
                      : "bg-surface-1 hover:bg-surface-3 text-ink-2 border border-border"
                  }`}
                >
                  {r}km
                </button>
              ))}
            </div>
          </div>

          {/* Urgency Filter */}
          <div className="md:col-span-4 space-y-1">
            <label className="text-[11px] font-bold uppercase tracking-wider text-ink-3">
              Threat Urgency
            </label>
            <div className="grid grid-cols-4 gap-1">
              {[
                { id: "all", label: "All" },
                { id: "critical", label: "Critical" },
                { id: "high", label: "High" },
                { id: "standard", label: "Standard" },
              ].map((tier) => (
                <button
                  key={tier.id}
                  onClick={() => setUrgencyFilter(tier.id)}
                  className={`py-1.5 rounded-lg text-xs font-medium transition-colors ${
                    urgencyFilter === tier.id
                      ? "bg-accent text-white shadow-sm"
                      : "bg-surface-1 hover:bg-surface-3 text-ink-2 border border-border"
                  }`}
                >
                  {tier.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Secondary Search & Live Fraud Switch */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-3 border-t border-border/60">
          <div className="relative w-full sm:w-80">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-ink-3" />
            <input
              type="text"
              placeholder="Search reference, scam type, city..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 rounded-xl text-xs bg-surface-1 border border-border text-ink placeholder:text-ink-3 focus:outline-none focus:ring-1 focus:ring-accent"
            />
          </div>

          <label className="flex items-center gap-2 cursor-pointer text-xs font-medium text-ink self-end sm:self-auto">
            <input
              type="checkbox"
              checked={isOngoingOnly}
              onChange={(e) => setIsOngoingOnly(e.target.checked)}
              className="rounded border-border text-rose-500 focus:ring-rose-500 w-4 h-4 bg-surface-1"
            />
            <span className="flex items-center gap-1.5 text-rose-400 font-semibold">
              <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping" />
              Ongoing / Active Threats Only
            </span>
          </label>
        </div>
      </div>

      {/* Mobile Tab Toggle */}
      <div className="flex lg:hidden rounded-xl bg-surface-2 p-1 border border-border">
        <button
          onClick={() => setMobileTab("map")}
          className={`flex-1 py-2 rounded-lg text-xs font-bold transition-all ${
            mobileTab === "map" ? "bg-accent text-white shadow-sm" : "text-ink-2"
          }`}
        >
          Jurisdictional Map ({filteredVictims.length})
        </button>
        <button
          onClick={() => setMobileTab("list")}
          className={`flex-1 py-2 rounded-lg text-xs font-bold transition-all ${
            mobileTab === "list" ? "bg-accent text-white shadow-sm" : "text-ink-2"
          }`}
        >
          Priority Triage Queue ({filteredVictims.length})
        </button>
      </div>

      {/* Main Split-Screen Workspace (Desktop 50/50, Mobile Segmented) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left: MapLibre Tactical Radar (Sticky on Desktop) */}
        <div
          className={`lg:col-span-7 h-[580px] lg:h-[720px] lg:sticky lg:top-4 ${
            mobileTab === "list" ? "hidden lg:block" : "block"
          }`}
        >
          <OfficerVictimMap
            stationAnchor={{
              latitude: selectedStation.lat,
              longitude: selectedStation.lng,
              name: selectedStation.name,
            }}
            radiusKm={radiusKm}
            victims={filteredVictims}
            selectedCaseId={selectedCaseId}
            onSelectCase={(victim) =>
              setSelectedCaseId(victim ? victim.properties.case_id : null)
            }
            onClaimCase={handleClaimCase}
            claimingId={claimingId}
          />
        </div>

        {/* Right: Scrollable Tactical Triage Queue */}
        <div
          className={`lg:col-span-5 space-y-3 h-[580px] lg:h-[720px] overflow-y-auto pr-1 ${
            mobileTab === "map" ? "hidden lg:block" : "block"
          }`}
        >
          <div className="flex items-center justify-between px-1 text-xs text-ink-3">
            <span>
              Showing <strong className="text-ink">{filteredVictims.length}</strong> distress incidents
            </span>
            <span className="font-mono text-[11px]">Ranked by Threat Urgency</span>
          </div>

          {loading ? (
            <div className="p-12 text-center rounded-2xl bg-surface-2 border border-border space-y-3">
              <Loader2 className="w-6 h-6 text-cyan-400 animate-spin mx-auto" />
              <p className="text-xs text-ink-3">Triaging nearby jurisdiction calls...</p>
            </div>
          ) : filteredVictims.length === 0 ? (
            <div className="p-12 text-center rounded-2xl bg-surface-2 border border-border space-y-3">
              <ShieldCheck className="w-8 h-8 text-emerald-400 mx-auto" />
              <h3 className="font-bold text-sm text-ink">No Unhandled Incidents Nearby</h3>
              <p className="text-xs text-ink-3 max-w-xs mx-auto">
                No citizen assistance requests matching your current filters within {radiusKm}km of {selectedStation.name}.
              </p>
            </div>
          ) : (
            filteredVictims.map((v) => {
              const isSelected = selectedCaseId === v.properties.case_id;
              const isCritical =
                v.properties.urgency_level === "critical" || v.properties.is_ongoing_fraud;
              const isHigh = v.properties.urgency_level === "high";

              return (
                <div
                  key={v.properties.case_id}
                  onClick={() => setSelectedCaseId(v.properties.case_id)}
                  className={`p-4 rounded-2xl border transition-all cursor-pointer ${
                    isSelected
                      ? "bg-surface-3 border-accent ring-2 ring-accent/30 shadow-md"
                      : "bg-surface-2 hover:bg-surface-3/60 border-border"
                  }`}
                >
                  {/* Top Bar */}
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="font-mono text-xs font-bold text-sky-400">
                        {v.properties.reference}
                      </span>
                      <span
                        className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider ${
                          isCritical
                            ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                            : isHigh
                            ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                            : "bg-blue-500/20 text-blue-300 border border-blue-500/30"
                        }`}
                      >
                        {v.properties.urgency_level}
                      </span>
                      {v.properties.is_ongoing_fraud && (
                        <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-red-600/30 text-red-200 border border-red-500/40 animate-pulse">
                          LIVE FRAUD
                        </span>
                      )}
                    </div>
                    <div className="text-right">
                      <span className="text-xs font-bold text-emerald-400">
                        {v.properties.distance_km} km
                      </span>
                      <span className="text-[10px] text-ink-3 block">from station</span>
                    </div>
                  </div>

                  {/* Incident Title */}
                  <h4 className="font-semibold text-sm text-ink mb-1">
                    {v.properties.incident_type}
                  </h4>

                  {/* Loss and Location */}
                  <div className="flex items-center justify-between text-xs text-ink-2 bg-surface-1 px-2.5 py-1.5 rounded-lg border border-border/50 mb-2">
                    <span>
                      Exposure:{" "}
                      <strong className="text-amber-400">
                        ₹{Number(v.properties.estimated_loss_inr || 0).toLocaleString("en-IN")}
                      </strong>
                    </span>
                    <span className="text-ink-3">
                      {v.properties.city}, {v.properties.state}
                    </span>
                  </div>

                  {/* Narrative Statement */}
                  <p className="text-xs text-ink-2 italic line-clamp-2 mb-3">
                    &ldquo;{v.properties.narrative}&rdquo;
                  </p>

                  {/* Footer Action Buttons */}
                  <div className="flex items-center justify-between gap-2 pt-2 border-t border-border/40">
                    <span className="text-[10px] text-ink-3">
                      Status:{" "}
                      <strong className="text-ink uppercase font-mono">
                        {v.properties.status}
                      </strong>
                    </span>

                    {v.properties.is_assigned_to_me ? (
                      <Link
                        href="/workbench/reports"
                        className="inline-flex items-center gap-1 text-xs font-bold text-emerald-400 hover:text-emerald-300"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <span>Assigned to You</span>
                        <ArrowRight className="w-3.5 h-3.5" />
                      </Link>
                    ) : (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleClaimCase(v);
                        }}
                        disabled={claimingId === v.properties.case_id}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white transition-all shadow-sm active:scale-95 disabled:opacity-50"
                      >
                        {claimingId === v.properties.case_id ? (
                          <>
                            <Loader2 className="w-3 h-3 animate-spin" />
                            <span>Claiming...</span>
                          </>
                        ) : (
                          <>
                            <ShieldCheck className="w-3.5 h-3.5" />
                            <span>Claim Case</span>
                          </>
                        )}
                      </button>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
