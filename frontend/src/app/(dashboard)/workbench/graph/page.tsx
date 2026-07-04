"use client";


import { api } from "@/lib/api";
import { useEffect, useState, useMemo } from "react";
import { NetworkVisualizer } from "@/components/graph/network-visualizer";
import { Network, Search, Loader2, Hexagon, Square, ArrowRight, AlertTriangle, Phone, Landmark, Globe, ShieldAlert } from "lucide-react";
import axios from "axios";
import { useAuthStore } from "@/lib/auth-store";

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
          headers: { Authorization: `Bearer ${token}` }
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
          headers: { Authorization: `Bearer ${token}` }
        });
        setSelectedCaseDetails(res.data);
      } catch (err) {
        console.error("Failed to load case details", err);
      }
    };
    fetchCaseDetails();
  }, [selectedNode, token]);

  // Compute stats
  const stats = useMemo(() => {
    const caseNodes = nodes.filter(n => n.label === 'Case');
    const entityNodes = nodes.filter(n => n.label !== 'Case');
    
    // Find clusters by counting edges per entity
    const entityEdgeCount: Record<string, number> = {};
    edges.forEach(e => {
      // The entity is usually the target
      const entityId = nodes.find(n => n.id === e.target && n.label !== 'Case')?.id 
                    || nodes.find(n => n.id === e.source && n.label !== 'Case')?.id;
      if (entityId) {
        entityEdgeCount[entityId] = (entityEdgeCount[entityId] || 0) + 1;
      }
    });

    const clusterSizes = Object.values(entityEdgeCount).filter(c => c > 1);
    const maxCluster = clusterSizes.length > 0 ? Math.max(...clusterSizes) : 0;

    return {
      totalCases: caseNodes.length,
      totalEntities: entityNodes.length,
      totalLinks: edges.length,
      clusters: clusterSizes.length,
      maxCluster,
    };
  }, [nodes, edges]);

  // Filter nodes
  const filteredNodes = useMemo(() => {
    if (!filter.trim()) return nodes;
    const q = filter.toLowerCase();
    const matchingIds = new Set<string>();
    
    nodes.forEach(n => {
      if ((n.value || '').toLowerCase().includes(q) || (n.label || '').toLowerCase().includes(q)) {
        matchingIds.add(n.id);
      }
    });

    // Also include connected nodes
    edges.forEach(e => {
      if (matchingIds.has(e.source)) matchingIds.add(e.target);
      if (matchingIds.has(e.target)) matchingIds.add(e.source);
    });

    return nodes.filter(n => matchingIds.has(n.id));
  }, [nodes, edges, filter]);

  const filteredEdges = useMemo(() => {
    const nodeIds = new Set(filteredNodes.map(n => n.id));
    return edges.filter(e => nodeIds.has(e.source) && nodeIds.has(e.target));
  }, [filteredNodes, edges]);

  return (
    <div className="h-[calc(100vh-8rem)] flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <Network className="w-8 h-8 text-blue-500" />
            Cyber Threat Intelligence Graph
          </h1>
          <p className="text-muted-foreground mt-1">
            Interactive Neo4j visualization — connected nodes reveal organized scam campaigns.
          </p>
        </div>
        
        <div className="relative w-72">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input 
            type="text"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Filter nodes (e.g., +91987...)" 
            className="w-full pl-10 pr-4 py-2 bg-card border border-border rounded-xl text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition-all"
          />
        </div>
      </div>

      {/* Stats Bar */}
      {!loading && (
        <div className="grid grid-cols-5 gap-3">
          {[
            { label: 'Total Cases', value: stats.totalCases, color: 'text-red-500', bg: 'bg-red-500/10' },
            { label: 'Shared Entities', value: stats.totalEntities, color: 'text-blue-500', bg: 'bg-blue-500/10' },
            { label: 'Connections', value: stats.totalLinks, color: 'text-slate-500', bg: 'bg-slate-500/10' },
            { label: 'Scam Clusters', value: stats.clusters, color: 'text-amber-500', bg: 'bg-amber-500/10' },
            { label: 'Largest Ring', value: `${stats.maxCluster} victims`, color: 'text-purple-500', bg: 'bg-purple-500/10' },
          ].map(s => (
            <div key={s.label} className={`${s.bg} rounded-xl px-4 py-3 border border-border`}>
              <p className="text-xs text-muted-foreground">{s.label}</p>
              <p className={`text-xl font-bold ${s.color}`}>{s.value}</p>
            </div>
          ))}
        </div>
      )}

      {/* Main Graph + Legend */}
      <div className="flex-1 flex gap-4 min-h-0">
        {/* Graph */}
        <div className="flex-1 glass-panel relative p-2">
          {loading ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center text-muted-foreground">
              <Loader2 className="w-8 h-8 animate-spin mb-4 text-blue-500" />
              Querying Neo4j Graph Database...
            </div>
          ) : (
            <NetworkVisualizer 
              nodes={filteredNodes} 
              edges={filteredEdges} 
              onNodeClick={setSelectedNode}
            />
          )}
        </div>

        <div className="w-80 glass-panel flex flex-col overflow-hidden">
          {selectedNode ? (
            <div className="p-5 flex-1 overflow-y-auto flex flex-col gap-4">
              <div className="flex justify-between items-start">
                <h3 className="font-semibold text-foreground text-sm uppercase tracking-wider">Node Details</h3>
                <button onClick={() => setSelectedNode(null)} className="text-xs text-muted-foreground hover:text-foreground">Close</button>
              </div>
              
              <div className="bg-muted/50 p-4 rounded-xl border border-border">
                <div className="flex items-center gap-2 mb-2">
                  <div className={`w-3 h-3 rounded-full ${selectedNode.type === 'Case' ? 'bg-red-500' : 'bg-blue-500'}`} />
                  <span className="font-semibold text-foreground">{selectedNode.type}</span>
                </div>
                <p className="text-sm font-medium text-foreground break-all">{selectedNode.label}</p>
                <p className="text-xs text-muted-foreground mt-1">ID: {selectedNode.id}</p>
              </div>

              {selectedNode.type === "Case" && selectedCaseDetails ? (
                <div className="space-y-4">
                  <div>
                    <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider mb-2">AI Reasoning</p>
                    <div className="bg-primary/10 border border-primary/20 p-3 rounded-lg text-sm text-foreground">
                      {selectedCaseDetails.ai_decision?.reasoning || "No reasoning available."}
                    </div>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider mb-2">Scam Classification</p>
                    <div className="flex items-center gap-2">
                      <ShieldAlert className="w-4 h-4 text-amber-500" />
                      <span className="text-sm font-medium">{selectedCaseDetails.ai_decision?.scam_type_classification || "Unknown"}</span>
                    </div>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider mb-2">Prevention Strategy</p>
                    <ul className="list-disc pl-4 space-y-1">
                      {selectedCaseDetails.ai_decision?.preventative_measures?.map((pm: string, i: number) => (
                        <li key={i} className="text-sm text-muted-foreground">{pm}</li>
                      )) || <li className="text-sm text-muted-foreground">No strategies generated.</li>}
                    </ul>
                  </div>
                </div>
              ) : selectedNode.type !== "Case" ? (
                <div className="space-y-4">
                  <div className="bg-amber-500/10 border border-amber-500/20 p-3 rounded-lg flex gap-2 items-start">
                    <AlertTriangle className="w-4 h-4 text-amber-500 shrink-0 mt-0.5" />
                    <p className="text-xs text-amber-500/90 leading-relaxed">
                      This is a shared entity node (IoC). Cases connected to this node belong to the same organized scam network.
                    </p>
                  </div>
                  <p className="text-xs text-muted-foreground">Select a connected Case node (Red Hexagon) to view the AI's deep analysis and prevention strategy for this cluster.</p>
                </div>
              ) : (
                <div className="flex items-center justify-center p-8">
                  <Loader2 className="w-6 h-6 animate-spin text-primary" />
                </div>
              )}
            </div>
          ) : (
            <div className="p-5 flex-1 overflow-y-auto flex flex-col gap-5">
              <h3 className="font-semibold text-foreground text-sm uppercase tracking-wider">Legend</h3>
              
              <div className="space-y-3">
                <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">Node Types</p>
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-red-500 rounded-md flex items-center justify-center"><Hexagon className="w-5 h-5 text-white" /></div>
                  <div><p className="text-sm font-medium text-foreground">Scam Case</p></div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-blue-500 rounded-md flex items-center justify-center"><Phone className="w-5 h-5 text-white" /></div>
                  <div><p className="text-sm font-medium text-foreground">Phone Number</p></div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-green-500 rounded-md flex items-center justify-center"><Landmark className="w-5 h-5 text-white" /></div>
                  <div><p className="text-sm font-medium text-foreground">Bank Account</p></div>
                </div>
              </div>

              <div className="border-t border-border" />
              <div className="space-y-2">
                <p className="text-xs text-muted-foreground font-medium uppercase tracking-wider">How to Read</p>
                <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="w-4 h-4 text-amber-500 mt-0.5 shrink-0" />
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      When multiple <span className="text-red-500 font-medium">red cases</span> connect to the same <span className="text-blue-500 font-medium">blue entity</span>, it means <span className="text-foreground font-semibold">one scammer is targeting multiple victims</span>.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
