"use client";

import { api } from "@/lib/api";
import { useState } from "react";
import SpatialMap from "@/components/map/spatial-map";
import { useAuthStore } from "@/lib/auth-store";
import { Loader2, X } from "lucide-react";
import axios from "axios";
import { Card, Inset } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { Badge } from "@/components/ui/badge";

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
      setClusterSummary("The AI summary for this cluster couldn't be generated.");
    } finally {
      setLoadingSummary(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100dvh-8.5rem)] md:h-[calc(100dvh-7rem)] pt-2">
      <PageHeader
        title="Spatial map"
        sub="Threat density and linked scam clusters across India. Dashed lines connect cases that share an attacker."
        className="mb-4 shrink-0"
      />

      <div className="flex-1 w-full relative min-h-0 flex flex-col lg:flex-row gap-4">
        <div className="flex-1 min-h-64 relative rounded-card overflow-hidden shadow-card">
          <SpatialMap onClusterSelect={handleClusterSelect} />
        </div>

        {selectedCluster && (
          <Card className="lg:w-96 shrink-0 max-h-[45%] lg:max-h-full p-5 flex flex-col overflow-y-auto rise-in">
            <div className="flex justify-between items-start mb-4">
              <div>
                <p className="text-xs text-ink-3 mb-1">Threat cluster</p>
                <h2 className="font-display font-semibold text-base text-ink">
                  Shared {String(selectedCluster.entity_type || "entity").toLowerCase()}
                </h2>
              </div>
              <button
                onClick={() => setSelectedCluster(null)}
                aria-label="Close panel"
                className="p-2 -mr-1 rounded-pill text-ink-3 hover:text-ink hover:bg-surface-2 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3 mb-5">
              <Inset className="p-3">
                <p className="text-xs text-ink-3 mb-1">Common vector</p>
                <p className="text-sm font-medium text-danger break-all tabular">
                  {selectedCluster.entity_value}
                </p>
              </Inset>
              <div className="flex items-center justify-between px-1">
                <span className="text-sm text-ink-2">Linked cases</span>
                <Badge tone="peach">{selectedCluster.case_texts?.length || 0} victims</Badge>
              </div>
            </div>

            <p className="text-xs text-ink-3 mb-2">AI summary</p>
            <Inset className="flex-1 p-4 text-sm leading-relaxed text-ink">
              {loadingSummary ? (
                <span className="flex items-center gap-2 text-ink-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Reading the linked cases…
                </span>
              ) : (
                <span className="whitespace-pre-wrap">{clusterSummary}</span>
              )}
            </Inset>
          </Card>
        )}
      </div>
    </div>
  );
}
