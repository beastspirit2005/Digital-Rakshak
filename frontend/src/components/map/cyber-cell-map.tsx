"use client";

import { useEffect, useRef, useState, useMemo } from "react";
import Map, {
  Marker,
  Popup,
  NavigationControl,
  FullscreenControl,
  MapRef
} from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";
import { useTheme } from "next-themes";
import {
  ShieldCheck,
  MapPin,
  PhoneCall,
  ExternalLink,
  Navigation,
  Compass,
  CheckCircle2,
  Building
} from "lucide-react";

export interface OfficialLocationItem {
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

interface CyberCellMapProps {
  locations: OfficialLocationItem[];
  selectedStationId: string | null;
  onStationSelect: (station: OfficialLocationItem) => void;
  userLocation: { lat: number; lng: number } | null;
}

export default function CyberCellMap({
  locations,
  selectedStationId,
  onStationSelect,
  userLocation,
}: CyberCellMapProps) {
  const mapRef = useRef<MapRef | null>(null);
  const { resolvedTheme } = useTheme();
  const [activePopup, setActivePopup] = useState<OfficialLocationItem | null>(null);

  // Sync active popup and camera flyTo when selectedStationId prop changes
  useEffect(() => {
    if (selectedStationId) {
      const match = locations.find((l) => l.id === selectedStationId);
      if (match) {
        setActivePopup(match);
        if (mapRef.current) {
          mapRef.current.flyTo({
            center: [match.longitude, match.latitude],
            zoom: 12,
            duration: 1200,
            essential: true,
          });
        }
      }
    }
  }, [selectedStationId, locations]);

  // Center on user location when GPS coordinates are available
  useEffect(() => {
    if (userLocation && mapRef.current) {
      mapRef.current.flyTo({
        center: [userLocation.lng, userLocation.lat],
        zoom: 11,
        duration: 1400,
        essential: true,
      });
    }
  }, [userLocation]);

  const mapStyleUrl = useMemo(() => {
    return resolvedTheme === "light"
      ? "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
      : "https://basemaps.cartocdn.com/gl/dark-matter-nolabels-gl-style/style.json";
  }, [resolvedTheme]);

  return (
    <div className="relative w-full h-full min-h-[420px] rounded-2xl overflow-hidden border border-white/10 shadow-2xl bg-[#090d16]">
      <Map
        ref={mapRef}
        initialViewState={{
          longitude: 78.9629,
          latitude: 20.5937,
          zoom: 4.2,
        }}
        mapStyle={mapStyleUrl}
        style={{ width: "100%", height: "100%" }}
      >
        <NavigationControl position="top-right" />
        <FullscreenControl position="top-right" />

        {/* User GPS Beacon */}
        {userLocation && (
          <Marker
            longitude={userLocation.lng}
            latitude={userLocation.lat}
            anchor="center"
          >
            <div className="relative flex items-center justify-center">
              <span className="animate-ping absolute inline-flex h-8 w-8 rounded-full bg-blue-400 opacity-60" />
              <div className="w-5 h-5 rounded-full bg-blue-500 border-2 border-white shadow-lg flex items-center justify-center">
                <div className="w-2 h-2 rounded-full bg-white" />
              </div>
            </div>
          </Marker>
        )}

        {/* Verified Police Station Pins */}
        {locations.map((loc) => {
          const isSelected = selectedStationId === loc.id;

          return (
            <Marker
              key={loc.id}
              longitude={loc.longitude}
              latitude={loc.latitude}
              anchor="bottom"
              onClick={(e) => {
                e.originalEvent.stopPropagation();
                setActivePopup(loc);
                onStationSelect(loc);
              }}
            >
              <div
                className={`group cursor-pointer transition-transform duration-200 ${
                  isSelected ? "scale-125 z-30" : "hover:scale-115 z-10"
                }`}
              >
                <div
                  className={`flex items-center justify-center w-8 h-8 rounded-xl shadow-xl transition-all ${
                    isSelected
                      ? "bg-amber-500 text-black border-2 border-white shadow-amber-500/50"
                      : "bg-[#0f172a] text-amber-400 border border-amber-500/40 hover:border-amber-400 shadow-black/80"
                  }`}
                >
                  <ShieldCheck className="w-5 h-5" />
                </div>
                {/* Station Tooltip pill */}
                <div className="hidden group-hover:block absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 whitespace-nowrap bg-black/90 text-[10px] text-white px-2 py-0.5 rounded border border-white/20 font-semibold shadow-md pointer-events-none">
                  {loc.name.slice(0, 28)}...
                </div>
              </div>
            </Marker>
          );
        })}

        {/* Active Station Detail Popup */}
        {activePopup && (
          <Popup
            longitude={activePopup.longitude}
            latitude={activePopup.latitude}
            anchor="top"
            closeButton={true}
            closeOnClick={false}
            onClose={() => setActivePopup(null)}
            className="dr-maplibre-popup z-40"
            maxWidth="320px"
          >
            <div className="p-3 bg-surface text-ink rounded-xl space-y-2 text-xs border border-line shadow-2xl backdrop-blur-md">
              <div className="flex items-center gap-1.5">
                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider bg-amber-500/15 text-amber-600 dark:text-amber-300 border border-amber-500/30">
                  {activePopup.jurisdiction_level} level
                </span>
                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-emerald-500/15 text-emerald-600 dark:text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
                  <CheckCircle2 className="w-2.5 h-2.5" />
                  Verified
                </span>
              </div>

              <h4 className="font-bold text-ink text-xs leading-snug">
                {activePopup.name}
              </h4>
              <p className="text-[11px] text-ink-3 line-clamp-2">
                {activePopup.address}
              </p>

              {activePopup.nodal_officer_designation && (
                <div className="text-[10px] text-ink-2">
                  <span className="text-ink-3 block uppercase font-bold">Nodal Officer</span>
                  {activePopup.nodal_officer_designation}
                </div>
              )}

              {activePopup.landline_number && (
                <div className="pt-1">
                  <a
                    href={`tel:${activePopup.landline_number}`}
                    className="inline-flex items-center gap-1 text-amber-600 dark:text-amber-400 font-mono font-bold hover:underline"
                  >
                    <PhoneCall className="w-3 h-3" />
                    {activePopup.landline_number}
                  </a>
                </div>
              )}

              <div className="pt-2 border-t border-line flex items-center justify-between">
                <a
                  href={activePopup.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-[10px] text-ink-3 hover:text-ink flex items-center gap-1"
                >
                  Govt Source <ExternalLink className="w-2.5 h-2.5" />
                </a>

                <a
                  href={`https://www.google.com/maps/search/?api=1&query=${activePopup.latitude},${activePopup.longitude}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-amber-500 hover:bg-amber-400 text-black font-bold text-[10px] transition"
                >
                  <Compass className="w-3 h-3" />
                  Directions
                </a>
              </div>
            </div>
          </Popup>
        )}
      </Map>

      {/* Map Legend Overlay */}
      <div className="absolute bottom-3 left-3 z-10 bg-surface/90 backdrop-blur-md px-3 py-2 rounded-xl border border-line flex items-center gap-3 text-[11px] text-ink-2 shadow-lg">
        <div className="flex items-center gap-1.5">
          <div className="w-3 h-3 rounded bg-amber-500 border border-line" />
          <span>Cyber Police Station</span>
        </div>
        {userLocation && (
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 rounded-full bg-blue-500 border border-line" />
            <span>Your Location</span>
          </div>
        )}
      </div>
    </div>
  );
}
