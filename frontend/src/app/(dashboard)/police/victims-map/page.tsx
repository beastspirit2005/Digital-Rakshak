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
  Globe,
  UserCheck,
  Phone,
  Send,
  Users
} from "lucide-react";
import { useToast } from "@/components/ui/toast";
import Link from "next/link";
import { VictimFeature, OfficerFeature } from "@/components/map/officer-victim-map";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

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
    name: "Maharashtra Cyber Police Headquarters, Cuffe Parade",
    city: "Mumbai, Maharashtra",
    lat: 18.9174,
    lng: 72.8184,
  },
  {
    id: "hyd-cell",
    name: "TGCSB Cyber Security Bureau HQ, Saifabad",
    city: "Hyderabad, Telangana",
    lat: 17.4042,
    lng: 78.4682,
  },
];

const INDIAN_STATES = [
  "All India", "Andhra Pradesh", "Assam", "Bihar", "Chhattisgarh", "Delhi", "Gujarat", "Haryana",
  "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra",
  "Odisha", "Punjab", "Rajasthan", "Tamil Nadu", "Telangana", "Uttar Pradesh", "Uttarakhand", "West Bengal"
];

export default function PoliceVictimsMapPage() {
  const { token, user } = useAuthStore();
  const pushToast = useToast();

  const isAdmin = user?.role === "admin";

  // Tactical Scope & Filters
  const [isAllIndia, setIsAllIndia] = useState<boolean>(false);
  const [selectedStation, setSelectedStation] = useState<StationPreset>(STATION_PRESETS[0]);
  const [radiusKm, setRadiusKm] = useState<number>(50);
  const [selectedState, setSelectedState] = useState<string>("All India");
  const [assignmentStatus, setAssignmentStatus] = useState<string>("all");
  const [urgencyFilter, setUrgencyFilter] = useState<string>("all");
  const [isOngoingOnly, setIsOngoingOnly] = useState<boolean>(false);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [showOfficers, setShowOfficers] = useState<boolean>(true);
  const [isLivePatrol, setIsLivePatrol] = useState<boolean>(false);

  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [claimingId, setClaimingId] = useState<string | null>(null);
  const [assigningCaseId, setAssigningCaseId] = useState<string | null>(null);

  const [victims, setVictims] = useState<VictimFeature[]>([]);
  const [officers, setOfficers] = useState<OfficerFeature[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [mobileTab, setMobileTab] = useState<"map" | "list">("map");

  // Fetch nearby victims based on station coordinates, radius, or nationwide surveillance
  const fetchNearbyVictims = useCallback(
    async (isBackground = false) => {
      if (!isBackground) setLoading(true);
      else setRefreshing(true);

      try {
        const params = new URLSearchParams({
          lat: selectedStation.lat.toString(),
          lng: selectedStation.lng.toString(),
          radius_km: radiusKm.toString(),
          all_india: isAllIndia ? "true" : "false",
        });

        if (selectedState !== "All India") {
          params.append("state", selectedState);
        }
        if (assignmentStatus !== "all") {
          params.append("assignment_status", assignmentStatus);
        }
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

        // Parallel Fetch: Victims + Officers Roster
        const [victimRes, officerRes] = await Promise.all([
          axios.get(api(`/police/nearby-victims?${params.toString()}`), { headers, withCredentials: true }),
          axios.get(api(`/police/officers-and-stations?${params.toString()}`), { headers, withCredentials: true }).catch(() => ({ data: { officers: [], stations: [] } })),
        ]);

        const data = victimRes.data;
        if (data && Array.isArray(data.features)) {
          setVictims(data.features);
        } else {
          setVictims([]);
        }

        // Combine officers and stations for spatial layer
        const offData = officerRes.data;
        const combinedOfficers: OfficerFeature[] = [
          ...(offData.officers || []),
          ...(offData.stations || []),
        ];
        setOfficers(combinedOfficers);
      } catch (err: any) {
        console.error("Failed to fetch nearby victims:", err);
        pushToast("danger", `Spatial query failed: ${formatApiError(err, "Could not load victim features.")}`);
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [selectedStation, radiusKm, isAllIndia, selectedState, assignmentStatus, urgencyFilter, isOngoingOnly, token, pushToast]
  );

  useEffect(() => {
    fetchNearbyVictims();
  }, [fetchNearbyVictims]);

  // Handle Station GPS Locate ("Locate Near Me")
  const handleUseCurrentGPS = () => {
    if (!navigator.geolocation) {
      pushToast("warning", "Your browser does not support Geolocation.");
      return;
    }

    setLoading(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const userPreset: StationPreset = {
          id: "live-patrol-gps",
          name: "Your Duty Field Location (GPS Anchor)",
          city: "Live Field Patrol",
          lat: Number(pos.coords.latitude.toFixed(4)),
          lng: Number(pos.coords.longitude.toFixed(4)),
        };
        setSelectedStation(userPreset);
        setIsLivePatrol(true);
        setIsAllIndia(false);
        pushToast("success", `GPS Radar Activated: Lat ${userPreset.lat}, Lng ${userPreset.lng}`);
      },
      (err) => {
        setLoading(false);
        pushToast("info", "Location access denied. Using default jurisdictional coordinates.");
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  // Claim / Undertake a case (Police)
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
                  status: "assigned",
                  is_assigned_to_me: true,
                  is_exact_location: true,
                  assignment_source: "map_radar_claim",
                  is_claimed_recently: true,
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

  // Direct In-Map Case Assignment (Admin)
  const handleAssignCase = async (caseId: string, officerId: string) => {
    setAssigningCaseId(caseId);
    try {
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      await axios.post(
        api(`/admin/cases/${caseId}/assign`),
        { assignee_id: officerId, notes: "Direct assignment from Tactical Map" },
        { headers, withCredentials: true }
      );

      const targetOfficer = officers.find((o) => o.id === officerId);
      const officerName = targetOfficer ? targetOfficer.name : "Officer";

      // Optimistically update case
      setVictims((prev) =>
        prev.map((v) =>
          v.properties.case_id === caseId
            ? {
                ...v,
                properties: {
                  ...v.properties,
                  status: "assigned",
                  assigned_to: officerId,
                  assignee_name: officerName,
                  is_exact_location: true,
                },
              }
            : v
        )
      );

      // Increment officer workload
      setOfficers((prev) =>
        prev.map((o) =>
          o.id === officerId
            ? { ...o, active_cases_count: (o.active_cases_count || 0) + 1 }
            : o
        )
      );

      pushToast("success", `Case assigned directly to ${officerName}. Status updated to ASSIGNED.`);
    } catch (err: any) {
      console.error("Failed to assign case:", err);
      pushToast("danger", `Assignment failed: ${formatApiError(err, "Could not assign case.")}`);
    } finally {
      setAssigningCaseId(null);
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
        v.properties.narrative?.toLowerCase().includes(q) ||
        v.properties.assignee_name?.toLowerCase().includes(q)
    );
  }, [victims, searchQuery]);

  // Aggregate Metrics
  const metrics = useMemo(() => {
    const total = victims.length;
    const critical = victims.filter(
      (v) => v.properties.urgency_level === "critical" || v.properties.is_ongoing_fraud
    ).length;
    const totalLoss = victims.reduce(
      (acc, v) => acc + Number(v.properties.estimated_loss_inr || v.properties.estimated_amount || 0),
      0
    );
    const assigned = victims.filter((v) => v.properties.status === "assigned" || v.properties.assigned_to).length;
    return { total, critical, totalLoss, assigned };
  }, [victims]);

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto pb-12 font-sans">
      {/* Page Title & Tactical Action Bar */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 pb-4 border-b border-border">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold text-accent-text uppercase tracking-wider mb-1">
            <Radio className="w-4 h-4 text-rose-500 animate-pulse" />
            <span>Tactical Command Network & Proximity Radar</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-ink">
            {isAllIndia ? "All-India Tactical Surveillance & Assignment Grid" : "Victims Proximity & Jurisdictional Response Radar"}
          </h1>
          <p className="text-sm text-ink-3 mt-1">
            Real-time geospatial intelligence connecting reported incidents with duty cyber cells and active field investigators.
          </p>
        </div>

        {/* Action Controls: Locate Near Me + All-India Scope */}
        <div className="flex items-center gap-2 flex-wrap">
          <Button
            onClick={handleUseCurrentGPS}
            variant="secondary"
            className="inline-flex items-center gap-2 text-xs font-bold border-cyan-500/40 bg-cyan-500/10 text-cyan-300 hover:bg-cyan-500/20 shadow-sm"
          >
            <Compass className="w-4 h-4 text-cyan-400 animate-pulse" />
            <span>Scan Near My Location</span>
          </Button>

          {isAdmin && (
            <div className="inline-flex rounded-xl bg-surface-2 p-1 border border-border">
              <button
                onClick={() => setIsAllIndia(false)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  !isAllIndia ? "bg-surface text-ink shadow-sm" : "text-ink-2 hover:text-ink"
                }`}
              >
                Local Radar
              </button>
              <button
                onClick={() => setIsAllIndia(true)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all inline-flex items-center gap-1.5 ${
                  isAllIndia ? "bg-accent text-white shadow-sm" : "text-ink-2 hover:text-ink"
                }`}
              >
                <Globe className="w-3.5 h-3.5" />
                <span>All-India Grid</span>
              </button>
            </div>
          )}

          <button
            onClick={() => fetchNearbyVictims(true)}
            disabled={refreshing || loading}
            className="inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium border border-border bg-surface-2 hover:bg-surface-3 text-ink transition-colors disabled:opacity-50"
            title="Sync Radar"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin text-accent-text" : ""}`} />
            <span>{refreshing ? "Syncing..." : "Sync"}</span>
          </button>
        </div>
      </div>

      {/* Differential Privacy & Compliance Notice */}
      <div className="rounded-xl p-3 bg-gradient-to-r from-amber-500/10 via-sky-500/10 to-indigo-500/10 border border-amber-500/20 flex flex-col md:flex-row items-start md:items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-lg bg-amber-500/20 text-amber-400">
            <Lock className="w-4 h-4" />
          </div>
          <div>
            <span className="font-bold text-amber-300 mr-1.5">
              Differential Privacy Standard:
            </span>
            <span className="text-ink-2">
              Unassigned victim coordinates have ~300m deterministic differential privacy jitter applied. Exact coordinates unlock upon case undertaking or administrative assignment.
            </span>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-400/20 text-amber-300 border border-amber-400/30">
            DP-300m
          </span>
          <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
            DPDP & BSA Compliant
          </span>
        </div>
      </div>

      {/* Tactical Metrics Strip */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="p-4 rounded-xl bg-surface-2 border border-border shadow-sm min-w-0 overflow-hidden">
          <div className="flex items-center justify-between text-xs text-ink-3 mb-1">
            <span>Reported Incidents</span>
            <Radio className="w-4 h-4 text-sky-400" />
          </div>
          <div className="text-2xl font-black text-ink">{metrics.total}</div>
          <div className="text-[11px] text-ink-3 mt-1">
            {isAllIndia ? "Across all Indian states" : `Within ${radiusKm}km radar ring`}
          </div>
        </div>

        <div className="p-4 rounded-xl bg-surface-2 border border-border shadow-sm min-w-0 overflow-hidden">
          <div className="flex items-center justify-between text-xs text-rose-400 mb-1">
            <span>Critical Threats</span>
            <Flame className="w-4 h-4 text-rose-500 animate-pulse" />
          </div>
          <div className="text-2xl font-black text-rose-400">{metrics.critical}</div>
          <div className="text-[11px] text-rose-400/80 mt-1">Immediate intervention SLA</div>
        </div>

        <div className="p-4 rounded-xl bg-surface-2 border border-border shadow-sm min-w-0 overflow-hidden">
          <div className="flex items-center justify-between text-xs text-amber-400 mb-1">
            <span>Threat Exposure</span>
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
          </div>
          <div
            className="text-xl sm:text-2xl font-black text-amber-300 tracking-tight truncate"
            title={`₹${Math.round(metrics.totalLoss).toLocaleString("en-IN")}`}
          >
            ₹{Math.round(metrics.totalLoss).toLocaleString("en-IN")}
          </div>
          <div className="text-[11px] text-ink-3 mt-1 flex items-center justify-between gap-1 flex-wrap">
            <span>Reported loss in scope</span>
            {metrics.totalLoss >= 100000 && (
              <span className="font-mono text-amber-400/90 font-semibold text-[10px]">
                {metrics.totalLoss >= 10000000
                  ? `(₹${(metrics.totalLoss / 10000000).toFixed(2)} Cr)`
                  : `(₹${(metrics.totalLoss / 100000).toFixed(2)} L)`}
              </span>
            )}
          </div>
        </div>

        <div className="p-4 rounded-xl bg-surface-2 border border-border shadow-sm min-w-0 overflow-hidden">
          <div className="flex items-center justify-between text-xs text-emerald-400 mb-1">
            <span>Active Duty Units</span>
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-black text-emerald-400">{officers.length}</div>
          <div className="text-[11px] text-ink-3 mt-1">Officers & cyber stations plotted</div>
        </div>
      </div>

      {/* Multi-Criteria Filtering Toolbar */}
      <div className="p-4 rounded-2xl bg-surface-2 border border-border shadow-sm space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-12 gap-3 items-center">
          {/* Station / State Selector */}
          <div className="lg:col-span-4 space-y-1">
            <label className="text-[11px] font-bold uppercase tracking-wider text-ink-3 flex items-center justify-between">
              <span>{isAllIndia ? "State Filter" : "Anchor Station"}</span>
              {!isAllIndia && (
                <button
                  onClick={handleUseCurrentGPS}
                  className="text-cyan-400 hover:text-cyan-300 lowercase text-[11px] flex items-center gap-1"
                >
                  <Compass className="w-3 h-3" />
                  <span>gps</span>
                </button>
              )}
            </label>

            {isAllIndia ? (
              <select
                value={selectedState}
                onChange={(e) => setSelectedState(e.target.value)}
                className="w-full px-3 py-2 rounded-xl text-xs bg-surface-1 border border-border text-ink focus:outline-none focus:ring-2 focus:ring-accent"
              >
                {INDIAN_STATES.map((st) => (
                  <option key={st} value={st}>{st}</option>
                ))}
              </select>
            ) : (
              <select
                value={selectedStation.id}
                onChange={(e) => {
                  const found = STATION_PRESETS.find((s) => s.id === e.target.value);
                  if (found) {
                    setSelectedStation(found);
                    setIsLivePatrol(false);
                  }
                }}
                className="w-full px-3 py-2 rounded-xl text-xs bg-surface-1 border border-border text-ink focus:outline-none focus:ring-2 focus:ring-accent"
              >
                {STATION_PRESETS.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name} ({s.city})
                  </option>
                ))}
                {selectedStation.id === "live-patrol-gps" && (
                  <option value="live-patrol-gps">Your Duty Field Location (GPS Anchor)</option>
                )}
              </select>
            )}
          </div>

          {/* Radar Radius Ring Selector (Hidden in All-India mode) */}
          {!isAllIndia ? (
            <div className="lg:col-span-3 space-y-1">
              <label className="text-[11px] font-bold uppercase tracking-wider text-ink-3">
                Radius Ring: {radiusKm} km
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
          ) : (
            <div className="lg:col-span-3 space-y-1">
              <label className="text-[11px] font-bold uppercase tracking-wider text-ink-3">
                Assignment Filter
              </label>
              <select
                value={assignmentStatus}
                onChange={(e) => setAssignmentStatus(e.target.value)}
                className="w-full px-3 py-2 rounded-xl text-xs bg-surface-1 border border-border text-ink focus:outline-none focus:ring-2 focus:ring-accent"
              >
                <option value="all">All Cases</option>
                <option value="unassigned">Unassigned Only</option>
                <option value="assigned_to_me">Assigned to Me</option>
                <option value="assigned">All Assigned Cases</option>
              </select>
            </div>
          )}

          {/* Urgency Filter */}
          <div className="lg:col-span-3 space-y-1">
            <label className="text-[11px] font-bold uppercase tracking-wider text-ink-3">
              Urgency Tier
            </label>
            <div className="grid grid-cols-4 gap-1">
              {[
                { id: "all", label: "All" },
                { id: "critical", label: "Crit" },
                { id: "high", label: "High" },
                { id: "standard", label: "Std" },
              ].map((item) => (
                <button
                  key={item.id}
                  onClick={() => setUrgencyFilter(item.id)}
                  className={`py-1.5 rounded-lg text-xs font-semibold transition-colors ${
                    urgencyFilter === item.id
                      ? "bg-accent text-white shadow-sm"
                      : "bg-surface-1 hover:bg-surface-3 text-ink-2 border border-border"
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>

          {/* Layer & Ongoing Toggles */}
          <div className="lg:col-span-2 flex items-center justify-between sm:justify-end gap-3 pt-4 sm:pt-0">
            <label className="flex items-center gap-1.5 cursor-pointer text-xs font-semibold text-ink">
              <input
                type="checkbox"
                checked={showOfficers}
                onChange={(e) => setShowOfficers(e.target.checked)}
                className="w-4 h-4 accent-accent rounded"
              />
              <span>Units</span>
            </label>

            <label className="flex items-center gap-1.5 cursor-pointer text-xs font-semibold text-rose-400">
              <input
                type="checkbox"
                checked={isOngoingOnly}
                onChange={(e) => setIsOngoingOnly(e.target.checked)}
                className="w-4 h-4 accent-rose-500 rounded"
              />
              <span>Live Only</span>
            </label>
          </div>
        </div>

        {/* Keyword Search Input */}
        <div className="relative">
          <Search className="w-4 h-4 text-ink-3 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search cases by reference number, incident type, city, victim statement, or assigned officer..."
            className="w-full pl-9 pr-4 py-2 rounded-xl text-xs bg-surface-1 border border-border text-ink placeholder:text-ink-3 focus:outline-none focus:ring-2 focus:ring-accent"
          />
        </div>
      </div>

      {/* Mobile Map / List Toggle */}
      <div className="flex sm:hidden p-1 rounded-xl bg-surface-2 border border-border">
        <button
          onClick={() => setMobileTab("map")}
          className={`flex-1 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
            mobileTab === "map" ? "bg-accent text-white shadow-sm" : "text-ink-2"
          }`}
        >
          Tactical Map
        </button>
        <button
          onClick={() => setMobileTab("list")}
          className={`flex-1 py-1.5 rounded-lg text-xs font-semibold transition-colors ${
            mobileTab === "list" ? "bg-accent text-white shadow-sm" : "text-ink-2"
          }`}
        >
          Cases List ({filteredVictims.length})
        </button>
      </div>

      {/* Main Map + Sidebar Split Screen */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Map Canvas */}
        <div
          className={`lg:col-span-8 xl:col-span-9 h-[540px] sm:h-[620px] lg:h-[720px] w-full ${
            mobileTab === "list" ? "hidden sm:block" : "block"
          }`}
        >
          <OfficerVictimMap
            stationAnchor={{
              latitude: selectedStation.lat,
              longitude: selectedStation.lng,
              name: selectedStation.name,
            }}
            radiusKm={radiusKm}
            isAllIndia={isAllIndia}
            isLivePatrol={isLivePatrol}
            victims={filteredVictims}
            officers={officers}
            showOfficersLayer={showOfficers}
            selectedCaseId={selectedCaseId}
            onSelectCase={(victim) => setSelectedCaseId(victim?.properties.case_id || null)}
            onClaimCase={handleClaimCase}
            onAssignCase={isAdmin ? handleAssignCase : undefined}
            claimingId={claimingId}
            isAdmin={isAdmin}
          />
        </div>

        {/* Sidebar Case Cards List */}
        <div
          className={`lg:col-span-4 xl:col-span-3 h-[540px] sm:h-[620px] lg:h-[720px] overflow-y-auto pr-1 space-y-3 ${
            mobileTab === "map" ? "hidden sm:block" : "block"
          }`}
        >
          <div className="flex items-center justify-between text-xs text-ink-3 pb-1 border-b border-border">
            <span>Filtered Incidents ({filteredVictims.length})</span>
            <span>Sorted by Urgency</span>
          </div>

          {loading ? (
            <div className="p-8 text-center text-ink-3 space-y-2">
              <Loader2 className="w-6 h-6 animate-spin mx-auto text-cyan-400" />
              <p className="text-xs">Loading tactical telemetry...</p>
            </div>
          ) : filteredVictims.length === 0 ? (
            <div className="p-8 text-center text-ink-3 rounded-2xl bg-surface-2 border border-border space-y-2">
              <ShieldCheck className="w-8 h-8 mx-auto text-emerald-400" />
              <p className="text-sm font-semibold text-ink">No Distress Calls Detected</p>
              <p className="text-xs">No incidents match the active filters or radius ring.</p>
            </div>
          ) : (
            filteredVictims.map((v) => {
              const isSelected = selectedCaseId === v.properties.case_id;
              const isCritical = v.properties.urgency_level === "critical" || v.properties.is_ongoing_fraud;
              const isHigh = v.properties.urgency_level === "high";
              const isAssigned = v.properties.status === "assigned" || Boolean(v.properties.assigned_to);

              return (
                <div
                  key={v.properties.case_id}
                  onClick={() => setSelectedCaseId(v.properties.case_id)}
                  className={`p-3.5 rounded-xl border transition-all cursor-pointer relative ${
                    isSelected
                      ? "bg-surface-3 border-cyan-500 shadow-md ring-1 ring-cyan-500"
                      : "bg-surface-2 border-border hover:border-ink-3 hover:bg-surface-3/50"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <span className="font-mono text-xs font-bold text-sky-400">
                          {v.properties.reference}
                        </span>
                        <span
                          className={`text-[9px] font-bold px-1.5 py-0.2 rounded uppercase ${
                            isCritical
                              ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                              : isHigh
                              ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                              : "bg-blue-500/20 text-blue-300 border border-blue-500/30"
                          }`}
                        >
                          {v.properties.urgency_level}
                        </span>
                        {v.properties.is_assigned_to_me && (v.properties.assignment_source === "map_radar_claim" || v.properties.is_claimed_recently) ? (
                          <span className="inline-flex items-center gap-1 text-[9px] font-bold px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
                            <Compass className="w-2.5 h-2.5" />
                            <span>Claimed by You</span>
                          </span>
                        ) : isAssigned ? (
                          <Badge tone="success" className="text-[9px] px-1 py-0">Assigned</Badge>
                        ) : null}
                      </div>
                      <h4 className="font-semibold text-xs text-ink mt-1">
                        {v.properties.incident_type}
                      </h4>
                    </div>
                    {!isAllIndia && (
                      <span className="text-xs font-bold font-mono text-emerald-400 shrink-0">
                        {v.properties.distance_km} km
                      </span>
                    )}
                  </div>

                  <p className="text-[11px] text-ink-2 line-clamp-2 mt-2 leading-relaxed italic">
                    &ldquo;{v.properties.narrative}&rdquo;
                  </p>

                  <div className="flex items-center justify-between text-[11px] text-ink-3 mt-3 pt-2 border-t border-border/50">
                    <span>Loss: <strong className="text-amber-400">₹{Number(v.properties.estimated_loss_inr || 0).toLocaleString("en-IN")}</strong></span>
                    <span>{v.properties.city}, {v.properties.state}</span>
                  </div>

                  {v.properties.assignee_name && (
                    <div className="text-[10px] text-emerald-400 font-mono mt-1.5">
                      Assigned to: {v.properties.assignee_name}
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
