"use client";


import { api } from "@/lib/api";
import { useState } from "react";
import SpatialMap from "@/components/map/spatial-map";
import { useAuthStore } from "@/lib/auth-store";
import { Loader2, ShieldAlert, X } from "lucide-react";
import axios from "axios";

export default function SpatialMapPage() {
  const [selectedCluster, setSelectedCluster] = useState<any>(null);
  const [clusterSummary, setClusterSummary] = useState<string | null>(null);
  const [loadingSummary, setLoadingSummary] = useState(false);
  const { token } = useAuthStore();

  const handleClusterSelect = async (cluster: any) => {
    setSelectedCluster(cluster);
    setClusterSummary(null);
    setLoadingSummary(true);

    try {
      const res = await axios.post(
        api("/cases/cluster/summary"),
        { case_texts: cluster.case_texts },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setClusterSummary(res.data.summary);
    } catch (err) {
      console.error("Failed to generate summary", err);
      setClusterSummary("Failed to generate AI summary for this cluster.");
    } finally {
      setLoadingSummary(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-2rem)]">
      <div className="flex flex-col gap-2 mb-4 shrink-0">
        <h1 className="text-3xl font-bold tracking-tight">Spatial Map</h1>
        <p className="text-muted-foreground">Geospatial visualization of cyber threat density and interconnected clusters across India.</p>
      </div>

      <div className="flex-1 w-full relative min-h-0 flex gap-4">
        {/* Map Container */}
        <div className={`transition-all duration-300 ${selectedCluster ? 'w-2/3' : 'w-full'} h-full relative rounded-xl overflow-hidden shadow-xl border border-border`}>
          <SpatialMap onClusterSelect={handleClusterSelect} />
        </div>

        {/* AI Cluster Summary Side Panel */}
        {selectedCluster && (
          <div className="w-1/3 h-full glass-panel border border-border rounded-xl p-6 flex flex-col overflow-y-auto animate-in slide-in-from-right-8 fade-in">
            <div className="flex justify-between items-start mb-6">
              <div className="flex items-center gap-2 text-primary">
                <ShieldAlert className="w-5 h-5 text-red-500" />
                <h2 className="text-xl font-bold">Threat Cluster Detected</h2>
              </div>
              <button 
                onClick={() => setSelectedCluster(null)}
                className="p-1 hover:bg-white/10 rounded-full transition-colors"
              >
                <X className="w-5 h-5 text-muted-foreground" />
              </button>
            </div>

            <div className="space-y-4 mb-6">
              <div className="p-3 bg-black/40 rounded-lg border border-white/5">
                <p className="text-sm text-muted-foreground mb-1">Common Vector</p>
                <p className="font-mono text-red-400 font-semibold break-all">
                  [{selectedCluster.entity_type}] {selectedCluster.entity_value}
                </p>
              </div>
              
              <div className="p-3 bg-black/40 rounded-lg border border-white/5">
                <p className="text-sm text-muted-foreground mb-1">Linked Cases</p>
                <p className="font-bold">{selectedCluster.case_texts?.length || 0} victims</p>
              </div>
            </div>

            <h3 className="font-semibold text-lg mb-3 flex items-center gap-2">
              <span className="bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">Ollama CTI Summary</span>
            </h3>
            
            <div className="flex-1 p-4 bg-black/30 rounded-lg border border-border/50 text-sm leading-relaxed">
              {loadingSummary ? (
                <div className="flex flex-col items-center justify-center h-32 gap-3 text-muted-foreground">
                  <Loader2 className="w-6 h-6 animate-spin text-primary" />
                  <p className="animate-pulse">Analyzing cluster footprint...</p>
                </div>
              ) : (
                <p className="whitespace-pre-wrap">{clusterSummary}</p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
