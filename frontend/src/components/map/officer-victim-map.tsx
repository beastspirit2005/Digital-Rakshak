"use client";

import { useEffect, useRef, useState, useMemo } from "react";
import Map, {
  Marker,
  Popup,
  NavigationControl,
  FullscreenControl,
  Source,
  Layer,
  MapRef
} from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";
import { useTheme } from "next-themes";
import {
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  Building,
  Navigation,
  Compass,
  CheckCircle2,
  Lock,
  Radio,
  Eye,
  ArrowRight,
  Loader2,
  Phone,
  UserCheck,
  Send,
  User,
  Users
} from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";

export interface VictimFeature {
  type: "Feature";
  geometry: {
    type: "Point";
    coordinates: [number, number]; // [lng, lat]
  };
  properties: {
    case_id: string;
    case_number: string;
    reference: string;
    incident_type: string;
    urgency_level: "critical" | "high" | "standard" | string;
    is_ongoing_fraud: boolean;
    estimated_loss_inr: number;
    distance_km: number;
    city: string;
    state: string;
    status: string;
    narrative: string;
    assigned_to?: string | null;
    assignee_name?: string | null;
    assignee_role?: string | null;
    assignee_station?: string | null;
    is_assigned_to_me: boolean;
    is_exact_location: boolean;
    created_at?: string;
    assignment_source?: string;
    claimed_at?: string;
    is_claimed_recently?: boolean;
  };
}

export interface OfficerFeature {
  id: string;
  type: "officer" | "station";
  name: string;
  email?: string;
  role: string;
  designation?: string;
  station_name?: string;
  station_phone?: string;
  city?: string;
  state?: string;
  active_cases_count?: number;
  coordinates: [number, number]; // [lng, lat]
  distance_km: number;
}

interface OfficerVictimMapProps {
  stationAnchor: {
    latitude: number;
    longitude: number;
    name?: string;
  };
  radiusKm: number;
  isAllIndia?: boolean;
  isLivePatrol?: boolean;
  victims: VictimFeature[];
  officers?: OfficerFeature[];
  showOfficersLayer?: boolean;
  selectedCaseId: string | null;
  onSelectCase: (victim: VictimFeature | null) => void;
  onClaimCase?: (victim: VictimFeature) => Promise<void> | void;
  onAssignCase?: (caseId: string, officerId: string) => Promise<void> | void;
  claimingId?: string | null;
  isAdmin?: boolean;
}

// Generate GeoJSON polygon circle for tactical jurisdiction radius ring
function createGeoJSONCircle(center: [number, number], radiusKm: number, points = 64) {
  const [lng, lat] = center;
  const coords: [number, number][] = [];
  const distanceX = radiusKm / (111.32 * Math.cos((lat * Math.PI) / 180));
  const distanceY = radiusKm / 110.574;

  for (let i = 0; i < points; i++) {
    const theta = (i / points) * (2 * Math.PI);
    const x = distanceX * Math.cos(theta);
    const y = distanceY * Math.sin(theta);
    coords.push([lng + x, lat + y]);
  }
  coords.push(coords[0]);

  return {
    type: "FeatureCollection" as const,
    features: [
      {
        type: "Feature" as const,
        geometry: {
          type: "Polygon" as const,
          coordinates: [coords],
        },
        properties: {},
      },
    ],
  };
}

