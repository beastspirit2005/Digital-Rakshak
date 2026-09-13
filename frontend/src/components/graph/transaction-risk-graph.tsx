"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import CytoscapeComponent from "react-cytoscapejs";
import cytoscape from "cytoscape";
import { ZoomIn, ZoomOut, Maximize2, RotateCcw } from "lucide-react";

interface TransactionRiskGraphProps {
  nodes: Array<{
    data?: any;
    id?: string;
    label?: string;
    type?: string;
    [key: string]: any;
  }>;
  edges: Array<{
    data?: any;
    id?: string;
    source?: string;
    target?: string;
    label?: string;
    [key: string]: any;
  }>;
  onNodeClick?: (nodeData: any) => void;
  height?: string;
}

export function TransactionRiskGraph({
  nodes,
  edges,
  onNodeClick,
  height = "380px"
}: TransactionRiskGraphProps) {
  const [mounted, setMounted] = useState(false);
  const [elements, setElements] = useState<any[]>([]);
  const cyRef = useRef<cytoscape.Core | null>(null);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    const cyNodes = nodes.map((n) => {
      const data = n.data || n;
      return {
        data: {
          id: data.id,
          label: data.label || data.id,
          type: data.type || "Account",
          ...data,
        },
      };
    });

    const cyEdges = edges.map((e, i) => {
      const data = e.data || e;
      return {
        data: {
          id: data.id || `edge-${i}`,
          source: data.source,
          target: data.target,
          label: data.label || "",
          ...data,
        },
      };
    });

    setElements([...cyNodes, ...cyEdges]);
  }, [nodes, edges]);

  useEffect(() => {
    return () => {
      if (cyRef.current) {
        cyRef.current.stop();
        cyRef.current.destroy();
        cyRef.current = null;
      }
    };
  }, []);

  const handleCy = useCallback(
    (cy: cytoscape.Core) => {
      if (cyRef.current === cy) return;
      cyRef.current = cy;

      cy.on("tap", "node", (evt) => {
        const node = evt.target;
        if (onNodeClick) {
          onNodeClick(node.data());
        }
      });
    },
    [onNodeClick]
  );

  const handleZoomIn = () => {
    if (cyRef.current) {
      cyRef.current.zoom(cyRef.current.zoom() * 1.25);
    }
  };

  const handleZoomOut = () => {
    if (cyRef.current) {
      cyRef.current.zoom(cyRef.current.zoom() * 0.8);
    }
  };

  const handleFit = () => {
    if (cyRef.current) {
      cyRef.current.fit(undefined, 30);
    }
  };

  const handleReset = () => {
    if (cyRef.current) {
      cyRef.current.layout(layout).run();
      cyRef.current.fit(undefined, 30);
    }
  };

  const layout = {
    name: "cose",
    idealEdgeLength: 100,
    nodeOverlap: 20,
    refresh: 20,
    fit: true,
    padding: 30,
    randomize: false,
    componentSpacing: 100,
    nodeRepulsion: 400000,
    edgeElasticity: 100,
    nestingFactor: 5,
    gravity: 80,
    numIter: 800,
    initialTemp: 200,
    coolingFactor: 0.95,
    minTemp: 1.0,
    animate: false,
  };

  const stylesheet: any[] = [
    {
      selector: "node",
      style: {
        label: "data(label)",
        "background-color": "#64748b",
        color: "#cbd5e1",
        "text-valign": "bottom",
        "text-halign": "center",
        "text-margin-y": 6,
        "font-size": "10px",
        "font-weight": 600,
        "text-max-width": "110px",
        "text-wrap": "ellipsis",
        width: 32,
        height: 32,
        "border-width": 2,
        "border-color": "#475569",
        "border-opacity": 0.5,
      },
    },
    {
      selector: 'node[type = "Account"]',
      style: {
        "background-color": "#3b82f6",
        shape: "round-diamond",
        width: 44,
        height: 44,
        "border-color": "#60a5fa",
        "border-width": 3,
        color: "#93c5fd",
        "font-weight": 700,
      },
    },
    {
      selector: 'node[type = "Beneficiary"]',
      style: {
        "background-color": "#f59e0b",
        shape: "ellipse",
        width: 38,
        height: 38,
        "border-color": "#fbbf24",
        "border-width": 2,
        color: "#fcd34d",
      },
    },
    {
      selector: 'node[type = "Transaction"]',
      style: {
        "background-color": "#ec4899",
        shape: "hexagon",
        width: 34,
        height: 34,
        "border-color": "#f472b6",
        "border-width": 2,
        color: "#f9a8d4",
      },
    },
    {
      selector: 'node[type = "Device"]',
      style: {
        "background-color": "#8b5cf6",
        shape: "round-rectangle",
        width: 36,
        height: 36,
        "border-color": "#a78bfa",
        "border-width": 2,
        color: "#c4b5fd",
      },
    },
    {
      selector: "edge",
      style: {
        width: 1.5,
        "line-color": "#475569",
        "target-arrow-color": "#64748b",
        "target-arrow-shape": "triangle",
        "curve-style": "bezier",
        label: "data(label)",
        "font-size": "8px",
        color: "#94a3b8",
        "text-rotation": "autorotate",
        "text-background-opacity": 0.8,
        "text-background-color": "#0f172a",
        "text-background-padding": "2px",
        "text-background-shape": "roundrectangle",
      },
    },
    {
      selector: "node:selected",
      style: {
        "border-width": 4,
        "border-color": "#38bdf8",
        "underlay-color": "#38bdf8",
        "underlay-padding": 4,
        "underlay-opacity": 0.4,
      },
    },
  ];

  if (!mounted) {
    return (
      <div
        className="w-full flex items-center justify-center bg-surface-2/40 rounded-card border border-line/15 text-ink-3 text-xs"
        style={{ height }}
      >
        Loading network topology...
      </div>
    );
  }

  return (
    <div className="relative w-full rounded-card border border-line/15 bg-surface-1 overflow-hidden" style={{ height }}>
      <CytoscapeComponent
        elements={elements}
        layout={layout}
        stylesheet={stylesheet}
        cy={handleCy}
        style={{ width: "100%", height: "100%" }}
      />

      {/* Floating Viewport Controls */}
      <div className="absolute top-3 right-3 flex items-center gap-1 bg-surface-2/80 backdrop-blur-md p-1 rounded-control border border-line/20 shadow-md z-10">
        <button
          onClick={handleZoomIn}
          title="Zoom In"
          className="p-1.5 hover:bg-surface-3/50 text-ink-2 hover:text-ink rounded-sm transition-colors text-xs"
        >
          <ZoomIn className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={handleZoomOut}
          title="Zoom Out"
          className="p-1.5 hover:bg-surface-3/50 text-ink-2 hover:text-ink rounded-sm transition-colors text-xs"
        >
          <ZoomOut className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={handleFit}
          title="Fit Network"
          className="p-1.5 hover:bg-surface-3/50 text-ink-2 hover:text-ink rounded-sm transition-colors text-xs"
        >
          <Maximize2 className="w-3.5 h-3.5" />
        </button>
        <button
          onClick={handleReset}
          title="Reset Layout"
          className="p-1.5 hover:bg-surface-3/50 text-ink-2 hover:text-ink rounded-sm transition-colors text-xs"
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Legend Badge Overlay */}
      <div className="absolute bottom-2.5 left-3 flex flex-wrap items-center gap-3 bg-surface-2/80 backdrop-blur-md px-2.5 py-1.5 rounded-control border border-line/20 text-[11px] text-ink-2 pointer-events-none z-10">
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-sm bg-blue-500 inline-block" />
          <span>Account</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-amber-500 inline-block" />
          <span>Beneficiary</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 bg-pink-500 inline-block" />
          <span>Txn</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-xs bg-purple-500 inline-block" />
          <span>Device</span>
        </div>
      </div>
    </div>
  );
}
