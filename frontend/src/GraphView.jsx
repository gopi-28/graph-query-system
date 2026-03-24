import { useEffect, useRef, useState, useCallback } from "react";
import CytoscapeComponent from "react-cytoscapejs";
import cytoscape from "cytoscape";

const NODE_COLORS = {
  Customer:        { bg: "#3b82f6", border: "#1d4ed8", text: "#ffffff" },
  SalesOrder:      { bg: "#8b5cf6", border: "#6d28d9", text: "#ffffff" },
  SalesOrderItem:  { bg: "#a78bfa", border: "#7c3aed", text: "#ffffff" },
  BillingDocument: { bg: "#f97316", border: "#c2410c", text: "#ffffff" },
  Delivery:        { bg: "#f59e0b", border: "#b45309", text: "#ffffff" },
  Payment:         { bg: "#10b981", border: "#047857", text: "#ffffff" },
  JournalEntry:    { bg: "#06b6d4", border: "#0e7490", text: "#ffffff" },
  Product:         { bg: "#ec4899", border: "#be185d", text: "#ffffff" },
  default:         { bg: "#64748b", border: "#475569", text: "#ffffff" },
};

const STYLESHEET = [
  {
    selector: "node",
    style: {
      label: "data(label)",
      "text-valign": "center",
      "text-halign": "center",
      "font-size": "9px",
      "font-family": "DM Sans, Segoe UI, sans-serif",
      "font-weight": "500",
      color: "#ffffff",
      "text-wrap": "wrap",
      "text-max-width": "80px",
      width: "60px",
      height: "60px",
      "border-width": "2px",
      "transition-property": "background-color, border-color, width, height",
      "transition-duration": "0.2s",
    },
  },
  ...Object.entries(NODE_COLORS).map(([type, colors]) => ({
    selector: type === "default" ? "node" : `node[type="${type}"]`,
    style: {
      "background-color": colors.bg,
      "border-color": colors.border,
    },
  })),
  {
    selector: "node.highlighted",
    style: {
      "background-color": "#fbbf24",
      "border-color": "#f59e0b",
      "border-width": "4px",
      width: "75px",
      height: "75px",
      "font-size": "10px",
    },
  },
  {
    selector: "node:selected",
    style: {
      "border-color": "#ffffff",
      "border-width": "3px",
      width: "70px",
      height: "70px",
    },
  },
  {
    selector: "edge",
    style: {
      width: 1.5,
      "line-color": "#2a3a5c",
      "target-arrow-color": "#2a3a5c",
      "target-arrow-shape": "triangle",
      "curve-style": "bezier",
      label: "data(label)",
      "font-size": "7px",
      color: "#5a6a8a",
      "text-background-color": "#0f1117",
      "text-background-opacity": 0.8,
      "text-background-padding": "2px",
    },
  },
  {
    selector: "edge.highlighted",
    style: {
      "line-color": "#4f8ef7",
      "target-arrow-color": "#4f8ef7",
      width: 2.5,
    },
  },
];

