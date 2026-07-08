"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import CytoscapeComponent from "react-cytoscapejs";
import cytoscape from "cytoscape";

/* Cytoscape paints to canvas, so CSS variables must be resolved to literal
   values — and re-resolved when the theme class flips. */
function useResolvedTokens(names: string[]) {
  const [tokens, setTokens] = useState<Record<string, string> | null>(null);

  useEffect(() => {
    const resolve = () => {
      const styles = getComputedStyle(document.documentElement);
      const next: Record<string, string> = {};
      for (const name of names) {
        next[name] = styles.getPropertyValue(name).trim();
      }
      setTokens(next);
    };
    resolve();
    const observer = new MutationObserver(resolve);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
    return () => observer.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [names.join(",")]);

  return tokens;
}

const TOKEN_NAMES = ["--chart-1", "--chart-2", "--chart-3", "--ink-2", "--ink-3", "--accent", "--line"];

export function NetworkVisualizer({
  nodes,
  edges,
  onNodeClick,
}: {
  nodes: any[];
  edges: any[];
  onNodeClick?: (nodeData: any) => void;
}) {
  const [elements, setElements] = useState<any[]>([]);
  const cyRef = useRef<cytoscape.Core | null>(null);
  const tokens = useResolvedTokens(TOKEN_NAMES);

  useEffect(() => {
    const cyNodes = nodes.map((n) => ({
      data: {
        id: n.id,
        label:
          n.label === "Case"
            ? `Case ${(n.value || "").substring(0, 12)}`
            : n.value || n.label || "Unknown",
        type: n.label,
        value: n.value,
        ...n.properties,
      },
    }));

    const cyEdges = edges.map((e, i) => ({
      data: { id: e.id || `edge-${i}`, source: e.source, target: e.target, label: e.type },
    }));

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
      cy.on("tap", "node", function (evt) {
        const node = evt.target;
        if (onNodeClick) onNodeClick(node.data());
      });
    },
    [onNodeClick]
  );

  const layout = {
    name: "cose",
    idealEdgeLength: 120,
    nodeOverlap: 20,
    refresh: 20,
    fit: true,
    padding: 40,
    randomize: false,
    componentSpacing: 120,
    nodeRepulsion: 500000,
    edgeElasticity: 100,
    nestingFactor: 5,
    gravity: 80,
    numIter: 1000,
    initialTemp: 200,
    coolingFactor: 0.95,
    minTemp: 1.0,
    animate: false,
  };

  if (!tokens) return null;

  const style: any[] = [
    {
      selector: "node",
      style: {
        label: "data(label)",
        "background-color": tokens["--ink-3"],
        color: tokens["--ink-2"],
        "text-valign": "bottom",
        "text-halign": "center",
        "text-margin-y": 8,
        "font-size": "10px",
        "font-weight": 600,
        "text-max-width": "80px",
        "text-wrap": "ellipsis",
        width: 32,
        height: 32,
        "border-width": 2,
        "border-color": tokens["--ink-3"],
        "border-opacity": 0.15,
      },
    },
    {
      selector: 'node[type = "Case"]',
      style: {
        "background-color": tokens["--chart-3"],
        shape: "hexagon",
        width: 40,
        height: 40,
        "border-color": tokens["--chart-3"],
        "border-opacity": 0.25,
        "border-width": 3,
      },
    },
    {
      selector: 'node[type = "PhoneNumber"]',
      style: {
        "background-color": tokens["--chart-2"],
        shape: "round-rectangle",
        "border-color": tokens["--chart-2"],
        "border-opacity": 0.25,
        width: 36,
        height: 36,
      },
    },
    {
      selector: 'node[type = "BankAccount"]',
      style: {
        "background-color": tokens["--chart-1"],
        shape: "diamond",
        "border-color": tokens["--chart-1"],
        "border-opacity": 0.25,
        width: 36,
        height: 36,
      },
    },
    {
      selector: "edge",
      style: {
        width: 2,
        "line-color": tokens["--ink-3"],
        "target-arrow-color": tokens["--ink-3"],
        "target-arrow-shape": "triangle",
        "curve-style": "bezier",
        opacity: 0.5,
        label: "data(label)",
        "font-size": "8px",
        color: tokens["--ink-3"],
        "text-rotation": "autorotate",
        "text-margin-y": -8,
      },
    },
    {
      selector: "node:active",
      style: {
        "overlay-opacity": 0.1,
        "overlay-color": tokens["--accent"],
      },
    },
    {
      selector: "node:selected",
      style: {
        "border-width": 4,
        "border-color": tokens["--accent"],
      },
    },
  ];

  if (elements.length === 0)
    return (
      <div className="h-full flex items-center justify-center text-sm text-ink-2">
        No graph data to show yet.
      </div>
    );

  return (
    <div className="w-full h-full overflow-hidden relative">
      <CytoscapeComponent
        key={JSON.stringify(tokens)}
        elements={elements}
        style={{ width: "100%", height: "100%" }}
        layout={layout}
        stylesheet={style}
        wheelSensitivity={0.1}
        cy={handleCy}
      />
    </div>
  );
}
