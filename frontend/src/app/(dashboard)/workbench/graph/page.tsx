"use client";

import { api } from "@/lib/api";
import { useEffect, useState, useMemo } from "react";
import { NetworkVisualizer } from "@/components/graph/network-visualizer";
import { Search, Loader2 } from "lucide-react";
import axios from "axios";
import { useAuthStore } from "@/lib/auth-store";
import { Card, Inset } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";
import { Badge } from "@/components/ui/badge";

const LEGEND = [
  { type: "Case", shape: "hexagon", color: "var(--chart-3)", label: "Scam case" },
  { type: "PhoneNumber", shape: "square", color: "var(--chart-2)", label: "Phone number" },
  { type: "BankAccount", shape: "diamond", color: "var(--chart-1)", label: "Bank account" },
];

export default function GraphExplorerPage() {
  const [nodes, setNodes] = useState<any[]>([]);
  const [edges, setEdges] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [selectedCaseDetails, setSelectedCaseDetails] = useState<any>(null);
  const { token } = useAuthStore();

  useEffect(() => {
    const fetchGraph = async () => {
      try {
        const response = await axios.get(api("/graph/network"), {
          headers: { Authorization: `Bearer ${token}` },
        });
        setNodes(response.data.nodes || []);
        setEdges(response.data.links || []);
      } catch (err) {
        console.error("Failed to load graph", err);
      } finally {
        setLoading(false);
      }
    };

    if (token) fetchGraph();
  }, [token]);

  useEffect(() => {
    if (!selectedNode || selectedNode.type !== "Case") {
      setSelectedCaseDetails(null);
      return;
    }
    const fetchCaseDetails = async () => {
      try {
        const res = await axios.get(api(`/cases/${selectedNode.value}`), {
          headers: { Authorization: `Bearer ${token}` },
        });
        setSelectedCaseDetails(res.data);
      } catch (err) {
        console.error("Failed to load case details", err);
      }
    };
    fetchCaseDetails();
  }, [selectedNode, token]);

  const stats = useMemo(() => {
    const caseNodes = nodes.filter((n) => n.label === "Case");
    const entityNodes = nodes.filter((n) => n.label !== "Case");

    const entityEdgeCount: Record<string, number> = {};
    edges.forEach((e) => {
      const entityId =
        nodes.find((n) => n.id === e.target && n.label !== "Case")?.id ||
        nodes.find((n) => n.id === e.source && n.label !== "Case")?.id;
      if (entityId) {
        entityEdgeCount[entityId] = (entityEdgeCount[entityId] || 0) + 1;
      }
    });

    const clusterSizes = Object.values(entityEdgeCount).filter((c) => c > 1);
    const maxCluster = clusterSizes.length > 0 ? Math.max(...clusterSizes) : 0;

    return {
      totalCases: caseNodes.length,
      totalEntities: entityNodes.length,
      totalLinks: edges.length,
      clusters: clusterSizes.length,
      maxCluster,
    };
  }, [nodes, edges]);

  const filteredNodes = useMemo(() => {
    if (!filter.trim()) return nodes;
    const q = filter.toLowerCase();
    const matchingIds = new Set<string>();

    nodes.forEach((n) => {
      if ((n.value || "").toLowerCase().includes(q) || (n.label || "").toLowerCase().includes(q)) {
        matchingIds.add(n.id);
      }
    });

    edges.forEach((e) => {
      if (matchingIds.has(e.source)) matchingIds.add(e.target);
      if (matchingIds.has(e.target)) matchingIds.add(e.source);
    });

    return nodes.filter((n) => matchingIds.has(n.id));
  }, [nodes, edges, filter]);

  const filteredEdges = useMemo(() => {
    const nodeIds = new Set(filteredNodes.map((n) => n.id));
    return edges.filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target));
  }, [filteredNodes, edges]);

  const graphStats = [
    { label: "Cases", value: stats.totalCases },
    { label: "Shared entities", value: stats.totalEntities },
    { label: "Connections", value: stats.totalLinks },
    { label: "Scam clusters", value: stats.clusters },
    { label: "Largest ring", value: `${stats.maxCluster} victims` },
  ];

  return (
    <div className="flex flex-col lg:h-[calc(100dvh-7rem)] pt-2 gap-4">
      <PageHeader
        title="Graph explorer"
        sub="Cases that share a phone number or bank account belong to the same operation."
        actions={
          <div className="relative">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-3" />
            <input
              type="search"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="Filter nodes, e.g. +91 98…"
              className="h-10 pl-10 pr-4 w-full sm:w-64 rounded-pill bg-surface text-sm text-ink placeholder:text-ink-3 border border-transparent hover:border-line focus:border-accent-text focus:outline-none transition-colors"
            />
          </div>
        }
      />

      {!loading && (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 shrink-0">
          {graphStats.map((s) => (
            <div key={s.label} className="rounded-card bg-surface-2 px-4 py-3">
              <p className="text-xs text-ink-3">{s.label}</p>
              <p className="font-display font-semibold text-lg text-ink tabular mt-0.5">{s.value}</p>
            </div>
          ))}
        </div>
      )}

      <div className="flex-1 flex flex-col lg:flex-row gap-4 min-h-0">
        <Card className="flex-1 relative overflow-hidden min-h-96">
          {loading ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center text-sm text-ink-2 gap-3">
              <Loader2 className="w-6 h-6 animate-spin" />
              Querying the intelligence graph…
            </div>
          ) : (
            <NetworkVisualizer
              nodes={filteredNodes}
              edges={filteredEdges}
              onNodeClick={setSelectedNode}
            />
          )}
        </Card>

        <Card className="lg:w-80 shrink-0 flex flex-col overflow-hidden max-h-[50vh] lg:max-h-none">
          {selectedNode ? (
            <div className="p-5 flex-1 overflow-y-auto flex flex-col gap-4">
              <div className="flex justify-between items-start">
                <p className="text-xs text-ink-3">Node details</p>
                <button
                  onClick={() => setSelectedNode(null)}
                  className="text-xs text-ink-2 hover:text-ink underline underline-offset-4"
                >
                  Close
                </button>
              </div>

              <Inset className="p-4">
                <div className="flex items-center gap-2 mb-1.5">
                  <span
                    className="w-2.5 h-2.5 rounded-[3px]"
                    style={{
                      backgroundColor:
                        LEGEND.find((l) => l.type === selectedNode.type)?.color ?? "var(--ink-3)",
                    }}
                  />
                  <span className="text-sm font-medium text-ink">{selectedNode.type}</span>
                </div>
                <p className="text-sm text-ink break-all">{selectedNode.label}</p>
              </Inset>

              {selectedNode.type === "Case" && selectedCaseDetails ? (
                <div className="space-y-4">
                  <div>
                    <p className="text-xs text-ink-3 mb-1.5">AI reasoning</p>
                    <p className="text-sm text-ink leading-relaxed">
                      {selectedCaseDetails.ai_decision?.reasoning || "No reasoning recorded."}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-ink-3 mb-1.5">Classification</p>
                    <Badge tone="peach" className="capitalize">
                      {(selectedCaseDetails.ai_decision?.scam_type_classification || "Unknown").replace(/_/g, " ")}
                    </Badge>
                  </div>
                  <div>
                    <p className="text-xs text-ink-3 mb-1.5">What to do</p>
                    <ul className="list-disc pl-4 space-y-1">
                      {selectedCaseDetails.ai_decision?.preventative_measures?.map(
                        (pm: string, i: number) => (
                          <li key={i} className="text-sm text-ink-2">{pm}</li>
                        )
                      ) || <li className="text-sm text-ink-2">No steps generated.</li>}
                    </ul>
                  </div>
                </div>
              ) : selectedNode.type !== "Case" ? (
                <p className="text-sm text-ink-2 leading-relaxed">
                  This is a shared entity. Every case connected to it belongs to the same
                  organized network — select a connected case node to read its analysis.
                </p>
              ) : (
                <div className="flex items-center justify-center p-8">
                  <Loader2 className="w-5 h-5 animate-spin text-ink-3" />
                </div>
              )}
            </div>
          ) : (
            <div className="p-5 flex-1 overflow-y-auto flex flex-col gap-5">
              <p className="text-xs text-ink-3">Legend</p>

              <div className="space-y-3">
                {LEGEND.map((item) => (
                  <div key={item.type} className="flex items-center gap-3">
                    <span
                      className="w-3.5 h-3.5 shrink-0"
                      style={{
                        backgroundColor: item.color,
                        borderRadius: item.shape === "square" ? 3 : undefined,
                        clipPath:
                          item.shape === "hexagon"
                            ? "polygon(25% 0, 75% 0, 100% 50%, 75% 100%, 25% 100%, 0 50%)"
                            : item.shape === "diamond"
                              ? "polygon(50% 0, 100% 50%, 50% 100%, 0 50%)"
                              : undefined,
                      }}
                    />
                    <span className="text-sm text-ink">{item.label}</span>
                  </div>
                ))}
              </div>

              <div className="border-t border-line" />
              <div>
                <p className="text-xs text-ink-3 mb-2">How to read it</p>
                <p className="text-sm text-ink-2 leading-relaxed">
                  When several cases connect to one phone number or account, a single scammer is
                  targeting multiple victims. Tap any node for detail.
                </p>
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
