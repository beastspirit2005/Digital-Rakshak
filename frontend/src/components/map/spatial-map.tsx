"use client";


import { api } from "@/lib/api";
import { useEffect, useMemo, useState } from "react";
import Map, { Source, Layer, NavigationControl, FullscreenControl } from "react-map-gl/maplibre";
import "maplibre-gl/dist/maplibre-gl.css";
import axios from "axios";
import { useAuthStore } from "@/lib/auth-store";
import { Loader2 } from "lucide-react";

interface SpatialMapProps {
  onClusterSelect?: (cluster: any) => void;
}

export default function SpatialMap(props: SpatialMapProps) {
  const [geoData, setGeoData] = useState<any>(null);
  const [clusterData, setClusterData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { token } = useAuthStore();
  
  // Passed up to the parent page.tsx
  const { onClusterSelect } = props;

  useEffect(() => {
    const fetchSpatialData = async () => {
      try {
        setError(null);
        const response = await axios.get(api("/cases/spatial"), {
          headers: { Authorization: `Bearer ${token}` }
        });
        
        if (!response.data.features || response.data.features.length === 0) {
          setError("No threat data available on the map.");
        }
        setGeoData(response.data);

        // Also fetch spatial clusters
        const clusterRes = await axios.get(api("/cases/clusters"), {
          headers: { Authorization: `Bearer ${token}` }
        });
        setClusterData(clusterRes.data);

      } catch (error) {
        console.error("Failed to fetch spatial data", error);
        setError("Failed to load spatial data. Ensure backend is running.");
      } finally {
        setLoading(false);
      }
    };
    
    if (token) fetchSpatialData();
  }, [token]);

  // Heatmap Layer Configuration
  const heatmapLayer: any = useMemo(() => ({
    id: "cases-heat",
    type: "heatmap",
    source: "cases",
    maxzoom: 15,
    paint: {
      "heatmap-weight": ["interpolate", ["linear"], ["get", "confidence_score"], 0, 0, 1, 1],
      "heatmap-intensity": ["interpolate", ["linear"], ["zoom"], 0, 1, 15, 3],
      "heatmap-color": [
        "interpolate", ["linear"], ["heatmap-density"],
        0, "rgba(33,102,172,0)",
        0.2, "rgb(103,169,207)",
        0.4, "rgb(209,229,240)",
        0.6, "rgb(253,219,199)",
        0.8, "rgb(239,138,98)",
        1, "rgb(220,57,18)"
      ],
      "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 0, 10, 15, 40],
      "heatmap-opacity": ["interpolate", ["linear"], ["zoom"], 7, 1, 15, 0],
    }
  }), []);

  // Point Layer Configuration
  const pointLayer: any = useMemo(() => ({
    id: "cases-point",
    type: "circle",
    source: "cases",
    minzoom: 10,
    paint: {
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 10, 4, 16, 12],
      "circle-color": [
        "interpolate", ["linear"], ["get", "confidence_score"],
        0, "#3b82f6",
        0.5, "#eab308",
        1, "#ef4444"
      ],
      "circle-stroke-color": "#ffffff",
      "circle-stroke-width": 1,
      "circle-opacity": [
        "interpolate", ["linear"], ["zoom"],
        7, 0,
        10, ["case", ["==", ["get", "is_unknown_location"], true], 0.3, 1]
      ]
    }
  }), []);

  // Line Layer for clusters
  const lineLayer: any = useMemo(() => ({
    id: "cases-cluster-lines",
    type: "line",
    source: "clusters",
    paint: {
      "line-color": "#ff0044",
      "line-width": 3,
      "line-opacity": 0.8,
      "line-dasharray": [2, 2]
    }
  }), []);

  if (loading) {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center bg-card rounded-2xl border border-border">
        <Loader2 className="w-8 h-8 animate-spin text-primary mb-4" />
        <p className="text-sm text-muted-foreground">Initializing Spatial Canvas...</p>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full">
      <Map
        initialViewState={{
          longitude: 78.9629,
          latitude: 20.5937,
          zoom: 3.5
        }}
        mapStyle="https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json"
        style={{ width: "100%", height: "100%", borderRadius: "1rem" }}
        interactiveLayerIds={["cases-point", "cases-cluster-lines"]}
        onClick={(e) => {
          if (e.features && e.features.length > 0) {
            const feature = e.features[0];
            if (feature.layer.id === "cases-cluster-lines") {
               // Parse the stringified JSON properties back into objects if needed
               const texts = typeof feature.properties?.case_texts === 'string' 
                 ? JSON.parse(feature.properties?.case_texts) 
                 : feature.properties?.case_texts;
                 
               if (onClusterSelect) {
                 onClusterSelect({
                   entity_type: feature.properties?.entity_type,
                   entity_value: feature.properties?.entity_value,
                   case_texts: texts,
                   is_unknown_location: feature.properties?.is_unknown_location
                 });
               }
            } else {
               alert(`Case: ${feature.properties?.case_number}\nType: ${feature.properties?.type}\nStatus: ${feature.properties?.status}`);
            }
          }
        }}
      >
        <NavigationControl position="top-right" />
        <FullscreenControl position="top-right" />

        {geoData && !error && (
          <Source id="cases" type="geojson" data={geoData}>
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
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-background/80 backdrop-blur-sm rounded-2xl">
          <div className="glass-panel p-6 rounded-2xl border border-border text-center max-w-md shadow-2xl">
            <h3 className="text-xl font-bold mb-2 text-primary">Map Unavailable</h3>
            <p className="text-muted-foreground">{error}</p>
          </div>
        </div>
      )}
    </div>
  );
}