export default function OfficerVictimMap({
  stationAnchor,
  radiusKm,
  isAllIndia = false,
  isLivePatrol = false,
  victims,
  officers = [],
  showOfficersLayer = true,
  selectedCaseId,
  onSelectCase,
  onClaimCase,
  onAssignCase,
  claimingId,
  isAdmin = false,
}: OfficerVictimMapProps) {
  const mapRef = useRef<MapRef | null>(null);
  const { resolvedTheme } = useTheme();

  const [activePopup, setActivePopup] = useState<VictimFeature | null>(null);
  const [activeOfficerPopup, setActiveOfficerPopup] = useState<OfficerFeature | null>(null);
  const [assigningCaseId, setAssigningCaseId] = useState<string | null>(null);

  // Sync active popup and flyTo camera when selectedCaseId changes externally
  useEffect(() => {
    if (selectedCaseId) {
      const match = victims.find((v) => v.properties.case_id === selectedCaseId);
      if (match) {
        setActivePopup(match);
        setActiveOfficerPopup(null);
        if (mapRef.current) {
          mapRef.current.flyTo({
            center: match.geometry.coordinates,
            zoom: 12.5,
            duration: 1100,
            essential: true,
          });
        }
      }
    }
  }, [selectedCaseId, victims]);

  // Recenter Camera Effect when anchor or nationwide scope changes
  useEffect(() => {
    if (!mapRef.current) return;
    if (isAllIndia) {
      mapRef.current.flyTo({
        center: [79.5, 22.5], // Central India
        zoom: 4.4,
        duration: 1200,
        essential: true,
      });
    } else {
      mapRef.current.flyTo({
        center: [stationAnchor.longitude, stationAnchor.latitude],
        zoom: radiusKm <= 25 ? 11 : radiusKm <= 50 ? 9.5 : 8.5,
        duration: 1100,
        essential: true,
      });
    }
  }, [isAllIndia, stationAnchor.latitude, stationAnchor.longitude, radiusKm]);

  const recenterStation = () => {
    if (mapRef.current) {
      if (isAllIndia) {
        mapRef.current.flyTo({ center: [79.5, 22.5], zoom: 4.4, duration: 1100 });
      } else {
        mapRef.current.flyTo({
          center: [stationAnchor.longitude, stationAnchor.latitude],
          zoom: radiusKm <= 25 ? 11 : radiusKm <= 50 ? 9.5 : 8.5,
          duration: 1100,
        });
      }
    }
  };

  const mapStyleUrl = useMemo(() => {
    return resolvedTheme === "light"
      ? "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
      : "https://basemaps.cartocdn.com/gl/dark-matter-nolabels-gl-style/style.json";
  }, [resolvedTheme]);

  const circleData = useMemo(() => {
    return createGeoJSONCircle(
      [stationAnchor.longitude, stationAnchor.latitude],
      radiusKm
    );
  }, [stationAnchor.longitude, stationAnchor.latitude, radiusKm]);

  // Nearby unassigned cases within officer jurisdiction for 1-click assignment
  const unassignedCasesForOfficer = useMemo(() => {
    if (!activeOfficerPopup) return [];
    const [oLng, oLat] = activeOfficerPopup.coordinates;
    return victims
      .filter((v) => v.properties.status !== "assigned" && !v.properties.assigned_to)
      .map((v) => {
        const [vLng, vLat] = v.geometry.coordinates;
        const R = 6371.0;
        const dLat = ((vLat - oLat) * Math.PI) / 180;
        const dLon = ((vLng - oLng) * Math.PI) / 180;
        const a =
          Math.sin(dLat / 2) * Math.sin(dLat / 2) +
          Math.cos((oLat * Math.PI) / 180) *
            Math.cos((vLat * Math.PI) / 180) *
            Math.sin(dLon / 2) *
            Math.sin(dLon / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        const dist = Math.round(R * c * 10) / 10;
        return { victim: v, distKm: dist };
      })
      .filter((item) => item.distKm <= 35)
      .sort((a, b) => a.distKm - b.distKm)
      .slice(0, 4);
  }, [activeOfficerPopup, victims]);

  // Ranked officers by proximity for active victim popup assignment
  const rankedOfficersForCase = useMemo(() => {
    if (!activePopup || !officers.length) return [];
    const [cLng, cLat] = activePopup.geometry.coordinates;
    return officers
      .filter((o) => o.type === "officer")
      .map((o) => {
        const [oLng, oLat] = o.coordinates;
        const R = 6371.0;
        const dLat = ((oLat - cLat) * Math.PI) / 180;
        const dLon = ((oLng - cLng) * Math.PI) / 180;
        const a =
          Math.sin(dLat / 2) * Math.sin(dLat / 2) +
          Math.cos((cLat * Math.PI) / 180) *
            Math.cos((oLat * Math.PI) / 180) *
            Math.sin(dLon / 2) *
            Math.sin(dLon / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        const dist = Math.round(R * c * 10) / 10;
        return { officer: o, distKm: dist };
      })
      .sort((a, b) => a.distKm - b.distKm)
      .slice(0, 4);
  }, [activePopup, officers]);

  return (
    <div className="relative w-full h-full min-h-[480px] rounded-2xl overflow-hidden border border-line shadow-2xl bg-surface">
      <Map
        ref={mapRef}
        initialViewState={{
          longitude: stationAnchor.longitude,
          latitude: stationAnchor.latitude,
          zoom: isAllIndia ? 4.4 : radiusKm <= 25 ? 11 : 9.8,
        }}
        mapStyle={mapStyleUrl}
        style={{ width: "100%", height: "100%" }}
        attributionControl={false}
      >
        <NavigationControl position="bottom-right" showCompass={true} />
        <FullscreenControl position="bottom-right" />

        {/* Tactical Radius Circle Layer (Hidden in All-India mode) */}
        {!isAllIndia && (
          <Source id="radius-coverage" type="geojson" data={circleData}>
            <Layer
              id="radius-fill"
              type="fill"
              paint={{
                "fill-color": isLivePatrol ? "#06b6d4" : "#0284c7",
                "fill-opacity": 0.08,
              }}
            />
            <Layer
              id="radius-stroke"
              type="line"
              paint={{
                "line-color": isLivePatrol ? "#22d3ee" : "#38bdf8",
                "line-width": 2,
                "line-dasharray": [3, 2],
                "line-opacity": 0.75,
              }}
            />
          </Source>
        )}

        {/* Station Anchor / Patrol Beacon Marker */}
        {!isAllIndia && (
          <Marker
            longitude={stationAnchor.longitude}
            latitude={stationAnchor.latitude}
            anchor="center"
          >
            <div className="relative group cursor-pointer" onClick={recenterStation}>
              {isLivePatrol ? (
                <div className="relative flex items-center justify-center">
                  <span className="absolute -inset-3 rounded-full bg-cyan-400/30 animate-ping pointer-events-none" />
                  <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-cyan-600 to-cyan-400 p-[2px] shadow-[0_0_24px_rgba(6,182,212,0.6)] flex items-center justify-center">
                    <div className="w-full h-full rounded-[14px] bg-slate-950 flex items-center justify-center">
                      <Compass className="w-5 h-5 text-cyan-300 animate-spin-slow" />
                    </div>
                  </div>
                </div>
              ) : (
                <div className="w-11 h-11 rounded-2xl bg-gradient-to-tr from-amber-600 to-amber-400 p-[2px] shadow-[0_0_24px_rgba(245,158,11,0.5)] transition-transform hover:scale-110 flex items-center justify-center">
                  <div className="w-full h-full rounded-[14px] bg-slate-950 flex items-center justify-center">
                    <Building className="w-5 h-5 text-amber-400" />
                  </div>
                </div>
              )}
              {/* Tooltip */}
              <div className="absolute -top-8 left-1/2 -translate-x-1/2 whitespace-nowrap px-2 py-0.5 rounded bg-slate-900/95 border border-white/10 text-[10px] font-semibold text-slate-200 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity z-20">
                {stationAnchor.name || (isLivePatrol ? "Live Patrol Anchor" : "Station HQ")}
              </div>
            </div>
          </Marker>
        )}

        {/* ================= OFFICER & CYBER CELL LAYER ================= */}
        {showOfficersLayer &&
          officers.map((off) => {
            const [lng, lat] = off.coordinates;
            const isStation = off.type === "station";
            const isSelected = activeOfficerPopup?.id === off.id;

            return (
              <Marker
                key={`off-${off.id}`}
                longitude={lng}
                latitude={lat}
                anchor="center"
                onClick={(e) => {
                  e.originalEvent.stopPropagation();
                  setActiveOfficerPopup(off);
                  setActivePopup(null);
                }}
              >
                <div className="relative cursor-pointer group">
                  <div
                    className={`relative flex items-center justify-center w-8 h-8 rounded-full border-2 transition-transform duration-200 group-hover:scale-125 ${
                      isSelected
                        ? "ring-4 ring-cyan-400 scale-125 z-30"
                        : "z-15"
                    } ${
                      isStation
                        ? "bg-slate-900 border-amber-400 text-amber-300 shadow-[0_0_14px_rgba(245,158,11,0.5)]"
                        : "bg-slate-950 border-cyan-400 text-cyan-300 shadow-[0_0_16px_rgba(6,182,212,0.6)]"
                    }`}
                  >
                    {isStation ? (
                      <Building className="w-4 h-4 text-amber-300" />
                    ) : (
                      <ShieldCheck className="w-4 h-4 text-cyan-300" />
                    )}
                  </div>

                  {/* Workload Indicator Badge */}
                  {!isStation && typeof off.active_cases_count === "number" && (
                    <div className="absolute -top-1.5 -right-1.5 px-1 min-w-[16px] h-4 rounded-full bg-cyan-500 text-slate-950 text-[9px] font-extrabold flex items-center justify-center shadow-md">
                      {off.active_cases_count}
                    </div>
                  )}

                  {/* Tooltip */}
                  <div className="absolute -bottom-5 left-1/2 -translate-x-1/2 whitespace-nowrap px-1.5 py-0.2 rounded text-[9px] font-mono font-bold bg-slate-900/90 border border-white/10 text-cyan-300 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity">
                    {off.name}
                  </div>
                </div>
              </Marker>
            );
          })}

        {/* ================= VICTIM CASE INCIDENTS LAYER ================= */}
        {victims.map((v) => {
          const [lng, lat] = v.geometry.coordinates;
          const isCritical = v.properties.urgency_level === "critical" || v.properties.is_ongoing_fraud;
          const isHigh = v.properties.urgency_level === "high";
          const isAssigned = v.properties.status === "assigned" || Boolean(v.properties.assigned_to);
          const isSelected = selectedCaseId === v.properties.case_id;
          const isMyClaim = Boolean(v.properties.is_assigned_to_me && (v.properties.assignment_source === "map_radar_claim" || v.properties.is_claimed_recently));

          return (
            <Marker
              key={v.properties.case_id}
              longitude={lng}
              latitude={lat}
              anchor="center"
              onClick={(e) => {
                e.originalEvent.stopPropagation();
                setActivePopup(v);
                setActiveOfficerPopup(null);
                onSelectCase(v);
              }}
            >
              <div className="relative cursor-pointer group">
                {/* Radiant pulsing cyan halo for cases claimed directly by this officer */}
                {isMyClaim && (
                  <span className="absolute -inset-2.5 rounded-full bg-cyan-500/40 animate-ping opacity-75 pointer-events-none" />
                )}

                {/* Urgent pulsing halo for critical ongoing threats */}
                {isCritical && !isAssigned && !isMyClaim && (
                  <span className="absolute -inset-2 rounded-full bg-rose-500/40 animate-ping opacity-75 pointer-events-none" />
                )}

                <div
                  className={`relative flex items-center justify-center w-8 h-8 rounded-full border-2 transition-transform duration-200 group-hover:scale-125 ${
                    isSelected
                      ? "ring-4 ring-cyan-400 scale-125 z-30"
                      : "z-10"
                  } ${
                    isMyClaim
                      ? "bg-cyan-950/95 border-cyan-400 text-cyan-300 ring-2 ring-cyan-400/60 shadow-[0_0_16px_rgba(6,182,212,0.8)]"
                      : isAssigned
                      ? "bg-emerald-950/90 border-emerald-500 text-emerald-300 shadow-[0_0_12px_rgba(16,185,129,0.5)]"
                      : isCritical
                      ? "bg-rose-950/90 border-rose-500 text-rose-300 shadow-[0_0_16px_rgba(244,63,94,0.6)]"
                      : isHigh
                      ? "bg-amber-950/90 border-amber-500 text-amber-300 shadow-[0_0_12px_rgba(245,158,11,0.5)]"
                      : "bg-blue-950/90 border-blue-500 text-blue-300 shadow-[0_0_10px_rgba(59,130,246,0.4)]"
                  }`}
                >
                  {isMyClaim ? (
                    <Compass className="w-4 h-4 text-cyan-300" />
                  ) : isAssigned ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-300" />
                  ) : isCritical ? (
                    <AlertTriangle className="w-4 h-4 animate-pulse" />
                  ) : isHigh ? (
                    <ShieldAlert className="w-4 h-4" />
                  ) : (
                    <Radio className="w-3.5 h-3.5" />
                  )}
                </div>

                {/* Claimed Tooltip Pill */}
                {isMyClaim ? (
                  <div className="absolute -top-6 left-1/2 -translate-x-1/2 whitespace-nowrap px-1.5 py-0.2 rounded text-[9px] font-bold bg-cyan-950 border border-cyan-400 text-cyan-300 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity z-30">
                    🎯 Claimed by You
                  </div>
                ) : null}

                {/* Distance Badge */}
                {!isAllIndia && (
                  <div className="absolute -bottom-4 left-1/2 -translate-x-1/2 whitespace-nowrap px-1.5 py-0.2 rounded text-[9px] font-mono font-bold bg-slate-900/90 border border-line text-slate-300 pointer-events-none">
                    {v.properties.distance_km}km
                  </div>
                )}
              </div>
            </Marker>
          );
        })}

        {/* ================= OFFICER COMMAND POPOVER ================= */}
        {activeOfficerPopup && (
          <Popup
            longitude={activeOfficerPopup.coordinates[0]}
            latitude={activeOfficerPopup.coordinates[1]}
            anchor="bottom"
            offset={[0, -18]}
            closeButton={true}
            closeOnClick={false}
            onClose={() => setActiveOfficerPopup(null)}
            className="digital-rakshak-map-popup z-50"
          >
            <div className="w-[300px] sm:w-[340px] p-3 text-ink bg-surface rounded-xl border border-line shadow-2xl space-y-3 font-sans">
              <div className="flex items-start justify-between border-b border-line pb-2">
                <div>
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider bg-accent/15 text-accent border border-accent/30">
                      {activeOfficerPopup.type === "station" ? "Precinct Station" : activeOfficerPopup.role.replace("_", " ")}
                    </span>
                    {typeof activeOfficerPopup.active_cases_count === "number" && (
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-surface-2 text-ink-2 border border-line">
                        {activeOfficerPopup.active_cases_count} Active Cases
                      </span>
                    )}
                  </div>
                  <h4 className="font-semibold text-sm text-ink mt-1">
                    {activeOfficerPopup.name}
                  </h4>
                  <p className="text-xs text-ink-3">
                    {activeOfficerPopup.designation || activeOfficerPopup.station_name}
                  </p>
                </div>
              </div>

              {/* Station & Contact */}
              <div className="grid grid-cols-2 gap-2 text-xs bg-surface-2 p-2 rounded-lg border border-line font-mono">
                <div>
                  <span className="text-[10px] text-ink-3 block">Jurisdiction</span>
                  <span className="text-ink-2 truncate block">
                    {activeOfficerPopup.city}, {activeOfficerPopup.state}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-ink-3 block">Station Phone</span>
                  <span className="text-accent font-bold block truncate">
                    {activeOfficerPopup.station_phone || "1930"}
                  </span>
                </div>
              </div>

              {/* Action Buttons: Direct Call & Dispatch */}
              <div className="grid grid-cols-2 gap-2 pt-1">
                {activeOfficerPopup.station_phone && (
                  <a
                    href={`tel:${activeOfficerPopup.station_phone}`}
                    className="flex items-center justify-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition-colors"
                  >
                    <Phone className="w-3.5 h-3.5" />
                    <span>Call Desk</span>
                  </a>
                )}
                <a
                  href={`mailto:${activeOfficerPopup.email || "police@digitalrakshak.in"}`}
                  className="flex items-center justify-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-surface-2 hover:bg-surface-3 text-ink-2 border border-line transition-colors"
                >
                  <Send className="w-3.5 h-3.5" />
                  <span>Send Dispatch</span>
                </a>
              </div>

              {/* 1-Click Jurisdiction Assignment (Admin Only) */}
              {isAdmin && onAssignCase && activeOfficerPopup.type === "officer" && (
                <div className="space-y-1.5 pt-2 border-t border-white/10">
                  <span className="text-[10px] font-bold uppercase text-slate-400 block tracking-wider">
                    Unassigned Incidents in Vicinity
                  </span>
                  {unassignedCasesForOfficer.length === 0 ? (
                    <span className="text-xs text-slate-400 italic block">
                      No unassigned cases within 35km jurisdiction.
                    </span>
                  ) : (
                    <div className="space-y-1.5 max-h-32 overflow-y-auto pr-1">
                      {unassignedCasesForOfficer.map(({ victim, distKm }) => (
                        <div
                          key={`assign-${victim.properties.case_id}`}
                          className="flex items-center justify-between p-1.5 rounded-lg bg-slate-900 border border-white/5 text-xs"
                        >
                          <div className="min-w-0 pr-2">
                            <span className="font-mono text-[10px] font-bold text-sky-400 block">
                              {victim.properties.reference} • {distKm}km
                            </span>
                            <span className="text-[11px] text-white truncate block">
                              {victim.properties.incident_type}
                            </span>
                          </div>
                          <button
                            onClick={async () => {
                              setAssigningCaseId(victim.properties.case_id);
                              await onAssignCase(victim.properties.case_id, activeOfficerPopup.id);
                              setAssigningCaseId(null);
                            }}
                            disabled={assigningCaseId === victim.properties.case_id}
                            className="px-2 py-1 rounded bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-[10px] shrink-0 disabled:opacity-50"
                          >
                            {assigningCaseId === victim.properties.case_id ? (
                              <Loader2 className="w-3 h-3 animate-spin" />
                            ) : (
                              "Assign"
                            )}
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </Popup>
        )}

        {/* ================= SELECTED VICTIM INCIDENT POPUP ================= */}
        {activePopup && (
          <Popup
            longitude={activePopup.geometry.coordinates[0]}
            latitude={activePopup.geometry.coordinates[1]}
            anchor="bottom"
            offset={[0, -18]}
            closeButton={true}
            closeOnClick={false}
            onClose={() => {
              setActivePopup(null);
              onSelectCase(null);
            }}
            className="digital-rakshak-map-popup z-40"
          >
            <div className="w-[300px] sm:w-[350px] p-3 text-ink bg-surface rounded-xl border border-line shadow-2xl space-y-3 font-sans max-h-[85vh] overflow-y-auto">
              {/* Header */}
              <div className="flex items-start justify-between gap-2 border-b border-line pb-2">
                <div>
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="font-mono text-xs font-bold text-accent">
                      {activePopup.properties.reference}
                    </span>
                    <span
                      className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider ${
                        activePopup.properties.urgency_level === "critical"
                          ? "bg-rose-500/15 text-rose-600 dark:text-rose-300 border border-rose-500/30"
                          : activePopup.properties.urgency_level === "high"
                          ? "bg-amber-500/15 text-amber-600 dark:text-amber-300 border border-amber-500/30"
                          : "bg-blue-500/15 text-blue-600 dark:text-blue-300 border border-blue-500/30"
                      }`}
                    >
                      {activePopup.properties.urgency_level}
                    </span>
                    {activePopup.properties.is_ongoing_fraud && (
                      <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-rose-600/20 text-rose-600 dark:text-rose-200 border border-rose-500/40 animate-pulse">
                        LIVE FRAUD
                      </span>
                    )}
                    {activePopup.properties.status === "assigned" && (
                      <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-600/20 text-emerald-600 dark:text-emerald-200 border border-emerald-500/40">
                        ASSIGNED
                      </span>
                    )}
                  </div>
                  <h4 className="font-semibold text-sm text-ink mt-1">
                    {activePopup.properties.incident_type}
                  </h4>
                </div>
                {!isAllIndia && (
                  <div className="text-right">
                    <span className="text-[10px] text-ink-3 block">Distance</span>
                    <span className="text-xs font-bold text-emerald-600 dark:text-emerald-400">
                      {activePopup.properties.distance_km} km
                    </span>
                  </div>
                )}
              </div>

              {/* Origin Banner if claimed by officer */}
              {activePopup.properties.is_assigned_to_me && (activePopup.properties.assignment_source === "map_radar_claim" || activePopup.properties.is_claimed_recently) && (
                <div className="flex items-center gap-2 p-2 rounded-lg bg-accent/10 border border-accent/30 text-xs text-accent">
                  <Compass className="w-4 h-4 shrink-0 text-accent" />
                  <span className="font-medium">Self-Claimed from Map Radar • Direct victim chat active</span>
                </div>
              )}

              {/* Financial & Location Metrics */}
              <div className="grid grid-cols-2 gap-2 text-xs bg-surface-2 p-2 rounded-lg border border-line">
                <div>
                  <span className="text-[10px] text-ink-3 block">Reported Loss</span>
                  <span className="font-bold text-amber-600 dark:text-amber-400">
                    ₹{Number(activePopup.properties.estimated_loss_inr || 0).toLocaleString("en-IN")}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-ink-3 block">Location</span>
                  <span className="text-ink-2 truncate block">
                    {activePopup.properties.city}, {activePopup.properties.state}
                  </span>
                </div>
              </div>

              {/* Assignee Information if assigned */}
              {activePopup.properties.assignee_name && (
                <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-xs space-y-0.5">
                  <span className="text-[10px] uppercase font-bold text-emerald-600 dark:text-emerald-400 block">Assigned Officer</span>
                  <span className="text-ink font-semibold block">{activePopup.properties.assignee_name}</span>
                  <span className="text-[11px] text-ink-3 block">{activePopup.properties.assignee_station || "Cyber Crime Unit"}</span>
                </div>
              )}

              {/* Narrative snippet */}
              <p className="text-xs text-ink-2 italic line-clamp-2 bg-surface-2 p-2 rounded border border-line">
                &ldquo;{activePopup.properties.narrative}&rdquo;
              </p>

              {/* Differential Privacy Notice */}
              <div className="flex items-center gap-1.5 text-[10px] px-2 py-1.5 rounded bg-surface-2 border border-line">
                {activePopup.properties.is_assigned_to_me || isAdmin ? (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500 shrink-0" />
                    <span className="text-emerald-600 dark:text-emerald-300">
                      {isAdmin ? "Admin view: Exact coordinates unlocked." : "Case assigned to you: Exact coordinates unlocked."}
                    </span>
                  </>
                ) : (
                  <>
                    <Lock className="w-3.5 h-3.5 text-amber-500 shrink-0" />
                    <span className="text-ink-3">
                      <strong className="text-amber-600 dark:text-amber-300 font-medium">~300m Differential Privacy</strong> active. Exact residence unlocks upon case undertaking.
                    </span>
                  </>
                )}
              </div>

              {/* Proximity-Sorted Field Officer Assignment (Admin Only) */}
              {isAdmin && onAssignCase && activePopup.properties.status !== "assigned" && (
                <div className="space-y-2 pt-2 border-t border-white/10">
                  <span className="text-[10px] font-bold uppercase text-cyan-400 block tracking-wider flex items-center gap-1">
                    <UserCheck className="w-3.5 h-3.5" />
                    <span>Assign Nearest Field Officer</span>
                  </span>

                  {rankedOfficersForCase.length === 0 ? (
                    <span className="text-xs text-slate-400 italic block">
                      No verified active officers located in this vicinity.
                    </span>
                  ) : (
                    <div className="space-y-1.5">
                      {rankedOfficersForCase.map(({ officer, distKm }) => (
                        <div
                          key={`case-off-${officer.id}`}
                          className="flex items-center justify-between p-1.5 rounded-lg bg-slate-900 border border-white/5 text-xs"
                        >
                          <div className="min-w-0 pr-2">
                            <span className="font-semibold text-white truncate block text-[11px]">
                              {officer.name} ({officer.role.replace("_", " ")})
                            </span>
                            <span className="text-[10px] text-slate-400 block font-mono">
                              {distKm}km away • {officer.active_cases_count || 0} active cases
                            </span>
                          </div>
                          <button
                            onClick={async () => {
                              setAssigningCaseId(activePopup.properties.case_id);
                              await onAssignCase(activePopup.properties.case_id, officer.id);
                              setAssigningCaseId(null);
                            }}
                            disabled={assigningCaseId === activePopup.properties.case_id}
                            className="px-2 py-1 rounded bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-[10px] shrink-0 disabled:opacity-50"
                          >
                            {assigningCaseId === activePopup.properties.case_id ? (
                              <Loader2 className="w-3 h-3 animate-spin" />
                            ) : (
                              "Assign"
                            )}
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Police Officer Claim Action */}
              <div className="pt-1 flex items-center gap-2">
                {activePopup.properties.is_assigned_to_me ? (
                  <Link
                    href={`/workbench/reports`}
                    className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition-colors"
                  >
                    <span>Open Case in Workbench</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                ) : onClaimCase && !isAdmin ? (
                  <button
                    onClick={() => onClaimCase(activePopup)}
                    disabled={claimingId === activePopup.properties.case_id}
                    className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white transition-all shadow-md active:scale-95 disabled:opacity-50"
                  >
                    {claimingId === activePopup.properties.case_id ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        <span>Undertaking Case...</span>
                      </>
                    ) : (
                      <>
                        <ShieldCheck className="w-3.5 h-3.5" />
                        <span>Claim & Undertake Case</span>
                      </>
                    )}
                  </button>
                ) : null}
              </div>
            </div>
          </Popup>
        )}
      </Map>

      {/* Floating Tactical HUD Controls */}
      <div className="absolute top-4 left-4 z-20 flex flex-col gap-2">
        <button
          onClick={recenterStation}
          className="flex items-center gap-2 px-3 py-2 rounded-xl bg-surface/90 hover:bg-surface text-ink border border-line backdrop-blur-md shadow-lg text-xs font-medium transition-all"
          title="Recenter Map Viewport"
        >
          <Compass className={cn("w-4 h-4", isLivePatrol ? "text-accent" : "text-amber-500")} />
          <span>{isAllIndia ? "Center: All India" : isLivePatrol ? "Patrol GPS Anchor" : "Station HQ"}</span>
        </button>
        <div className="px-3 py-1.5 rounded-xl bg-surface/90 backdrop-blur-md border border-line text-[11px] text-ink-2 font-mono shadow-lg">
          {isAllIndia ? (
            <span>Grid: <strong className="text-accent">All India</strong></span>
          ) : (
            <span>Radar: <strong className="text-accent">{radiusKm} km</strong></span>
          )}
          {" • "}Cases: <strong className="text-amber-500">{victims.length}</strong>
          {showOfficersLayer && (
            <> • Units: <strong className="text-accent">{officers.length}</strong></>
          )}
        </div>
      </div>

      {/* Map Legend Overlay */}
      <div className="absolute bottom-4 left-4 z-20 hidden sm:flex items-center gap-3 px-3 py-1.5 rounded-xl bg-surface/90 backdrop-blur-md border border-line text-[10px] text-ink-2 shadow-lg">
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-pulse" />
          <span>Critical Live</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
          <span>High Urgency</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
          <span>Assigned</span>
        </div>
        <div className="flex items-center gap-1.5 border-l border-line pl-2">
          <ShieldCheck className="w-3.5 h-3.5 text-accent" />
          <span>Officers & Stations</span>
        </div>
      </div>
    </div>
  );
}
