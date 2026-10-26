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
  Loader2
} from "lucide-react";
import Link from "next/link";

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
    is_assigned_to_me: boolean;
    is_exact_location: boolean;
    created_at?: string;
  };
}

interface OfficerVictimMapProps {
  stationAnchor: {
    latitude: number;
    longitude: number;
    name?: string;
  };
  radiusKm: number;
  victims: VictimFeature[];
  selectedCaseId: string | null;
  onSelectCase: (victim: VictimFeature | null) => void;
  onClaimCase?: (victim: VictimFeature) => Promise<void> | void;
  claimingId?: string | null;
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
  victims,
  selectedCaseId,
  onSelectCase,
  onClaimCase,
  claimingId,
}: OfficerVictimMapProps) {
  const mapRef = useRef<MapRef | null>(null);
  const { resolvedTheme } = useTheme();
  const [activePopup, setActivePopup] = useState<VictimFeature | null>(null);

  // Sync active popup and flyTo camera when selectedCaseId changes externally
  useEffect(() => {
    if (selectedCaseId) {
      const match = victims.find((v) => v.properties.case_id === selectedCaseId);
      if (match) {
        setActivePopup(match);
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

  // Recenter on station when stationAnchor coordinates change
  const recenterStation = () => {
    if (mapRef.current) {
      mapRef.current.flyTo({
        center: [stationAnchor.longitude, stationAnchor.latitude],
        zoom: radiusKm <= 25 ? 11 : radiusKm <= 50 ? 9.5 : 8.5,
        duration: 1200,
        essential: true,
      });
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

  return (
    <div className="relative w-full h-full min-h-[480px] rounded-2xl overflow-hidden border border-white/10 shadow-2xl bg-[#090d16]">
      <Map
        ref={mapRef}
        initialViewState={{
          longitude: stationAnchor.longitude,
          latitude: stationAnchor.latitude,
          zoom: radiusKm <= 25 ? 11 : 9.8,
        }}
        mapStyle={mapStyleUrl}
        style={{ width: "100%", height: "100%" }}
        attributionControl={false}
      >
        <NavigationControl position="bottom-right" showCompass={true} />
        <FullscreenControl position="bottom-right" />

        {/* Tactical Radius Circle Layer */}
        <Source id="radius-coverage" type="geojson" data={circleData}>
          <Layer
            id="radius-fill"
            type="fill"
            paint={{
              "fill-color": "#0284c7",
              "fill-opacity": 0.08,
            }}
          />
          <Layer
            id="radius-stroke"
            type="line"
            paint={{
              "line-color": "#38bdf8",
              "line-width": 2,
              "line-dasharray": [3, 2],
              "line-opacity": 0.75,
            }}
          />
        </Source>

        {/* Station Anchor Marker */}
        <Marker
          longitude={stationAnchor.longitude}
          latitude={stationAnchor.latitude}
          anchor="center"
        >
          <div className="relative group cursor-pointer">
            <div className="w-11 h-11 rounded-2xl bg-gradient-to-tr from-amber-600 to-amber-400 p-[2px] shadow-[0_0_24px_rgba(245,158,11,0.5)] transition-transform hover:scale-110 flex items-center justify-center">
              <div className="w-full h-full rounded-[14px] bg-slate-950 flex items-center justify-center">
                <Building className="w-5 h-5 text-amber-400" />
              </div>
            </div>
            {/* Tooltip */}
            <div className="absolute -top-8 left-1/2 -translate-x-1/2 whitespace-nowrap px-2 py-0.5 rounded bg-slate-900/95 border border-amber-500/30 text-[10px] font-semibold text-amber-300 pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity">
              {stationAnchor.name || "Station Anchor"}
            </div>
          </div>
        </Marker>

        {/* Victim Markers */}
        {victims.map((v) => {
          const [lng, lat] = v.geometry.coordinates;
          const isCritical = v.properties.urgency_level === "critical" || v.properties.is_ongoing_fraud;
          const isHigh = v.properties.urgency_level === "high";
          const isSelected = selectedCaseId === v.properties.case_id;

          return (
            <Marker
              key={v.properties.case_id}
              longitude={lng}
              latitude={lat}
              anchor="center"
              onClick={(e) => {
                e.originalEvent.stopPropagation();
                setActivePopup(v);
                onSelectCase(v);
              }}
            >
              <div className="relative cursor-pointer group">
                {/* Urgent pulsing halo for critical ongoing threats */}
                {isCritical && (
                  <span className="absolute -inset-2 rounded-full bg-rose-500/40 animate-ping opacity-75 pointer-events-none" />
                )}

                <div
                  className={`relative flex items-center justify-center w-8 h-8 rounded-full border-2 transition-transform duration-200 group-hover:scale-125 ${
                    isSelected
                      ? "ring-4 ring-cyan-400 scale-125 z-30"
                      : "z-10"
                  } ${
                    isCritical
                      ? "bg-rose-950/90 border-rose-500 text-rose-300 shadow-[0_0_16px_rgba(244,63,94,0.6)]"
                      : isHigh
                      ? "bg-amber-950/90 border-amber-500 text-amber-300 shadow-[0_0_12px_rgba(245,158,11,0.5)]"
                      : "bg-blue-950/90 border-blue-500 text-blue-300 shadow-[0_0_10px_rgba(59,130,246,0.4)]"
                  }`}
                >
                  {isCritical ? (
                    <AlertTriangle className="w-4 h-4 animate-pulse" />
                  ) : isHigh ? (
                    <ShieldAlert className="w-4 h-4" />
                  ) : (
                    <Radio className="w-3.5 h-3.5" />
                  )}
                </div>

                {/* Distance Badge */}
                <div className="absolute -bottom-4 left-1/2 -translate-x-1/2 whitespace-nowrap px-1.5 py-0.2 rounded text-[9px] font-mono font-bold bg-slate-900/90 border border-white/10 text-slate-300 pointer-events-none">
                  {v.properties.distance_km}km
                </div>
              </div>
            </Marker>
          );
        })}

        {/* Selected Victim Popup */}
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
            <div className="w-[300px] sm:w-[340px] p-3 text-slate-100 bg-[#0c1220] rounded-xl border border-white/10 shadow-2xl space-y-3 font-sans">
              {/* Header */}
              <div className="flex items-start justify-between gap-2 border-b border-white/10 pb-2">
                <div>
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className="font-mono text-xs font-bold text-sky-400">
                      {activePopup.properties.reference}
                    </span>
                    <span
                      className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider ${
                        activePopup.properties.urgency_level === "critical"
                          ? "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                          : activePopup.properties.urgency_level === "high"
                          ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                          : "bg-blue-500/20 text-blue-300 border border-blue-500/30"
                      }`}
                    >
                      {activePopup.properties.urgency_level}
                    </span>
                    {activePopup.properties.is_ongoing_fraud && (
                      <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-red-600/30 text-red-200 border border-red-500/40 animate-pulse">
                        LIVE FRAUD
                      </span>
                    )}
                  </div>
                  <h4 className="font-semibold text-sm text-white mt-1">
                    {activePopup.properties.incident_type}
                  </h4>
                </div>
                <div className="text-right">
                  <span className="text-[10px] text-slate-400 block">Distance</span>
                  <span className="text-xs font-bold text-emerald-400">
                    {activePopup.properties.distance_km} km
                  </span>
                </div>
              </div>

              {/* Financial & Location Metrics */}
              <div className="grid grid-cols-2 gap-2 text-xs bg-slate-900/60 p-2 rounded-lg border border-white/5">
                <div>
                  <span className="text-[10px] text-slate-400 block">Reported Loss</span>
                  <span className="font-bold text-amber-300">
                    ₹{Number(activePopup.properties.estimated_loss_inr || 0).toLocaleString("en-IN")}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-400 block">Location</span>
                  <span className="text-slate-200 truncate block">
                    {activePopup.properties.city}, {activePopup.properties.state}
                  </span>
                </div>
              </div>

              {/* Narrative snippet */}
              <p className="text-xs text-slate-300 italic line-clamp-2 bg-slate-950/40 p-2 rounded border border-white/5">
                &ldquo;{activePopup.properties.narrative}&rdquo;
              </p>

              {/* Differential Privacy Notice */}
              <div className="flex items-center gap-1.5 text-[10px] px-2 py-1.5 rounded bg-slate-900/80 border border-white/10">
                {activePopup.properties.is_assigned_to_me ? (
                  <>
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    <span className="text-emerald-300">
                      Case assigned to you. Exact coordinates unlocked.
                    </span>
                  </>
                ) : (
                  <>
                    <Lock className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                    <span className="text-slate-400">
                      <strong className="text-amber-300 font-medium">~300m Differential Privacy</strong> active. Exact residence unlocks upon case undertaking.
                    </span>
                  </>
                )}
              </div>

              {/* Actions */}
              <div className="pt-1 flex items-center gap-2">
                {activePopup.properties.is_assigned_to_me ? (
                  <Link
                    href={`/workbench/reports`}
                    className="flex-1 inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition-colors"
                  >
                    <span>Open Case in Workbench</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                ) : onClaimCase ? (
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
          className="flex items-center gap-2 px-3 py-2 rounded-xl bg-slate-900/90 hover:bg-slate-800 text-slate-200 border border-white/10 backdrop-blur-md shadow-lg text-xs font-medium transition-all"
          title="Recenter Map to Station"
        >
          <Compass className="w-4 h-4 text-amber-400" />
          <span>Station HQ</span>
        </button>
        <div className="px-3 py-1.5 rounded-xl bg-slate-900/85 backdrop-blur-md border border-white/10 text-[11px] text-slate-300 font-mono shadow-lg">
          Radar: <span className="text-cyan-400 font-bold">{radiusKm} km</span> | Victims: <span className="text-amber-400 font-bold">{victims.length}</span>
        </div>
      </div>

      {/* Map Legend Overlay */}
      <div className="absolute bottom-4 left-4 z-20 hidden sm:flex items-center gap-3 px-3 py-1.5 rounded-xl bg-slate-900/90 backdrop-blur-md border border-white/10 text-[10px] text-slate-300 shadow-lg">
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-pulse" />
          <span>Critical Live</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-amber-500" />
          <span>High Urgency</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-blue-500" />
          <span>Standard</span>
        </div>
        <div className="flex items-center gap-1.5 border-l border-white/10 pl-2">
          <Building className="w-3 h-3 text-amber-400" />
          <span>Station Anchor</span>
        </div>
      </div>
    </div>
  );
}
