"use client";

import { api } from "@/lib/api";
import { useEffect, useMemo, useState } from "react";
import Map, { Source, Layer, NavigationControl, FullscreenControl } from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";
import axios from "axios";
import { useTheme } from "next-themes";
import { useAuthStore } from "@/lib/auth-store";
import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";

interface SpatialMapProps {
  onClusterSelect?: (cluster: any) => void;
}

/* Map layers render to canvas, so ramp colors are literal values chosen to sit
   on both Carto basemaps: neutral → warm → danger as confidence rises. */
const CONFIDENCE_RAMP = { low: "#8a948c", mid: "#d9a441", high: "#c4553f" };

export default function SpatialMap(props: SpatialMapProps) {
  const [geoData, setGeoData] = useState<any>(null);
  const [clusterData, setClusterData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mapLayer, setMapLayer] = useState<"scams" | "counterfeit">("scams");
  const { token } = useAuthStore();
  const { resolvedTheme } = useTheme();

  const { onClusterSelect } = props;

  useEffect(() => {
    const fetchSpatialData = async () => {
      try {
        setError(null);
        const response = await axios.get(api("/cases/spatial"), {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (!response.data.features || response.data.features.length === 0) {
          setError("No threat data on the map yet.");
        }
        setGeoData(response.data);

        const clusterRes = await axios.get(api("/cases/clusters"), {
          headers: { Authorization: `Bearer ${token}` },
        });
        setClusterData(clusterRes.data);
      } catch (error) {
        console.error("Failed to fetch spatial data", error);
        setError("The map data couldn't be loaded. Check that the backend is running.");
      } finally {
        setLoading(false);
      }
    };

    if (token) fetchSpatialData();
  }, [token]);

  // Heatmap Layer Configuration
  const heatmapLayer: any = useMemo(() => {
    const isCounterfeit = mapLayer === "counterfeit";
    return {
      id: "cases-heat",
      type: "heatmap",
      source: "cases",
      maxzoom: 15,
      paint: {
        "heatmap-weight": ["interpolate", ["linear"], ["get", "confidence_score"], 0, 0, 1, 1],
        "heatmap-intensity": ["interpolate", ["linear"], ["zoom"], 0, 1, 15, 3],
        "heatmap-color": isCounterfeit 
          ? [
              "interpolate", ["linear"], ["heatmap-density"],
              0, "rgba(16,185,129,0)",
              0.2, "rgba(52,211,153,0.35)",
              0.4, "rgba(16,185,129,0.55)",
              0.6, "rgba(5,150,105,0.75)",
              0.8, "rgba(4,120,87,0.85)",
              1, "rgba(2,44,34,0.9)"
            ]
          : [
              "interpolate",
              ["linear"],
              ["heatmap-density"],
              0, "rgba(138,148,140,0)",
              0.3, "rgba(138,148,140,0.35)",
              0.55, "rgba(217,164,65,0.55)",
              0.8, "rgba(217,142,112,0.75)",
              1, "rgba(196,85,63,0.9)",
            ],
        "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 0, 10, 15, 40],
        "heatmap-opacity": ["interpolate", ["linear"], ["zoom"], 7, 1, 15, 0],
      },
    };
  }, [mapLayer]);

  // Point Layer Configuration
  const pointLayer: any = useMemo(() => {
    const isCounterfeit = mapLayer === "counterfeit";
    const ramp = isCounterfeit 
      ? { low: "#6e8a75", mid: "#10b981", high: "#047857" } 
      : CONFIDENCE_RAMP;
    return {
      id: "cases-point",
      type: "circle",
      source: "cases",
      minzoom: 10,
      paint: {
        "circle-radius": ["interpolate", ["linear"], ["zoom"], 10, 4, 16, 12],
        "circle-color": [
          "interpolate",
          ["linear"],
          ["get", "confidence_score"],
          0, ramp.low,
          0.5, ramp.mid,
          1, ramp.high,
        ],
        "circle-stroke-color": resolvedTheme === "dark" ? "#1c211a" : "#fbfaf5",
        "circle-stroke-width": 1.5,
        "circle-opacity": [
          "interpolate",
          ["linear"],
          ["zoom"],
          7, 0,
          10, ["case", ["==", ["get", "is_unknown_location"], true], 0.3, 1],
        ],
      },
    };
  }, [mapLayer, resolvedTheme]);

  // Warning Zone Layer
  const warningZoneLayer: any = useMemo(() => {
    const isCounterfeit = mapLayer === "counterfeit";
    return {
      id: "warning-zones",
      type: "circle",
      source: "cases",
      paint: {
        "circle-radius": ["interpolate", ["linear"], ["zoom"], 3, 20, 10, 80, 15, 200],
        "circle-color": isCounterfeit ? "#10b981" : "#ef4444",
        "circle-opacity": 0.25,
        "circle-blur": 0.8
      }
    };
  }, [mapLayer]);

  // Line Layer for clusters
  const lineLayer: any = useMemo(() => {
    const isCounterfeit = mapLayer === "counterfeit";
    return {
      id: "cases-cluster-lines",
      type: "line",
      source: "clusters",
      paint: {
        "line-color": isCounterfeit ? "#34d399" : CONFIDENCE_RAMP.high,
        "line-width": 2.5,
        "line-opacity": 0.85,
        "line-dasharray": [2, 2],
      },
    };
  }, [mapLayer]);

  const filteredGeoData = useMemo(() => {
    if (!geoData) return null;
    return {
      ...geoData,
      features: geoData.features.filter((f: any) => {
        const isCounterfeit = f.properties.type === "Counterfeit Note";
        return mapLayer === "counterfeit" ? isCounterfeit : !isCounterfeit;
      }),
    };
  }, [geoData, mapLayer]);

  if (loading) {
    return <Skeleton className="w-full h-full rounded-card" />;
  }

  return (
    <div className="relative w-full h-full">
      <Map
        initialViewState={{
          longitude: 78.9629,
          latitude: 20.5937,
          zoom: 3.5,
        }}
        mapStyle={
          resolvedTheme === "dark"
            ? "https://basemaps.cartocdn.com/gl/dark-matter-nolabels-gl-style/style.json"
            : "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json"
        }
        style={{ width: "100%", height: "100%" }}
        interactiveLayerIds={["cases-point", "cases-cluster-lines"]}
        onClick={(e) => {
          if (e.features && e.features.length > 0) {
            const feature = e.features[0];
            if (feature.layer.id === "cases-cluster-lines") {
              const texts =
                typeof feature.properties?.case_texts === "string"
                  ? JSON.parse(feature.properties?.case_texts)
                  : feature.properties?.case_texts;

              if (onClusterSelect) {
                onClusterSelect({
                  entity_type: feature.properties?.entity_type,
                  entity_value: feature.properties?.entity_value,
                  case_texts: texts,
                  is_unknown_location: feature.properties?.is_unknown_location,
                });
              }
            } else {
              alert(
                `Case: ${feature.properties?.case_number}\nType: ${feature.properties?.type}\nStatus: ${feature.properties?.status}`
              );
            }
          }
        }}
      >
        <NavigationControl position="top-right" />
        <FullscreenControl position="top-right" />

        {/* layer switch */}
        <div className="absolute top-3 left-3 z-10 bg-surface p-1 rounded-control shadow-card flex gap-1">
          {(
            [
              { id: "scams", label: "Cyber scams" },
              { id: "counterfeit", label: "Fake currency" },
            ] as const
          ).map((layer) => (
            <button
              key={layer.id}
              onClick={() => setMapLayer(layer.id)}
              className={cn(
                "px-3 h-8 text-xs font-medium rounded-[6px] transition-colors duration-150",
                mapLayer === layer.id
                  ? "bg-surface-3 text-ink"
                  : "text-ink-2 hover:text-ink hover:bg-surface-2"
              )}
            >
              {layer.label}
            </button>
          ))}
        </div>

        {/* confidence legend */}
        <div className="absolute bottom-3 left-3 z-10 bg-surface px-3 py-2 rounded-control shadow-card flex items-center gap-2 text-xs text-ink-2">
          <span>Low</span>
          <span
            className="h-1.5 w-16 rounded-pill"
            style={{
              background: `linear-gradient(to right, ${CONFIDENCE_RAMP.low}, ${CONFIDENCE_RAMP.mid}, ${CONFIDENCE_RAMP.high})`,
            }}
          />
          <span>High confidence</span>
        </div>

        {filteredGeoData && !error && (
          <Source id="cases" type="geojson" data={filteredGeoData}>
            <Layer {...warningZoneLayer} />
            <Layer {...heatmapLayer} />
            <Layer {...pointLayer} />
          </Source>
        )}

        {clusterData && !error && (
          <Source id="clusters" type="geojson" data={clusterData}>
            <Layer {...lineLayer} />
          </Source>
        )}
      </Map>

      {error && (
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-bg/70">
          <div className="bg-surface rounded-card shadow-card p-6 text-center max-w-sm">
            <h3 className="font-display font-semibold text-base text-ink mb-1.5">
              Map unavailable
            </h3>
            <p className="text-sm text-ink-2">{error}</p>
          </div>
        </div>
      )}
    </div>
  );
}
