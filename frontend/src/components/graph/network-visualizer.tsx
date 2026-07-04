"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import CytoscapeComponent from "react-cytoscapejs";
import cytoscape from "cytoscape";

export function NetworkVisualizer({ nodes, edges, onNodeClick }: { nodes: any[], edges: any[], onNodeClick?: (nodeData: any) => void }) {
  const [elements, setElements] = useState<any[]>([]);
  const cyRef = useRef<cytoscape.Core | null>(null);

  useEffect(() => {
    const cyNodes = nodes.map(n => ({
      data: { 
        id: n.id, 
        label: n.label === 'Case' 
          ? `Case ${(n.value || '').substring(0, 12)}` 
          : (n.value || n.label || 'Unknown'),
        type: n.label, 
        value: n.value,
        ...n.properties 
      }
    }));
    
    const cyEdges = edges.map((e, i) => ({
      data: { id: e.id || `edge-${i}`, source: e.source, target: e.target, label: e.type }
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

  const handleCy = useCallback((cy: cytoscape.Core) => {
    if (cyRef.current === cy) return; // Prevent multiple listeners
    cyRef.current = cy;
    cy.on('tap', 'node', function(evt){
      const node = evt.target;
      if (onNodeClick) onNodeClick(node.data());
    });
  }, [onNodeClick]);

  const layout = {
    name: 'cose',
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
    animate: false
  };

  const style: cytoscape.Stylesheet[] = [
    {
      selector: 'node',
      style: {
        'label': 'data(label)',
        'background-color': '#8b5cf6',
        'color': '#64748b',
        'text-valign': 'bottom',
        'text-halign': 'center',
        'text-margin-y': 8,
        'font-size': '10px',
        'font-weight': 600,
        'text-max-width': '80px',
        'text-wrap': 'ellipsis',
        'width': 32,
        'height': 32,
        'border-width': 2,
        'border-color': '#8b5cf6',
        'border-opacity': 0.15,
      }
    },
    {
      selector: 'node[type = "Case"]',
      style: {
        'background-color': '#ef4444',
        'shape': 'hexagon',
        'width': 40,
        'height': 40,
        'border-color': '#ef4444',
        'border-opacity': 0.25,
        'border-width': 3,
      }
    },
    {
      selector: 'node[type = "PhoneNumber"]',
      style: {
        'background-color': '#3b82f6',
        'shape': 'round-rectangle',
        'border-color': '#3b82f6',
        'border-opacity': 0.25,
        'width': 36,
        'height': 36,
      }
    },
    {
      selector: 'node[type = "BankAccount"]',
      style: {
        'background-color': '#22c55e',
        'shape': 'diamond',
        'border-color': '#22c55e',
        'border-opacity': 0.25,
        'width': 36,
        'height': 36,
      }
    },
    {
      selector: 'edge',
      style: {
        'width': 2,
        'line-color': '#94a3b8',
        'target-arrow-color': '#94a3b8',
        'target-arrow-shape': 'triangle',
        'curve-style': 'bezier',
        'opacity': 0.5,
        'label': 'data(label)',
        'font-size': '8px',
        'color': '#94a3b8',
        'text-rotation': 'autorotate',
        'text-margin-y': -8,
      }
    },
    {
      selector: 'node:active',
      style: {
        'overlay-opacity': 0.1,
        'overlay-color': '#3b82f6',
      }
    },
    {
      selector: 'node:selected',
      style: {
        'border-width': 4,
        'border-color': '#facc15',
      }
    }
  ];

  if (elements.length === 0) return <div className="h-full flex items-center justify-center text-muted-foreground">No graph data to display.</div>;

  return (
    <div className="w-full h-full bg-background/50 rounded-xl border border-border overflow-hidden relative">
      <CytoscapeComponent
        elements={elements}
        style={{ width: '100%', height: '100%' }}
        layout={layout}
        stylesheet={style}
        wheelSensitivity={0.1}
        cy={handleCy}
      />
    </div>
  );
}
