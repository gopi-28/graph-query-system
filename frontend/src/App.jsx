import { useState, useEffect } from "react";
import GraphView from "./GraphView";
import ChatPanel from "./ChatPanel";

export default function App() {
  const [selectedNode, setSelectedNode] = useState(null);
  const [highlightedNodes, setHighlightedNodes] = useState([]);
  const [stats, setStats] = useState(null);

  useEffect(() => {
    fetch("http://localhost:8000/api/stats")
      .then((r) => r.json())
      .then((data) => setStats(data))
      .catch(() => {});
  }, []);

  return (
    <div style={styles.root}>
      <header style={styles.header}>
        <div style={styles.headerLeft}>
          <div style={styles.logo}>⬡</div>
          <div>
            <div style={styles.title}>SAP O2C Graph Explorer</div>
            <div style={styles.subtitle}>Order-to-Cash Intelligence System</div>
          </div>
        </div>
        {stats && (
          <div style={styles.statsRow}>
            {[
              { label: "Nodes", value: stats.total_nodes },
              { label: "Edges", value: stats.total_edges },
              { label: "Customers", value: stats.node_types?.Customer || 0 },
              { label: "Orders", value: stats.node_types?.SalesOrder || 0 },
              { label: "Invoices", value: stats.node_types?.BillingDocument || 0 },
            ].map((s) => (
              <div key={s.label} style={styles.statBadge}>
                <span style={styles.statValue}>{s.value}</span>
                <span style={styles.statLabel}>{s.label}</span>
              </div>
            ))}
          </div>
        )}
      </header>

      <div style={styles.main}>
        <div style={styles.graphPanel}>
          <GraphView
            highlightedNodes={highlightedNodes}
            onNodeSelect={setSelectedNode}
          />
        </div>
        <div style={styles.chatPanel}>
          <ChatPanel
            selectedNode={selectedNode}
            onHighlight={setHighlightedNodes}
          />
        </div>
      </div>
    </div>
  );
}

const styles = {
  root: {
    display: "flex",
    flexDirection: "column",
    height: "100vh",
    width: "100vw",
    background: "#0f1117",
    color: "#e8e8e8",
    fontFamily: "'DM Sans', 'Segoe UI', sans-serif",
    overflow: "hidden",
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "0 24px",
    height: "56px",
    background: "#161b27",
    borderBottom: "1px solid #2a3044",
    flexShrink: 0,
  },
  headerLeft: {
    display: "flex",
    alignItems: "center",
    gap: "12px",
  },
  logo: {
    fontSize: "24px",
    color: "#4f8ef7",
    lineHeight: 1,
  },
  title: {
    fontSize: "15px",
    fontWeight: "600",
    color: "#f0f0f0",
    letterSpacing: "0.01em",
  },
  subtitle: {
    fontSize: "11px",
    color: "#6b7a99",
    marginTop: "1px",
  },
  statsRow: {
    display: "flex",
    gap: "8px",
  },
  statBadge: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    background: "#1e2537",
    border: "1px solid #2a3044",
    borderRadius: "8px",
    padding: "4px 12px",
    minWidth: "56px",
  },
  statValue: {
    fontSize: "14px",
    fontWeight: "700",
    color: "#4f8ef7",
  },
  statLabel: {
    fontSize: "9px",
    color: "#6b7a99",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
  },
  main: {
    display: "flex",
    flex: 1,
    overflow: "hidden",
  },
  graphPanel: {
    flex: 1,
    overflow: "hidden",
    borderRight: "1px solid #2a3044",
  },
  chatPanel: {
    width: "400px",
    flexShrink: 0,
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
  },
};