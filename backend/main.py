"""
main.py — FastAPI Server
========================
PURPOSE:
    This is the main entry point of the backend.
    It creates a web server with API endpoints that the
    React frontend will call.

WHY FastAPI?
    - Very fast and easy to use
    - Automatic API documentation at /docs
    - Built-in support for CORS (needed for React frontend)
    - Modern Python with type hints

API ENDPOINTS:
    GET  /                          → Health check
    GET  /api/graph                 → Returns graph data for visualization
    GET  /api/graph/expand/{id}     → Returns neighbors of a node
    GET  /api/graph/node/{id}       → Returns full node details
    POST /api/chat                  → Main chat endpoint (NL → SQL → Answer)
    GET  /api/schema                → Returns database schema (for debugging)

HOW TO RUN:
    uvicorn main:app --reload --port 8000

    Then open: http://localhost:8000/docs
    to see all API endpoints with auto-generated documentation.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import uvicorn

from db import get_schema_description
from graph import get_graph, graph_to_json, get_node_neighbors
try:
    from llm import chat
except Exception as e:
    print(f"ERROR importing llm: {e}")
    raise

# ─── CREATE FASTAPI APP ───────────────────────────────────────────────────────

app = FastAPI(
    title="SAP O2C Graph Query System",
    description="Graph-based data exploration and natural language querying for SAP Order-to-Cash data",
    version="1.0.0"
)

# ─── CORS MIDDLEWARE ──────────────────────────────────────────────────────────
# CORS = Cross-Origin Resource Sharing
# WHY: Your React frontend runs on http://localhost:5173
#      Your FastAPI backend runs on http://localhost:8000
#      Browsers block requests between different ports by default.
#      This middleware tells the browser "it's okay, allow these requests."

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your actual frontend URL
    allow_credentials=True,
    allow_methods=["*"],  # Allow GET, POST, etc.
    allow_headers=["*"],
)


# ─── REQUEST/RESPONSE MODELS ──────────────────────────────────────────────────
# Pydantic models define the shape of request and response data.
# FastAPI uses these for automatic validation and documentation.

class ChatRequest(BaseModel):
    """What the frontend sends when user types a message"""
    message: str
    conversation_history: Optional[List[dict]] = []  # for follow-up questions


class ChatResponse(BaseModel):
    """What we send back to the frontend"""
    answer: str
    sql: Optional[str] = None
    nodes_to_highlight: List[str] = []
    is_off_topic: bool = False
    result_count: Optional[int] = None


# ─── STARTUP EVENT ────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    """
    This runs ONCE when the server starts.
    We pre-build the graph so the first API call is fast.

    Without this, the first call to /api/graph would take a few
    seconds to build the graph. Pre-building avoids that delay.
    """
    print("Server starting — pre-building graph...")
    get_graph()  # builds and caches the graph
    print("Graph ready!")


# ─── ENDPOINTS ────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    """Health check — confirms the server is running"""
    return {
        "status": "running",
        "message": "SAP O2C Graph Query System",
        "docs": "/docs"
    }


@app.get("/api/graph")
def get_full_graph():
    """
    Returns the full graph as Cytoscape.js-compatible JSON.

    The frontend calls this on startup to draw the initial graph.
    We limit to 300 nodes to keep the browser responsive.

    Response format:
    {
        "nodes": [{"data": {"id": "...", "label": "...", "type": "..."}}],
        "edges": [{"data": {"source": "...", "target": "...", "label": "..."}}]
    }
    """
    try:
        data = graph_to_json(limit=300)
        return {
            "nodes": data["nodes"],
            "edges": data["edges"],
            "total_nodes": len(data["nodes"]),
            "total_edges": len(data["edges"])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/graph/expand/{node_id}")
def expand_node(node_id: str):
    """
    Returns a node and all its direct neighbors.

    Called when user clicks a node in the graph to "expand" it.

    Example: clicking "order_80001" returns:
        - the order node itself
        - its customer node
        - its delivery nodes
        - its billing document nodes
        - its order item nodes

    Args:
        node_id: the graph node ID (e.g. "order_80001")
    """
    try:
        data = get_node_neighbors(node_id)
        if not data["nodes"]:
            raise HTTPException(
                status_code=404,
                detail=f"Node '{node_id}' not found in graph"
            )
        return data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/graph/node/{node_id}")
def get_node_details(node_id: str):
    """
    Returns full metadata for a single node.

    Called when user clicks a node to see its details in the info panel.
    Shows all the fields from the database record.

    Args:
        node_id: the graph node ID (e.g. "billing_90504298")
    """
    G = get_graph()

    if not G.has_node(node_id):
        raise HTTPException(
            status_code=404,
            detail=f"Node '{node_id}' not found"
        )

    attrs = G.nodes[node_id]
    return {
        "id": node_id,
        "type": attrs.get("type"),
        "label": attrs.get("label"),
        "entity_id": attrs.get("entity_id"),
        "data": {k: str(v) for k, v in (attrs.get("data") or {}).items()}
    }


@app.post("/api/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    """
    Main chat endpoint — the core of the application.

    FLOW:
        1. Receive user's natural language question
        2. Pass to llm.py which:
            a. Checks guardrails
            b. Generates SQL
            c. Executes SQL
            d. Formats answer
        3. Return answer + SQL + nodes to highlight

    The frontend shows:
        - The natural language answer
        - The SQL query (in a collapsible section)
        - Highlights the relevant nodes in the graph

    Request body:
    {
        "message": "Which customers have the most orders?",
        "conversation_history": [...]  // optional, for follow-ups
    }
    """
    if not request.message or not request.message.strip():
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty"
        )

    try:
        result = chat(
            user_message=request.message.strip(),
            conversation_history=request.conversation_history or []
        )
        return ChatResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/schema")
def get_schema():
    """
    Returns the database schema as text.
    Useful for debugging — shows all tables and columns.
    Also used by the LLM in its system prompt.
    """
    try:
        schema = get_schema_description()
        return {"schema": schema}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
def get_stats():
    """
    Returns basic statistics about the graph.
    Shown in the frontend as an overview dashboard.
    """
    try:
        G = get_graph()
        from collections import Counter
        type_counts = Counter(
            attrs.get("type") for _, attrs in G.nodes(data=True)
        )
        edge_counts = Counter(
            attrs.get("label") for _, _, attrs in G.edges(data=True)
        )
        return {
            "total_nodes": G.number_of_nodes(),
            "total_edges": G.number_of_edges(),
            "node_types": dict(type_counts),
            "edge_types": dict(edge_counts)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── RUN DIRECTLY ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    """
    Run: python main.py
    OR:  uvicorn main:app --reload --port 8000

    --reload means the server restarts when you save changes
    This is great during development
    """
    uvicorn.run(
        "main:app",
        host="0.0.0.0",  # listen on all interfaces
        port=8000,
        reload=True  # auto-restart on file changes
    )
