import { useState, useRef, useEffect } from "react";

const EXAMPLE_QUESTIONS = [
  "How many sales orders are there?",
  "Which products appear in the most billing documents?",
  "Show me all customers and their total order amounts",
  "Which billing documents are cancelled?",
  "Trace the flow of sales order 80738109",
  "Which sales orders have deliveries but no billing documents?",
  "What is the total payment amount received?",
  "List all customers with their addresses",
];

export default function ChatPanel({ selectedNode, onHighlight }) {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hello! I can answer questions about your SAP Order-to-Cash data. Ask me about sales orders, deliveries, billing documents, payments, customers, or products.",
      sql: null,
      isOffTopic: false,
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [expandedSql, setExpandedSql] = useState(null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (selectedNode) {
      const suggestion = `Tell me about ${selectedNode.type} ${selectedNode.entity_id}`;
      setInput(suggestion);
      inputRef.current?.focus();
    }
  }, [selectedNode]);

  const sendMessage = async (messageText) => {
    const text = messageText || input.trim();
    if (!text || loading) return;

    setInput("");
    setLoading(true);

    const userMessage = { role: "user", content: text };
    setMessages((prev) => [...prev, userMessage]);

    try {
      const history = messages
        .slice(-6)
        .map((m) => ({ role: m.role, content: m.content }));

      const response = await fetch("http://localhost:8000/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          conversation_history: history,
        }),
      });

      const data = await response.json();

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.answer,
          sql: data.sql,
          isOffTopic: data.is_off_topic,
          resultCount: data.result_count,
          highlightedNodes: data.nodes_to_highlight,
        },
      ]);

      if (data.nodes_to_highlight && data.nodes_to_highlight.length > 0) {
        onHighlight(data.nodes_to_highlight);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "Connection error — make sure the backend server is running on port 8000.",
          sql: null,
          isOffTopic: false,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <span style={styles.headerIcon}>💬</span>
        <span style={styles.headerTitle}>Query Assistant</span>
        <span style={styles.headerBadge}>AI Powered</span>
      </div>

      <div style={styles.messages}>
        {messages.map((msg, idx) => (
          <div key={idx} style={styles.messageWrapper}>
            <div
              style={{
                ...styles.bubble,
                ...(msg.role === "user" ? styles.userBubble : styles.botBubble),
                ...(msg.isOffTopic ? styles.offTopicBubble : {}),
              }}
            >
              <div style={styles.roleLabel}>
                {msg.role === "user" ? "You" : "Assistant"}
                {msg.isOffTopic && (
                  <span style={styles.offTopicTag}>Out of scope</span>
                )}
              </div>

              <div style={styles.messageText}>{msg.content}</div>

              {msg.resultCount !== undefined && msg.resultCount > 0 && (
                <div style={styles.resultCount}>
                  {msg.resultCount} records found
                  {msg.highlightedNodes?.length > 0 &&
                    ` · ${msg.highlightedNodes.length} nodes highlighted`}
                </div>
              )}

              {msg.sql && (
                <div style={styles.sqlSection}>
                  <button
                    style={styles.sqlToggle}
                    onClick={() =>
                      setExpandedSql(expandedSql === idx ? null : idx)
                    }
                  >
                    {expandedSql === idx ? "▼" : "▶"} View SQL query
                  </button>
                  {expandedSql === idx && (
                    <pre style={styles.sqlCode}>{msg.sql}</pre>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div style={styles.messageWrapper}>
            <div style={{ ...styles.bubble, ...styles.botBubble }}>
              <div style={styles.roleLabel}>Assistant</div>
              <div style={styles.typingDots}>
                <span style={{ ...styles.dot, animationDelay: "0ms" }} />
                <span style={{ ...styles.dot, animationDelay: "150ms" }} />
                <span style={{ ...styles.dot, animationDelay: "300ms" }} />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {messages.length === 1 && (
        <div style={styles.examples}>
          <div style={styles.examplesTitle}>Try asking:</div>
          <div style={styles.examplesList}>
            {EXAMPLE_QUESTIONS.map((q) => (
              <button
                key={q}
                style={styles.exampleBtn}
                onClick={() => sendMessage(q)}
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      <div style={styles.inputArea}>
        <textarea
          ref={inputRef}
          style={styles.textarea}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about orders, deliveries, billing, payments..."
          rows={2}
          disabled={loading}
        />
        <button
          style={{
            ...styles.sendBtn,
            opacity: loading || !input.trim() ? 0.5 : 1,
          }}
          onClick={() => sendMessage()}
          disabled={loading || !input.trim()}
        >
          {loading ? "..." : "Send"}
        </button>
      </div>

      <div style={styles.footer}>
        Press Enter to send · Shift+Enter for new line
      </div>

      <style>{`
        @keyframes bounce {
          0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
          40% { transform: translateY(-6px); opacity: 1; }
        }
      `}</style>
    </div>
  );
}

const styles = {
  container: {
    display: "flex",
    flexDirection: "column",
    height: "100%",
    background: "#161b27",
  },
  header: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    padding: "12px 16px",
    borderBottom: "1px solid #2a3044",
    flexShrink: 0,
  },
  headerIcon: { fontSize: "16px" },
  headerTitle: {
    fontSize: "13px",
    fontWeight: "600",
    color: "#e8e8e8",
    flex: 1,
  },
  headerBadge: {
    fontSize: "10px",
    background: "#1e3a5f",
    color: "#4f8ef7",
    border: "1px solid #2a4a7f",
    padding: "2px 8px",
    borderRadius: "10px",
  },
  messages: {
    flex: 1,
    overflowY: "auto",
    padding: "12px",
    display: "flex",
    flexDirection: "column",
    gap: "10px",
  },
  messageWrapper: { display: "flex", flexDirection: "column" },
  bubble: {
    padding: "10px 12px",
    borderRadius: "10px",
    maxWidth: "100%",
    fontSize: "13px",
    lineHeight: "1.5",
  },
  userBubble: {
    background: "#1e2d4a",
    border: "1px solid #2a3d6a",
    alignSelf: "flex-end",
    maxWidth: "85%",
  },
  botBubble: {
    background: "#1a1f2e",
    border: "1px solid #252d40",
    alignSelf: "flex-start",
    width: "100%",
  },
  offTopicBubble: {
    background: "#2a1a1a",
    border: "1px solid #4a2a2a",
  },
  roleLabel: {
    fontSize: "10px",
    fontWeight: "600",
    color: "#4f8ef7",
    marginBottom: "5px",
    display: "flex",
    alignItems: "center",
    gap: "6px",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
  },
  offTopicTag: {
    background: "#4a2a2a",
    color: "#f87171",
    padding: "1px 6px",
    borderRadius: "4px",
    fontSize: "9px",
  },
  messageText: { color: "#d0d8e8", whiteSpace: "pre-wrap" },
  resultCount: {
    marginTop: "6px",
    fontSize: "10px",
    color: "#10b981",
    fontWeight: "500",
  },
  sqlSection: { marginTop: "8px" },
  sqlToggle: {
    background: "none",
    border: "1px solid #2a3a5c",
    color: "#6b7a99",
    fontSize: "10px",
    padding: "3px 8px",
    borderRadius: "4px",
    cursor: "pointer",
    fontFamily: "inherit",
  },
  sqlCode: {
    marginTop: "6px",
    background: "#0d1117",
    border: "1px solid #2a3044",
    borderRadius: "6px",
    padding: "8px 10px",
    fontSize: "10px",
    color: "#7dd3fc",
    overflowX: "auto",
    whiteSpace: "pre",
    fontFamily: "'Courier New', monospace",
  },
  typingDots: {
    display: "flex",
    gap: "4px",
    alignItems: "center",
    padding: "4px 0",
  },
  dot: {
    width: "6px",
    height: "6px",
    background: "#4f8ef7",
    borderRadius: "50%",
    display: "inline-block",
    animation: "bounce 1.2s ease-in-out infinite",
  },
  examples: {
    padding: "10px 12px",
    borderTop: "1px solid #2a3044",
    flexShrink: 0,
  },
  examplesTitle: {
    fontSize: "10px",
    color: "#4a5568",
    marginBottom: "6px",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
  },
  examplesList: {
    display: "flex",
    flexDirection: "column",
    gap: "4px",
    maxHeight: "160px",
    overflowY: "auto",
  },
  exampleBtn: {
    background: "#1a1f2e",
    border: "1px solid #252d40",
    borderRadius: "6px",
    color: "#8899b8",
    fontSize: "11px",
    padding: "6px 10px",
    textAlign: "left",
    cursor: "pointer",
    fontFamily: "inherit",
  },
  inputArea: {
    display: "flex",
    gap: "8px",
    padding: "10px 12px",
    borderTop: "1px solid #2a3044",
    flexShrink: 0,
    alignItems: "flex-end",
  },
  textarea: {
    flex: 1,
    background: "#0f1117",
    border: "1px solid #2a3044",
    borderRadius: "8px",
    color: "#e8e8e8",
    fontSize: "13px",
    padding: "8px 12px",
    resize: "none",
    fontFamily: "inherit",
    lineHeight: "1.4",
    outline: "none",
  },
  sendBtn: {
    background: "#4f8ef7",
    border: "none",
    borderRadius: "8px",
    color: "#ffffff",
    fontSize: "13px",
    fontWeight: "600",
    padding: "8px 16px",
    cursor: "pointer",
    flexShrink: 0,
    fontFamily: "inherit",
  },
  footer: {
    padding: "6px 12px",
    fontSize: "10px",
    color: "#2a3044",
    textAlign: "center",
    flexShrink: 0,
  },
};