export default function GraphView({ highlightedNodes, onNodeSelect }) {
  const cyRef = useRef(null);
  const [elements, setElements] = useState([]);
  const [selectedNodeData, setSelectedNodeData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const expandedNodes = useRef(new Set());

  useEffect(() => {
    setLoading(true);
    fetch("http://localhost:8000/api/graph")
      .then((r) => r.json())
      .then((data) => {
        const nodes = data.nodes.map((n) => ({ data: n.data }));
        const edges = data.edges.map((e) => ({ data: e.data }));
        setElements([...nodes, ...edges]);
        setLoading(false);
      })
      .catch(() => {
        setError("Could not connect to backend. Is the server running?");
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    if (!cyRef.current) return;
    const cy = cyRef.current;
    cy.nodes().removeClass("highlighted");
    cy.edges().removeClass("highlighted");
    if (highlightedNodes && highlightedNodes.length > 0) {
      highlightedNodes.forEach((nodeId) => {
        const node = cy.getElementById(nodeId);
        if (node) {
          node.addClass("highlighted");
          node.connectedEdges().addClass("highlighted");
        }
      });
      const firstNode = cy.getElementById(highlightedNodes[0]);
      if (firstNode && firstNode.length > 0) {
        cy.animate({ fit: { eles: firstNode, padding: 100 } }, { duration: 500 });
      }
    }
  }, [highlightedNodes]);

  const handleNodeClick = useCallback((event) => {
    const node = event.target;
    const nodeId = node.id();
    const nodeData = node.data();
    setSelectedNodeData(nodeData);
    onNodeSelect(nodeData);

    if (!expandedNodes.current.has(nodeId)) {
      expandedNodes.current.add(nodeId);
      fetch(`http://localhost:8000/api/graph/expand/${encodeURIComponent(nodeId)}`)
        .then((r) => r.json())
        .then((data) => {
          if (!cyRef.current) return;
          const cy = cyRef.current;
          const newElements = [];
          data.nodes.forEach((n) => {
            if (!cy.getElementById(n.data.id).length) {
              newElements.push({ data: n.data });
            }
          });
          data.edges.forEach((e) => {
            if (!cy.getElementById(e.data.id).length) {
              newElements.push({ data: e.data });
            }
          });
          if (newElements.length > 0) {
            cy.add(newElements);
            cy.layout({
              name: "cose",
              animate: true,
              animationDuration: 500,
              randomize: false,
              fit: false,
            }).run();
          }
        })
        .catch(() => {});
    }
  }, [onNodeSelect]);

  const handleCyReady = useCallback((cy) => {
    cyRef.current = cy;
    cy.on("tap", "node", handleNodeClick);
    cy.on("tap", (e) => {
      if (e.target === cy) {
        setSelectedNodeData(null);
        onNodeSelect(null);
      }
    });
  }, [handleNodeClick, onNodeSelect]);

  if (loading) {
    return (
      <div style={styles.centered}>
        <div style={styles.spinner} />
        <div style={styles.loadingText}>Loading graph...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={styles.centered}>
        <div style={styles.errorText}>{error}</div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <CytoscapeComponent
        elements={elements}
        stylesheet={STYLESHEET}
        layout={{ name: "cose", animate: true, animationDuration: 800 }}
        style={{ width: "100%", height: "100%" }}
        cy={handleCyReady}
      />

      <div style={styles.legend}>
        {Object.entries(NODE_COLORS)
          .filter(([type]) => type !== "default")
          .map(([type, colors]) => (
            <div key={type} style={styles.legendItem}>
              <div style={{ ...styles.legendDot, background: colors.bg }} />
              <span style={styles.legendLabel}>{type}</span>
            </div>
          ))}
      </div>

      {selectedNodeData && (
        <div style={styles.infoPanel}>
          <div style={styles.infoPanelHeader}>
            <div
              style={{
                ...styles.infoTypeTag,
                background: NODE_COLORS[selectedNodeData.type]?.bg || "#64748b",
              }}
            >
              {selectedNodeData.type}
            </div>
            <button
              style={styles.closeBtn}
              onClick={() => setSelectedNodeData(null)}
            >
              ✕
            </button>
          </div>
          <div style={styles.infoPanelTitle}>{selectedNodeData.label}</div>
          <div style={styles.infoFields}>
            {Object.entries(selectedNodeData)
              .filter(([k]) => !["id", "label", "type"].includes(k))
              .filter(([, v]) => v && v !== "None" && v !== "null" && v !== "")
              .map(([key, value]) => (
                <div key={key} style={styles.infoRow}>
                  <span style={styles.infoKey}>
                    {key.replace(/([A-Z])/g, " $1").toLowerCase()}
                  </span>
                  <span style={styles.infoValue}>{String(value)}</span>
                </div>
              ))}
          </div>
          <div style={styles.infoPanelHint}>
            Click node again to expand neighbors
          </div>
        </div>
      )}

      <div style={styles.tip}>
        Click any node to expand • Drag to pan • Scroll to zoom
      </div>
    </div>
  );
}

const styles = {
  container: {
    width: "100%",
    height: "100%",
    position: "relative",
    background: "#0f1117",
  },
  centered: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    height: "100%",
    gap: "16px",
  },
  spinner: {
    width: "36px",
    height: "36px",
    border: "3px solid #2a3044",
    borderTop: "3px solid #4f8ef7",
    borderRadius: "50%",
    animation: "spin 1s linear infinite",
  },
  loadingText: { color: "#6b7a99", fontSize: "14px" },
  errorText: {
    color: "#f87171",
    fontSize: "14px",
    textAlign: "center",
    padding: "24px",
  },
  legend: {
    position: "absolute",
    bottom: "40px",
    left: "16px",
    background: "rgba(22, 27, 39, 0.92)",
    border: "1px solid #2a3044",
    borderRadius: "10px",
    padding: "10px 14px",
    display: "flex",
    flexDirection: "column",
    gap: "6px",
  },
  legendItem: { display: "flex", alignItems: "center", gap: "8px" },
  legendDot: { width: "10px", height: "10px", borderRadius: "50%", flexShrink: 0 },
  legendLabel: { fontSize: "11px", color: "#9aa5be" },
  infoPanel: {
    position: "absolute",
    top: "16px",
    left: "16px",
    width: "260px",
    background: "rgba(22, 27, 39, 0.97)",
    border: "1px solid #2a3044",
    borderRadius: "12px",
    padding: "14px",
    maxHeight: "420px",
    overflowY: "auto",
  },
  infoPanelHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "8px",
  },
  infoTypeTag: {
    fontSize: "10px",
    fontWeight: "600",
    color: "#fff",
    padding: "2px 8px",
    borderRadius: "4px",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
  },
  closeBtn: {
    background: "none",
    border: "none",
    color: "#6b7a99",
    cursor: "pointer",
    fontSize: "13px",
    padding: "2px 6px",
  },
  infoPanelTitle: {
    fontSize: "13px",
    fontWeight: "600",
    color: "#e8e8e8",
    marginBottom: "10px",
    lineHeight: 1.3,
  },
  infoFields: { display: "flex", flexDirection: "column", gap: "5px" },
  infoRow: { display: "flex", justifyContent: "space-between", gap: "8px", fontSize: "11px" },
  infoKey: { color: "#6b7a99", flexShrink: 0, textTransform: "capitalize" },
  infoValue: { color: "#c8d0e0", textAlign: "right", wordBreak: "break-all" },
  infoPanelHint: { marginTop: "10px", fontSize: "10px", color: "#4a5568", fontStyle: "italic" },
  tip: {
    position: "absolute",
    bottom: "16px",
    left: "50%",
    transform: "translateX(-50%)",
    fontSize: "11px",
    color: "#3a4560",
    background: "rgba(15,17,23,0.8)",
    padding: "4px 12px",
    borderRadius: "20px",
    whiteSpace: "nowrap",
  },
};